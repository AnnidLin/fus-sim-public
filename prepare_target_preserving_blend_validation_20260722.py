from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parent
SELECTED = ROOT / "outputs" / "target_preserving_waveform_blend_20260722" / "selected_element_signals.npz"
CONTROL = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "offset_y-10p0_z-02p5" / "tr" / "element_signals.npz"
CONSTRAINED = ROOT / "outputs" / "dual_point_constrained_refocus_20260721" / "run" / "element_signals.npz"
OFFLINE = ROOT / "outputs" / "target_preserving_waveform_blend_20260722" / "offline_blend_gate.json"
EVIDENCE = ROOT / "outputs" / "evidence_briefs" / "target_preserving_blend_validation_20260722" / "evidence_brief.json"
OUTPUT = ROOT / "outputs" / "target_preserving_blend_validation_20260722" / "run"


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as stored:
        return {key: np.asarray(stored[key]) for key in stored.files}


def sha256_bytes(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes(order="C")).hexdigest()


def expected_blend(control: np.ndarray, constrained: np.ndarray, fraction: float) -> np.ndarray:
    first = np.asarray(control, dtype=np.float64)
    second = np.asarray(constrained, dtype=np.float64)
    if first.shape != second.shape:
        raise ValueError("endpoint signal shapes differ")
    return ((1.0 - fraction) * first + fraction * second).astype(np.float32)


def main() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    offline = json.loads(OFFLINE.read_text(encoding="utf-8"))
    selected = load_npz(SELECTED)
    control = load_npz(CONTROL)
    constrained = load_npz(CONSTRAINED)
    alpha = float(selected["waveform_blend_fraction"])
    expected = expected_blend(control["signals"], constrained["signals"], alpha)
    signals = np.asarray(selected["signals"], dtype=np.float32)
    mask = np.asarray(selected["source_mask"], dtype=np.uint8)
    gates = evidence["waveform_gates"]
    predicted = offline["selected"]
    checks = {
        "offline_gate_pass": offline["status"] == "offline_blend_gate_pass",
        "selected_fraction_exact": alpha == evidence["selected_blend_fraction"] == predicted["blend_fraction"],
        "signals_shape_exact": list(signals.shape) == gates["signals_shape"],
        "finite_nonzero": bool(np.all(np.isfinite(signals)) and np.max(np.abs(signals)) > 0),
        "source_mask_hash_exact": sha256_bytes(mask) == gates["source_mask_sha256"],
        "source_rows_exact": np.array_equal(selected["mask_point_ijk"], control["mask_point_ijk"]),
        "blend_matrix_exact": np.array_equal(signals, expected),
        "target_prediction_pass": predicted["target_retention"] >= gates["target_retention_min"],
        "hotspot_prediction_pass": predicted["corrected_original_hotspot_suppression"] >= gates["conservative_original_hotspot_suppression_min"],
    }
    if not all(checks.values()):
        raise ValueError(f"waveform gate failed: {checks}")
    if (OUTPUT / "pressure_max_mpa.npz").exists() or (OUTPUT / "summary.json").exists():
        raise FileExistsError("validation pressure output already exists")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    output_arrays: dict[str, Any] = dict(selected)
    np.savez_compressed(OUTPUT / "element_signals.npz", **output_arrays)
    report = {
        "status": "waveform_gate_pass",
        "blend_fraction": alpha,
        "checks": {name: bool(value) for name, value in checks.items()},
        "predicted_target_retention": predicted["target_retention"],
        "predicted_conservative_original_hotspot_suppression": predicted["corrected_original_hotspot_suppression"],
        "waveform_peak_vs_control": predicted["waveform_peak_vs_control"],
        "signals_shape": list(signals.shape),
        "source_mask_sha256": sha256_bytes(mask),
        "signals_sha256": sha256_bytes(signals),
        "pressure_executed": False,
    }
    (OUTPUT / "waveform_gate.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
