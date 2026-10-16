from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from design_dual_point_hotspot_constrained_tr_20260720 import (
    extract_transfer_phasor,
    null_projected_weights,
    predicted_response,
)


ROOT = Path(__file__).resolve().parent
TARGET_ARTIFACT = ROOT / "outputs" / "dual_point_hotspot_constrained_tr_20260720" / "target_transfer_steering.npz"
TARGET_SIGNALS = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "offset_y-10p0_z-02p5" / "tr" / "element_signals.npz"
HOTSPOT_RUN = ROOT / "outputs" / "dual_point_hotspot_calibration_20260721" / "run"
EVIDENCE = ROOT / "outputs" / "evidence_briefs" / "dual_point_hotspot_calibration_20260721" / "evidence_brief.json"
OUTPUT = ROOT / "outputs" / "dual_point_hotspot_calibration_20260721" / "offline_analysis"


def array_hash(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes(order="C")).hexdigest()


def normalized_weights(weights: np.ndarray, reference_max_abs: float) -> np.ndarray:
    weights = np.asarray(weights, dtype=np.complex128)
    current = float(np.max(np.abs(weights)))
    if not np.isfinite(current) or current <= 0:
        raise ValueError("candidate weights are zero or non-finite")
    return weights * (reference_max_abs / current)


def evaluate_candidates(
    target_transfer: np.ndarray,
    hotspot_transfer: np.ndarray,
    regularization_fractions: list[float],
    minimum_target_retention: float,
    minimum_hotspot_suppression: float,
) -> list[dict[str, Any]]:
    target = np.asarray(target_transfer, dtype=np.complex128)
    hotspot = np.asarray(hotspot_transfer, dtype=np.complex128)
    if target.shape != hotspot.shape or target.ndim != 1:
        raise ValueError("target and hotspot transfer vectors must have the same 1D shape")
    conventional = np.conjugate(target)
    reference_max_abs = float(np.max(np.abs(conventional)))
    conventional = normalized_weights(conventional, reference_max_abs)
    target_reference = abs(predicted_response(target, conventional))
    hotspot_reference = abs(predicted_response(hotspot, conventional))
    if target_reference <= 0 or hotspot_reference <= 0:
        raise ValueError("conventional predicted responses must be nonzero")

    rows: list[dict[str, Any]] = []
    for fraction in regularization_fractions:
        candidate = null_projected_weights(target, hotspot, fraction)
        candidate = normalized_weights(candidate, reference_max_abs)
        target_response = abs(predicted_response(target, candidate))
        hotspot_response = abs(predicted_response(hotspot, candidate))
        target_retention = float(target_response / target_reference)
        hotspot_ratio = float(hotspot_response / hotspot_reference)
        hotspot_suppression = float(1.0 - hotspot_ratio)
        finite = bool(
            np.all(np.isfinite(candidate))
            and np.isfinite(target_retention)
            and np.isfinite(hotspot_suppression)
        )
        passes = bool(
            finite
            and target_retention >= minimum_target_retention
            and hotspot_suppression >= minimum_hotspot_suppression
        )
        rows.append({
            "regularization_fraction": float(fraction),
            "target_response_abs": float(target_response),
            "hotspot_response_abs": float(hotspot_response),
            "target_retention": target_retention,
            "hotspot_response_ratio": hotspot_ratio,
            "hotspot_suppression": hotspot_suppression,
            "max_abs_weight": float(np.max(np.abs(candidate))),
            "l2_weight_norm": float(np.linalg.norm(candidate)),
            "finite": finite,
            "passes_offline_gate": passes,
            "weights": candidate,
        })
    return rows


