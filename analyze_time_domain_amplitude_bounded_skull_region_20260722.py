from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from analyze_hotspot_transfer_20260721 import validate_transfer_inputs
from analyze_target_hard_constrained_hotspot_20260722 import array_hash, load_npz
from analyze_three_vector_skull_region_optimization_20260722 import (
    affine_two_endpoint_correction,
    field_ratios,
    response_ratio,
)
from design_dual_point_hotspot_constrained_tr_20260720 import (
    extract_transfer_phasor,
    null_projected_weights,
)
from prepare_dual_point_constrained_refocus_20260721 import normalize_max, realize_replay_phasors


ROOT = Path(__file__).resolve().parent
CONTROL_SIGNALS = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "offset_y-10p0_z-02p5" / "tr" / "element_signals.npz"
HOTSPOT1_SIGNALS = ROOT / "outputs" / "dual_point_hotspot_calibration_20260721" / "run" / "element_signals.npz"
HOTSPOT2_SIGNALS = ROOT / "outputs" / "second_skull_hotspot_calibration_20260722" / "run" / "element_signals.npz"
STRONG_SIGNALS = ROOT / "outputs" / "dual_point_constrained_refocus_20260721" / "run" / "element_signals.npz"
BLEND_SIGNALS = ROOT / "outputs" / "target_preserving_blend_validation_20260722" / "run" / "element_signals.npz"
EVIDENCE = ROOT / "outputs" / "evidence_briefs" / "time_domain_amplitude_bounded_skull_region_20260722" / "evidence_brief.json"
OUTPUT = ROOT / "outputs" / "time_domain_amplitude_bounded_skull_region_20260722"
HOTSPOTS = ((38, 39, 34), (40, 20, 18))


def simplex_coefficients(step: float) -> np.ndarray:
    reciprocal = round(1.0 / float(step))
    if step <= 0 or not np.isclose(reciprocal * step, 1.0, rtol=0.0, atol=1e-12):
        raise ValueError("simplex step must be a positive exact divisor of one")
    rows = []
    for first in range(reciprocal + 1):
        for second in range(reciprocal - first + 1):
            rows.append((first, second, reciprocal - first - second))
    return np.asarray(rows, dtype=np.float64) / reciprocal


def triangle_peak_upper_bounds(coefficients: np.ndarray, basis_peaks: np.ndarray) -> np.ndarray:
    values = np.asarray(coefficients, dtype=np.float64)
    peaks = np.asarray(basis_peaks, dtype=np.float64)
    if values.ndim != 2 or peaks.shape != (values.shape[1],) or np.any(values < 0) or np.any(peaks < 0):
        raise ValueError("coefficients and basis peaks are incompatible or negative")
    return values @ peaks


def exact_mixture_peaks(
    basis_waveforms: np.ndarray,
    coefficients: np.ndarray,
    candidate_batch: int = 16,
    sample_chunk: int = 131_072,
) -> np.ndarray:
    basis = np.asarray(basis_waveforms)
    values = np.asarray(coefficients, dtype=np.float64)
    if basis.ndim != 3 or values.ndim != 2 or values.shape[1] != basis.shape[0]:
        raise ValueError("basis waveforms and coefficients have incompatible shapes")
    flat = basis.reshape(basis.shape[0], -1)
    result = np.zeros(values.shape[0], dtype=np.float64)
    for candidate_start in range(0, values.shape[0], candidate_batch):
        candidate_stop = min(values.shape[0], candidate_start + candidate_batch)
        batch = values[candidate_start:candidate_stop]
        maxima = np.zeros(batch.shape[0], dtype=np.float64)
        for sample_start in range(0, flat.shape[1], sample_chunk):
            sample_stop = min(flat.shape[1], sample_start + sample_chunk)
            mixed = batch @ flat[:, sample_start:sample_stop]
            maxima = np.maximum(maxima, np.max(np.abs(mixed), axis=1))
        result[candidate_start:candidate_stop] = maxima
    return result


