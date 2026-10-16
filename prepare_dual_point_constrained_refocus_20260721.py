from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.signal import hilbert

from design_dual_point_hotspot_constrained_tr_20260720 import extract_transfer_phasor, predicted_response


ROOT = Path(__file__).resolve().parent
TARGET_SIGNALS = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "offset_y-10p0_z-02p5" / "tr" / "element_signals.npz"
TRANSFER = ROOT / "outputs" / "dual_point_hotspot_calibration_20260721" / "offline_analysis" / "hotspot_transfer_steering.npz"
SELECTED = ROOT / "outputs" / "dual_point_hotspot_calibration_20260721" / "offline_analysis" / "selected_complex_weights.npz"
EVIDENCE = ROOT / "outputs" / "evidence_briefs" / "dual_point_constrained_refocus_20260721" / "evidence_brief.json"
OUTPUT = ROOT / "outputs" / "dual_point_constrained_refocus_20260721" / "run"
EXPECTED_MASK_HASH = "78bfe794004ff4df3ba1e41879684a55c29694fa41c2ed76bc067bb040ae5907"


def mask_hash(mask: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(mask, dtype=np.uint8).tobytes(order="C")).hexdigest()


def normalize_max(weights: np.ndarray, reference_max: float) -> np.ndarray:
    value = np.asarray(weights, dtype=np.complex128)
    maximum = float(np.max(np.abs(value)))
    if maximum <= 0 or not np.isfinite(maximum):
        raise ValueError("complex weights are zero or non-finite")
    return value * (reference_max / maximum)


def realize_replay_phasors(
    recorded_signals: np.ndarray,
    desired_replay_weights: np.ndarray,
    dt_s: float,
    frequency_hz: float,
    chunk_rows: int = 128,
) -> tuple[np.ndarray, np.ndarray]:
    recorded = np.asarray(recorded_signals, dtype=np.float64)
    desired = np.asarray(desired_replay_weights, dtype=np.complex128)
    if recorded.ndim != 2 or desired.shape != (recorded.shape[0],):
        raise ValueError("recorded signals and desired weights have incompatible shapes")
    conventional_replay = np.fliplr(recorded)
    current = extract_transfer_phasor(conventional_replay, dt_s, frequency_hz)
    floor = max(float(np.max(np.abs(current))) * 1e-12, np.finfo(float).tiny)
    if np.any(np.abs(current) <= floor):
        raise ValueError("at least one conventional replay phasor is too small for stable conversion")
    multiplier = desired / current
    modified_replay = np.empty_like(conventional_replay)
    for start in range(0, recorded.shape[0], chunk_rows):
        stop = min(recorded.shape[0], start + chunk_rows)
        analytic = hilbert(conventional_replay[start:stop], axis=1)
        modified_replay[start:stop] = np.real(analytic * multiplier[start:stop, None])
    realized = extract_transfer_phasor(modified_replay, dt_s, frequency_hz)
    modified_recorded = np.fliplr(modified_replay).astype(np.float32)
    return modified_recorded, realized


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare gated dual-point constrained TR replay waveforms.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    gates = evidence["waveform_gates"]
    with np.load(TARGET_SIGNALS, allow_pickle=False) as stored:
        original = {key: np.asarray(stored[key]) for key in stored.files}
    with np.load(TRANSFER, allow_pickle=False) as stored:
        target_transfer = np.asarray(stored["target_transfer"], dtype=np.complex128)
        hotspot_transfer = np.asarray(stored["hotspot_transfer"], dtype=np.complex128)
    with np.load(SELECTED, allow_pickle=False) as stored:
        desired = np.asarray(stored["weights"], dtype=np.complex128)
        regularization = float(stored["regularization_fraction"])
        selected_mask = np.asarray(stored["source_mask"], dtype=np.uint8)
        selected_rows = np.asarray(stored["mask_point_ijk"], dtype=np.int32)
    source_mask = np.asarray(original["source_mask"], dtype=np.uint8)
    source_rows = np.asarray(original["mask_point_ijk"], dtype=np.int32)
    if regularization != 1.0:
        raise ValueError("selected regularization differs from preregistered value 1.0")
    if not np.array_equal(source_mask, selected_mask) or not np.array_equal(source_rows, selected_rows):
        raise ValueError("selected weights source mapping mismatch")
    if mask_hash(source_mask) != EXPECTED_MASK_HASH:
        raise ValueError("source mask hash mismatch")
    dt_s = float(original["dt_s"])
    frequency_hz = float(original["frequency_hz"])
    modified_recorded, realized = realize_replay_phasors(original["signals"], desired, dt_s, frequency_hz)

    reference_max = float(np.max(np.abs(np.conjugate(target_transfer))))
    desired_normalized = normalize_max(desired, reference_max)
    realized_normalized = normalize_max(realized, reference_max)
    relative_l2 = float(np.linalg.norm(realized_normalized - desired_normalized) / np.linalg.norm(desired_normalized))
    conventional = normalize_max(np.conjugate(target_transfer), reference_max)
    target_reference = abs(predicted_response(target_transfer, conventional))
    hotspot_reference = abs(predicted_response(hotspot_transfer, conventional))
    target_retention = float(abs(predicted_response(target_transfer, realized_normalized)) / target_reference)
    hotspot_ratio = float(abs(predicted_response(hotspot_transfer, realized_normalized)) / hotspot_reference)
    hotspot_suppression = 1.0 - hotspot_ratio
    checks = {
        "shape_exact": modified_recorded.shape == (2979, 1867),
        "finite_nonzero": bool(np.all(np.isfinite(modified_recorded)) and np.max(np.abs(modified_recorded)) > 0),
        "source_mask_hash_exact": mask_hash(source_mask) == EXPECTED_MASK_HASH,
        "relative_complex_l2_pass": relative_l2 <= gates["maximum_relative_complex_l2_error"],
        "target_retention_pass": target_retention >= gates["minimum_target_retention"],
        "hotspot_suppression_pass": hotspot_suppression >= gates["minimum_hotspot_suppression"],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_arrays: dict[str, Any] = dict(original)
    output_arrays["signals"] = modified_recorded
    output_arrays["dual_point_regularization_fraction"] = np.array(regularization, dtype=np.float64)
    output_arrays["dual_point_waveform_method"] = np.array(evidence["waveform_method"])
    np.savez_compressed(args.output_dir / "element_signals.npz", **output_arrays)
    report = {
        "status": "waveform_gate_pass" if all(checks.values()) else "waveform_gate_fail",
        "regularization_fraction": regularization,
        "relative_complex_l2_error": relative_l2,
        "realized_target_retention": target_retention,
        "realized_hotspot_response_ratio": hotspot_ratio,
        "realized_hotspot_suppression": hotspot_suppression,
        "checks": {name: bool(value) for name, value in checks.items()},
        "source_mask_sha256": mask_hash(source_mask),
        "signals_shape": list(modified_recorded.shape),
        "signals_max_abs_before_refocus_normalization_pa": float(np.max(np.abs(modified_recorded))),
        "constrained_refocus_authorized_by_waveform_gate": all(checks.values()),
        "pressure_executed": False,
        "claim_boundary": "waveform_realization_only_not_pressure_evidence",
    }
    (args.output_dir / "waveform_gate.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "waveform_gate_pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