def select_candidate(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    passing = [row for row in rows if row["passes_offline_gate"]]
    if not passing:
        return None
    return max(passing, key=lambda row: (row["target_retention"], row["hotspot_suppression"]))


def validate_transfer_inputs(target: dict[str, np.ndarray], hotspot: dict[str, np.ndarray]) -> dict[str, bool]:
    target_mask = np.asarray(target["source_mask"], dtype=np.uint8)
    hotspot_mask = np.asarray(hotspot["source_mask"], dtype=np.uint8)
    target_rows = np.asarray(target["mask_point_ijk"], dtype=np.int32)
    hotspot_rows = np.asarray(hotspot["mask_point_ijk"], dtype=np.int32)
    return {
        "source_mask_exact": np.array_equal(target_mask, hotspot_mask),
        "c_order_rows_exact": np.array_equal(target_rows, hotspot_rows),
        "source_mask_hash_exact": array_hash(hotspot_mask) == "78bfe794004ff4df3ba1e41879684a55c29694fa41c2ed76bc067bb040ae5907",
        "signal_shape_exact": np.asarray(target["signals"]).shape == np.asarray(hotspot["signals"]).shape == (2979, 1867),
        "dt_exact": np.isclose(float(target["dt_s"]), float(hotspot["dt_s"]), rtol=1e-12, atol=1e-16),
        "frequency_exact": float(target["frequency_hz"]) == float(hotspot["frequency_hz"]) == 500000.0,
        "grid_exact": np.asarray(hotspot["grid_shape"]).astype(int).tolist() == [125, 60, 50],
        "target_exact": np.asarray(hotspot["target_index_ijk"]).astype(int).tolist() == [114, 36, 26],
        "crop_exact": np.asarray(hotspot["crop_origin_ijk"]).astype(int).tolist() == [37, 100, 79],
        "hotspot_local_exact": np.asarray(hotspot["calibration_point_local_ijk"]).astype(int).tolist() == [38, 39, 34],
        "hotspot_full_exact": np.asarray(hotspot["calibration_point_full_ijk"]).astype(int).tolist() == [75, 139, 113],
        "cfl_pml_exact": float(target["cfl"]) == float(hotspot["cfl"]) == 0.2 and int(target["pml_size"]) == int(hotspot["pml_size"]) == 12,
    }


def serializable_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "weights"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze the frozen H1 hotspot transfer without k-Wave.")
    parser.add_argument("--hotspot-signals", type=Path, default=HOTSPOT_RUN / "element_signals.npz")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()

    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    gate = evidence["offline_gate"]
    with np.load(TARGET_SIGNALS, allow_pickle=False) as stored:
        target_signals = {key: np.asarray(stored[key]) for key in stored.files}
    with np.load(args.hotspot_signals, allow_pickle=False) as stored:
        hotspot_signals = {key: np.asarray(stored[key]) for key in stored.files}
    checks = validate_transfer_inputs(target_signals, hotspot_signals)
    if not all(checks.values()):
        raise ValueError(f"transfer input consistency failed: {checks}")

    with np.load(TARGET_ARTIFACT, allow_pickle=False) as stored:
        target_transfer = np.asarray(stored["target_transfer"], dtype=np.complex128)
    recomputed_target = extract_transfer_phasor(
        target_signals["signals"], float(target_signals["dt_s"]), float(target_signals["frequency_hz"])
    )
    target_recompute_relative_l2 = float(
        np.linalg.norm(target_transfer - recomputed_target) / np.linalg.norm(recomputed_target)
    )
    if target_recompute_relative_l2 > 1e-6:
        raise ValueError(f"stored target transfer mismatch: relative L2={target_recompute_relative_l2}")

    hotspot_transfer = extract_transfer_phasor(
        hotspot_signals["signals"], float(hotspot_signals["dt_s"]), float(hotspot_signals["frequency_hz"])
    )
    rows = evaluate_candidates(
        target_transfer,
        hotspot_transfer,
        [float(value) for value in gate["regularization_fractions"]],
        float(gate["minimum_target_retention"]),
        float(gate["minimum_hotspot_suppression"]),
    )
    selected = select_candidate(rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output_dir / "hotspot_transfer_steering.npz",
        hotspot_transfer=hotspot_transfer.astype(np.complex64),
        target_transfer=target_transfer.astype(np.complex64),
        source_mask=np.asarray(hotspot_signals["source_mask"], dtype=np.uint8),
        mask_point_ijk=np.asarray(hotspot_signals["mask_point_ijk"], dtype=np.int32),
        dt_s=np.asarray(hotspot_signals["dt_s"], dtype=np.float64),
        frequency_hz=np.asarray(hotspot_signals["frequency_hz"], dtype=np.float64),
    )
    if selected is not None:
        np.savez_compressed(
            args.output_dir / "selected_complex_weights.npz",
            weights=np.asarray(selected["weights"], dtype=np.complex64),
            regularization_fraction=np.array(selected["regularization_fraction"], dtype=np.float64),
            source_mask=np.asarray(hotspot_signals["source_mask"], dtype=np.uint8),
            mask_point_ijk=np.asarray(hotspot_signals["mask_point_ijk"], dtype=np.int32),
        )

    report = {
        "status": "offline_gate_pass" if selected is not None else "offline_gate_fail",
        "input_checks": {name: bool(value) for name, value in checks.items()},
        "target_transfer_recompute_relative_l2": target_recompute_relative_l2,
        "normalization": gate["normalization"],
        "minimum_target_retention": gate["minimum_target_retention"],
        "minimum_hotspot_suppression": gate["minimum_hotspot_suppression"],
        "selection_rule": gate["selection"],
        "candidates": [serializable_row(row) for row in rows],
        "selected": None if selected is None else serializable_row(selected),
        "constrained_refocus_authorized_by_offline_gate": selected is not None,
        "pressure_executed_by_analysis": False,
        "claim_boundary": "linear_transfer_prediction_only_not_refocus_or_clinical_evidence",
    }
    (args.output_dir / "offline_gate.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# H1 Dual-Point Offline Gate",
        "",
        f"Status: **{report['status']}**",
        "",
        "| regularization | target retention | hotspot suppression | pass |",
        "|---:|---:|---:|:---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['regularization_fraction']:.3g} | {row['target_retention']:.4f} | "
            f"{row['hotspot_suppression']:.4f} | {'yes' if row['passes_offline_gate'] else 'no'} |"
        )
    lines.extend(["", "This is an amplitude-normalized linear transfer prediction. It is not a pressure-field or clinical result."])
    (args.output_dir / "offline_gate.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "selected": report["selected"]}, indent=2))


if __name__ == "__main__":
    main()
