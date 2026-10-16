from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import nibabel as nib
import numpy as np
from nibabel.processing import resample_from_to

from build_ct_acoustic_model import CTBuildConfig, apply_mapping_profile, save_model


ROOT = Path(__file__).resolve().parent
DEFAULT_CT = ROOT / "outputs" / "nlm_public_case_intake_20260722" / "ct_native_ras.nii.gz"
DEFAULT_PROFILE = ROOT / "acoustic_mapping_profiles" / "simple_hu300.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "nlm_ct_acoustic_model_affine_simple_hu300_dx0p75_20260723"


class AffineModelBuildError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def explicit_isotropic_grid(image: nib.spatialimages.SpatialImage, target_mm: float) -> tuple[tuple[int, int, int], np.ndarray]:
    if target_mm <= 0:
        raise AffineModelBuildError("target spacing must be positive")
    canonical = nib.as_closest_canonical(image)
    spatial = np.asarray(canonical.affine[:3, :3], dtype=np.float64)
    source_spacing = np.linalg.norm(spatial, axis=0)
    if np.any(source_spacing <= 0):
        raise AffineModelBuildError("source affine has invalid spacing")
    shape = tuple(int(value) for value in np.maximum(
        1, np.rint(np.asarray(canonical.shape[:3], dtype=float) * source_spacing / target_mm)
    ))
    directions = spatial / source_spacing
    affine = np.eye(4, dtype=np.float64)
    affine[:3, :3] = directions * target_mm
    affine[:3, 3] = canonical.affine[:3, 3]
    return shape, affine


def roundtrip_max_error_voxels(affine: np.ndarray, shape: tuple[int, int, int]) -> float:
    points = np.asarray([
        [x, y, z, 1.0]
        for x in (0, shape[0] - 1, (shape[0] - 1) / 2)
        for y in (0, shape[1] - 1, (shape[1] - 1) / 2)
        for z in (0, shape[2] - 1, (shape[2] - 1) / 2)
    ])
    world = (affine @ points.T).T
    recovered = (np.linalg.inv(affine) @ world.T).T
    return float(np.max(np.abs(recovered[:, :3] - points[:, :3])))


def attach_affine(source_npz: Path, destination_npz: Path, affine: np.ndarray) -> None:
    with np.load(source_npz, allow_pickle=False) as source:
        payload = {name: np.asarray(source[name]) for name in source.files}
    payload["affine_ijk_to_world_mm"] = np.asarray(affine, dtype=np.float64)
    np.savez_compressed(destination_npz, **payload)


def build(ct_path: Path, profile_path: Path, output_dir: Path, target_mm: float, max_shape: int) -> dict:
    source = nib.as_closest_canonical(nib.load(str(ct_path)))
    shape, affine = explicit_isotropic_grid(source, target_mm)
    if max(shape) > max_shape:
        raise AffineModelBuildError(f"requested grid {shape} exceeds max_shape={max_shape}")
    output_dir.mkdir(parents=True, exist_ok=True)
    resampled_path = output_dir / "ct_resampled_explicit_0p75mm_ras.nii.gz"
    resampled = resample_from_to(source, (shape, affine), order=1, mode="constant", cval=-1200.0)
    resampled.set_qform(affine, code=1); resampled.set_sform(affine, code=1)
    nib.save(resampled, str(resampled_path))
    config = CTBuildConfig(
        nifti_file=resampled_path,
        output_dir=output_dir,
        target_dx_m=target_mm * 1e-3,
        max_shape=max_shape,
    )
    save_model(apply_mapping_profile(config, profile_path))
    summary_path = output_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary["resampling"].get("resampled") is not False:
        raise AffineModelBuildError("core builder unexpectedly performed a second resampling")
    base_model = output_dir / "acoustic_model_3d.npz"
    affine_model = output_dir / "acoustic_model_3d_affine.npz"
    attach_affine(base_model, affine_model, affine)
    with np.load(affine_model, allow_pickle=False) as model:
        model_shape = tuple(model["labels"].shape)
        labels, counts = np.unique(model["labels"], return_counts=True)
        stored_affine = np.asarray(model["affine_ijk_to_world_mm"], dtype=np.float64)
    spacing = np.linalg.norm(stored_affine[:3, :3], axis=0)
    roundtrip = roundtrip_max_error_voxels(stored_affine, model_shape)
    checks = {
        "model_shape_matches_explicit_grid": model_shape == shape,
        "stored_affine_matches_explicit_grid": bool(np.allclose(stored_affine, affine, rtol=0.0, atol=1e-10)),
        "spacing_is_exact_0p75_mm": bool(np.allclose(spacing, target_mm, rtol=0.0, atol=1e-10)),
        "world_roundtrip_below_1e_6_voxel": roundtrip < 1e-6,
        "core_builder_second_resampling_disabled": summary["resampling"].get("resampled") is False,
        "labels_exactly_0_1_2": labels.tolist() == [0, 1, 2],
        "all_material_classes_nonempty": bool(np.all(counts > 0)),
    }
    if not all(checks.values()):
        raise AffineModelBuildError(f"affine model validation failed: {checks}")
    report = {
        "build_version": "1.0.0", "case_id": "nlm_additional_head_72m",
        "source_ct_path": str(ct_path.relative_to(ROOT)), "source_ct_sha256": sha256_file(ct_path),
        "resampled_ct_path": str(resampled_path.relative_to(ROOT)), "resampled_ct_sha256": sha256_file(resampled_path),
        "mapping_profile": str(profile_path.relative_to(ROOT)), "parameter_changes": False,
        "base_model_path": str(base_model.relative_to(ROOT)), "base_model_sha256": sha256_file(base_model),
        "affine_model_path": str(affine_model.relative_to(ROOT)), "affine_model_sha256": sha256_file(affine_model),
        "shape_xyz": list(model_shape), "spacing_mm_xyz": spacing.tolist(),
        "affine_ijk_to_world_mm": stored_affine.tolist(), "roundtrip_max_error_voxels": roundtrip,
        "label_counts": {str(int(label)): int(count) for label, count in zip(labels, counts)}, "checks": checks,
        "world_mapping": {"status": "available", "coordinate_system": "RAS_mm"},
        "registered_anatomical_roi_ready": False, "pressure_executed": False, "clinical_safety_claim": False,
        "claim_boundary": "coordinate_preserving_postmortem_public_binary_screening_model_not_paper_grade_or_clinical",
    }
    (output_dir / "affine_model_build_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an affine-preserving NLM public CT screening acoustic model.")
    parser.add_argument("--ct", type=Path, default=DEFAULT_CT)
    parser.add_argument("--mapping-profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--target-dx-mm", type=float, default=0.75)
    parser.add_argument("--max-shape", type=int, default=340)
    args = parser.parse_args()
    print(json.dumps(build(args.ct.resolve(), args.mapping_profile.resolve(), args.output_dir.resolve(), args.target_dx_mm, args.max_shape), indent=2))


if __name__ == "__main__":
    main()
