from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import ndimage

import register_nlm_ct_t2 as baseline


def make_outer_head_masks(ct: np.ndarray, t2: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    ct_mask = baseline.largest_component(ct > -500.0)
    ct_mask = ndimage.binary_fill_holes(ndimage.binary_closing(ct_mask, iterations=1))
    positive = t2[t2 > 0]
    if positive.size < 1000:
        raise baseline.RegistrationError("T2 has insufficient positive support")
    threshold = float(np.percentile(positive, 10.0))
    t2_mask = baseline.largest_component(t2 >= threshold)
    t2_mask = ndimage.binary_fill_holes(ndimage.binary_closing(t2_mask, iterations=1))
    return ct_mask, t2_mask, threshold


def register(ct_path: Path, t2_path: Path, output_dir: Path, coarse_mm: float) -> dict:
    baseline.make_masks = make_outer_head_masks
    report = baseline.register(ct_path, t2_path, output_dir, coarse_mm)
    old_threshold = report.pop("t2_mask_otsu_threshold")
    report["t2_outer_head_positive_percentile_10_threshold"] = old_threshold
    report["mask_semantics"] = "homologous_outer_head_support_masks"
    report["diagnostic_root_cause"] = "baseline_Otsu_T2_mask_selected_bright_internal_tissue_not_outer_head"
    (output_dir / "registration_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Corrected NLM CT/T2 rigid registration using homologous outer-head masks.")
    parser.add_argument("--ct", type=Path, default=baseline.DEFAULT_CT)
    parser.add_argument("--t2", type=Path, default=baseline.DEFAULT_T2)
    parser.add_argument("--output-dir", type=Path, default=baseline.DEFAULT_OUTPUT)
    parser.add_argument("--coarse-mm", type=float, default=4.0)
    args = parser.parse_args()
    print(json.dumps(register(args.ct.resolve(), args.t2.resolve(), args.output_dir.resolve(), args.coarse_mm), indent=2))


if __name__ == "__main__":
    main()
