from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from generate_a4_quick_screen_report_20260718 import extract_pressure, load_json, material_analysis


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719"
BRIEF = ROOT / "outputs" / "evidence_briefs" / "a5_heldout_tr_confirmation"
TRAJECTORIES = ["offset_y-10p0_z-02p5", "offset_y+05p0_z+05p0", "offset_y+12p5_z-15p0"]


def analyze(trajectory: str) -> dict:
    arm = OUTPUT / trajectory / "tr"
    runner = load_json(arm / "runner_status.json")
    summary = load_json(arm / "summary.json")
    pressure = extract_pressure(summary)
    material = material_analysis(arm / "pressure_max_mpa.npz", pressure)
    npz_path = arm / "pressure_max_mpa.npz"
    finite = False
    if npz_path.exists():
        with np.load(npz_path) as data:
            finite = bool(np.all(np.isfinite(np.asarray(data["pressure_max_mpa"]))))
    source_counts = ((summary or {}).get("source") or {}).get("source_label_counts")
    source_points = ((summary or {}).get("source") or {}).get("source_points")
    source_safe = source_counts == {"0": source_points}
    runner_ok = bool(runner and runner.get("status") == "kwave_ok")
    tg = pressure.get("target_to_global_peak_ratio")
    target_peak = pressure.get("target_window_peak_mpa")
    skull_peak = material.get("skull_peak_mpa")
    skull_focus = skull_peak / target_peak if skull_peak is not None and target_peak else None
    distance = pressure.get("global_peak_to_target_distance_mm")
    global_material = material.get("global_peak_material")
    checks = {
        "runner_and_finite": {"value": runner_ok and finite, "threshold": True, "pass": runner_ok and finite},
        "target_to_global": {"value": tg, "threshold": 0.90, "pass": tg is not None and tg >= 0.90},
        "global_peak_not_skull": {"value": global_material, "threshold": "not skull", "pass": global_material is not None and not global_material.startswith("skull")},
        "skull_to_focus": {"value": skull_focus, "threshold": 1.25, "pass": skull_focus is not None and skull_focus <= 1.25},
        "peak_to_target_mm": {"value": distance, "threshold": 10.0, "pass": distance is not None and distance <= 10.0},
        "source_background_only": {"value": source_counts, "threshold": {"0": source_points}, "pass": source_safe},
    }
    complete = runner_ok and summary is not None and material["available"]
    verdict = "pass" if complete and all(item["pass"] for item in checks.values()) else ("fail" if complete else "incomplete")
    return {
        "trajectory": trajectory,
        "runner_status": None if runner is None else runner.get("status"),
        "summary_present": summary is not None,
        "pressure": pressure,
        "material": material,
        "field_finite": finite,
        "source_label_counts": source_counts,
        "skull_focus_ratio": skull_focus,
        "checks": checks,
        "verdict": verdict,
    }


def fmt(value, digits=3) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def main() -> None:
    rows = [analyze(value) for value in TRAJECTORIES]
    n_pass = sum(row["verdict"] == "pass" for row in rows)
    n_incomplete = sum(row["verdict"] == "incomplete" for row in rows)
    verdict = "confirmatory_pass" if n_pass >= 2 else "confirmatory_hold"
    report = {
        "status": verdict,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol": "outputs/evidence_briefs/a5_heldout_tr_confirmation/evidence_brief.md",
        "registered_before_pressure": True,
        "trajectories": rows,
        "n_pass": n_pass,
        "n_incomplete": n_incomplete,
        "study_min_pass": 2,
        "a5_mapping_uncertainty_unlocked": verdict == "confirmatory_pass",
        "claim_level": "single_case_engineering_heldout_tr_confirmation",
        "blocked_claims": ["multi-subject generalization", "mapping robustness", "absolute pressure validity", "thermal or clinical safety", "transcranial efficacy"],
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "heldout_tr_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# A5 Held-Out TR Confirmation Report",
        "",
        f"- Verdict: `{verdict}` ({n_pass}/3 pass; {n_incomplete} incomplete)",
        "- Protocol registered before held-out pressure execution.",
        "- Claim level: single-case engineering held-out TR confirmation.",
        "",
        "| Trajectory | t/g | skull/focus | peak material | peak-target (mm) | gates | verdict |",
        "|---|---:|---:|---|---:|---:|---|",
    ]
    for row in rows:
        passed = sum(item["pass"] for item in row["checks"].values())
        lines.append(
            f"| `{row['trajectory']}` | {fmt(row['pressure'].get('target_to_global_peak_ratio'))} | {fmt(row['skull_focus_ratio'])} | "
            f"{row['material'].get('global_peak_material') or '-'} | {fmt(row['pressure'].get('global_peak_to_target_distance_mm'), 2)} | {passed}/6 | **{row['verdict']}** |"
        )
    lines.extend([
        "",
        "The original A4 hold remains unchanged. This is an independent held-out protocol with preregistered absolute endpoints.",
        "",
        "No absolute cross-method pressure comparison is made because TR replay is normalized. No thermal or clinical claim is supported.",
    ])
    (OUTPUT / "heldout_tr_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    gap = {
        "generated_at": report["generated_at"],
        "status": verdict,
        "n_pass": n_pass,
        "n_incomplete": n_incomplete,
        "deviations": [],
        "next": "mapping uncertainty packet may be designed" if verdict == "confirmatory_pass" else "A5 remains blocked; do not run mapping or thermal batches",
        "claim_boundary": report["claim_level"],
    }
    (BRIEF / "gap_feedback.json").write_text(json.dumps(gap, indent=2) + "\n", encoding="utf-8")
    (BRIEF / "gap_feedback.md").write_text(
        f"# Gap Feedback: A5 Held-Out TR Confirmation\n\n- Verdict: `{verdict}`\n- Passed: {n_pass}/3\n- Incomplete: {n_incomplete}\n- Deviations: none recorded by report generator.\n- Next: {gap['next']}\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": verdict, "n_pass": n_pass, "n_incomplete": n_incomplete}))


if __name__ == "__main__":
    main()
