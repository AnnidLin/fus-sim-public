from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from bbb_element_plan import aggregate_element_plan, reconstruction_metrics, virtual_patch_ids
from design_dual_point_hotspot_constrained_tr_20260720 import extract_transfer_phasor


ROOT = Path(__file__).resolve().parent
SIGNALS = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "offset_y+12p5_z-15p0" / "tr" / "element_signals.npz"
SELECTION = ROOT / "outputs" / "trajectory_geometry_reuse_gate_20260722" / "selected_trajectory.json"
EVIDENCE = ROOT / "outputs" / "evidence_briefs" / "bbb_element_plan_h3_20260722" / "evidence_brief.json"
OUTPUT = ROOT / "outputs" / "bbb_element_plan_h3_20260722"


def mask_hash(mask: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(mask, dtype=np.uint8).tobytes(order="C")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the selected H3 virtual element-level drive-plan fixture.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    frozen = evidence["frozen"]
    if selection["trajectory"] != frozen["trajectory"] or selection["new_pressure_required"]:
        raise ValueError("selected trajectory packet does not authorize H3 existing-field reuse")

    with np.load(SIGNALS, allow_pickle=False) as stored:
        signals = np.asarray(stored["signals"], dtype=np.float64)
        dt_s = float(stored["dt_s"])
        frequency_hz = float(stored["frequency_hz"])
        points = np.asarray(stored["mask_point_ijk"], dtype=np.int32)
        source_mask = np.asarray(stored["source_mask"], dtype=np.uint8)
        source_center = np.asarray(stored["bowl_index_ijk"], dtype=np.int32)
        target = np.asarray(stored["target_index_ijk"], dtype=np.int32)
    transfer = extract_transfer_phasor(signals, dt_s, frequency_hz)
    weights = np.conjugate(transfer)
    ids = virtual_patch_ids(
        points,
        source_center,
        target,
        int(frozen["virtual_patch_rows"]),
        int(frozen["virtual_patch_columns"]),
    )
    records, expanded = aggregate_element_plan(
        weights,
        points,
        ids,
        int(frozen["amplitude_bits"]),
        int(frozen["phase_bits"]),
    )
    metrics = reconstruction_metrics(weights, expanded, transfer)
    checks = {
        "source_mask_hash_exact": mask_hash(source_mask) == frozen["source_mask_sha256"],
        "source_point_count_exact": points.shape[0] == frozen["source_point_count"],
        "point_count_conserved": sum(record["point_count"] for record in records) == points.shape[0],
        "virtual_element_slots_exact": (
            frozen["virtual_patch_rows"] * frozen["virtual_patch_columns"]
            == evidence["gates"]["virtual_element_slots"]
        ),
        "active_virtual_elements_min": (
            sum(record["active"] for record in records)
            >= evidence["gates"]["active_virtual_elements_min"]
        ),
        "finite_controls": bool(np.all(np.isfinite(expanded))),
        "predicted_target_response_retention": (
            metrics["predicted_response_retention"] >= evidence["gates"]["predicted_target_response_retention_min"]
        ),
        "frequency_exact": frequency_hz == frozen["frequency_hz"],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output_dir / "virtual_element_mapping.npz",
        element_ids=ids,
        source_points_ijk=points,
        source_mask=source_mask,
        expanded_point_weights=expanded.astype(np.complex64),
    )
    with (args.output_dir / "element_drive_plan.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["element_id", "point_count", "centroid_i", "centroid_j", "centroid_k", "amplitude", "phase_rad", "phase_deg", "active"],
        )
        writer.writeheader()
        for record in records:
            centroid = record["centroid_ijk"]
            writer.writerow({
                "element_id": record["element_id"],
                "point_count": record["point_count"],
                "centroid_i": centroid[0],
                "centroid_j": centroid[1],
                "centroid_k": centroid[2],
                "amplitude": record["amplitude"],
                "phase_rad": record["phase_rad"],
                "phase_deg": record["phase_deg"],
                "active": record["active"],
            })
    summary: dict[str, Any] = {
        "status": "h3_virtual_element_plan_ready" if all(checks.values()) else "h3_virtual_element_plan_gate_fail",
        "trajectory": frozen["trajectory"],
        "element_semantics": "virtual_patch_not_device_hardware",
        "partition": {"rows": frozen["virtual_patch_rows"], "columns": frozen["virtual_patch_columns"]},
        "source_point_count": int(points.shape[0]),
        "active_element_count": len(records),
        "virtual_element_slots": frozen["virtual_patch_rows"] * frozen["virtual_patch_columns"],
        "source_mask_sha256": mask_hash(source_mask),
        "quantization": {"amplitude_bits": frozen["amplitude_bits"], "phase_bits": frozen["phase_bits"]},
        "reconstruction": metrics,
        "checks": checks,
        "hardware_geometry_required_for_device_export": True,
        "pressure_executed": False,
        "claim_boundary": evidence["claim_boundary"],
    }
    (args.output_dir / "element_plan_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
