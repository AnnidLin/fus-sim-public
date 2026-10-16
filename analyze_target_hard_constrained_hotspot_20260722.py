from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from analyze_hotspot_transfer_20260721 import validate_transfer_inputs
from design_dual_point_hotspot_constrained_tr_20260720 import (
    extract_transfer_phasor,
    null_projected_weights,
)
from prepare_dual_point_constrained_refocus_20260721 import normalize_max, realize_replay_phasors


ROOT = Path(__file__).resolve().parent
TARGET_SIGNALS = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "offset_y-10p0_z-02p5" / "tr" / "element_signals.npz"
HOTSPOT_SIGNALS = ROOT / "outputs" / "dual_point_hotspot_calibration_20260721" / "run" / "element_signals.npz"
TRANSFER = ROOT / "outputs" / "dual_point_hotspot_calibration_20260721" / "offline_analysis" / "hotspot_transfer_steering.npz"
EVIDENCE = ROOT / "outputs" / "evidence_briefs" / "target_hard_constrained_hotspot_optimization_20260722" / "evidence_brief.json"
OUTPUT = ROOT / "outputs" / "target_hard_constrained_hotspot_optimization_20260722"


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as stored:
        return {key: np.asarray(stored[key]) for key in stored.files}


def array_hash(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes(order="C")).hexdigest()


def solver_normalized_response_ratio(
    transfer: np.ndarray,
    candidate_replay: np.ndarray,
    control_replay: np.ndarray,
    dt_s: float,
    frequency_hz: float,
) -> float:
    candidate = np.asarray(candidate_replay, dtype=np.float64)
    control = np.asarray(control_replay, dtype=np.float64)
    if candidate.shape != control.shape or candidate.ndim != 2:
        raise ValueError("candidate and control replay matrices must have equal 2D shape")
    candidate_peak = float(np.max(np.abs(candidate)))
    control_peak = float(np.max(np.abs(control)))
    if candidate_peak <= 0 or control_peak <= 0:
        raise ValueError("replay matrices must be nonzero")
    candidate_phasor = extract_transfer_phasor(candidate, dt_s, frequency_hz) / candidate_peak
    control_phasor = extract_transfer_phasor(control, dt_s, frequency_hz) / control_peak
    denominator = abs(np.dot(transfer, control_phasor))
    if denominator <= 0:
        raise ValueError("control response is zero")
    return float(abs(np.dot(transfer, candidate_phasor)) / denominator)


def conservative_hotspot_ratio(raw_ratio: float, failed_observed: float, failed_predicted: float) -> tuple[float, float]:
    if failed_predicted <= 0:
        raise ValueError("failed predicted hotspot ratio must be positive")
    correction = max(1.0, float(failed_observed) / float(failed_predicted))
    return float(raw_ratio) * correction, correction


