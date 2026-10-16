from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "outputs" / "evidence_briefs" / "trajectory_geometry_reuse_gate_20260722" / "evidence_brief.json"
OUTPUT = ROOT / "outputs" / "trajectory_geometry_reuse_gate_20260722"


def by_key(rows: list[dict[str, Any]], key: str, value: str) -> dict[str, Any]:
    matches = [row for row in rows if row.get(key) == value]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {key}={value}, found {len(matches)}")
    return matches[0]


def fractional_reduction(reference: float, candidate: float) -> float:
    if reference <= 0:
        raise ValueError("reference must be positive")
    return 1.0 - float(candidate) / float(reference)


def source_background_only(label_counts: dict[str, int]) -> bool:
    return bool(label_counts) and all(str(label) == "0" for label in label_counts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reuse gate for existing Case 079 held-out trajectory fields.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    heldout = json.loads((ROOT / evidence["inputs"]["heldout_report"]).read_text(encoding="utf-8"))
    ranking = json.loads((ROOT / evidence["inputs"]["path_ranking"]).read_text(encoding="utf-8"))
    selection = json.loads((ROOT / evidence["inputs"]["trajectory_selection"]).read_text(encoding="utf-8"))

    reference_id = evidence["reference_trajectory"]
    candidate_id = evidence["candidate_trajectory"]
    reference = by_key(heldout["trajectories"], "trajectory", reference_id)
    candidate = by_key(heldout["trajectories"], "trajectory", candidate_id)
    reference_rank = by_key(ranking["records"], "trajectory", reference_id)
    candidate_rank = by_key(ranking["records"], "trajectory", candidate_id)
    candidate_geometry = by_key(selection["selected"], "candidate_id", candidate_id)
    gates = evidence["reuse_gates"]

    target_retention = candidate["pressure"]["target_window_peak_mpa"] / reference["pressure"]["target_window_peak_mpa"]
    skull_reduction = fractional_reduction(
        reference["material"]["skull_peak_mpa"], candidate["material"]["skull_peak_mpa"]
    )
    checks = {
        "same_heldout_protocol": bool(heldout["registered_before_pressure"]),
        "source_background_only": source_background_only(candidate["source_label_counts"]),
        "has_skull_crossing": bool(candidate_rank["hard_gate"]["has_skull_crossing"]),
        "no_post_skull_background_gap": bool(candidate_rank["hard_gate"]["no_post_skull_background_gap"]),
        "target_pressure_retention": target_retention >= gates["target_pressure_retention_vs_reference_min"],
        "skull_peak_reduction": skull_reduction >= gates["skull_peak_reduction_vs_reference_min"],
        "target_global_ratio_not_worse": (
            candidate["pressure"]["target_to_global_peak_ratio"]
            >= reference["pressure"]["target_to_global_peak_ratio"]
        ),
        "global_peak_to_target_distance": (
            candidate["pressure"]["global_peak_to_target_distance_mm"]
            <= gates["global_peak_to_target_distance_mm_max"]
        ),
        "observed_heldout_verdict": candidate["verdict"] == gates["observed_heldout_verdict"],
        "validated_acoustic_rank": candidate_rank["validated_rank"] == gates["validated_acoustic_rank"],
        "selection_geometry_matches": bool(
            candidate_geometry["background_only"]
            and candidate_geometry["entry_plan"]["has_skull_crossing"]
        ),
    }
    passed = all(checks.values())

    rows = []
    for trajectory in heldout["trajectories"]:
        ranked = by_key(ranking["records"], "trajectory", trajectory["trajectory"])
        rows.append({
            "trajectory": trajectory["trajectory"],
            "target_window_peak_mpa": trajectory["pressure"]["target_window_peak_mpa"],
            "global_peak_mpa": trajectory["pressure"]["global_peak_mpa"],
            "skull_peak_mpa": trajectory["material"]["skull_peak_mpa"],
            "target_to_global_peak_ratio": trajectory["pressure"]["target_to_global_peak_ratio"],
            "global_peak_to_target_distance_mm": trajectory["pressure"]["global_peak_to_target_distance_mm"],
            "source_background_only": source_background_only(trajectory["source_label_counts"]),
            "has_skull_crossing": ranked["hard_gate"]["has_skull_crossing"],
            "validated_acoustic_cost": ranked["validated_acoustic_cost"],
            "validated_rank": ranked["validated_rank"],
            "heldout_verdict": trajectory["verdict"],
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "existing_trajectory_reuse_gate_pass" if passed else "existing_trajectory_reuse_gate_fail",
        "reference_trajectory": reference_id,
        "candidate_trajectory": candidate_id,
        "target_pressure_retention_vs_reference": target_retention,
        "skull_peak_reduction_vs_reference": skull_reduction,
        "target_global_ratio_change": (
            candidate["pressure"]["target_to_global_peak_ratio"]
            - reference["pressure"]["target_to_global_peak_ratio"]
        ),
        "global_peak_distance_reduction_mm": (
            reference["pressure"]["global_peak_to_target_distance_mm"]
            - candidate["pressure"]["global_peak_to_target_distance_mm"]
        ),
        "checks": checks,
        "selected_trajectory": candidate_id if passed else None,
        "comparison": rows,
        "pressure_executed": False,
        "pressure_execution_authorized": False,
        "claim_boundary": evidence["claim_boundary"],
    }
    (args.output_dir / "reuse_gate.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with (args.output_dir / "trajectory_comparison.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    selected_packet = {
        "status": "selected_existing_fullwave_trajectory" if passed else "no_trajectory_selected",
        "trajectory": candidate_id if passed else None,
        "entry_plan": candidate_geometry["entry_plan"] if passed else None,
        "pressure_summary_path": (
            f"outputs/a5_heldout_tr_confirmation_20260719/{candidate_id}/tr/summary.json" if passed else None
        ),
        "pressure_field_path": candidate["material"]["npz_path"] if passed else None,
        "selection_evidence": "outputs/trajectory_geometry_reuse_gate_20260722/reuse_gate.json",
        "new_pressure_required": False,
        "claim_boundary": evidence["claim_boundary"],
    }
    (args.output_dir / "selected_trajectory.json").write_text(
        json.dumps(selected_packet, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Existing Trajectory/Geometry Reuse Gate",
        "",
        f"Status: **{report['status']}**",
        f"Selected: `{report['selected_trajectory']}`.",
        "",
        f"- Target pressure retention versus H1: `{target_retention:.4f}`.",
        f"- Skull-peak reduction versus H1: `{skull_reduction:.4f}`.",
        f"- Target/global ratio change: `{report['target_global_ratio_change']:+.4f}`.",
        f"- Global-peak distance reduction: `{report['global_peak_distance_reduction_mm']:.3f} mm`.",
        "",
        "| trajectory | target MPa | skull peak MPa | target/global | peak distance mm | validated rank | verdict |",
        "|:---|---:|---:|---:|---:|---:|:---:|",
    ]
    for row in sorted(rows, key=lambda item: item["validated_rank"]):
        lines.append(
            f"| {row['trajectory']} | {row['target_window_peak_mpa']:.4f} | {row['skull_peak_mpa']:.4f} | "
            f"{row['target_to_global_peak_ratio']:.4f} | {row['global_peak_to_target_distance_mm']:.3f} | "
            f"{row['validated_rank']} | {row['heldout_verdict']} |"
        )
    lines.extend(["", "This reuses an existing field; no new pressure run is authorized or required."])
    (args.output_dir / "reuse_gate.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "selected_trajectory": report["selected_trajectory"],
        "target_pressure_retention_vs_reference": target_retention,
        "skull_peak_reduction_vs_reference": skull_reduction,
        "checks": checks,
    }, indent=2))


if __name__ == "__main__":
    main()
