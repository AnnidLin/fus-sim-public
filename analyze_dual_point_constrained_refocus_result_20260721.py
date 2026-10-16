from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parent
CONTROL = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "offset_y-10p0_z-02p5" / "tr"
CANDIDATE = ROOT / "outputs" / "dual_point_constrained_refocus_20260721" / "run"
OUTPUT = ROOT / "outputs" / "dual_point_constrained_refocus_20260721" / "result"

THRESHOLDS = {
    "target_window_retention_min": 0.80,
    "skull_peak_reduction_min": 0.20,
    "target_global_ratio_decline_abs_max": 0.05,
    "non_target_peak_vs_control_global_max": 1.00,
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_arm(run_dir: Path) -> dict[str, Any]:
    summary = _load_json(run_dir / "summary.json")
    pressure_summary = summary["pressure"]
    with np.load(run_dir / "pressure_max_mpa.npz", allow_pickle=False) as stored:
        pressure = np.asarray(stored["pressure_max_mpa"], dtype=np.float64)
        labels = np.asarray(stored["labels"])
    if pressure.shape != labels.shape or not np.all(np.isfinite(pressure)):
        raise ValueError(f"Invalid pressure field in {run_dir}")

    target = np.asarray(summary["source"]["target_index_ijk"], dtype=int)
    radius = int(pressure_summary["target_window_radius_grid_points"])
    coordinates = np.indices(pressure.shape)
    target_window = np.sum((coordinates - target.reshape(3, 1, 1, 1)) ** 2, axis=0) <= radius**2
    non_target = np.where(target_window, -np.inf, pressure)
    non_target_flat = int(np.argmax(non_target))
    non_target_index = np.unravel_index(non_target_flat, pressure.shape)
    skull_values = pressure[labels == 2]
    if skull_values.size == 0:
        raise ValueError(f"No skull voxels in {run_dir}")

    return {
        "target_window_peak_mpa": float(pressure_summary["target_window_peak_mpa"]),
        "global_peak_mpa": float(pressure_summary["global_peak_mpa"]),
        "target_to_global_peak_ratio": float(pressure_summary["target_to_global_peak_ratio"]),
        "skull_peak_mpa": float(np.max(skull_values)),
        "non_target_peak_mpa": float(non_target[non_target_index]),
        "non_target_peak_index_ijk": [int(value) for value in non_target_index],
        "non_target_peak_material_label": int(labels[non_target_index]),
        "replay_max_abs_pa": float(summary["time_reversal"]["replay_max_abs_pa"]),
        "source_points": int(summary["source"]["source_points"]),
        "target_index_ijk": target.tolist(),
        "target_window_radius_grid_points": radius,
        "field_shape": list(pressure.shape),
    }


def compare(control: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    target_retention = candidate["target_window_peak_mpa"] / control["target_window_peak_mpa"]
    skull_reduction = 1.0 - candidate["skull_peak_mpa"] / control["skull_peak_mpa"]
    target_global_decline = control["target_to_global_peak_ratio"] - candidate["target_to_global_peak_ratio"]
    non_target_vs_control = candidate["non_target_peak_mpa"] / control["global_peak_mpa"]
    tolerance = 1e-12
    gates = {
        "target_window_retention": target_retention + tolerance >= THRESHOLDS["target_window_retention_min"],
        "skull_peak_reduction": skull_reduction + tolerance >= THRESHOLDS["skull_peak_reduction_min"],
        "target_global_ratio_decline": target_global_decline <= THRESHOLDS["target_global_ratio_decline_abs_max"] + tolerance,
        "no_stronger_new_non_target_peak": non_target_vs_control <= THRESHOLDS["non_target_peak_vs_control_global_max"] + tolerance,
    }
    input_checks = {
        "field_shape_exact": candidate["field_shape"] == control["field_shape"],
        "target_exact": candidate["target_index_ijk"] == control["target_index_ijk"],
        "target_window_exact": candidate["target_window_radius_grid_points"] == control["target_window_radius_grid_points"],
        "source_points_exact": candidate["source_points"] == control["source_points"],
        "matched_replay_normalization": bool(
            np.isclose(candidate["replay_max_abs_pa"], control["replay_max_abs_pa"], rtol=0.0, atol=1e-6)
        ),
    }
    passed = all(gates.values()) and all(input_checks.values())
    return {
        "status": "four_gate_pass" if passed else "four_gate_fail",
        "passed": passed,
        "input_checks": input_checks,
        "thresholds": THRESHOLDS,
        "metrics": {
            "target_window_retention": target_retention,
            "skull_peak_reduction": skull_reduction,
            "target_global_ratio_decline_abs": target_global_decline,
            "candidate_non_target_vs_control_global": non_target_vs_control,
        },
        "gates": gates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the preregistered constrained-refocus pressure gates.")
    parser.add_argument("--control-dir", type=Path, default=CONTROL)
    parser.add_argument("--candidate-dir", type=Path, default=CANDIDATE)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()

    control = load_arm(args.control_dir)
    candidate = load_arm(args.candidate_dir)
    comparison = compare(control, candidate)
    report = {
        **comparison,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "single_preregistered_dual_point_constrained_refocus",
        "pressure_runs_in_this_packet": 1,
        "additional_pressure_run_authorized": False,
        "control": control,
        "candidate": candidate,
        "claim_boundary": "single_case_single_trajectory_engineering_evidence_not_clinical_safety",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "four_gate_result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    metric_rows = [
        ("Target-window retention", report["metrics"]["target_window_retention"], ">=", THRESHOLDS["target_window_retention_min"], report["gates"]["target_window_retention"]),
        ("Skull-peak reduction", report["metrics"]["skull_peak_reduction"], ">=", THRESHOLDS["skull_peak_reduction_min"], report["gates"]["skull_peak_reduction"]),
        ("Target/global ratio decline", report["metrics"]["target_global_ratio_decline_abs"], "<=", THRESHOLDS["target_global_ratio_decline_abs_max"], report["gates"]["target_global_ratio_decline"]),
        ("Non-target/control-global", report["metrics"]["candidate_non_target_vs_control_global"], "<=", THRESHOLDS["non_target_peak_vs_control_global_max"], report["gates"]["no_stronger_new_non_target_peak"]),
    ]
    lines = [
        "# Dual-Point Constrained Refocus Result",
        "",
        f"Status: **{report['status']}**",
        "",
        "| Preregistered gate | Value | Threshold | Pass |",
        "|---|---:|---:|:---:|",
    ]
    lines.extend(f"| {name} | {value:.6f} | {operator} {threshold:.2f} | {'yes' if passed else 'no'} |" for name, value, operator, threshold, passed in metric_rows)
    lines.extend([
        "",
        f"Control target/skull peaks: {control['target_window_peak_mpa']:.6f} / {control['skull_peak_mpa']:.6f} MPa.",
        f"Candidate target/skull peaks: {candidate['target_window_peak_mpa']:.6f} / {candidate['skull_peak_mpa']:.6f} MPa.",
        "",
        "Exactly one constrained pressure replay was evaluated. No additional pressure run is authorized by this packet.",
        "This is single-case engineering evidence and does not establish BBB-opening dose or clinical safety.",
    ])
    (args.output_dir / "four_gate_result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "metrics": report["metrics"], "gates": report["gates"]}, indent=2))


if __name__ == "__main__":
    main()

