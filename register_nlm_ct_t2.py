from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import nibabel as nib
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage, optimize
from nibabel.processing import resample_to_output


ROOT = Path(__file__).resolve().parent
DEFAULT_CT = ROOT / "outputs" / "nlm_public_case_intake_20260722" / "ct_native_ras.nii.gz"
DEFAULT_T2 = ROOT / "outputs" / "nlm_public_case_intake_20260722" / "t2_native_ras.nii.gz"
DEFAULT_OUTPUT = ROOT / "outputs" / "nlm_ct_t2_registration_20260722"


class RegistrationError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def largest_component(mask: np.ndarray) -> np.ndarray:
    labels, count = ndimage.label(mask)
    if count == 0:
        raise RegistrationError("foreground mask is empty")
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return labels == int(np.argmax(sizes))


def otsu_threshold(values: np.ndarray, bins: int = 256) -> float:
    finite = np.asarray(values[np.isfinite(values)], dtype=np.float64)
    if finite.size == 0 or float(finite.max()) <= float(finite.min()):
        raise RegistrationError("cannot threshold an empty or constant image")
    histogram, edges = np.histogram(finite, bins=bins, range=(float(finite.min()), float(finite.max())))
    probabilities = histogram.astype(np.float64) / float(histogram.sum())
    centers = (edges[:-1] + edges[1:]) * 0.5
    omega = np.cumsum(probabilities)
    mean = np.cumsum(probabilities * centers)
    total_mean = mean[-1]
    denominator = omega * (1.0 - omega)
    variance = np.zeros_like(denominator)
    valid = denominator > 0
    variance[valid] = (total_mean * omega[valid] - mean[valid]) ** 2 / denominator[valid]
    return float(centers[int(np.argmax(variance))])


def world_centroid(mask: np.ndarray, affine: np.ndarray) -> np.ndarray:
    coordinates = np.argwhere(mask)
    if coordinates.size == 0:
        raise RegistrationError("cannot compute centroid of empty mask")
    centroid_ijk = coordinates.mean(axis=0)
    return (affine @ np.asarray([*centroid_ijk, 1.0]))[:3]


def rotation_matrix_xyz(degrees_xyz: np.ndarray) -> np.ndarray:
    x, y, z = np.deg2rad(np.asarray(degrees_xyz, dtype=np.float64))
    rx = np.asarray([[1, 0, 0], [0, np.cos(x), -np.sin(x)], [0, np.sin(x), np.cos(x)]])
    ry = np.asarray([[np.cos(y), 0, np.sin(y)], [0, 1, 0], [-np.sin(y), 0, np.cos(y)]])
    rz = np.asarray([[np.cos(z), -np.sin(z), 0], [np.sin(z), np.cos(z), 0], [0, 0, 1]])
    return rz @ ry @ rx


def rigid_transform(parameters: np.ndarray, moving_center: np.ndarray, fixed_center: np.ndarray) -> np.ndarray:
    transform = np.eye(4, dtype=np.float64)
    transform[:3, :3] = rotation_matrix_xyz(parameters[:3])
    transform[:3, 3] = fixed_center + np.asarray(parameters[3:]) - transform[:3, :3] @ moving_center
    return transform


def resample_array(moving: np.ndarray, moving_affine: np.ndarray, fixed_shape: tuple[int, int, int],
                   fixed_affine: np.ndarray, moving_to_fixed: np.ndarray, order: int) -> np.ndarray:
    mapping = np.linalg.inv(moving_affine) @ np.linalg.inv(moving_to_fixed) @ fixed_affine
    return ndimage.affine_transform(
        moving, mapping[:3, :3], offset=mapping[:3, 3], output_shape=fixed_shape,
        order=order, mode="constant", cval=0.0, prefilter=order > 1,
    )


def normalized_mutual_information(fixed: np.ndarray, moving: np.ndarray, valid: np.ndarray, bins: int = 48) -> float:
    if int(valid.sum()) < 1000:
        return 0.0
    x, y = fixed[valid], moving[valid]
    histogram, _, _ = np.histogram2d(x, y, bins=bins)
    probability = histogram / float(histogram.sum())
    px, py = probability.sum(axis=1), probability.sum(axis=0)
    nonzero_joint = probability > 0
    hx = -float(np.sum(px[px > 0] * np.log(px[px > 0])))
    hy = -float(np.sum(py[py > 0] * np.log(py[py > 0])))
    hxy = -float(np.sum(probability[nonzero_joint] * np.log(probability[nonzero_joint])))
    return (hx + hy) / hxy if hxy > 0 else 0.0


def dice_score(fixed_mask: np.ndarray, moving_mask: np.ndarray) -> float:
    denominator = int(fixed_mask.sum()) + int(moving_mask.sum())
    return 2.0 * float(np.logical_and(fixed_mask, moving_mask).sum()) / denominator if denominator else 0.0


