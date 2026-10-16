from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.signal import hilbert

from analyze_target_hard_constrained_hotspot_20260722 import array_hash, load_npz
from analyze_hotspot_transfer_20260721 import validate_transfer_inputs
from design_dual_point_hotspot_constrained_tr_20260720 import extract_transfer_phasor


ROOT = Path(__file__).resolve().parent
CONTROL_SIGNALS = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "offset_y-10p0_z-02p5" / "tr" / "element_signals.npz"
HOTSPOT1_SIGNALS = ROOT / "outputs" / "dual_point_hotspot_calibration_20260721" / "run" / "element_signals.npz"
HOTSPOT2_SIGNALS = ROOT / "outputs" / "second_skull_hotspot_calibration_20260722" / "run" / "element_signals.npz"
STRONG_SIGNALS = ROOT / "outputs" / "dual_point_constrained_refocus_20260721" / "run" / "element_signals.npz"
BLEND_SIGNALS = ROOT / "outputs" / "target_preserving_blend_validation_20260722" / "run" / "element_signals.npz"
CONTROL_FIELD = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "offset_y-10p0_z-02p5" / "tr" / "pressure_max_mpa.npz"
STRONG_FIELD = ROOT / "outputs" / "dual_point_constrained_refocus_20260721" / "run" / "pressure_max_mpa.npz"
BLEND_FIELD = ROOT / "outputs" / "target_preserving_blend_validation_20260722" / "run" / "pressure_max_mpa.npz"
EVIDENCE = ROOT / "outputs" / "evidence_briefs" / "three_vector_skull_region_optimization_20260722" / "evidence_brief.json"
OUTPUT = ROOT / "outputs" / "three_vector_skull_region_optimization_20260722"
HOTSPOTS = ((38, 39, 34), (40, 20, 18))


def minimum_norm_response_weights(response_matrix: np.ndarray, baseline_weights: np.ndarray, desired_response: np.ndarray) -> np.ndarray:
    matrix = np.asarray(response_matrix, dtype=np.complex128)
    baseline = np.asarray(baseline_weights, dtype=np.complex128)
    desired = np.asarray(desired_response, dtype=np.complex128)
    if matrix.ndim != 2 or baseline.shape != (matrix.shape[1],) or desired.shape != (matrix.shape[0],):
        raise ValueError("response matrix, weights and desired response have incompatible shapes")
    residual = desired - matrix @ baseline
    gram = matrix @ matrix.conj().T
    correction_coefficients = np.linalg.lstsq(gram, residual, rcond=1e-12)[0]
    result = baseline + matrix.conj().T @ correction_coefficients
    relative_constraint_error = np.linalg.norm(matrix @ result - desired) / max(np.linalg.norm(desired), 1e-30)
    if relative_constraint_error > 1e-6:
        raise ValueError(f"response constraints are not resolved: relative error={relative_constraint_error}")
    return result


def affine_two_endpoint_correction(raw_ratio: float, raw_anchor: float, observed_anchor: float) -> float:
    denominator = float(raw_anchor) - 1.0
    if abs(denominator) < 1e-12:
        raise ValueError("raw anchor is too close to the control endpoint")
    slope = (float(observed_anchor) - 1.0) / denominator
    return 1.0 + (float(raw_ratio) - 1.0) * slope


def waveform_peak_from_analytic(analytic_control_replay: np.ndarray, multiplier: np.ndarray, chunk_rows: int = 128) -> float:
    maximum = 0.0
    for start in range(0, analytic_control_replay.shape[0], chunk_rows):
        stop = min(analytic_control_replay.shape[0], start + chunk_rows)
        block = np.real(analytic_control_replay[start:stop] * multiplier[start:stop, None])
        maximum = max(maximum, float(np.max(np.abs(block))))
    return maximum


def response_ratio(transfer: np.ndarray, weights: np.ndarray, candidate_peak: float, baseline_weights: np.ndarray, baseline_peak: float) -> float:
    denominator = abs(np.dot(transfer, baseline_weights) / baseline_peak)
    if denominator <= 0 or candidate_peak <= 0:
        raise ValueError("response normalization denominator is zero")
    return float(abs(np.dot(transfer, weights) / candidate_peak) / denominator)


