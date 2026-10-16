"""A.4 adaptive quick screen report generator (2026-07-18 night session).

Reads the six arm outputs under outputs/a4_quick_screen_20260718/<traj>/{baseline,tr}
and applies the preregistered quick gates from
outputs/evidence_briefs/a4_quick_screen_tr_gated_trajectories/evidence_brief.md:

  per trajectory (all four must hold for pass):
    1. TR target/global peak ratio (t/g) >= 0.35
    2. TR global-peak material != skull (label != 2)
    3. TR skull-peak / target-window-peak <= 2.5
    4. TR t/g >= 3x the trajectory's own baseline t/g

  A.4 -> A.5 unlock: >= 2 of 3 trajectories pass.

Outputs:
  outputs/a4_quick_screen_20260718/a4_quick_screen_report.json / .md
  outputs/evidence_briefs/a4_quick_screen_tr_gated_trajectories/gap_feedback.json / .md

All conclusions are engineering quick-screen observations (single realization,
quick preset); no clinical or paper-grade claims.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
OUT_ROOT = PROJECT_ROOT / "outputs" / "a4_quick_screen_20260718"
BRIEF_DIR = PROJECT_ROOT / "outputs" / "evidence_briefs" / "a4_quick_screen_tr_gated_trajectories"

TRAJS = [
    "offset_y+00p0_z-20p0",
    "offset_y+17p5_z-02p5",
    "offset_y+17p5_z+10p0",
]

SKULL_LABEL = 2
MATERIAL_LABEL_NAMES = {0: "background (label 0)", 1: "soft_tissue (label 1)", 2: "skull (label 2)"}

GATE_TG_MIN = 0.35
GATE_SKULL_FOCUS_MAX = 2.5
GATE_IMPROVEMENT_MIN = 3.0
UNLOCK_MIN_PASS = 2


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def extract_pressure(summary: dict | None) -> dict:
    pressure = (summary or {}).get("pressure") or {}
    keys = [
        "target_window_peak_mpa",
        "target_window_peak_index_ijk",
        "global_peak_mpa",
        "global_peak_index_ijk",
        "global_peak_to_target_distance_mm",
        "target_to_global_peak_ratio",
        "metric_semantics_version",
    ]
    return {k: pressure.get(k) for k in keys}


def material_analysis(npz_path: Path, pressure_metrics: dict) -> dict:
    result = {
        "npz_path": rel(npz_path),
        "available": False,
        "skull_peak_mpa": None,
        "global_peak_material": None,
        "target_window_peak_material": None,
        "note": None,
    }
    if not npz_path.exists():
        result["note"] = "pressure_max_mpa.npz missing"
        return result
    data = np.load(npz_path)
    pressure = np.asarray(data["pressure_max_mpa"], dtype=np.float64)
    labels = np.asarray(data["labels"])
    result["available"] = True
    if pressure.shape != labels.shape or not np.any(labels == SKULL_LABEL):
        result["note"] = "labels missing or no skull voxels; skull analysis limited"
        return result
    result["skull_peak_mpa"] = float(np.max(pressure[labels == SKULL_LABEL]))

    def _material_at(idx) -> str | None:
        if idx is None:
            return None
        ijk = [int(v) for v in idx]
        if any(v < 0 or v >= labels.shape[d] for d, v in enumerate(ijk)):
            return None
        return MATERIAL_LABEL_NAMES.get(int(labels[tuple(ijk)]), f"unknown ({int(labels[tuple(ijk)])})")

    result["global_peak_material"] = _material_at(pressure_metrics.get("global_peak_index_ijk"))
    result["target_window_peak_material"] = _material_at(pressure_metrics.get("target_window_peak_index_ijk"))
    return result


def analyze_arm(traj: str, arm: str) -> dict:
    arm_dir = OUT_ROOT / traj / arm
    status = load_json(arm_dir / "runner_status.json")
    summary = load_json(arm_dir / "summary.json")
    pressure = extract_pressure(summary)
    npz = material_analysis(arm_dir / "pressure_max_mpa.npz", pressure)
    runner_ok = bool(status and status.get("status") == "kwave_ok")
    return {
        "arm": arm,
        "dir": rel(arm_dir),
        "runner_status": None if status is None else status.get("status"),
        "runner_ok": runner_ok,
        "summary_present": summary is not None,
        "pressure": pressure,
        "npz": npz,
        "t_g": pressure.get("target_to_global_peak_ratio"),
    }


def evaluate_trajectory(traj: str) -> dict:
    baseline = analyze_arm(traj, "baseline")
    tr = analyze_arm(traj, "tr")
    checks: dict[str, dict] = {}

    if not (baseline["runner_ok"] and tr["runner_ok"] and tr["t_g"] is not None and baseline["t_g"] is not None):
        missing = []
        if not baseline["runner_ok"]:
            missing.append(f"baseline runner_status={baseline['runner_status']}")
        if not tr["runner_ok"]:
            missing.append(f"tr runner_status={tr['runner_status']}")
        if tr["t_g"] is None:
            missing.append("TR t/g missing")
        if baseline["t_g"] is None:
            missing.append("baseline t/g missing")
        return {
            "traj": traj,
            "baseline": baseline,
            "tr": tr,
            "checks": checks,
            "verdict": "incomplete",
            "reason": "; ".join(missing) or "metrics incomplete",
        }

    tr_tg = float(tr["t_g"])
    base_tg = float(baseline["t_g"])
    skull_peak = tr["npz"].get("skull_peak_mpa")
    focus_peak = tr["pressure"].get("target_window_peak_mpa")
    skull_focus = (skull_peak / focus_peak) if (skull_peak is not None and focus_peak) else None
    improvement = (tr_tg / base_tg) if base_tg > 0 else None

    checks["tr_tg_min"] = {
        "value": tr_tg, "threshold": GATE_TG_MIN, "pass": tr_tg >= GATE_TG_MIN,
        "desc": "TR t/g >= 0.35",
    }
    gmat = tr["npz"].get("global_peak_material")
    checks["tr_global_peak_not_skull"] = {
        "value": gmat, "threshold": "!= skull (label 2)",
        "pass": (gmat is not None and not str(gmat).startswith("skull")),
        "desc": "TR global peak material != skull",
    }
    checks["tr_skull_focus_ratio"] = {
        "value": skull_focus, "threshold": GATE_SKULL_FOCUS_MAX,
        "pass": (skull_focus is not None and skull_focus <= GATE_SKULL_FOCUS_MAX),
        "desc": "TR skull/focus <= 2.5",
    }
    checks["tr_improvement_over_baseline"] = {
        "value": improvement, "threshold": GATE_IMPROVEMENT_MIN,
        "pass": (improvement is not None and improvement >= GATE_IMPROVEMENT_MIN),
        "desc": "TR t/g >= 3x own baseline",
    }
    verdict = "pass" if all(c["pass"] for c in checks.values()) else "fail"
    failed = [c["desc"] for c in checks.values() if not c["pass"]]
    return {
        "traj": traj,
        "baseline": baseline,
        "tr": tr,
        "checks": checks,
        "skull_focus_ratio": skull_focus,
        "improvement_x": improvement,
        "verdict": verdict,
        "reason": "all four quick gates hold" if verdict == "pass" else "failed: " + "; ".join(failed),
    }


def fmt(v, nd=4):
    return "—" if v is None else f"{v:.{nd}f}"


def main() -> None:
    trajectories = [evaluate_trajectory(t) for t in TRAJS]
    n_pass = sum(1 for t in trajectories if t["verdict"] == "pass")
    n_incomplete = sum(1 for t in trajectories if t["verdict"] == "incomplete")
    a5_unlocked = n_pass >= UNLOCK_MIN_PASS

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "protocol": rel(BRIEF_DIR / "evidence_brief.md"),
        "claim_level": "engineering quick-screen observation (single realization, quick preset); no clinical or paper-grade claims",
        "gates": {
            "tr_tg_min": GATE_TG_MIN,
            "tr_global_peak_not_skull": True,
            "tr_skull_focus_max": GATE_SKULL_FOCUS_MAX,
            "tr_improvement_min_x": GATE_IMPROVEMENT_MIN,
            "unlock_min_pass": UNLOCK_MIN_PASS,
        },
        "trajectories": trajectories,
        "n_pass": n_pass,
        "n_incomplete": n_incomplete,
        "a4_verdict": "unlock_a5" if a5_unlocked else "hold",
        "a4_verdict_reason": (
            f"{n_pass}/3 trajectories passed all four quick gates (need >= {UNLOCK_MIN_PASS})."
            + (f" {n_incomplete} trajectory(ies) incomplete (runner failure/memory)." if n_incomplete else "")
        ),
    }
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "a4_quick_screen_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# A.4 Adaptive Quick Screen Report (2026-07-18)",
        "",
        f"- Generated: {report['generated_utc']}",
        f"- Protocol: `{report['protocol']}`",
        f"- Claim level: {report['claim_level']}",
        "",
        f"## Verdict: **{report['a4_verdict']}** — {report['a4_verdict_reason']}",
        "",
        "| Trajectory | baseline t/g | TR t/g | TR improvement | TR skull/focus | TR global-peak material | TR peak-target dist (mm) | gates | verdict |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for t in trajectories:
        b, tr_ = t["baseline"], t["tr"]
        n_gates_pass = sum(1 for c in t.get("checks", {}).values() if c["pass"])
        lines.append(
            f"| {t['traj']} | {fmt(b['t_g'])} | {fmt(tr_['t_g'])} | {fmt(t.get('improvement_x'), 2)}x "
            f"| {fmt(t.get('skull_focus_ratio'), 2)} | {tr_['npz'].get('global_peak_material') or '—'} "
            f"| {fmt(tr_['pressure'].get('global_peak_to_target_distance_mm'), 2)} | {n_gates_pass}/4 | **{t['verdict']}** |"
        )
    lines += [
        "",
        "## Gate definitions (preregistered)",
        "",
        f"1. TR t/g >= {GATE_TG_MIN} (TR reference bound established at 079 (+5,0): 0.364)",
        f"2. TR global peak material != skull (label 2, via pressure_max_mpa.npz labels)",
        f"3. TR skull-peak / target-window-peak <= {GATE_SKULL_FOCUS_MAX} ((+5,0) bound: 2.53)",
        f"4. TR t/g >= {GATE_IMPROVEMENT_MIN}x the trajectory's own baseline t/g",
        "",
        "## Notes",
        "",
        "- Baseline arm ran the low-memory point-waveform architecture (online extrema + target point waveform); TR refocus recorded p_max/p_min only (see brief 'execution amendments'). All gate metrics derive from pressure_max_mpa.npz + labels and are architecture-invariant.",
        "- Cross-arm absolute MPa comparison is not made (TR normalization caveat, A.3 discipline); only scale-invariant ratios are gated.",
        "- Comparison against the (+5,0) TR bound (standard preset) is context only; preset difference recorded as a limitation.",
    ]
    if n_incomplete:
        lines.append(f"- {n_incomplete} trajectory(ies) incomplete due to runner failure (system memory pressure during the concurrent batch, dx0.375 prioritized); failed arms are rerun sequentially and this report regenerated.")
    (OUT_ROOT / "a4_quick_screen_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    gap = {
        "generated_utc": report["generated_utc"],
        "brief": rel(BRIEF_DIR / "evidence_brief.md"),
        "report": rel(OUT_ROOT / "a4_quick_screen_report.json"),
        "a4_verdict": report["a4_verdict"],
        "n_pass": n_pass,
        "n_incomplete": n_incomplete,
        "deviations": [
            "baseline arm executed via low-memory point-waveform script (original script OOM at 5.95 GiB full-series allocation); TR refocus target waveform disabled (same memory bound). Gate metrics unaffected (NPZ + labels based).",
            "23:39 system-level memory exhaustion killed one TR calibrate mid-run; failed arms rerun sequentially after the concurrent batch drains.",
        ],
        "per_trajectory": [
            {
                "traj": t["traj"], "verdict": t["verdict"], "reason": t["reason"],
                "baseline_tg": t["baseline"]["t_g"], "tr_tg": t["tr"]["t_g"],
                "skull_focus_ratio": t.get("skull_focus_ratio"), "improvement_x": t.get("improvement_x"),
            }
            for t in trajectories
        ],
        "next_actions": (
            ["A.5 expensive-grid stage is UNLOCKED for the passing trajectories (>=2/3 quick-gate pass)."]
            if a5_unlocked else
            ["A.5 remains HELD: fewer than 2/3 trajectories passed the quick gates."]
        ),
    }
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    (BRIEF_DIR / "gap_feedback.json").write_text(json.dumps(gap, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        f"# Gap Feedback — A.4 quick screen ({report['generated_utc']})",
        "",
        f"- Verdict: **{report['a4_verdict']}** ({report['a4_verdict_reason']})",
        f"- Report: `{rel(OUT_ROOT / 'a4_quick_screen_report.md')}`",
        "",
        "## Per-trajectory",
        "",
    ]
    for t in trajectories:
        md.append(f"- `{t['traj']}`: **{t['verdict']}** — {t['reason']} "
                  f"(baseline t/g {fmt(t['baseline']['t_g'])}, TR t/g {fmt(t['tr']['t_g'])}, "
                  f"skull/focus {fmt(t.get('skull_focus_ratio'), 2)}, improvement {fmt(t.get('improvement_x'), 2)}x)")
    md += ["", "## Deviations", ""]
    md += [f"- {d}" for d in gap["deviations"]]
    md += ["", "## Next actions", ""]
    md += [f"- {a}" for a in gap["next_actions"]]
    (BRIEF_DIR / "gap_feedback.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({"a4_verdict": report["a4_verdict"], "n_pass": n_pass, "n_incomplete": n_incomplete}))


if __name__ == "__main__":
    main()
