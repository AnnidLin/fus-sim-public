from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import nibabel as nib
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage


ROOT = Path(__file__).resolve().parent
DEFAULT_CT = ROOT / "outputs" / "nlm_public_case_intake_20260722" / "ct_native_ras.nii.gz"
DEFAULT_OUTPUT = ROOT / "outputs" / "nlm_image_derived_proxy_roi_20260722"


class ProxyROIError(ValueError):
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
        raise ProxyROIError("foreground mask has no connected component")
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return labels == int(np.argmax(sizes))


def spherical_mask(shape: tuple[int, int, int], center: tuple[int, int, int],
                   spacing_mm: tuple[float, float, float], radius_mm: float) -> np.ndarray:
    if radius_mm <= 0:
        raise ProxyROIError("radius must be positive")
    grids = np.ogrid[tuple(slice(0, size) for size in shape)]
    squared = sum(((grid - coordinate) * spacing) ** 2 for grid, coordinate, spacing in zip(grids, center, spacing_mm))
    return squared <= radius_mm**2


def choose_deep_head_proxy(ct: np.ndarray, spacing_mm: tuple[float, float, float]) -> tuple[int, int, int]:
    bone_area = np.sum(ct >= 300.0, axis=(0, 1))
    skull_slices = np.flatnonzero(bone_area >= 1000)
    if skull_slices.size < 20:
        raise ProxyROIError("insufficient skull-bearing slices for proxy selection")
    lower = int(round(float(skull_slices[0] + 0.68 * (skull_slices[-1] - skull_slices[0]))))
    upper = int(round(float(skull_slices[0] + 0.82 * (skull_slices[-1] - skull_slices[0]))))
    best: tuple[float, tuple[int, int, int]] | None = None
    for z_index in range(lower, upper + 1):
        foreground = largest_component(ct[:, :, z_index] > -500.0)
        foreground = ndimage.binary_fill_holes(ndimage.binary_closing(foreground, iterations=3))
        distance = ndimage.distance_transform_edt(foreground, sampling=spacing_mm[:2])
        x_index, y_index = np.unravel_index(int(np.argmax(distance)), distance.shape)
        score = float(distance[x_index, y_index])
        candidate = (int(x_index), int(y_index), z_index)
        if best is None or score > best[0]:
            best = (score, candidate)
    if best is None or best[0] < 20.0:
        raise ProxyROIError("no sufficiently deep head proxy candidate found")
    return best[1]


def _window_ct(slice_data: np.ndarray) -> np.ndarray:
    normalized = np.clip((slice_data + 100.0) / 1100.0, 0.0, 1.0)
    return (normalized * 255).astype(np.uint8)


def save_preview(ct: np.ndarray, roi: np.ndarray, center: tuple[int, int, int], destination: Path) -> None:
    x, y, z = center
    panels = []
    for base, overlay in ((ct[:, :, z], roi[:, :, z]), (ct[x, :, :], roi[x, :, :])):
        gray = _window_ct(base).T
        rgb = np.repeat(gray[:, :, None], 3, axis=2)
        mask = overlay.T
        rgb[mask] = np.array([255, 40, 40], dtype=np.uint8)
        panels.append(Image.fromarray(rgb).resize((420, 420), Image.Resampling.NEAREST))
    canvas = Image.new("RGB", (840, 460), "white")
    canvas.paste(panels[0], (0, 40)); canvas.paste(panels[1], (420, 40))
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 10), "Axial CT + image-derived proxy", fill="black")
    draw.text((430, 10), "Sagittal CT + image-derived proxy", fill="black")
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination)


def generate(ct_path: Path, output_dir: Path, radius_mm: float) -> dict:
    image = nib.load(str(ct_path))
    ct = np.asanyarray(image.dataobj, dtype=np.float32)
    if ct.ndim != 3:
        raise ProxyROIError("CT must be three-dimensional")
    spacing = tuple(float(value) for value in image.header.get_zooms()[:3])
    center = choose_deep_head_proxy(ct, spacing)
    roi = spherical_mask(ct.shape, center, spacing, radius_mm)
    if np.any(ct[roi] >= 300.0):
        raise ProxyROIError("proxy sphere intersects thresholded bone")
    output_dir.mkdir(parents=True, exist_ok=True)
    mask_path = output_dir / "deep_head_proxy_mask.nii.gz"
    mask_image = nib.Nifti1Image(roi.astype(np.uint8), image.affine, image.header)
    mask_image.set_data_dtype(np.uint8)
    mask_image.set_qform(image.affine, code=1); mask_image.set_sform(image.affine, code=1)
    nib.save(mask_image, str(mask_path))
    preview_path = output_dir / "deep_head_proxy_preview.png"
    save_preview(ct, roi, center, preview_path)
    center_world = (image.affine @ np.asarray([*center, 1.0]))[:3]
    result = {
        "proxy_version": "1.0.0", "case_id": "nlm_additional_head_72m",
        "roi_id": "nlm_deep_head_image_derived_proxy_r5mm", "anatomical_status": "image_derived_proxy",
        "source_image": str(ct_path.relative_to(ROOT)), "source_image_sha256": sha256_file(ct_path),
        "mask_path": str(mask_path.relative_to(ROOT)), "mask_sha256": sha256_file(mask_path),
        "preview_path": str(preview_path.relative_to(ROOT)), "center_ijk": list(center),
        "center_ras_mm": center_world.tolist(), "radius_mm": radius_mm, "voxel_count": int(roi.sum()),
        "generation_method": "deepest_point_in_upper_skull_bearing_CT_range_plus_physical_sphere",
        "limitations": [
            "not_an_anatomical_segmentation", "not_a_tumor_or_lesion", "not_clinically_validated",
            "postmortem_formalin_preserved_donor", "five_CT_slices_were_linearly_interpolated_during_intake",
        ],
        "registration_ready": False, "pressure_executed": False, "clinical_safety_claim": False,
        "claim_boundary": "real_public_image_geometry_proxy_for_pipeline_testing_only",
    }
    (output_dir / "proxy_roi_report.json").write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a non-anatomical image-derived ROI proxy from public NLM CT.")
    parser.add_argument("--ct", type=Path, default=DEFAULT_CT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--radius-mm", type=float, default=5.0)
    args = parser.parse_args()
    print(json.dumps(generate(args.ct.resolve(), args.output_dir.resolve(), args.radius_mm), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