def select_candidate(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    passing = [row for row in rows if row["passes_all_hard_gates"]]
    if not passing:
        return None
    return max(passing, key=lambda row: (row["minimum_corrected_hotspot_suppression"], row["target_retention"]))


def field_ratios(point: tuple[int, int, int]) -> tuple[float, float]:
    with np.load(CONTROL_FIELD, allow_pickle=False) as stored:
        control = float(stored["pressure_max_mpa"][point])
    with np.load(STRONG_FIELD, allow_pickle=False) as stored:
        strong = float(stored["pressure_max_mpa"][point])
    with np.load(BLEND_FIELD, allow_pickle=False) as stored:
        blend = float(stored["pressure_max_mpa"][point])
    return strong / control, blend / control


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline target-hard, two-hotspot response optimization.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    model_gates = evidence["model_gates"]
    candidate_gates = evidence["candidate_gates"]

    control = load_npz(CONTROL_SIGNALS)
    hotspot1 = load_npz(HOTSPOT1_SIGNALS)
    hotspot2 = load_npz(HOTSPOT2_SIGNALS)
    strong = load_npz(STRONG_SIGNALS)
    blend = load_npz(BLEND_SIGNALS)
    consistency1 = validate_transfer_inputs(control, hotspot1)
    consistency2 = validate_transfer_inputs(control, hotspot2)
    consistency2["hotspot_local_exact"] = np.asarray(hotspot2["calibration_point_local_ijk"]).astype(int).tolist() == [40, 20, 18]
    consistency2["hotspot_full_exact"] = np.asarray(hotspot2["calibration_point_full_ijk"]).astype(int).tolist() == [77, 120, 97]
    endpoint_checks = {
        "strong_source_mask": np.array_equal(control["source_mask"], strong["source_mask"]),
        "blend_source_mask": np.array_equal(control["source_mask"], blend["source_mask"]),
        "strong_rows": np.array_equal(control["mask_point_ijk"], strong["mask_point_ijk"]),
        "blend_rows": np.array_equal(control["mask_point_ijk"], blend["mask_point_ijk"]),
        "mask_hash": array_hash(np.asarray(control["source_mask"], dtype=np.uint8)) == evidence["source_mask_sha256"],
    }
    if not all(consistency1.values()) or not all(consistency2.values()) or not all(endpoint_checks.values()):
        raise ValueError("three-vector input consistency failed")

    dt_s = float(control["dt_s"])
    frequency_hz = float(control["frequency_hz"])
    target_transfer = extract_transfer_phasor(control["signals"], dt_s, frequency_hz)
    hotspot_transfers = [
        extract_transfer_phasor(hotspot1["signals"], dt_s, frequency_hz),
        extract_transfer_phasor(hotspot2["signals"], dt_s, frequency_hz),
    ]
    response_matrix = np.vstack([target_transfer, *hotspot_transfers])
    control_replay = np.fliplr(np.asarray(control["signals"], dtype=np.float64))
    strong_replay = np.fliplr(np.asarray(strong["signals"], dtype=np.float64))
    blend_replay = np.fliplr(np.asarray(blend["signals"], dtype=np.float64))
    baseline_weights = extract_transfer_phasor(control_replay, dt_s, frequency_hz)
    strong_weights = extract_transfer_phasor(strong_replay, dt_s, frequency_hz)
    blend_weights = extract_transfer_phasor(blend_replay, dt_s, frequency_hz)
    baseline_peak = float(np.max(np.abs(control_replay)))
    strong_peak = float(np.max(np.abs(strong_replay)))
    blend_peak = float(np.max(np.abs(blend_replay)))

    target_strong_raw = response_ratio(target_transfer, strong_weights, strong_peak, baseline_weights, baseline_peak)
    target_blend_raw = response_ratio(target_transfer, blend_weights, blend_peak, baseline_weights, baseline_peak)
    observed_target_strong = 0.41219449575498485
    observed_target_blend = 0.8544566463216217
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

    current = baseline_weights
    floor = max(float(np.max(np.abs(current))) * 1e-12, np.finfo(float).tiny)
    if np.any(np.abs(current) <= floor):
        raise ValueError("control replay phasor contains unstable rows")
    analytic = hilbert(control_replay, axis=1)
    baseline_responses = response_matrix @ baseline_weights
    rows: list[dict[str, Any]] = []
    candidate_weights: dict[tuple[float, float, float], np.ndarray] = {}
    for target_gain, residual1, residual2 in itertools.product(
        evidence["target_gain_candidates"],
        evidence["hotspot_residual_candidates"],
        evidence["hotspot_residual_candidates"],
    ):
        desired = baseline_responses * np.array([target_gain, residual1, residual2], dtype=np.complex128)
        weights = minimum_norm_response_weights(response_matrix, baseline_weights, desired)
        multiplier = weights / current
        candidate_peak = waveform_peak_from_analytic(analytic, multiplier)
        target_ratio = response_ratio(target_transfer, weights, candidate_peak, baseline_weights, baseline_peak)
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
        hard_gates = {
            "endpoint_model": all(model_checks.values()),
            "finite": bool(np.all(np.isfinite(weights)) and np.isfinite(candidate_peak)),
            "target_retention": target_ratio >= candidate_gates["target_retention_min"],
            "hotspot1_suppression": suppressions[0] >= candidate_gates["each_corrected_hotspot_suppression_min"],
            "hotspot2_suppression": suppressions[1] >= candidate_gates["each_corrected_hotspot_suppression_min"],
            "waveform_peak": peak_ratio <= candidate_gates["waveform_peak_vs_control_max"],
        }
        key = (float(target_gain), float(residual1), float(residual2))
        row = {
            "target_gain_request": key[0],
            "hotspot1_residual_request": key[1],
            "hotspot2_residual_request": key[2],
            "target_retention": target_ratio,
            "corrected_hotspot1_suppression": suppressions[0],
            "corrected_hotspot2_suppression": suppressions[1],
            "minimum_corrected_hotspot_suppression": min(suppressions),
            "waveform_peak_vs_control": peak_ratio,
            "hard_gates": hard_gates,
            "passes_all_hard_gates": all(hard_gates.values()),
        }
        rows.append(row)
        candidate_weights[key] = weights

    selected = select_candidate(rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if selected is not None:
        key = (
            selected["target_gain_request"],
            selected["hotspot1_residual_request"],
            selected["hotspot2_residual_request"],
        )
        weights = candidate_weights[key]
        multiplier = weights / current
        selected_replay = np.real(analytic * multiplier[:, None])
        output_arrays: dict[str, Any] = dict(control)
        output_arrays["signals"] = np.fliplr(selected_replay).astype(np.float32)
        output_arrays["three_vector_target_gain"] = np.array(key[0], dtype=np.float64)
        output_arrays["three_vector_hotspot_residuals"] = np.array(key[1:], dtype=np.float64)
        np.savez_compressed(args.output_dir / "selected_element_signals.npz", **output_arrays)

    report = {
        "status": "offline_three_vector_gate_pass" if selected is not None else "offline_three_vector_gate_fail",
        "calibration1_checks": {name: bool(value) for name, value in consistency1.items()},
        "calibration2_checks": {name: bool(value) for name, value in consistency2.items()},
        "endpoint_input_checks": {name: bool(value) for name, value in endpoint_checks.items()},
        "model_checks": model_checks,
        "target_model": {
            "strong_raw_prediction": target_strong_raw,
            "strong_observed": observed_target_strong,
            "blend_raw_prediction": target_blend_raw,
            "blend_observed": observed_target_blend,
        },
        "hotspot_models": hotspot_models,
        "response_matrix_condition_number": float(np.linalg.cond(response_matrix @ response_matrix.conj().T)),
        "candidate_count": len(rows),
        "candidates": rows,
        "selected": selected,
        "pressure_executed": False,
        "pressure_execution_authorized": False,
        "claim_boundary": evidence["claim_boundary"],
    }
    (args.output_dir / "offline_three_vector_gate.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Three-Vector Skull-Region Offline Gate",
        "",
        f"Status: **{report['status']}**",
        f"Candidate count: `{len(rows)}`.",
        "",
        "| target gain | h1 residual | h2 residual | target retention | min hotspot suppression | peak/control | pass |",
        "|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for row in rows:
        if row["passes_all_hard_gates"] or row is selected:
            lines.append(
                f"| {row['target_gain_request']:.2f} | {row['hotspot1_residual_request']:.2f} | "
                f"{row['hotspot2_residual_request']:.2f} | {row['target_retention']:.4f} | "
                f"{row['minimum_corrected_hotspot_suppression']:.4f} | {row['waveform_peak_vs_control']:.4f} | "
                f"{'yes' if row['passes_all_hard_gates'] else 'no'} |"
            )
    lines.extend(["", "No pressure execution is authorized by this offline report."])
    (args.output_dir / "offline_three_vector_gate.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "candidate_count": len(rows), "selected": selected, "model_checks": model_checks}, indent=2))


if __name__ == "__main__":
    main()
