#!/usr/bin/env python3
"""Decompose ITRUSST Phase-A amplitude-field disagreement.

This is a post-processing diagnostic only.  It never resamples fields and does
not alter benchmark outputs.  Small integer translations and a single global
least-squares amplitude factor are fitted on a fixed interior comparison mask
to distinguish displacement, gain, and residual shape disagreement.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from analyze_itrusst_benchmark import build_analysis_mask, load_array, load_contract


ROOT = Path(__file__).resolve().parent
DEFAULT_COMPARISONS = (
    ROOT / "outputs/itrusst_bm1_sc1_axisymmetric_ppw12_20260803/comparison.json",
    ROOT / "outputs/itrusst_bm3_sc1_axisymmetric_ppw12_retry1_20260804/comparison.json",
    ROOT / "outputs/itrusst_bm4_sc1_axisymmetric_ppw12_throttled_20260807/comparison.json",
)


def _shift_without_wrap(field: np.ndarray, shift: tuple[int, ...]) -> np.ndarray:
    result = np.full(field.shape, np.nan, dtype=np.float64)
    source: list[slice] = []
    target: list[slice] = []
    for size, offset in zip(field.shape, shift):
        if offset >= 0:
            source.append(slice(0, size - offset))
            target.append(slice(offset, size))
        else:
            source.append(slice(-offset, size))
            target.append(slice(0, size + offset))
    result[tuple(target)] = field[tuple(source)]
    return result


def _relative_l2(reference: np.ndarray, candidate: np.ndarray, mask: np.ndarray) -> float:
    ref = reference[mask]
    cand = candidate[mask]
    return 100.0 * float(np.linalg.norm(cand - ref) / np.linalg.norm(ref))


def _fit_scale(reference: np.ndarray, candidate: np.ndarray, mask: np.ndarray) -> float:
    ref = reference[mask]
    cand = candidate[mask]
    denominator = float(np.dot(cand, cand))
    if denominator <= 0:
        raise ValueError("candidate energy is zero")
    return float(np.dot(ref, cand) / denominator)


def diagnose_case(comparison_path: Path, max_shift_samples: int = 6) -> dict[str, Any]:
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    benchmark = int(str(comparison["benchmark"]).removeprefix("BM"))
    reference = np.asarray(
        load_array(Path(comparison["inputs"]["reference"]["path"])), dtype=np.float64
    ).squeeze()
    candidate = np.asarray(
        load_array(Path(comparison["inputs"]["candidate"]["path"])), dtype=np.float64
    ).squeeze()
    order = comparison.get("candidate_axis_order")
    if isinstance(order, list) and len(order) == candidate.ndim:
        candidate = np.transpose(candidate, tuple(int(item) for item in order))
    if reference.shape != candidate.shape or reference.ndim != 2:
        raise ValueError(
            f"{comparison_path}: expected matched 2-D fields, got "
            f"{reference.shape} and {candidate.shape}"
        )

    contract = load_contract()
    full_mask = build_analysis_mask(reference.shape, benchmark, 1, contract)
    # Keep the evaluation set fixed for every candidate shift.  This prevents a
    # shift from appearing better merely because it drops difficult edge voxels.
    interior = np.zeros(reference.shape, dtype=bool)
    margin = max_shift_samples
    interior[margin : reference.shape[0] - margin, margin : reference.shape[1] - margin] = True
    mask = full_mask & interior
    if not np.any(mask):
        raise ValueError("fixed interior analysis mask is empty")

    raw_l2 = _relative_l2(reference, candidate, mask)
    raw_scale = _fit_scale(reference, candidate, mask)
    scale_only_l2 = _relative_l2(reference, raw_scale * candidate, mask)
    best: dict[str, Any] | None = None
    for lateral_shift in range(-max_shift_samples, max_shift_samples + 1):
        for axial_shift in range(-max_shift_samples, max_shift_samples + 1):
            shift = (lateral_shift, axial_shift)
            shifted = _shift_without_wrap(candidate, shift)
            if not np.all(np.isfinite(shifted[mask])):
                continue
            shift_l2 = _relative_l2(reference, shifted, mask)
            scale = _fit_scale(reference, shifted, mask)
            combined_l2 = _relative_l2(reference, scale * shifted, mask)
            item = {
                "shift_samples_lateral_axial": list(shift),
                "shift_only_relative_l2_percent": shift_l2,
                "fitted_reference_over_candidate_scale": scale,
                "shift_and_scale_relative_l2_percent": combined_l2,
            }
            if best is None or combined_l2 < best["shift_and_scale_relative_l2_percent"]:
                best = item
    assert best is not None

    ref_values = reference[mask]
    cand_values = candidate[mask]
    correlation = float(np.corrcoef(ref_values, cand_values)[0, 1])
    reference_peak = float(np.max(reference[mask]))
    amplitude_bands: dict[str, Any] = {}
    previous_threshold = float("inf")
    for label, db in (("main_lobe_0_to_minus6db", 6), ("near_field_minus6_to_minus12db", 12)):
        threshold = reference_peak * 10.0 ** (-db / 20.0)
        band_mask = mask & (reference >= threshold) & (reference < previous_threshold)
        if np.any(band_mask):
            band_scale = _fit_scale(reference, candidate, band_mask)
            amplitude_bands[label] = {
                "voxels": int(np.count_nonzero(band_mask)),
                "raw_relative_l2_percent": _relative_l2(reference, candidate, band_mask),
                "fitted_reference_over_candidate_scale": band_scale,
                "scaled_relative_l2_percent": _relative_l2(
                    reference, band_scale * candidate, band_mask
                ),
            }
        previous_threshold = threshold
    background_mask = mask & (reference < previous_threshold)
    if np.any(background_mask):
        background_scale = _fit_scale(reference, candidate, background_mask)
        amplitude_bands["below_minus12db"] = {
            "voxels": int(np.count_nonzero(background_mask)),
            "raw_relative_l2_percent": _relative_l2(reference, candidate, background_mask),
            "fitted_reference_over_candidate_scale": background_scale,
            "scaled_relative_l2_percent": _relative_l2(
                reference, background_scale * candidate, background_mask
            ),
        }
    dx_mm = float(comparison["comparison_dx_mm"])
    shifts = best["shift_samples_lateral_axial"]
    return {
        "benchmark": f"BM{benchmark}",
        "comparison_path": str(comparison_path.resolve()),
        "shape": list(reference.shape),
        "fixed_mask_voxels": int(np.count_nonzero(mask)),
        "max_shift_samples": max_shift_samples,
        "comparison_dx_mm": dx_mm,
        "raw_fixed_mask_relative_l2_percent": raw_l2,
        "raw_pearson_correlation": correlation,
        "scale_only": {
            "fitted_reference_over_candidate_scale": raw_scale,
            "relative_l2_percent": scale_only_l2,
        },
        "best_shift_and_scale": {
            **best,
            "shift_mm_lateral_axial": [float(value) * dx_mm for value in shifts],
        },
        "reference_amplitude_bands": amplitude_bands,
        "l2_reduction_percentage_points": raw_l2
        - best["shift_and_scale_relative_l2_percent"],
        "interpretation_guardrail": (
            "Post-hoc diagnostic fit only; it is not a corrected benchmark result "
            "and must not replace the preregistered unaligned comparison."
        ),
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ITRUSST Phase-A discrepancy decomposition",
        "",
        "This report is a post-hoc diagnostic. Fitted shifts and gains do not alter the official benchmark results.",
        "",
        "| Case | Raw L2 (%) | Correlation | Scale-only L2 (%) | Best shift (lat, axial; mm) | Shift+scale L2 (%) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for case in report["cases"]:
        best = case["best_shift_and_scale"]
        shift = best["shift_mm_lateral_axial"]
        lines.append(
            f"| {case['benchmark']} | {case['raw_fixed_mask_relative_l2_percent']:.3f} | "
            f"{case['raw_pearson_correlation']:.5f} | {case['scale_only']['relative_l2_percent']:.3f} | "
            f"({shift[0]:.2f}, {shift[1]:.2f}) | {best['shift_and_scale_relative_l2_percent']:.3f} |"
        )
    lines.extend(
        [
            "",
            "Interpretation: a large decrease after shifting indicates spatial registration/focal displacement; "
            "a large decrease after scaling indicates global amplitude or attenuation disagreement; the remainder "
            "is shape disagreement or a more complex model difference.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-shift-samples", type=int, default=6)
    args = parser.parse_args()
    if args.max_shift_samples < 0:
        raise ValueError("max-shift-samples must be non-negative")
    report = {
        "schema_version": "1.0",
        "claim_level": "engineering_posthoc_diagnostic",
        "cases": [
            diagnose_case(path, args.max_shift_samples) for path in DEFAULT_COMPARISONS
        ],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "discrepancy_decomposition.json"
    md_path = args.output_dir / "discrepancy_decomposition.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"status": "completed", "json": str(json_path), "markdown": str(md_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
