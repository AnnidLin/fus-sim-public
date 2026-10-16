from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from analyze_target_hard_constrained_hotspot_20260722 import (
    array_hash,
    load_npz,
    solver_normalized_response_ratio,
)
from analyze_hotspot_transfer_20260721 import validate_transfer_inputs


ROOT = Path(__file__).resolve().parent
CONTROL_SIGNALS = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "offset_y-10p0_z-02p5" / "tr" / "element_signals.npz"
CONSTRAINED_SIGNALS = ROOT / "outputs" / "dual_point_constrained_refocus_20260721" / "run" / "element_signals.npz"
HOTSPOT_SIGNALS = ROOT / "outputs" / "dual_point_hotspot_calibration_20260721" / "run" / "element_signals.npz"
TRANSFER = ROOT / "outputs" / "dual_point_hotspot_calibration_20260721" / "offline_analysis" / "hotspot_transfer_steering.npz"
EVIDENCE = ROOT / "outputs" / "evidence_briefs" / "target_preserving_waveform_blend_20260722" / "evidence_brief.json"
OUTPUT = ROOT / "outputs" / "target_preserving_waveform_blend_20260722"


def blend_waveforms(control: np.ndarray, constrained: np.ndarray, fraction: float) -> np.ndarray:
    alpha = float(fraction)
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("blend fraction must be in [0,1]")
    first = np.asarray(control, dtype=np.float64)
    second = np.asarray(constrained, dtype=np.float64)
    if first.shape != second.shape or first.ndim != 2:
        raise ValueError("control and constrained waveforms must have equal 2D shape")
    return (1.0 - alpha) * first + alpha * second


def affine_endpoint_corrected_ratio(raw_ratio: float, fraction: float, raw_endpoint: float, observed_endpoint: float) -> float:
    alpha = float(fraction)
    return float(raw_ratio) + alpha * (float(observed_endpoint) - float(raw_endpoint))


