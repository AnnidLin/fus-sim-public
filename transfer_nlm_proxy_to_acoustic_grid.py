from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import nibabel as nib
import numpy as np
from nibabel.processing import resample_from_to


ROOT = Path(__file__).resolve().parent
DEFAULT_PROXY = ROOT / "outputs" / "nlm_image_derived_proxy_roi_20260722" / "deep_head_proxy_mask.nii.gz"
DEFAULT_PROXY_REPORT = ROOT / "outputs" / "nlm_image_derived_proxy_roi_20260722" / "proxy_roi_report.json"
DEFAULT_MODEL = ROOT / "outputs" / "nlm_ct_acoustic_model_affine_simple_hu300_dx0p75_20260723" / "acoustic_model_3d_affine.npz"
DEFAULT_OUTPUT = ROOT / "outputs" / "nlm_proxy_acoustic_grid_20260723"


class ProxyTransferError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def world_to_index(world_mm: np.ndarray, affine: np.ndarray) -> np.ndarray:
    point = np.asarray([*np.asarray(world_mm, dtype=np.float64), 1.0])
    return (np.linalg.inv(affine) @ point)[:3]


def transfer(proxy_path: Path, proxy_report_path: Path, model_path: Path, output_dir: Path) -> dict:
    proxy_report = json.loads(proxy_report_path.read_text(encoding="utf-8"))
    if proxy_report.get("anatomical_status") != "image_derived_proxy":
        raise ProxyTransferError("only image_derived_proxy inputs are accepted")
    proxy_image = nib.load(str(proxy_path))
    with np.load(model_path, allow_pickle=False) as model:
        if "affine_ijk_to_world_mm" not in model.files:
            raise ProxyTransferError("acoustic model has no authoritative affine")
        model_affine = np.asarray(model["affine_ijk_to_world_mm"], dtype=np.float64)
        model_shape = tuple(int(value) for value in model["labels"].shape)
    transferred = resample_from_to(proxy_image, (model_shape, model_affine), order=0, mode="constant", cval=0)
    mask = np.asarray(transferred.dataobj) > 0
    if not np.any(mask):
        raise ProxyTransferError("proxy became empty after nearest-neighbor transfer")
    center_float = world_to_index(np.asarray(proxy_report["center_ras_mm"]), model_affine)
    center = tuple(int(np.rint(value)) for value in center_float)
    if any(value < 0 or value >= size for value, size in zip(center, model_shape)):
        raise ProxyTransferError("proxy center lies outside acoustic grid")
    center_inside = bool(mask[center])
    if not center_inside:
        raise ProxyTransferError("transferred proxy does not contain its world-space center")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "deep_head_proxy_on_acoustic_grid.nii.gz"
    output_image = nib.Nifti1Image(mask.astype(np.uint8), model_affine)
    output_image.set_qform(model_affine, code=1); output_image.set_sform(model_affine, code=1)
    nib.save(output_image, str(output_path))
    report = {
        "transfer_version": "1.0.0", "case_id": "nlm_additional_head_72m",
        "roi_id": proxy_report["roi_id"], "anatomical_status": "image_derived_proxy",
        "source_proxy_path": str(proxy_path.relative_to(ROOT)), "source_proxy_sha256": sha256_file(proxy_path),
        "source_proxy_report": str(proxy_report_path.relative_to(ROOT)),
        "acoustic_model_path": str(model_path.relative_to(ROOT)), "acoustic_model_sha256": sha256_file(model_path),
        "output_mask_path": str(output_path.relative_to(ROOT)), "output_mask_sha256": sha256_file(output_path),
        "output_shape_xyz": list(model_shape), "mask_affine_ijk_to_world_mm": model_affine.tolist(),
        "center_world_ras_mm": proxy_report["center_ras_mm"], "center_model_ijk_float": center_float.tolist(),
        "center_model_ijk_rounded": list(center), "center_inside_mask": center_inside,
        "voxel_count": int(mask.sum()), "interpolation": "nearest_neighbor",
        "proxy_coordinate_transfer_ready": True, "registered_anatomical_roi_ready": False,
        "limitations": proxy_report["limitations"] + ["transferred_to_binary_HU300_screening_acoustic_grid"],
        "pressure_executed": False, "clinical_safety_claim": False,
        "claim_boundary": "world_mapped_image_derived_proxy_for_postmortem_public_pipeline_testing_only",
    }
    (output_dir / "proxy_transfer_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Transfer the NLM image-derived proxy onto the affine-aware acoustic grid.")
    parser.add_argument("--proxy", type=Path, default=DEFAULT_PROXY)
    parser.add_argument("--proxy-report", type=Path, default=DEFAULT_PROXY_REPORT)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(transfer(args.proxy.resolve(), args.proxy_report.resolve(), args.model.resolve(), args.output_dir.resolve()), indent=2))


if __name__ == "__main__":
    main()