def prepare_coarse(image: nib.spatialimages.SpatialImage, voxel_mm: float) -> tuple[np.ndarray, np.ndarray]:
    coarse = resample_to_output(image, voxel_sizes=(voxel_mm, voxel_mm, voxel_mm), order=1)
    return np.asarray(coarse.get_fdata(dtype=np.float32)), np.asarray(coarse.affine, dtype=np.float64)


def make_masks(ct: np.ndarray, t2: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    ct_mask = largest_component(ct > -500.0)
    ct_mask = ndimage.binary_fill_holes(ndimage.binary_closing(ct_mask, iterations=1))
    positive = t2[t2 > 0]
    threshold = otsu_threshold(positive)
    t2_mask = largest_component(t2 > threshold)
    t2_mask = ndimage.binary_fill_holes(ndimage.binary_closing(t2_mask, iterations=1))
    return ct_mask, t2_mask, threshold


def evaluate(parameters: np.ndarray, ct: np.ndarray, t2: np.ndarray, ct_affine: np.ndarray,
             t2_affine: np.ndarray, ct_mask: np.ndarray, t2_mask: np.ndarray,
             moving_center: np.ndarray, fixed_center: np.ndarray) -> dict[str, float]:
    transform = rigid_transform(parameters, moving_center, fixed_center)
    moved_t2 = resample_array(t2, t2_affine, ct.shape, ct_affine, transform, order=1)
    moved_mask = resample_array(t2_mask.astype(np.uint8), t2_affine, ct.shape, ct_affine, transform, order=0) > 0
    valid = ct_mask & moved_mask & (moved_t2 > 0)
    fixed_scaled = np.clip(ct, -200.0, 1200.0)
    moving_high = float(np.percentile(moved_t2[valid], 99.0)) if np.any(valid) else 1.0
    moving_scaled = np.clip(moved_t2, 0.0, max(moving_high, 1.0))
    return {
        "nmi": normalized_mutual_information(fixed_scaled, moving_scaled, valid),
        "dice": dice_score(ct_mask, moved_mask),
        "overlap_voxels": int(valid.sum()),
    }


def optimize_registration(ct: np.ndarray, t2: np.ndarray, ct_affine: np.ndarray, t2_affine: np.ndarray,
                          ct_mask: np.ndarray, t2_mask: np.ndarray) -> tuple[np.ndarray, dict, dict, optimize.OptimizeResult]:
    fixed_center, moving_center = world_centroid(ct_mask, ct_affine), world_centroid(t2_mask, t2_affine)

    def objective(parameters: np.ndarray) -> float:
        metrics = evaluate(parameters, ct, t2, ct_affine, t2_affine, ct_mask, t2_mask, moving_center, fixed_center)
        return -(metrics["nmi"] + 0.35 * metrics["dice"])

    initial = np.zeros(6, dtype=np.float64)
    before = evaluate(initial, ct, t2, ct_affine, t2_affine, ct_mask, t2_mask, moving_center, fixed_center)
    bounds = [(-12.0, 12.0)] * 3 + [(-30.0, 30.0)] * 3
    global_result = optimize.differential_evolution(
        objective, bounds=bounds, seed=20260722, maxiter=10, popsize=5, polish=False,
        workers=1, updating="immediate", atol=1e-4,
    )
    local_result = optimize.minimize(
        objective, global_result.x, method="Powell", bounds=bounds,
        options={"maxiter": 80, "xtol": 0.05, "ftol": 1e-5},
    )
    parameters = np.asarray(local_result.x if local_result.fun <= global_result.fun else global_result.x)
    after = evaluate(parameters, ct, t2, ct_affine, t2_affine, ct_mask, t2_mask, moving_center, fixed_center)
    result = local_result if local_result.fun <= global_result.fun else global_result
    return parameters, before, after, result


def _normalize_panel(array: np.ndarray, low: float, high: float) -> np.ndarray:
    return (np.clip((array-low)/(high-low), 0, 1)*255).astype(np.uint8)


def save_preview(ct: np.ndarray, moved_t2: np.ndarray, ct_mask: np.ndarray, destination: Path) -> None:
    overlap = ct_mask & (moved_t2 > 0)
    areas = overlap.sum(axis=(0, 1))
    z = int(np.argmax(areas))
    ct_gray = _normalize_panel(ct[:, :, z].T, -200.0, 1200.0)
    t2_high = max(float(np.percentile(moved_t2[moved_t2 > 0], 99)), 1.0)
    t2_gray = _normalize_panel(moved_t2[:, :, z].T, 0.0, t2_high)
    overlay = np.stack([ct_gray, t2_gray, ct_gray], axis=2)
    panels = [Image.fromarray(np.repeat(ct_gray[:, :, None], 3, axis=2)),
              Image.fromarray(np.repeat(t2_gray[:, :, None], 3, axis=2)), Image.fromarray(overlay)]
    canvas = Image.new("RGB", (900, 330), "white")
    draw = ImageDraw.Draw(canvas)
    for index, (panel, title) in enumerate(zip(panels, ("CT", "Registered T2", "CT/T2 overlay"))):
        panel.thumbnail((300, 300), Image.Resampling.LANCZOS)
        canvas.paste(panel, (index*300, 30)); draw.text((index*300+8, 8), title, fill="black")
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination)


