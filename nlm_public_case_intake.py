from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import nibabel as nib
import numpy as np
import pydicom

ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = ROOT / "outputs" / "nlm_additional_head_import_20260722" / "raw_data_manifest.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "nlm_public_case_intake_20260722"


class PublicCaseIntakeError(ValueError):
    pass


@dataclass(frozen=True)
class SliceHeader:
    path: Path
    rows: int
    columns: int
    pixel_spacing_rc_mm: tuple[float, float]
    orientation_lps: tuple[float, ...]
    position_lps_mm: tuple[float, float, float]
    modality: str
    series_uid: str
    frame_uid: str
    sop_uid: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _float_tuple(value: Iterable[Any], size: int, name: str) -> tuple[float, ...]:
    result = tuple(float(item) for item in value)
    if len(result) != size or not np.all(np.isfinite(result)):
        raise PublicCaseIntakeError(f"{name} must contain {size} finite values")
    return result


def read_header(path: Path) -> SliceHeader:
    ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
    required = ("Rows", "Columns", "PixelSpacing", "ImageOrientationPatient", "ImagePositionPatient")
    missing = [name for name in required if not hasattr(ds, name)]
    if missing:
        raise PublicCaseIntakeError(f"{path}: missing DICOM geometry tags {missing}")
    return SliceHeader(
        path, int(ds.Rows), int(ds.Columns),
        _float_tuple(ds.PixelSpacing, 2, "PixelSpacing"),
        _float_tuple(ds.ImageOrientationPatient, 6, "ImageOrientationPatient"),
        _float_tuple(ds.ImagePositionPatient, 3, "ImagePositionPatient"),
        str(getattr(ds, "Modality", "")).upper(), str(getattr(ds, "SeriesInstanceUID", "")),
        str(getattr(ds, "FrameOfReferenceUID", "")), str(getattr(ds, "SOPInstanceUID", "")),
    )


def slice_normal(orientation_lps: Iterable[float]) -> np.ndarray:
    orientation = np.asarray(tuple(orientation_lps), dtype=np.float64)
    if orientation.shape != (6,):
        raise PublicCaseIntakeError("orientation must contain six direction cosines")
    normal = np.cross(orientation[:3], orientation[3:])
    norm = float(np.linalg.norm(normal))
    if norm <= 1e-8:
        raise PublicCaseIntakeError("DICOM row and column directions are degenerate")
    return normal / norm


def build_affine_ras(orientation_lps: Iterable[float], pixel_spacing_rc_mm: Iterable[float],
                     origin_lps_mm: Iterable[float], slice_step_mm: float) -> np.ndarray:
    orientation = np.asarray(tuple(orientation_lps), dtype=np.float64)
    spacing = np.asarray(tuple(pixel_spacing_rc_mm), dtype=np.float64)
    origin = np.asarray(tuple(origin_lps_mm), dtype=np.float64)
    if spacing.shape != (2,) or np.any(spacing <= 0) or slice_step_mm <= 0:
        raise PublicCaseIntakeError("voxel spacing must be positive")
    affine = np.eye(4, dtype=np.float64)
    affine[:3, 0] = orientation[:3] * spacing[1]
    affine[:3, 1] = orientation[3:] * spacing[0]
    affine[:3, 2] = slice_normal(orientation) * slice_step_mm
    affine[:3, 3] = origin
    return np.diag([-1.0, -1.0, 1.0, 1.0]) @ affine