def sentinel_peak_lower_bounds(
    basis_waveforms: np.ndarray,
    coefficients: np.ndarray,
    top_samples_per_basis: int,
) -> np.ndarray:
    basis = np.asarray(basis_waveforms)
    values = np.asarray(coefficients, dtype=np.float64)
    if basis.ndim != 3 or values.ndim != 2 or values.shape[1] != basis.shape[0]:
        raise ValueError("basis waveforms and coefficients have incompatible shapes")
    flat = basis.reshape(basis.shape[0], -1)
    count = min(int(top_samples_per_basis), flat.shape[1])
    if count <= 0:
        raise ValueError("top samples per basis must be positive")
    indices = np.unique(np.concatenate([
        np.argpartition(np.abs(row), -count)[-count:] for row in flat
    ]))
    return np.max(np.abs(values @ flat[:, indices]), axis=1)


def select_margin_candidate(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    passing = [row for row in rows if row.get("passes_pressure_margin", False)]
    if not passing:
        return None
    return max(
        passing,
        key=lambda row: (
            row["minimum_corrected_hotspot_suppression"],
            row["target_retention"],
            -row["waveform_peak_vs_control"],
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline time-domain amplitude-bounded skull-region optimization.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    model_gates = evidence["model_gates"]
    hard_gates = evidence["hard_gates"]
    margin_gates = evidence["pressure_margin_gates"]

    control = load_npz(CONTROL_SIGNALS)
    hotspot1 = load_npz(HOTSPOT1_SIGNALS)
    hotspot2 = load_npz(HOTSPOT2_SIGNALS)
    strong = load_npz(STRONG_SIGNALS)
    blend = load_npz(BLEND_SIGNALS)
    consistency1 = validate_transfer_inputs(control, hotspot1)
    consistency2 = validate_transfer_inputs(control, hotspot2)
    consistency2["hotspot_local_exact"] = np.asarray(hotspot2["calibration_point_local_ijk"]).astype(int).tolist() == [40, 20, 18]
    consistency2["hotspot_full_exact"] = np.asarray(hotspot2["calibration_point_full_ijk"]).astype(int).tolist() == [77, 120, 97]
    endpoint_inputs = {
        "strong_source_mask": np.array_equal(control["source_mask"], strong["source_mask"]),
        "blend_source_mask": np.array_equal(control["source_mask"], blend["source_mask"]),
        "strong_rows": np.array_equal(control["mask_point_ijk"], strong["mask_point_ijk"]),
        "blend_rows": np.array_equal(control["mask_point_ijk"], blend["mask_point_ijk"]),
        "mask_hash": array_hash(np.asarray(control["source_mask"], dtype=np.uint8)) == evidence["frozen"]["source_mask_sha256"],
    }
    if not all(consistency1.values()) or not all(consistency2.values()) or not all(endpoint_inputs.values()):
        raise ValueError("amplitude-bounded optimization input consistency failed")

    dt_s = float(control["dt_s"])
    frequency_hz = float(control["frequency_hz"])
    target_transfer = extract_transfer_phasor(control["signals"], dt_s, frequency_hz)
    hotspot_transfers = [
        extract_transfer_phasor(hotspot1["signals"], dt_s, frequency_hz),
        extract_transfer_phasor(hotspot2["signals"], dt_s, frequency_hz),
    ]
    control_replay = np.fliplr(np.asarray(control["signals"], dtype=np.float32)).copy()
    strong_replay = np.fliplr(np.asarray(strong["signals"], dtype=np.float32)).copy()
    blend_replay = np.fliplr(np.asarray(blend["signals"], dtype=np.float32)).copy()
    baseline_weights = extract_transfer_phasor(control_replay, dt_s, frequency_hz)
    strong_weights = extract_transfer_phasor(strong_replay, dt_s, frequency_hz)
    blend_weights = extract_transfer_phasor(blend_replay, dt_s, frequency_hz)
    baseline_peak = float(np.max(np.abs(control_replay)))
    strong_peak = float(np.max(np.abs(strong_replay)))
    blend_peak = float(np.max(np.abs(blend_replay)))

    observed_target_strong = 0.41219449575498485
    observed_target_blend = 0.8544566463216217
    target_strong_raw = response_ratio(target_transfer, strong_weights, strong_peak, baseline_weights, baseline_peak)
    target_blend_raw = response_ratio(target_transfer, blend_weights, blend_peak, baseline_weights, baseline_peak)
    model_checks: dict[str, bool] = {
        "target_strong": abs(target_strong_raw - observed_target_strong) <= model_gates["target_endpoint_abs_error_max"],
        "target_blend": abs(target_blend_raw - observed_target_blend) <= model_gates["target_endpoint_abs_error_max"],
    }
    hotspot_models: list[dict[str, float]] = []
    for index, (transfer, point) in enumerate(zip(hotspot_transfers, HOTSPOTS, strict=True), start=1):
        raw_strong = response_ratio(transfer, strong_weights, strong_peak, baseline_weights, baseline_peak)
        raw_blend = response_ratio(transfer, blend_weights, blend_peak, baseline_weights, baseline_peak)
        observed_strong, observed_blend = field_ratios(point)
        corrected_blend = affine_two_endpoint_correction(raw_blend, raw_strong, observed_strong)
        error = abs(corrected_blend - observed_blend)
        model_checks[f"hotspot{index}_independent_blend"] = error <= model_gates["independent_blend_hotspot_abs_error_max"]
        hotspot_models.append({
            "raw_strong_ratio": raw_strong,
            "observed_strong_ratio": observed_strong,
            "raw_blend_ratio": raw_blend,
            "corrected_blend_ratio": corrected_blend,
            "observed_blend_ratio": observed_blend,
            "independent_blend_abs_error": error,
        })
    if not all(model_checks.values()):
        raise ValueError(f"endpoint response model failed: {model_checks}")

    coefficients = simplex_coefficients(float(evidence["frozen"]["simplex_step"]))
    reference_max = float(np.max(np.abs(np.conjugate(target_transfer))))
    all_rows: list[dict[str, Any]] = []
    exact_rows: list[dict[str, Any]] = []
    selected_waveforms: dict[tuple[float, int], np.ndarray] = {}
    basis_summaries: list[dict[str, Any]] = []
    for h2_regularization in evidence["frozen"]["h2_regularization_fractions"]:
        desired_h2 = normalize_max(
            null_projected_weights(target_transfer, hotspot_transfers[1], float(h2_regularization)),
            reference_max,
        )
        h2_recorded, _ = realize_replay_phasors(control["signals"], desired_h2, dt_s, frequency_hz)
        h2_replay = np.fliplr(np.asarray(h2_recorded, dtype=np.float32)).copy()
        basis = np.stack([control_replay, strong_replay, h2_replay], axis=0)
        basis_peaks = np.max(np.abs(basis), axis=(1, 2)).astype(np.float64)
        basis_weights = np.stack(
            [extract_transfer_phasor(item, dt_s, frequency_hz) for item in basis], axis=0
        )
        upper_peaks = triangle_peak_upper_bounds(coefficients, basis_peaks)
        lower_peaks = sentinel_peak_lower_bounds(
            basis,
            coefficients,
            int(evidence["frozen"]["sentinel_top_samples_per_basis"]),
        )
        mixture_weights = coefficients @ basis_weights
        target_possible_upper_bounds = np.asarray([
            response_ratio(target_transfer, weights, lower_peak, baseline_weights, baseline_peak)
            for weights, lower_peak in zip(mixture_weights, lower_peaks, strict=True)
        ])
        hotspot_best_case_suppressions = []
        for transfer, model in zip(hotspot_transfers, hotspot_models, strict=True):
            raw_lower_bounds = np.asarray([
                response_ratio(transfer, weights, upper_peak, baseline_weights, baseline_peak)
                for weights, upper_peak in zip(mixture_weights, upper_peaks, strict=True)
            ])
            corrected_lower_bounds = np.asarray([
                affine_two_endpoint_correction(
                    raw, model["raw_strong_ratio"], model["observed_strong_ratio"]
                )
                for raw in raw_lower_bounds
            ])
            hotspot_best_case_suppressions.append(1.0 - corrected_lower_bounds)
        conservative_indices = np.flatnonzero(
            (lower_peaks / baseline_peak <= hard_gates["waveform_peak_vs_control_max"])
            & (target_possible_upper_bounds >= hard_gates["target_retention_min"])
            & (
                hotspot_best_case_suppressions[0]
                >= hard_gates["each_corrected_hotspot_suppression_min"]
            )
            & (
                hotspot_best_case_suppressions[1]
                >= hard_gates["each_corrected_hotspot_suppression_min"]
            )
        )
        basis_summaries.append({
            "h2_regularization_fraction": float(h2_regularization),
            "basis_peak_vs_control": (basis_peaks / baseline_peak).tolist(),
            "candidate_count": int(coefficients.shape[0]),
            "conservative_screen_count": int(conservative_indices.size),
        })
        for index in range(coefficients.shape[0]):
            all_rows.append({
                "h2_regularization_fraction": float(h2_regularization),
                "coefficient_index": int(index),
                "coefficients_control_h1_h2": coefficients[index].tolist(),
                "triangle_peak_upper_vs_control": float(upper_peaks[index] / baseline_peak),
                "sentinel_peak_lower_vs_control": float(lower_peaks[index] / baseline_peak),
                "target_retention_possible_upper_bound": float(target_possible_upper_bounds[index]),
                "hotspot1_suppression_best_case_upper_bound": float(
                    hotspot_best_case_suppressions[0][index]
                ),
                "hotspot2_suppression_best_case_upper_bound": float(
                    hotspot_best_case_suppressions[1][index]
                ),
                "passes_conservative_screen": bool(index in conservative_indices),
            })
        if conservative_indices.size == 0:
            continue
        retained_coefficients = coefficients[conservative_indices]
        exact_peaks = exact_mixture_peaks(basis, retained_coefficients)
        for local_index, candidate_index in enumerate(conservative_indices):
            candidate_peak = float(exact_peaks[local_index])
            weights = mixture_weights[candidate_index]
            target_retention = response_ratio(target_transfer, weights, candidate_peak, baseline_weights, baseline_peak)
            raw_hotspot_ratios = [
                response_ratio(transfer, weights, candidate_peak, baseline_weights, baseline_peak)
                for transfer in hotspot_transfers
            ]
            corrected_ratios = [
                affine_two_endpoint_correction(raw, model["raw_strong_ratio"], model["observed_strong_ratio"])
                for raw, model in zip(raw_hotspot_ratios, hotspot_models, strict=True)
            ]
            suppressions = [1.0 - value for value in corrected_ratios]
            peak_ratio = candidate_peak / baseline_peak
            hard = {
                "target_retention": target_retention >= hard_gates["target_retention_min"],
                "hotspot1_suppression": suppressions[0] >= hard_gates["each_corrected_hotspot_suppression_min"],
                "hotspot2_suppression": suppressions[1] >= hard_gates["each_corrected_hotspot_suppression_min"],
                "waveform_peak": peak_ratio <= hard_gates["waveform_peak_vs_control_max"],
            }
            margin = {
                "target_retention": target_retention >= margin_gates["target_retention_min"],
                "hotspot1_suppression": suppressions[0] >= margin_gates["each_corrected_hotspot_suppression_min"],
                "hotspot2_suppression": suppressions[1] >= margin_gates["each_corrected_hotspot_suppression_min"],
                "waveform_peak": peak_ratio <= margin_gates["waveform_peak_vs_control_max"],
            }
            row = {
                "h2_regularization_fraction": float(h2_regularization),
                "coefficient_index": int(candidate_index),
                "coefficients_control_h1_h2": coefficients[candidate_index].tolist(),
                "triangle_peak_upper_vs_control": float(upper_peaks[candidate_index] / baseline_peak),
                "waveform_peak_vs_control": peak_ratio,
                "target_retention": target_retention,
                "corrected_hotspot1_suppression": suppressions[0],
                "corrected_hotspot2_suppression": suppressions[1],
                "minimum_corrected_hotspot_suppression": min(suppressions),
                "hard_gates": hard,
                "margin_gates": margin,
                "passes_all_hard_gates": all(hard.values()),
                "passes_pressure_margin": all(margin.values()),
            }
            exact_rows.append(row)
            if row["passes_pressure_margin"]:
                selected_waveforms[(float(h2_regularization), int(candidate_index))] = np.tensordot(
                    coefficients[candidate_index], basis, axes=(0, 0)
                ).astype(np.float32)

    selected = select_margin_candidate(exact_rows)
    hard_pass_count = sum(row["passes_all_hard_gates"] for row in exact_rows)
    margin_pass_count = sum(row["passes_pressure_margin"] for row in exact_rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if selected is not None:
        key = (selected["h2_regularization_fraction"], selected["coefficient_index"])
        output_arrays: dict[str, Any] = dict(control)
        output_arrays["signals"] = np.fliplr(selected_waveforms[key]).astype(np.float32)
        output_arrays["amplitude_bounded_coefficients_control_h1_h2"] = np.asarray(
            selected["coefficients_control_h1_h2"], dtype=np.float64
        )
        output_arrays["amplitude_bounded_h2_regularization_fraction"] = np.array(key[0], dtype=np.float64)
        np.savez_compressed(args.output_dir / "selected_element_signals.npz", **output_arrays)

    report = {
        "status": "pressure_margin_candidate_found" if selected is not None else "pressure_margin_not_found_close_weight_optimization",
        "calibration1_checks": {name: bool(value) for name, value in consistency1.items()},
        "calibration2_checks": {name: bool(value) for name, value in consistency2.items()},
        "endpoint_input_checks": {name: bool(value) for name, value in endpoint_inputs.items()},
        "model_checks": model_checks,
        "hotspot_models": hotspot_models,
        "basis_summaries": basis_summaries,
        "candidate_count": len(all_rows),
        "exact_waveform_candidate_count": len(exact_rows),
        "hard_pass_count": hard_pass_count,
        "pressure_margin_pass_count": margin_pass_count,
        "selected": selected,
        "exact_candidates": exact_rows,
        "conservative_screen_candidates": all_rows,
        "pressure_executed": False,
        "pressure_execution_authorized": False,
        "claim_boundary": evidence["claim_boundary"],
    }
    (args.output_dir / "offline_amplitude_bounded_gate.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    ranked = sorted(
        exact_rows,
        key=lambda row: (
            row["passes_pressure_margin"],
            row["passes_all_hard_gates"],
            row["minimum_corrected_hotspot_suppression"],
            row["target_retention"],
        ),
        reverse=True,
    )[:12]
    lines = [
        "# Time-Domain Amplitude-Bounded Offline Gate",
        "",
        f"Status: **{report['status']}**",
        f"Candidates: `{len(all_rows)}`; exact waveform checks: `{len(exact_rows)}`; hard passes: `{hard_pass_count}`; margin passes: `{margin_pass_count}`.",
        "",
        "| H2 lambda | control/H1/H2 | target | H1 suppression | H2 suppression | peak/control | hard | margin |",
        "|---:|:---:|---:|---:|---:|---:|:---:|:---:|",
    ]
    for row in ranked:
        coeff = "/".join(f"{value:.3f}" for value in row["coefficients_control_h1_h2"])
        lines.append(
            f"| {row['h2_regularization_fraction']:.3g} | {coeff} | {row['target_retention']:.4f} | "
            f"{row['corrected_hotspot1_suppression']:.4f} | {row['corrected_hotspot2_suppression']:.4f} | "
            f"{row['waveform_peak_vs_control']:.4f} | {'yes' if row['passes_all_hard_gates'] else 'no'} | "
            f"{'yes' if row['passes_pressure_margin'] else 'no'} |"
        )
    lines.extend(["", "No pressure execution is authorized by this offline report."])
    (args.output_dir / "offline_amplitude_bounded_gate.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "candidate_count": report["candidate_count"],
        "exact_waveform_candidate_count": report["exact_waveform_candidate_count"],
        "hard_pass_count": hard_pass_count,
        "pressure_margin_pass_count": margin_pass_count,
        "selected": selected,
    }, indent=2))


if __name__ == "__main__":
    main()
