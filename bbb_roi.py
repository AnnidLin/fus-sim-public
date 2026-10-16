from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from bbb_planning_contract import DEFAULT_EXAMPLE, DEFAULT_SCHEMA, load_json, validate_contract


ROOT = Path(__file__).resolve().parent


class ROIError(ValueError):
    pass


@dataclass(frozen=True)
class LoadedROI:
    mask: np.ndarray
    affine_ijk_to_world_mm: np.ndarray | None
    source_format: str
    source_path: str | None


def validate_binary_mask(mask: np.ndarray, expected_shape: tuple[int, int, int] | None = None) -> np.ndarray:
    value = np.asarray(mask)
    if value.ndim != 3:
        raise ROIError(f"ROI mask must be 3D, got shape {value.shape}")
    if expected_shape is not None and value.shape != expected_shape:
        raise ROIError(f"ROI shape mismatch: {value.shape} vs expected {expected_shape}")
    if not np.all(np.isfinite(value)):
        raise ROIError("ROI mask contains non-finite values")
    if not np.all((value == 0) | (value == 1)):
        raise ROIError("ROI mask must be binary with values 0/1")
    binary = value.astype(bool)
    if not np.any(binary):
        raise ROIError("ROI mask is empty")
    return binary


def load_roi_mask(
    path: Path,
    expected_shape: tuple[int, int, int],
    expected_affine_ijk_to_world_mm: np.ndarray | None = None,
) -> LoadedROI:
    name = path.name.lower()
    if name.endswith(".nii") or name.endswith(".nii.gz"):
        if expected_affine_ijk_to_world_mm is None:
            raise ROIError("NIfTI loading requires an authoritative expected affine")
        import nibabel as nib

        image = nib.load(str(path))
        affine = np.asarray(image.affine, dtype=np.float64)
        expected_affine = np.asarray(expected_affine_ijk_to_world_mm, dtype=np.float64)
        if affine.shape != (4, 4) or expected_affine.shape != (4, 4):
            raise ROIError("NIfTI and expected affines must be 4x4")
        if not np.allclose(affine, expected_affine, rtol=1e-6, atol=1e-5):
            raise ROIError("NIfTI affine mismatch; explicit registration/resampling is required")
        mask = np.asanyarray(image.dataobj)
        source_format = "nifti"
    elif name.endswith(".npz"):
        with np.load(path, allow_pickle=False) as stored:
            keys = [key for key in ("roi_mask", "mask") if key in stored.files]
            if len(keys) != 1:
                raise ROIError("NPZ must contain exactly one of roi_mask or mask")
            mask = np.asarray(stored[keys[0]])
        affine = None
        source_format = "npz"
    elif name.endswith(".npy"):
        mask = np.load(path, allow_pickle=False)
        affine = None
        source_format = "npy"
    else:
        raise ROIError(f"unsupported ROI format: {path.name}")
    return LoadedROI(
        mask=validate_binary_mask(mask, expected_shape),
        affine_ijk_to_world_mm=affine,
        source_format=source_format,
        source_path=str(path),
    )


def sphere_mask(
    shape_ijk: tuple[int, int, int],
    center_ijk: tuple[int, int, int],
    spacing_m_ijk: tuple[float, float, float],
    radius_m: float,
) -> np.ndarray:
    if len(shape_ijk) != 3 or any(size <= 0 for size in shape_ijk):
        raise ROIError("shape_ijk must contain three positive values")
    if len(center_ijk) != 3 or any(index < 0 or index >= size for index, size in zip(center_ijk, shape_ijk, strict=True)):
        raise ROIError("sphere center is outside the grid")
    if len(spacing_m_ijk) != 3 or any(not np.isfinite(value) or value <= 0 for value in spacing_m_ijk):
        raise ROIError("spacing_m_ijk must contain three finite positive values")
    if not np.isfinite(radius_m) or radius_m <= 0:
        raise ROIError("radius_m must be finite and positive")

    mask = np.zeros(shape_ijk, dtype=bool)
    extents = [int(np.ceil(radius_m / spacing)) for spacing in spacing_m_ijk]
    starts = [max(0, center - extent) for center, extent in zip(center_ijk, extents, strict=True)]
    stops = [min(size, center + extent + 1) for center, extent, size in zip(center_ijk, extents, shape_ijk, strict=True)]
    for i in range(starts[0], stops[0]):
        for j in range(starts[1], stops[1]):
            for k in range(starts[2], stops[2]):
                distance_sq = sum(
                    ((index - center) * spacing) ** 2
                    for index, center, spacing in zip((i, j, k), center_ijk, spacing_m_ijk, strict=True)
                )
                if distance_sq <= radius_m**2 + 1e-18:
                    mask[i, j, k] = True
    return validate_binary_mask(mask, shape_ijk)