def scan_series(dicom_dir: Path, expected_count: int, expected_modality: str) -> dict[str, Any]:
    paths = sorted(path for path in dicom_dir.iterdir() if path.is_file() and ".part" not in path.name)
    if len(paths) != expected_count:
        raise PublicCaseIntakeError(f"{dicom_dir}: expected {expected_count} files, found {len(paths)}")
    headers = [read_header(path) for path in paths]
    modalities, dimensions = {x.modality for x in headers}, {(x.rows, x.columns) for x in headers}
    series_uids, frame_uids = {x.series_uid for x in headers}, {x.frame_uid for x in headers}
    if modalities != {expected_modality}:
        raise PublicCaseIntakeError(f"unexpected modality values: {sorted(modalities)}")
    if len(dimensions) != 1 or len(series_uids) != 1 or len(frame_uids) != 1:
        raise PublicCaseIntakeError("DICOM series identifiers or matrix dimensions are inconsistent")
    orientation, spacing = np.asarray(headers[0].orientation_lps), np.asarray(headers[0].pixel_spacing_rc_mm)
    if max(float(np.max(np.abs(np.asarray(x.orientation_lps) - orientation))) for x in headers) > 1e-5:
        raise PublicCaseIntakeError("per-slice orientation is inconsistent")
    if max(float(np.max(np.abs(np.asarray(x.pixel_spacing_rc_mm) - spacing))) for x in headers) > 1e-5:
        raise PublicCaseIntakeError("per-slice pixel spacing is inconsistent")

    normal = slice_normal(orientation)
    positions = np.asarray([np.dot(x.position_lps_mm, normal) for x in headers])
    order = np.argsort(positions, kind="stable")
    headers, positions = [headers[int(i)] for i in order], positions[order]
    retained: list[SliceHeader] = []
    retained_positions: list[float] = []
    duplicates: list[str] = []
    for header, position in zip(headers, positions):
        if retained_positions and abs(float(position) - retained_positions[-1]) <= 1e-6:
            prior = retained[-1]
            if not header.sop_uid or header.sop_uid != prior.sop_uid or sha256_file(header.path) != sha256_file(prior.path):
                raise PublicCaseIntakeError("distinct DICOM images occupy the same slice position")
            duplicates.append(header.path.name)
        else:
            retained.append(header)
            retained_positions.append(float(position))
    headers, positions = retained, np.asarray(retained_positions, dtype=np.float64)
    differences = np.diff(positions)
    if differences.size == 0 or np.any(differences <= 0):
        raise PublicCaseIntakeError("slice positions are not unique and monotonic")
    slice_step = float(np.median(differences))
    grid_indices = np.rint((positions - positions[0]) / slice_step).astype(int)
    grid_errors = np.abs(positions - (positions[0] + grid_indices * slice_step))
    geometry_valid = float(np.max(grid_errors)) <= max(1e-3, slice_step * 1e-3)
    if not geometry_valid:
        raise PublicCaseIntakeError("slice positions do not lie on one regular physical lattice")
    regularized_count = int(grid_indices[-1]) + 1
    missing_indices = sorted(set(range(regularized_count)) - set(int(x) for x in grid_indices))
    missing_positions = [float(positions[0] + index * slice_step) for index in missing_indices]
    affine = build_affine_ras(orientation, spacing, headers[0].position_lps_mm, slice_step)
    shape = (headers[0].columns, headers[0].rows, regularized_count)
    corners = np.asarray([[x, y, z, 1.0] for x in (0, shape[0]-1) for y in (0, shape[1]-1) for z in (0, shape[2]-1)])
    world = (affine @ corners.T).T[:, :3]
    return {
        "headers": headers, "slice_grid_indices": grid_indices.tolist(), "shape_xyz": list(shape),
        "spacing_mm_xyz": [float(spacing[1]), float(spacing[0]), slice_step],
        "affine_ijk_to_ras_mm": affine.tolist(), "orientation_lps": orientation.tolist(),
        "slice_position_range_mm": [float(positions[0]), float(positions[-1])],
        "slice_step_max_deviation_mm": float(np.max(np.abs(differences - slice_step))),
        "geometry_valid": geometry_valid, "source_grid_complete": not missing_indices,
        "source_file_count": len(paths), "retained_source_slice_count": len(headers),
        "regularized_slice_count": regularized_count, "excluded_exact_duplicate_files": duplicates,
        "missing_slice_indices": missing_indices, "missing_slice_positions_mm": missing_positions,
        "regularization_method": "none" if not missing_indices else "linear_interpolation_on_physical_slice_lattice",
        "modality": expected_modality, "series_uid": next(iter(series_uids)),
        "frame_of_reference_uid": next(iter(frame_uids)),
        "world_bounds_ras_mm": [world.min(axis=0).tolist(), world.max(axis=0).tolist()],
    }


