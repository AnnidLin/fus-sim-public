from __future__ import annotations

import argparse
import json
from pathlib import Path

import nibabel as nib
import numpy as np
from PIL import Image, ImageDraw

import register_nlm_ct_t2 as registration


ROOT = Path(__file__).resolve().parent
DEFAULT_REGISTRATION = ROOT / "outputs" / "nlm_ct_t2_registration_20260722" / "registration_report.json"


def quantitative_checks(report: dict) -> dict[str, bool | float]:
    before, after = report["metrics_before"], report["metrics_after"]
    nmi_gain = float(after["nmi"] - before["nmi"])
    dice_change = float(after["dice"] - before["dice"])
    composite_before = float(before["nmi"] + 0.35 * before["dice"])
    composite_after = float(after["nmi"] + 0.35 * after["dice"])
    checks: dict[str, bool | float] = {
        "nmi_gain": nmi_gain,
        "dice_change": dice_change,
        "composite_before": composite_before,
        "composite_after": composite_after,
        "nmi_gain_at_least_0p02": nmi_gain >= 0.02,
        "final_dice_at_least_0p80": float(after["dice"]) >= 0.80,
        "dice_drop_within_0p02": dice_change >= -0.02,
        "composite_improved": composite_after > composite_before,
        "transform_plausible": bool(report["checks"]["transform_plausible"]),
    }
    checks["quantitative_gate_pass"] = all(
        bool(checks[key]) for key in (
            "nmi_gain_at_least_0p02", "final_dice_at_least_0p80", "dice_drop_within_0p02",
            "composite_improved", "transform_plausible",
        )
    )
    return checks


def normalize(array: np.ndarray, low: float, high: float) -> np.ndarray:
    return (np.clip((array - low) / (high - low), 0.0, 1.0) * 255).astype(np.uint8)


def overlay_panel(ct: np.ndarray, t2: np.ndarray) -> Image.Image:
    ct_gray = normalize(ct, -200.0, 1200.0)
    positive = t2[t2 > 0]
    high = max(float(np.percentile(positive, 99.0)), 1.0)
    t2_gray = normalize(t2, 0.0, high)
    rgb = np.stack([ct_gray, t2_gray, ct_gray // 3], axis=2)
    return Image.fromarray(rgb).resize((320, 320), Image.Resampling.NEAREST)


def save_orthogonal_preview(ct: np.ndarray, t2: np.ndarray, destination: Path) -> list[int]:
    overlap = (ct > -500.0) & (t2 > 0)
    center = tuple(int(round(value)) for value in np.argwhere(overlap).mean(axis=0))
    x, y, z = center
    planes = [
        (ct[:, :, z].T, t2[:, :, z].T, "Axial overlay"),
        (ct[:, y, :].T, t2[:, y, :].T, "Coronal overlay"),
        (ct[x, :, :].T, t2[x, :, :].T, "Sagittal overlay"),
    ]
    canvas = Image.new("RGB", (960, 350), "white")
    draw = ImageDraw.Draw(canvas)
    for index, (fixed, moving, title) in enumerate(planes):
        canvas.paste(overlay_panel(fixed, moving), (index * 320, 30))
        draw.text((index * 320 + 8, 8), title, fill="black")
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination)
    return list(center)


def finalize(registration_path: Path, codex_visual_review: str) -> dict:
    report = json.loads(registration_path.read_text(encoding="utf-8"))
    output_dir = registration_path.parent
    ct_image = nib.load(str(ROOT / report["fixed_ct_path"]))
    ct_coarse, _ = registration.prepare_coarse(ct_image, float(json.loads((ROOT / report["transform_path"]).read_text())["coarse_voxel_mm"]))
    t2_registered = np.asarray(nib.load(str(ROOT / report["registered_coarse_t2_path"])).get_fdata(dtype=np.float32))
    preview_path = output_dir / "registration_orthogonal_qc.png"
    review_center = save_orthogonal_preview(ct_coarse, t2_registered, preview_path)
    checks = quantitative_checks(report)
    if codex_visual_review not in {"pending", "pass", "fail"}:
        raise ValueError("codex visual review must be pending, pass, or fail")
    research_registration_ready = bool(checks["quantitative_gate_pass"] and codex_visual_review == "pass")
    result = {
        "qc_version": "1.0.0", "case_id": report["case_id"], "registration_report": str(registration_path.relative_to(ROOT)),
        "quantitative_checks": checks, "orthogonal_preview": str(preview_path.relative_to(ROOT)),
        "review_center_coarse_ijk": review_center, "codex_visual_review": codex_visual_review,
        "expert_human_visual_qc_pass": False, "research_registration_ready": research_registration_ready,
        "registered_anatomical_roi_ready": False,
        "status": "research_registration_ready_expert_review_pending" if research_registration_ready else "registration_qc_incomplete",
        "pressure_executed": False, "clinical_safety_claim": False,
        "claim_boundary": "postmortem_public_research_registration_not_expert_or_clinical_validation",
    }
    (output_dir / "registration_qc_report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize quantitative and orthogonal visual QC for NLM CT/T2 registration.")
    parser.add_argument("--registration-report", type=Path, default=DEFAULT_REGISTRATION)
    parser.add_argument("--codex-visual-review", choices=("pending", "pass", "fail"), default="pending")
    args = parser.parse_args()
    print(json.dumps(finalize(args.registration_report.resolve(), args.codex_visual_review), indent=2))


if __name__ == "__main__":
    main()