def summarize_roi(mask: np.ndarray, spacing_m_ijk: tuple[float, float, float]) -> dict[str, Any]:
    binary = validate_binary_mask(mask)
    points = np.argwhere(binary)
    return {
        "shape_ijk": list(binary.shape),
        "voxel_count": int(points.shape[0]),
        "voxel_volume_m3": float(np.prod(spacing_m_ijk)),
        "roi_volume_m3": float(points.shape[0] * np.prod(spacing_m_ijk)),
        "centroid_ijk": np.mean(points, axis=0).tolist(),
        "bounds_min_ijk": np.min(points, axis=0).astype(int).tolist(),
        "bounds_max_ijk": np.max(points, axis=0).astype(int).tolist(),
        "coordinate_convention": "zero_based_numpy_ijk",
        "array_order": "numpy_c_order",
    }


def pressure_coverage_metrics(
    pressure_pa: np.ndarray,
    roi_mask: np.ndarray,
    threshold_pa: float,
    labels: np.ndarray | None = None,
) -> dict[str, Any]:
    pressure = np.asarray(pressure_pa, dtype=np.float64)
    roi = validate_binary_mask(roi_mask, pressure.shape)
    if not np.all(np.isfinite(pressure)) or np.any(pressure < 0):
        raise ROIError("pressure_pa must be finite and nonnegative")
    if not np.isfinite(threshold_pa) or threshold_pa < 0:
        raise ROIError("threshold_pa must be finite and nonnegative")
    roi_values = pressure[roi]
    mean = float(np.mean(roi_values))
    result: dict[str, Any] = {
        "threshold_pa": float(threshold_pa),
        "roi_voxel_count": int(roi_values.size),
        "roi_peak_pressure_pa": float(np.max(roi_values)),
        "roi_mean_pressure_pa": mean,
        "roi_median_pressure_pa": float(np.median(roi_values)),
        "roi_p10_pressure_pa": float(np.percentile(roi_values, 10)),
        "roi_p90_pressure_pa": float(np.percentile(roi_values, 90)),
        "roi_coefficient_of_variation": None if mean == 0 else float(np.std(roi_values) / mean),
        "roi_coverage_fraction": float(np.mean(roi_values >= threshold_pa)),
        "global_peak_pressure_pa": float(np.max(pressure)),
        "global_peak_ijk": np.unravel_index(int(np.argmax(pressure)), pressure.shape),
    }
    result["global_peak_ijk"] = [int(value) for value in result["global_peak_ijk"]]
    if labels is not None:
        tissue = np.asarray(labels)
        if tissue.shape != pressure.shape:
            raise ROIError("labels shape must match pressure")
        skull_values = pressure[tissue == 2]
        brain_values = pressure[(tissue == 1) & ~roi]
        result["skull_peak_pressure_pa"] = None if skull_values.size == 0 else float(np.max(skull_values))
        result["non_target_brain_peak_pressure_pa"] = None if brain_values.size == 0 else float(np.max(brain_values))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the Case 079 ROI contract fixture without simulation.")
    parser.add_argument("--plan", type=Path, default=DEFAULT_EXAMPLE)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs" / "bbb_roi_case079_20260721")
    args = parser.parse_args()

    plan = load_json(args.plan)
    validate_contract(plan, load_json(DEFAULT_SCHEMA), verify_file_hashes=True)
    patient = plan["patient_model"]
    roi = plan["target_roi"]
    if roi["generation"]["method"] != "sphere_from_center":
        raise ROIError("CLI fixture generation currently requires sphere_from_center")
    mask = sphere_mask(
        tuple(patient["shape_ijk"]),
        tuple(roi["center_full_ijk"]),
        tuple(patient["spacing_m_ijk"]),
        float(roi["generation"]["radius_m"]),
    )
    summary = summarize_roi(mask, tuple(patient["spacing_m_ijk"]))
    if summary["voxel_count"] != roi["voxel_count"]:
        raise ROIError("generated ROI voxel count differs from planning contract")
    summary.update({
        "status": "pass",
        "plan_id": plan["plan_id"],
        "roi_id": roi["roi_id"],
        "roi_kind": roi["roi_kind"],
        "anatomical_status": roi["anatomical_status"],
        "pressure_executed": False,
        "claim_boundary": "synthetic_roi_fixture_not_anatomical",
    })
    args.output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output_dir / "roi_mask.npz",
        roi_mask=mask.astype(np.uint8),
        spacing_m_ijk=np.asarray(patient["spacing_m_ijk"], dtype=np.float64),
        center_full_ijk=np.asarray(roi["center_full_ijk"], dtype=np.int32),
        radius_m=np.array(roi["generation"]["radius_m"], dtype=np.float64),
    )
    (args.output_dir / "roi_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
