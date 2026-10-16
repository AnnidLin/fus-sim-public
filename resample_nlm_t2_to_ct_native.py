from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parent
DEFAULT_CT = ROOT / "outputs" / "nlm_public_case_intake_20260722" / "ct_native_ras.nii.gz"
DEFAULT_T2 = ROOT / "outputs" / "nlm_public_case_intake_20260722" / "t2_native_ras.nii.gz"
DEFAULT_TRANSFORM = ROOT / "outputs" / "nlm_ct_t2_registration_20260722" / "t2_to_ct_rigid_transform.json"
DEFAULT_QC = ROOT / "outputs" / "nlm_ct_t2_registration_20260722" / "registration_qc_report.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "nlm_ct_t2_native_resample_20260723"


class NativeResampleError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fixed_to_moving_voxel_mapping(
    fixed_affine: np.ndarray, moving_affine: np.ndarray, moving_to_fixed: np.ndarray
) -> np.ndarray:
    mapping = np.linalg.inv(moving_affine) @ np.linalg.inv(moving_to_fixed) @ fixed_affine
    if mapping.shape != (4, 4) or not np.all(np.isfinite(mapping)):
        raise NativeResampleError("invalid fixed-to-moving voxel mapping")
    return mapping


def block_offset(mapping: np.ndarray, z_start: int) -> np.ndarray:
    return mapping[:3, 3] + mapping[:3, :3] @ np.asarray([0.0, 0.0, float(z_start)])


def close_memmap(array: np.memmap) -> None:
    array.flush()
    handle = getattr(array, "_mmap", None)
    if handle is not None:
        handle.close()


def resample_blockwise(
    moving: np.ndarray, output: np.memmap, mapping: np.ndarray, block_slices: int
) -> None:
    if block_slices < 1:
        raise NativeResampleError("block_slices must be positive")
    for z_start in range(0, output.shape[2], block_slices):
        depth = min(block_slices, output.shape[2] - z_start)
        output[:, :, z_start : z_start + depth] = ndimage.affine_transform(
            moving,
            mapping[:3, :3],
            offset=block_offset(mapping, z_start),
            output_shape=(output.shape[0], output.shape[1], depth),
            order=1,
            mode="constant",
            cval=0.0,
            prefilter=False,
        )
    output.flush()


def run(
    ct_path: Path,
    t2_path: Path,
    transform_path: Path,
    qc_path: Path,
    output_dir: Path,
    block_slices: int,
) -> dict:
    qc = json.loads(qc_path.read_text(encoding="utf-8"))
    if qc.get("research_registration_ready") is not True:
        raise NativeResampleError("research registration QC must pass before native-grid resampling")
    transform_record = json.loads(transform_path.read_text(encoding="utf-8"))
    transform = np.asarray(transform_record["matrix_moving_ras_to_fixed_ras_mm"], dtype=np.float64)
    ct_image, t2_image = nib.load(str(ct_path)), nib.load(str(t2_path))
    if len(ct_image.shape) != 3 or len(t2_image.shape) != 3:
        raise NativeResampleError("CT and T2 must be three-dimensional")
    moving = np.asarray(t2_image.get_fdata(dtype=np.float32))
    mapping = fixed_to_moving_voxel_mapping(ct_image.affine, t2_image.affine, transform)
    output_dir.mkdir(parents=True, exist_ok=True)
    work_path = output_dir / "t2_native_resample_work.dat"
    output = np.memmap(work_path, mode="w+", dtype=np.float32, shape=ct_image.shape)
    result_image = None
    try:
        resample_blockwise(moving, output, mapping, block_slices)
        output_path = output_dir / "t2_registered_to_ct_native.nii.gz"
        result_image = nib.Nifti1Image(output, ct_image.affine)
        result_image.set_qform(ct_image.affine, code=1)
        result_image.set_sform(ct_image.affine, code=1)
        result_image.header.set_xyzt_units("mm")
        nib.save(result_image, str(output_path))
        positive_voxels = int(np.count_nonzero(output > 0))
        intensity_range = [float(np.min(output)), float(np.max(output))]
    finally:
        if result_image is not None:
            del result_image
        close_memmap(output)
        del output
        work_path.unlink(missing_ok=True)
    saved = nib.load(str(output_path))
    affine_matches = bool(np.allclose(saved.affine, ct_image.affine, rtol=0.0, atol=1e-5))
    shape_matches = tuple(saved.shape) == tuple(ct_image.shape)
    if not affine_matches or not shape_matches or positive_voxels == 0:
        raise NativeResampleError("native-grid output failed geometry or coverage validation")
    report = {
        "resample_version": "1.0.1",
        "case_id": "nlm_additional_head_72m",
        "source_t2_path": str(t2_path.relative_to(ROOT)),
        "source_t2_sha256": sha256_file(t2_path),
        "fixed_ct_path": str(ct_path.relative_to(ROOT)),
        "fixed_ct_sha256": sha256_file(ct_path),
        "transform_path": str(transform_path.relative_to(ROOT)),
        "transform_sha256": sha256_file(transform_path),
        "registration_qc_path": str(qc_path.relative_to(ROOT)),
        "output_path": str(output_path.relative_to(ROOT)),
        "output_sha256": sha256_file(output_path),
        "shape_xyz": list(saved.shape),
        "affine_ijk_to_ras_mm": saved.affine.tolist(),
        "positive_voxel_count": positive_voxels,
        "intensity_range": intensity_range,
        "checks": {
            "shape_matches_ct": shape_matches,
            "affine_matches_ct": affine_matches,
            "research_registration_qc_passed": True,
            "codex_visual_review_passed": qc.get("codex_visual_review") == "pass",
            "expert_human_visual_qc_passed": False,
            "temporary_memmap_removed": not work_path.exists(),
        },
        "native_grid_candidate_ready": True,
        "registered_anatomical_roi_ready": False,
        "pressure_executed": False,
        "clinical_safety_claim": False,
        "claim_boundary": "postmortem_public_native_grid_registration_candidate_not_expert_or_clinical_validation",
    }
    (output_dir / "native_resample_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Resample the research-ready NLM T2 candidate onto the native CT grid.")
    parser.add_argument("--ct", type=Path, default=DEFAULT_CT)
    parser.add_argument("--t2", type=Path, default=DEFAULT_T2)
    parser.add_argument("--transform", type=Path, default=DEFAULT_TRANSFORM)
    parser.add_argument("--registration-qc", type=Path, default=DEFAULT_QC)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--block-slices", type=int, default=16)
    args = parser.parse_args()
    result = run(
        args.ct.resolve(), args.t2.resolve(), args.transform.resolve(),
        args.registration_qc.resolve(), args.output_dir.resolve(), args.block_slices,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