def load_scaled_volume(series: dict[str, Any]) -> np.ndarray:
    volume = np.full(tuple(series["shape_xyz"]), np.nan, dtype=np.float32)
    present = [int(value) for value in series["slice_grid_indices"]]
    for header, index in zip(series["headers"], present):
        ds = pydicom.dcmread(str(header.path), force=True)
        plane = ds.pixel_array.astype(np.float32)
        volume[:, :, index] = (plane * float(getattr(ds, "RescaleSlope", 1.0)) + float(getattr(ds, "RescaleIntercept", 0.0))).T
    for missing in series["missing_slice_indices"]:
        lower = max((index for index in present if index < missing), default=None)
        upper = min((index for index in present if index > missing), default=None)
        if lower is None or upper is None:
            raise PublicCaseIntakeError("cannot interpolate a missing edge slice")
        weight = (missing - lower) / (upper - lower)
        volume[:, :, missing] = volume[:, :, lower] * (1.0-weight) + volume[:, :, upper] * weight
    if np.any(~np.isfinite(volume)):
        raise PublicCaseIntakeError("regularized volume contains non-finite voxels")
    return volume


def save_nifti(series: dict[str, Any], destination: Path) -> dict[str, Any]:
    volume, affine = load_scaled_volume(series), np.asarray(series["affine_ijk_to_ras_mm"], dtype=np.float64)
    image = nib.Nifti1Image(volume, affine)
    image.set_qform(affine, code=1); image.set_sform(affine, code=1); image.header.set_xyzt_units("mm")
    destination.parent.mkdir(parents=True, exist_ok=True)
    nib.save(image, str(destination))
    return {"path": str(destination.relative_to(ROOT)), "sha256": sha256_file(destination),
            "shape_xyz": list(volume.shape), "dtype": str(volume.dtype),
            "intensity_range": [float(np.min(volume)), float(np.max(volume))],
            "interpolated_slice_count": len(series["missing_slice_indices"])}


def _public_summary(series: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in series.items() if key not in {"headers", "slice_grid_indices"}}


def run_intake(manifest_path: Path, output_dir: Path, write_nifti: bool) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("case_id") != "nlm_additional_head_72m":
        raise PublicCaseIntakeError("unexpected public case identifier")
    series_manifest = {item["series"]: item for item in manifest["series"]}
    ct = scan_series(ROOT/series_manifest["ct"]["dicom_dir"], series_manifest["ct"]["file_count"], "CT")
    t2 = scan_series(ROOT/series_manifest["t2"]["dicom_dir"], series_manifest["t2"]["file_count"], "MR")
    same_frame = ct["frame_of_reference_uid"] == t2["frame_of_reference_uid"]
    output_dir.mkdir(parents=True, exist_ok=True)
    nifti = {}
    if write_nifti:
        nifti = {"ct": save_nifti(ct, output_dir/"ct_native_ras.nii.gz"),
                  "t2": save_nifti(t2, output_dir/"t2_native_ras.nii.gz")}
    result = {
        "intake_version": "1.0.0", "case_id": manifest["case_id"],
        "source_manifest": str(manifest_path.relative_to(ROOT)), "source_manifest_sha256": sha256_file(manifest_path),
        "subject_semantics": manifest["subject_semantics"], "series": {"ct": _public_summary(ct), "t2": _public_summary(t2)},
        "nifti": nifti, "checks": {"ct_geometry_valid": ct["geometry_valid"], "t2_geometry_valid": t2["geometry_valid"],
            "ct_source_grid_complete": ct["source_grid_complete"], "t2_source_grid_complete": t2["source_grid_complete"],
            "shared_frame_of_reference": same_frame},
        "registration_status": "native_alignment_valid" if same_frame else "rigid_registration_required",
        "pressure_executed": False, "clinical_safety_claim": False,
        "claim_boundary": "public_postmortem_research_imaging_input_only",
    }
    (output_dir/"intake_report.json").write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit and convert the NLM Additional Head CT/T2 public case.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write-nifti", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run_intake(args.manifest.resolve(), args.output_dir.resolve(), args.write_nifti), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