def register(ct_path: Path, t2_path: Path, output_dir: Path, coarse_mm: float) -> dict:
    ct_image, t2_image = nib.load(str(ct_path)), nib.load(str(t2_path))
    ct_coarse, ct_affine = prepare_coarse(ct_image, coarse_mm)
    t2_coarse, t2_affine = prepare_coarse(t2_image, coarse_mm)
    ct_mask, t2_mask, t2_threshold = make_masks(ct_coarse, t2_coarse)
    parameters, before, after, optimizer_result = optimize_registration(
        ct_coarse, t2_coarse, ct_affine, t2_affine, ct_mask, t2_mask
    )
    fixed_center, moving_center = world_centroid(ct_mask, ct_affine), world_centroid(t2_mask, t2_affine)
    transform = rigid_transform(parameters, moving_center, fixed_center)
    plausible = bool(np.max(np.abs(parameters[:3])) <= 12.0 and np.linalg.norm(parameters[3:]) <= 45.0)
    improved = bool(after["nmi"] > before["nmi"] and after["dice"] > before["dice"])
    quantitative_pass = bool(plausible and improved and after["dice"] >= 0.55 and after["nmi"] >= 1.05)
    output_dir.mkdir(parents=True, exist_ok=True)
    transform_path = output_dir / "t2_to_ct_rigid_transform.json"
    transform_record = {
        "transform_version": "1.0.0", "type": "rigid_6dof", "moving": "t2", "fixed": "ct",
        "matrix_moving_ras_to_fixed_ras_mm": transform.tolist(), "parameters_rotation_deg_translation_mm": parameters.tolist(),
        "coarse_voxel_mm": coarse_mm, "optimizer_success": bool(optimizer_result.success),
    }
    transform_path.write_text(json.dumps(transform_record, indent=2)+"\n", encoding="utf-8")
    output_nifti = output_dir / "t2_registered_to_ct_coarse.nii.gz"
    moved_t2 = resample_array(t2_coarse, t2_affine, ct_coarse.shape, ct_affine, transform, order=1).astype(np.float32)
    registered = nib.Nifti1Image(moved_t2, ct_affine)
    registered.set_qform(ct_affine, code=1); registered.set_sform(ct_affine, code=1)
    nib.save(registered, str(output_nifti))
    preview_path = output_dir / "registration_preview.png"
    save_preview(ct_coarse, moved_t2, ct_mask, preview_path)
    report = {
        "registration_version": "1.0.0", "case_id": "nlm_additional_head_72m",
        "fixed_ct_path": str(ct_path.relative_to(ROOT)), "fixed_ct_sha256": sha256_file(ct_path),
        "moving_t2_path": str(t2_path.relative_to(ROOT)), "moving_t2_sha256": sha256_file(t2_path),
        "transform_path": str(transform_path.relative_to(ROOT)), "transform_sha256": sha256_file(transform_path),
        "registered_coarse_t2_path": str(output_nifti.relative_to(ROOT)), "registered_coarse_t2_sha256": sha256_file(output_nifti),
        "preview_path": str(preview_path.relative_to(ROOT)), "metrics_before": before, "metrics_after": after,
        "checks": {"metrics_improved": improved, "transform_plausible": plausible, "quantitative_gate_pass": quantitative_pass,
                   "manual_visual_qc_pass": False},
        "status": "awaiting_manual_visual_qc" if quantitative_pass else "quantitative_registration_gate_failed",
        "registered_anatomical_roi_ready": False, "pressure_executed": False, "clinical_safety_claim": False,
        "claim_boundary": "postmortem_public_multimodal_rigid_registration_research_qc_only",
        "t2_mask_otsu_threshold": t2_threshold,
    }
    (output_dir / "registration_report.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Rigidly register public NLM T2 to CT with quantitative QC gates.")
    parser.add_argument("--ct", type=Path, default=DEFAULT_CT); parser.add_argument("--t2", type=Path, default=DEFAULT_T2)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT); parser.add_argument("--coarse-mm", type=float, default=4.0)
    args = parser.parse_args()
    print(json.dumps(register(args.ct.resolve(), args.t2.resolve(), args.output_dir.resolve(), args.coarse_mm), indent=2))


if __name__ == "__main__":
    main()
