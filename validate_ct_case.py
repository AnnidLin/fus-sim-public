from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from build_ct_acoustic_model import read_ct_slices, read_nifti_file


PROJECT_ROOT = Path(__file__).resolve().parent


def is_nifti_path(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".nii") or name.endswith(".nii.gz")


def case_id_from_path(path: Path) -> str:
    name = path.name
    lower = name.lower()
    if lower.endswith(".nii.gz"):
        return name[:-7]
    if lower.endswith(".nii"):
        return name[:-4]
    return path.name


def folder_size_bytes(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


def detect_ct_format(path: Path) -> str:
    if path.is_file() and is_nifti_path(path):
        return "nifti"
    if path.is_dir():
        return "dicom_folder"
    return "unsupported"


def read_ct_case(path: Path) -> tuple[np.ndarray, tuple[float, float, float], dict[str, Any], str]:
    ct_format = detect_ct_format(path)
    if ct_format == "nifti":
        volume, spacing_m, metadata = read_nifti_file(path)
    elif ct_format == "dicom_folder":
        volume, spacing_m, metadata = read_ct_slices(path)
    else:
        raise ValueError(f"Unsupported CT case path: {path}")
    return volume, spacing_m, metadata, ct_format


def finite_percentiles(values: np.ndarray) -> dict[str, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {
            "min": float("nan"),
            "p1": float("nan"),
            "p5": float("nan"),
            "median": float("nan"),
            "p95": float("nan"),
            "p99": float("nan"),
            "max": float("nan"),
        }
    percentiles = np.percentile(finite, [1, 5, 50, 95, 99])
    return {
        "min": float(finite.min()),
        "p1": float(percentiles[0]),
        "p5": float(percentiles[1]),
        "median": float(percentiles[2]),
        "p95": float(percentiles[3]),
        "p99": float(percentiles[4]),
        "max": float(finite.max()),
    }


def status_from_warnings(warnings: list[str], errors: list[str]) -> str:
    if errors:
        return "error"
    if warnings:
        return "warning"
    return "ok"


def summarize_loaded_case(
    case_id: str,
    ct_path: Path,
    volume: np.ndarray,
    spacing_m: tuple[float, float, float],
    metadata: dict[str, Any],
    ct_format: str,
) -> dict[str, Any]:
    shape = [int(value) for value in volume.shape]
    spacing_mm = [float(value * 1e3) for value in spacing_m]
    stats = finite_percentiles(volume)
    voxel_count = int(np.prod(shape))
    finite_mask = np.isfinite(volume)
    finite_count = int(np.count_nonzero(finite_mask))
    bone_mask = finite_mask & (volume >= 300.0)
    air_mask = finite_mask & (volume < -500.0)
    soft_like_mask = finite_mask & (volume >= -500.0) & (volume < 300.0)
    warnings: list[str] = []
    errors: list[str] = []

    if finite_count == 0:
        errors.append("volume_has_no_finite_voxels")
    if shape[2] < 16:
        warnings.append("low_slice_count")
    if max(spacing_mm) > 3.0:
        warnings.append("coarse_spacing_over_3mm")
    if spacing_mm[2] > 3.0:
        warnings.append("coarse_z_spacing_over_3mm")
    if stats["max"] < 300.0:
        warnings.append("no_bone_intensity_range_gte_300hu")
    if stats["min"] > -300.0:
        warnings.append("no_air_like_intensity_range")
    if stats["max"] > 5000.0 or stats["min"] < -2000.0:
        warnings.append("intensity_range_outside_typical_ct_hu")

    bone_fraction = float(np.count_nonzero(bone_mask) / max(finite_count, 1))
    air_fraction = float(np.count_nonzero(air_mask) / max(finite_count, 1))
    soft_like_fraction = float(np.count_nonzero(soft_like_mask) / max(finite_count, 1))
    likely_ct_hu = bool(stats["min"] <= -500.0 and stats["max"] >= 300.0)

    return {
        "case_id": case_id,
        "ct_path": str(ct_path),
        "format": ct_format,
        "status": status_from_warnings(warnings, errors),
        "warnings": warnings,
        "errors": errors,
        "file_size_bytes": folder_size_bytes(ct_path),
        "shape_xyz": shape,
        "spacing_mm_xyz": spacing_mm,
        "slice_count": int(metadata.get("slice_count", shape[2])),
        "intensity_stats": stats,
        "hu_or_intensity_range": [stats["min"], stats["max"]],
        "likely_ct_hu": likely_ct_hu,
        "has_bone_intensity_range_gte_300hu": bool(stats["max"] >= 300.0 and np.count_nonzero(bone_mask) > 0),
        "bone_voxel_fraction_gte_300hu": bone_fraction,
        "air_voxel_fraction_lt_minus_500hu": air_fraction,
        "soft_like_voxel_fraction": soft_like_fraction,
        "voxel_count": voxel_count,
        "source_metadata": metadata,
    }


def summarize_case(case_id: str, ct_path: Path) -> dict[str, Any]:
    try:
        volume, spacing_m, metadata, ct_format = read_ct_case(ct_path)
        return summarize_loaded_case(case_id, ct_path, volume, spacing_m, metadata, ct_format)
    except Exception as exc:
        return {
            "case_id": case_id,
            "ct_path": str(ct_path),
            "format": detect_ct_format(ct_path),
            "status": "error",
            "warnings": [],
            "errors": [str(exc)],
            "file_size_bytes": folder_size_bytes(ct_path) if ct_path.exists() else 0,
        }


def save_qc_outputs(summary: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "qc_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "qc_summary.txt").open("w", encoding="utf-8") as handle:
        handle.write(f"case_id={summary.get('case_id')}\n")
        handle.write(f"status={summary.get('status')}\n")
        handle.write(f"format={summary.get('format')}\n")
        handle.write(f"ct_path={summary.get('ct_path')}\n")
        handle.write(f"file_size_bytes={summary.get('file_size_bytes')}\n")
        handle.write(f"shape_xyz={summary.get('shape_xyz')}\n")
        handle.write(f"spacing_mm_xyz={summary.get('spacing_mm_xyz')}\n")
        handle.write(f"slice_count={summary.get('slice_count')}\n")
        handle.write(f"hu_or_intensity_range={summary.get('hu_or_intensity_range')}\n")
        handle.write(f"likely_ct_hu={summary.get('likely_ct_hu')}\n")
        handle.write(f"has_bone_intensity_range_gte_300hu={summary.get('has_bone_intensity_range_gte_300hu')}\n")
        handle.write(f"bone_voxel_fraction_gte_300hu={summary.get('bone_voxel_fraction_gte_300hu')}\n")
        for warning in summary.get("warnings", []):
            handle.write(f"warning={warning}\n")
        for error in summary.get("errors", []):
            handle.write(f"error={error}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run lightweight CT case QC for a NIfTI file or DICOM folder.")
    parser.add_argument("--case-id", required=True, help="Case identifier to write into the QC summary.")
    parser.add_argument("--ct-path", required=True, help="Path to a .nii/.nii.gz file or DICOM folder.")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs" / "ct_case_qc"),
        help="Output directory for qc_summary.json/txt.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = summarize_case(args.case_id, Path(args.ct_path))
    save_qc_outputs(summary, Path(args.output_dir))
    if summary["status"] == "error":
        raise SystemExit(f"ERROR: CT case QC failed for {args.case_id}: {summary.get('errors')}")
    if summary["status"] == "warning":
        print(f"WARNING: CT case QC completed with warnings for {args.case_id}: {summary.get('warnings')}")
    else:
        print(f"OK: CT case QC completed for {args.case_id}")


if __name__ == "__main__":
    main()