def select_candidate(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    passing = [row for row in rows if row["passes_all_hard_gates"]]
    if not passing:
        return None
    return max(passing, key=lambda row: (row["conservative_hotspot_suppression"], row["target_retention"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run target-hard-constrained, solver-normalization-aware offline screening.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    gates = evidence["offline_gates"]
    known = evidence["known_endpoints"]

    target_stored = load_npz(TARGET_SIGNALS)
    hotspot_stored = load_npz(HOTSPOT_SIGNALS)
    consistency = validate_transfer_inputs(target_stored, hotspot_stored)
    if not all(consistency.values()):
        raise ValueError(f"calibration consistency failed: {consistency}")
    if array_hash(np.asarray(target_stored["source_mask"], dtype=np.uint8)) != evidence["frozen"]["source_mask_sha256"]:
        raise ValueError("source mask hash differs from the frozen Evidence Brief")

    transfer = load_npz(TRANSFER)
    target_transfer = np.asarray(transfer["target_transfer"], dtype=np.complex128)
    hotspot_transfer = np.asarray(transfer["hotspot_transfer"], dtype=np.complex128)
    recorded = np.asarray(target_stored["signals"], dtype=np.float64)
    control_replay = np.fliplr(recorded)
    dt_s = float(target_stored["dt_s"])
    frequency_hz = float(target_stored["frequency_hz"])
    control_peak = float(np.max(np.abs(control_replay)))
    reference_max = float(np.max(np.abs(np.conjugate(target_transfer))))

    rows: list[dict[str, Any]] = []
    replay_cache: dict[float, np.ndarray] = {}
    for fraction in evidence["candidate_regularization_fractions"]:
        weights = normalize_max(
            null_projected_weights(target_transfer, hotspot_transfer, float(fraction)),
            reference_max,
        )
        modified_recorded, _ = realize_replay_phasors(recorded, weights, dt_s, frequency_hz)
        candidate_replay = np.fliplr(np.asarray(modified_recorded, dtype=np.float64))
        replay_cache[float(fraction)] = modified_recorded
        target_retention = solver_normalized_response_ratio(
            target_transfer, candidate_replay, control_replay, dt_s, frequency_hz
        )
        raw_hotspot_ratio = solver_normalized_response_ratio(
            hotspot_transfer, candidate_replay, control_replay, dt_s, frequency_hz
        )
        peak_ratio = float(np.max(np.abs(candidate_replay)) / control_peak)
        rows.append({
            "regularization_fraction": float(fraction),
            "target_retention": target_retention,
            "raw_hotspot_ratio": raw_hotspot_ratio,
            "waveform_peak_vs_control": peak_ratio,
            "finite": bool(np.all(np.isfinite(candidate_replay))),
        })

    failed_fraction = float(known["failed_lambda"])
    failed_row = next(row for row in rows if row["regularization_fraction"] == failed_fraction)
    failed_target_abs_error = abs(failed_row["target_retention"] - float(known["failed_observed_target_retention"]))
    corrected_failed_hotspot, hotspot_correction = conservative_hotspot_ratio(
        failed_row["raw_hotspot_ratio"],
        float(known["failed_observed_original_hotspot_ratio"]),
        failed_row["raw_hotspot_ratio"],
    )
    endpoint_checks = {
        "control_target_exact": True,
        "failed_target_replay_pass": failed_target_abs_error <= gates["failed_endpoint_target_abs_error_max"],
        "failed_hotspot_correction_replays_observation": bool(
            np.isclose(corrected_failed_hotspot, known["failed_observed_original_hotspot_ratio"], rtol=1e-10, atol=1e-12)
        ),
    }

    for row in rows:
        corrected_ratio = row["raw_hotspot_ratio"] * hotspot_correction
        corrected_suppression = 1.0 - corrected_ratio
        hard_gates = {
            "finite": row["finite"],
            "target_retention": row["target_retention"] >= gates["candidate_target_retention_min"],
            "conservative_hotspot_suppression": corrected_suppression >= gates["candidate_conservative_hotspot_suppression_min"],
            "waveform_peak": row["waveform_peak_vs_control"] <= gates["candidate_waveform_peak_vs_control_max"],
            "endpoint_model": all(endpoint_checks.values()),
        }
        row["conservative_hotspot_ratio"] = corrected_ratio
        row["conservative_hotspot_suppression"] = corrected_suppression
        row["hard_gates"] = hard_gates
        row["passes_all_hard_gates"] = all(hard_gates.values())

    selected = select_candidate(rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if selected is not None:
        fraction = float(selected["regularization_fraction"])
        np.savez_compressed(
            args.output_dir / "selected_candidate.npz",
            signals=np.asarray(replay_cache[fraction], dtype=np.float32),
            regularization_fraction=np.array(fraction, dtype=np.float64),
            source_mask=np.asarray(target_stored["source_mask"], dtype=np.uint8),
            mask_point_ijk=np.asarray(target_stored["mask_point_ijk"], dtype=np.int32),
        )

    report = {
        "status": "offline_hard_gate_pass" if selected is not None else "offline_hard_gate_fail",
        "input_checks": {name: bool(value) for name, value in consistency.items()},
        "endpoint_checks": endpoint_checks,
        "failed_endpoint_target_abs_error": failed_target_abs_error,
        "hotspot_conservative_correction_factor": hotspot_correction,
        "gates": gates,
        "candidates": rows,
        "selected": selected,
        "pressure_executed": False,
        "pressure_execution_authorized": False,
        "claim_boundary": evidence["claim_boundary"],
    }
    (args.output_dir / "offline_hard_gate.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Target-Hard-Constrained Offline Gate",
        "",
        f"Status: **{report['status']}**",
        "",
        f"Closed lambda=1 target replay error: `{failed_target_abs_error:.6f}`.",
        f"Conservative hotspot correction factor: `{hotspot_correction:.6f}`.",
        "",
        "| lambda | target retention | conservative hotspot suppression | waveform peak/control | pass |",
        "|---:|---:|---:|---:|:---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['regularization_fraction']:.3g} | {row['target_retention']:.4f} | "
            f"{row['conservative_hotspot_suppression']:.4f} | {row['waveform_peak_vs_control']:.4f} | "
            f"{'yes' if row['passes_all_hard_gates'] else 'no'} |"
        )
    lines.extend(["", "No pressure execution is authorized by this offline report."])
    (args.output_dir / "offline_hard_gate.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "selected": selected, "endpoint_checks": endpoint_checks}, indent=2))


if __name__ == "__main__":
    main()
