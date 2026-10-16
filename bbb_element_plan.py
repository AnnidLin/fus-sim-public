from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from design_dual_point_hotspot_constrained_tr_20260720 import predicted_response


ROOT = Path(__file__).resolve().parent
TARGET_TRANSFER = ROOT / "outputs" / "dual_point_hotspot_constrained_tr_20260720" / "target_transfer_steering.npz"
OUTPUT = ROOT / "outputs" / "bbb_element_plan_case079_20260721"


class ElementPlanError(ValueError):
    pass


def virtual_patch_ids(
    source_points_ijk: np.ndarray,
    source_center_ijk: np.ndarray,
    target_ijk: np.ndarray,
    rows: int,
    columns: int,
) -> np.ndarray:
    points = np.asarray(source_points_ijk, dtype=np.float64)
    center = np.asarray(source_center_ijk, dtype=np.float64)
    target = np.asarray(target_ijk, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or points.shape[0] == 0:
        raise ElementPlanError("source_points_ijk must be a nonempty [N,3] array")
    if center.shape != (3,) or target.shape != (3,) or rows <= 0 or columns <= 0:
        raise ElementPlanError("invalid virtual patch geometry")
    axis = target - center
    norm = float(np.linalg.norm(axis))
    if norm <= 0:
        raise ElementPlanError("source center and target must differ")
    axis /= norm
    arbitrary = np.array([1.0, 0.0, 0.0])
    if abs(float(np.dot(axis, arbitrary))) > 0.95:
        arbitrary = np.array([0.0, 1.0, 0.0])
    tangent_u = np.cross(arbitrary, axis)
    tangent_u /= np.linalg.norm(tangent_u)
    tangent_v = np.cross(axis, tangent_u)
    relative = points - center
    u = relative @ tangent_u
    v = relative @ tangent_v
    u_edges = np.linspace(float(np.min(u)), float(np.max(u)), rows + 1)
    v_edges = np.linspace(float(np.min(v)), float(np.max(v)), columns + 1)
    return (
        np.digitize(u, u_edges[1:-1]) * columns
        + np.digitize(v, v_edges[1:-1])
    ).astype(np.int32)


def quantize_complex_controls(weights: np.ndarray, amplitude_bits: int, phase_bits: int) -> np.ndarray:
    value = np.asarray(weights, dtype=np.complex128)
    if value.ndim != 1 or not np.all(np.isfinite(value)):
        raise ElementPlanError("weights must be a finite 1D complex vector")
    if amplitude_bits < 1 or phase_bits < 1:
        raise ElementPlanError("quantization bits must be positive")
    amplitude = np.abs(value)
    maximum = float(np.max(amplitude))
    normalized = amplitude if maximum == 0 else amplitude / maximum
    amp_levels = 2**amplitude_bits - 1
    amplitude_q = np.rint(normalized * amp_levels) / amp_levels
    phase = np.mod(np.angle(value), 2 * np.pi)
    phase_levels = 2**phase_bits
    phase_q = np.rint(phase / (2 * np.pi) * phase_levels) % phase_levels
    phase_q = phase_q / phase_levels * 2 * np.pi
    return amplitude_q * np.exp(1j * phase_q)


def aggregate_element_plan(
    point_weights: np.ndarray,
    source_points_ijk: np.ndarray,
    element_ids: np.ndarray,
    amplitude_bits: int | None = None,
    phase_bits: int | None = None,
) -> tuple[list[dict[str, Any]], np.ndarray]:
    weights = np.asarray(point_weights, dtype=np.complex128)
    points = np.asarray(source_points_ijk, dtype=np.float64)
    ids = np.asarray(element_ids, dtype=np.int64)
    if weights.ndim != 1 or points.shape != (weights.size, 3) or ids.shape != (weights.size,):
        raise ElementPlanError("weights, source points, and element IDs have incompatible shapes")
    if not np.all(np.isfinite(weights)) or np.any(ids < 0):
        raise ElementPlanError("weights must be finite and element IDs nonnegative")
    unique_ids = np.unique(ids)
    controls = np.zeros(unique_ids.size, dtype=np.complex128)
    records: list[dict[str, Any]] = []
    for output_index, element_id in enumerate(unique_ids):
        member = ids == element_id
        controls[output_index] = np.mean(weights[member])
        centroid = np.mean(points[member], axis=0)
        records.append({
            "element_id": int(element_id),
            "point_count": int(np.sum(member)),
            "centroid_ijk": centroid.tolist(),
        })
    if amplitude_bits is not None or phase_bits is not None:
        if amplitude_bits is None or phase_bits is None:
            raise ElementPlanError("amplitude_bits and phase_bits must be provided together")
        controls = quantize_complex_controls(controls, amplitude_bits, phase_bits)
    expanded = np.empty(weights.shape, dtype=np.complex128)
    id_to_output = {int(element_id): index for index, element_id in enumerate(unique_ids)}
    for point_index, element_id in enumerate(ids):
        expanded[point_index] = controls[id_to_output[int(element_id)]]
    reference_max = float(np.max(np.abs(weights)))
    expanded_max = float(np.max(np.abs(expanded)))
    if reference_max > 0 and expanded_max > 0:
        expanded *= reference_max / expanded_max
        controls *= reference_max / expanded_max
    for record, control in zip(records, controls, strict=True):
        record.update({
            "amplitude": float(abs(control)),
            "phase_rad": float(np.angle(control)),
            "phase_deg": float(np.degrees(np.angle(control))),
            "active": bool(abs(control) > 0),
        })
    return records, expanded


def reconstruction_metrics(original: np.ndarray, expanded: np.ndarray, transfer: np.ndarray | None = None) -> dict[str, Any]:
    original = np.asarray(original, dtype=np.complex128)
    expanded = np.asarray(expanded, dtype=np.complex128)
    if original.shape != expanded.shape or original.ndim != 1:
        raise ElementPlanError("original and expanded weights must have the same 1D shape")
    norm = float(np.linalg.norm(original))
    result: dict[str, Any] = {
        "relative_complex_l2_error": 0.0 if norm == 0 else float(np.linalg.norm(expanded - original) / norm),
        "original_max_abs": float(np.max(np.abs(original))),
        "expanded_max_abs": float(np.max(np.abs(expanded))),
    }
    if transfer is not None:
        reference = abs(predicted_response(transfer, original))
        candidate = abs(predicted_response(transfer, expanded))
        result["predicted_response_retention"] = None if reference == 0 else float(candidate / reference)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a virtual element-level H1 drive-plan fixture.")
    parser.add_argument("--rows", type=int, default=7)
    parser.add_argument("--columns", type=int, default=7)
    parser.add_argument("--amplitude-bits", type=int, default=10)
    parser.add_argument("--phase-bits", type=int, default=10)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    with np.load(TARGET_TRANSFER, allow_pickle=False) as stored:
        transfer = np.asarray(stored["target_transfer"], dtype=np.complex128)
        weights = np.asarray(stored["conventional_weights"], dtype=np.complex128)
        points = np.asarray(stored["mask_point_ijk"], dtype=np.int32)
        source_mask = np.asarray(stored["source_mask"], dtype=np.uint8)
    ids = virtual_patch_ids(points, np.array([16, 23, 23]), np.array([114, 36, 26]), args.rows, args.columns)
    records, expanded = aggregate_element_plan(weights, points, ids, args.amplitude_bits, args.phase_bits)
    metrics = reconstruction_metrics(weights, expanded, transfer)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output_dir / "virtual_element_mapping.npz",
        element_ids=ids,
        source_points_ijk=points,
        source_mask=source_mask,
        expanded_point_weights=expanded.astype(np.complex64),
    )
    with (args.output_dir / "element_drive_plan.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["element_id", "point_count", "centroid_i", "centroid_j", "centroid_k", "amplitude", "phase_rad", "phase_deg", "active"])
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
    summary = {
        "status": "virtual_element_plan_ready",
        "element_semantics": "virtual_patch_not_device_hardware",
        "partition": {"rows": args.rows, "columns": args.columns},
        "source_point_count": int(points.shape[0]),
        "active_element_count": len(records),
        "point_count_conserved": sum(record["point_count"] for record in records) == points.shape[0],
        "quantization": {"amplitude_bits": args.amplitude_bits, "phase_bits": args.phase_bits},
        "reconstruction": metrics,
        "hardware_geometry_required_for_device_export": True,
        "pressure_executed": False,
        "claim_boundary": "virtual_patch_not_device_hardware",
    }
    (args.output_dir / "element_plan_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