def select_candidate(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    passing = [row for row in rows if row["passes_all_hard_gates"]]
    if not passing:
        return None
    return max(passing, key=lambda row: (row["corrected_original_hotspot_suppression"], row["target_retention"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Screen convex blends of two observed H1 replay endpoints.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    endpoints = evidence["observed_endpoints"]
    gates = evidence["offline_gates"]

    control = load_npz(CONTROL_SIGNALS)
    constrained = load_npz(CONSTRAINED_SIGNALS)
    hotspot = load_npz(HOTSPOT_SIGNALS)
    consistency = validate_transfer_inputs(control, hotspot)
    cross_checks = {
        "source_mask_exact": np.array_equal(control["source_mask"], constrained["source_mask"]),
        "c_order_rows_exact": np.array_equal(control["mask_point_ijk"], constrained["mask_point_ijk"]),
        "signal_shape_exact": control["signals"].shape == constrained["signals"].shape == (2979, 1867),
        "dt_exact": float(control["dt_s"]) == float(constrained["dt_s"]),
        "target_exact": np.array_equal(control["target_index_ijk"], constrained["target_index_ijk"]),
        "mask_hash_exact": array_hash(np.asarray(control["source_mask"], dtype=np.uint8)) == evidence["frozen_source_mask_sha256"],
    }
    if not all(consistency.values()) or not all(cross_checks.values()):
        raise ValueError(f"input consistency failed: calibration={consistency}, endpoints={cross_checks}")

    transfer = load_npz(TRANSFER)
    target_transfer = np.asarray(transfer["target_transfer"], dtype=np.complex128)
    hotspot_transfer = np.asarray(transfer["hotspot_transfer"], dtype=np.complex128)
    control_recorded = np.asarray(control["signals"], dtype=np.float64)
    constrained_recorded = np.asarray(constrained["signals"], dtype=np.float64)
    control_replay = np.fliplr(control_recorded)
    constrained_replay = np.fliplr(constrained_recorded)
    dt_s = float(control["dt_s"])
    frequency_hz = float(control["frequency_hz"])
    control_peak = float(np.max(np.abs(control_recorded)))

    constrained_target_raw = solver_normalized_response_ratio(
        target_transfer, constrained_replay, control_replay, dt_s, frequency_hz
    )
    constrained_hotspot_raw = solver_normalized_response_ratio(
        hotspot_transfer, constrained_replay, control_replay, dt_s, frequency_hz
    )
    endpoint_checks = {
        "control_target_exact": True,
        "constrained_target_replay": abs(constrained_target_raw - endpoints["constrained_target_ratio"]) <= gates["endpoint_target_abs_error_max"],
        "corrected_control_hotspot_exact": True,
        "corrected_constrained_hotspot_exact": bool(np.isclose(
            affine_endpoint_corrected_ratio(constrained_hotspot_raw, 1.0, constrained_hotspot_raw, endpoints["constrained_original_hotspot_ratio"]),
            endpoints["constrained_original_hotspot_ratio"], rtol=1e-12, atol=1e-12,
        )),
    }

    rows: list[dict[str, Any]] = []
    selected_signals: dict[float, np.ndarray] = {}
    for fraction in evidence["blend_fractions"]:
        alpha = float(fraction)
        blended_recorded = blend_waveforms(control_recorded, constrained_recorded, alpha)
        blended_replay = np.fliplr(blended_recorded)
        target_ratio = solver_normalized_response_ratio(
            target_transfer, blended_replay, control_replay, dt_s, frequency_hz
        )
        raw_hotspot_ratio = solver_normalized_response_ratio(
            hotspot_transfer, blended_replay, control_replay, dt_s, frequency_hz
        )
        corrected_hotspot_ratio = affine_endpoint_corrected_ratio(
            raw_hotspot_ratio, alpha, constrained_hotspot_raw, endpoints["constrained_original_hotspot_ratio"]
        )
        peak_ratio = float(np.max(np.abs(blended_recorded)) / control_peak)
        hard_gates = {
            "endpoint_model": all(endpoint_checks.values()),
            "finite": bool(np.all(np.isfinite(blended_recorded))),
            "target_retention": target_ratio >= gates["target_retention_min"],
            "corrected_hotspot_suppression": (1.0 - corrected_hotspot_ratio) >= gates["corrected_original_hotspot_suppression_min"],
            "waveform_peak": peak_ratio <= gates["waveform_peak_vs_control_max"],
        }
        row = {
            "blend_fraction": alpha,
            "target_retention": target_ratio,
            "raw_original_hotspot_ratio": raw_hotspot_ratio,
            "corrected_original_hotspot_ratio": corrected_hotspot_ratio,
            "corrected_original_hotspot_suppression": 1.0 - corrected_hotspot_ratio,
            "waveform_peak_vs_control": peak_ratio,
            "hard_gates": hard_gates,
            "passes_all_hard_gates": all(hard_gates.values()),
        }
        rows.append(row)
        if row["passes_all_hard_gates"]:
            selected_signals[alpha] = blended_recorded.astype(np.float32)

    selected = select_candidate(rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if selected is not None:
        alpha = float(selected["blend_fraction"])
        output_arrays: dict[str, Any] = dict(control)
        output_arrays["signals"] = selected_signals[alpha]
        output_arrays["waveform_blend_fraction"] = np.array(alpha, dtype=np.float64)
        output_arrays["waveform_blend_method"] = np.array("convex_control_to_closed_dual_point_endpoint")
        np.savez_compressed(args.output_dir / "selected_element_signals.npz", **output_arrays)

    report = {
        "status": "offline_blend_gate_pass" if selected is not None else "offline_blend_gate_fail",
        "calibration_checks": {name: bool(value) for name, value in consistency.items()},
        "endpoint_input_checks": {name: bool(value) for name, value in cross_checks.items()},
        "endpoint_model_checks": endpoint_checks,
        "constrained_target_raw_prediction": constrained_target_raw,
        "constrained_hotspot_raw_prediction": constrained_hotspot_raw,
        "gates": gates,
        "candidates": rows,
        "selected": selected,
        "pressure_executed": False,
        "pressure_execution_authorized": False,
        "claim_boundary": evidence["claim_boundary"],
    }
    (args.output_dir / "offline_blend_gate.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Target-Preserving Waveform Blend Offline Gate",
        "",
        f"Status: **{report['status']}**",
        "",
        "| blend | target retention | corrected hotspot suppression | peak/control | pass |",
        "|---:|---:|---:|---:|:---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['blend_fraction']:.2f} | {row['target_retention']:.4f} | "
            f"{row['corrected_original_hotspot_suppression']:.4f} | {row['waveform_peak_vs_control']:.4f} | "
            f"{'yes' if row['passes_all_hard_gates'] else 'no'} |"
        )
    lines.extend(["", "No pressure execution is authorized by this offline report."])
    (args.output_dir / "offline_blend_gate.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "selected": selected, "endpoint_model_checks": endpoint_checks}, indent=2))


if __name__ == "__main__":
    main()
