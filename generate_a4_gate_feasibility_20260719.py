from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "outputs" / "a4_quick_screen_20260718" / "a4_quick_screen_report.json"
EQUIVALENCE = ROOT / "outputs" / "a4b_standard_tr_confirmation_20260719" / "preset_equivalence" / "preset_equivalence_report.json"
OUTPUT = ROOT / "outputs" / "a4_gate_feasibility_20260719"


def main() -> None:
    source = json.loads(INPUT.read_text(encoding="utf-8"))
    equivalence = json.loads(EQUIVALENCE.read_text(encoding="utf-8"))
    threshold = float(source["gates"]["tr_improvement_min_x"])
    rows = []
    for item in source["trajectories"]:
        baseline = float(item["baseline"]["t_g"])
        tr_value = float(item["tr"]["t_g"])
        maximum = 1.0 / baseline
        rows.append(
            {
                "trajectory": item["traj"],
                "baseline_target_global": baseline,
                "tr_target_global": tr_value,
                "observed_improvement_x": tr_value / baseline,
                "mathematical_maximum_improvement_x": maximum,
                "three_x_gate_feasible": maximum >= threshold,
                "original_verdict": item["verdict"],
                "global_peak_material": item["tr"]["npz"]["global_peak_material"],
                "global_peak_to_target_mm": item["tr"]["pressure"]["global_peak_to_target_distance_mm"],
                "skull_focus_ratio": item["skull_focus_ratio"],
            }
        )

    report = {
        "status": "gate_feasibility_audited",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_report": str(INPUT.relative_to(ROOT)),
        "identity": "target/global is bounded by 1, so improvement <= 1 / baseline_target_global",
        "relative_gate_threshold_x": threshold,
        "trajectories": rows,
        "n_mathematically_infeasible": sum(not row["three_x_gate_feasible"] for row in rows),
        "original_a4_verdict": source["a4_verdict"],
        "original_a4_verdict_preserved": True,
        "a4b_pressure_execution": "not_run_evidence_redundant",
        "a4b_numerically_equivalent": equivalence["numerically_equivalent"],
        "decision": (
            "Keep the original A4 hold. Do not rerun label-only A4b pressure. For future confirmatory protocols, "
            "use preregistered absolute localization and material-hotspot gates, and treat relative improvement as descriptive."
        ),
        "claim_boundary": "post hoc gate-design audit; no retroactive pass and no clinical or paper-grade transcranial claim",
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "a4_gate_feasibility.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# A4 Relative-Gate Feasibility Audit",
        "",
        f"- Status: `{report['status']}`",
        f"- Original A4 verdict: `{report['original_a4_verdict']}` (preserved)",
        f"- Mathematically infeasible trajectories: {report['n_mathematically_infeasible']}/{len(rows)}",
        f"- A4b pressure: `{report['a4b_pressure_execution']}`",
        "",
        "## Mathematical bound",
        "",
        "Because target/global cannot exceed 1, a trajectory with baseline ratio b has maximum possible relative improvement 1/b. A 3x gate is therefore impossible whenever b > 1/3.",
        "",
        "| Trajectory | Baseline t/g | TR t/g | Observed gain | Maximum gain | 3x feasible | Other decisive finding |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        other = f"peak={row['global_peak_material']}; distance={row['global_peak_to_target_mm']:.2f} mm"
        lines.append(
            f"| `{row['trajectory']}` | {row['baseline_target_global']:.4f} | {row['tr_target_global']:.4f} | "
            f"{row['observed_improvement_x']:.2f}x | {row['mathematical_maximum_improvement_x']:.2f}x | "
            f"{'yes' if row['three_x_gate_feasible'] else 'no'} | {other} |"
        )
    lines.extend(
        [
            "",
            "## Governance decision",
            "",
            "The original A4 hold remains unchanged. The audit is post hoc and cannot convert failed trajectories into preregistered passes. The fresh quick/standard fingerprint audit found zero numerical differences, so label-only pressure reruns are blocked as evidence-redundant.",
            "",
            "A future confirmatory protocol should preregister absolute target dominance, non-skull global-peak material, skull/focus ratio, and peak-to-target distance. Relative improvement may remain descriptive but should not be a universal pass gate across heterogeneous baselines.",
            "",
            "Claim boundary: post hoc gate-design audit only; no clinical, thermal, or paper-grade transcranial claim.",
        ]
    )
    (OUTPUT / "a4_gate_feasibility.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "infeasible": report["n_mathematically_infeasible"], "a4": report["original_a4_verdict"]}))


if __name__ == "__main__":
    main()
