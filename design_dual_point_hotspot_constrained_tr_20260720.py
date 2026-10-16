from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
CONTROL = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "offset_y-10p0_z-02p5" / "tr"
OUTPUT = ROOT / "outputs" / "dual_point_hotspot_constrained_tr_20260720"
FREQUENCY_HZ = 500_000.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_transfer_phasor(signals: np.ndarray, dt_s: float, frequency_hz: float) -> np.ndarray:
    signals = np.asarray(signals, dtype=np.float64)
    if signals.ndim != 2 or not np.all(np.isfinite(signals)):
        raise ValueError("signals must be a finite [elements, time] matrix")
    time = np.arange(signals.shape[1], dtype=np.float64) * dt_s
    kernel = np.exp(-2j * np.pi * frequency_hz * time)
    phasor = signals @ kernel
    if not np.all(np.isfinite(phasor)) or not np.any(np.abs(phasor) > 0):
        raise ValueError("transfer phasor is zero or non-finite")
    return phasor


def null_projected_weights(
    target_transfer: np.ndarray,
    hotspot_transfer: np.ndarray,
    regularization_fraction: float = 0.0,
) -> np.ndarray:
    target = np.asarray(target_transfer, dtype=np.complex128)
    hotspot = np.asarray(hotspot_transfer, dtype=np.complex128)
    if target.shape != hotspot.shape or target.ndim != 1:
        raise ValueError("target and hotspot transfers must be equal-length vectors")
    q0 = np.conjugate(target)
    energy = float(np.vdot(hotspot, hotspot).real)
    if energy <= 0:
        raise ValueError("hotspot transfer has zero energy")
    denominator = energy * (1.0 + max(float(regularization_fraction), 0.0))
    return q0 - np.conjugate(hotspot) * (np.dot(hotspot, q0) / denominator)


def predicted_response(transfer: np.ndarray, source_weights: np.ndarray) -> complex:
    return complex(np.dot(np.asarray(transfer), np.asarray(source_weights)))


def main() -> None:
    signals_path = CONTROL / "element_signals.npz"
    pressure_path = CONTROL / "pressure_max_mpa.npz"
    with np.load(signals_path, allow_pickle=False) as stored:
        signals = np.asarray(stored["signals"], dtype=np.float32)
        dt_s = float(np.asarray(stored["dt_s"]).item())
        mask = np.asarray(stored["source_mask"], dtype=np.uint8)
        mask_points = np.asarray(stored["mask_point_ijk"], dtype=np.int32)
        crop_origin = np.asarray(stored["crop_origin_ijk"], dtype=np.int32)
        target_local = np.asarray(stored["target_index_ijk"], dtype=np.int32)
    with np.load(pressure_path) as field:
        pressure = np.asarray(field["pressure_max_mpa"])
        labels = np.asarray(field["labels"])
        hotspot_local = np.asarray(np.unravel_index(int(np.argmax(pressure)), pressure.shape), dtype=np.int32)
        hotspot_label = int(labels[tuple(hotspot_local)])
        hotspot_pressure = float(pressure[tuple(hotspot_local)])

    target_transfer = extract_transfer_phasor(signals, dt_s, FREQUENCY_HZ)
    conventional_weights = np.conjugate(target_transfer)
    target_response = predicted_response(target_transfer, conventional_weights)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUTPUT / "target_transfer_steering.npz",
        target_transfer=target_transfer.astype(np.complex64),
        conventional_weights=conventional_weights.astype(np.complex64),
        mask_point_ijk=mask_points,
        source_mask=mask,
        dt_s=np.array(dt_s),
        frequency_hz=np.array(FREQUENCY_HZ),
    )
    request = {
        "status": "hotspot_transfer_required_no_pressure_authorized",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "trajectory": "offset_y-10p0_z-02p5",
        "frequency_hz": FREQUENCY_HZ,
        "element_count": int(signals.shape[0]),
        "time_sample_count": int(signals.shape[1]),
        "dt_s": dt_s,
        "crop_origin_ijk": crop_origin.tolist(),
        "target_local_ijk": target_local.tolist(),
        "target_full_ijk": (target_local + crop_origin).tolist(),
        "hotspot_local_ijk": hotspot_local.tolist(),
        "hotspot_full_ijk": (hotspot_local + crop_origin).tolist(),
        "hotspot_label": hotspot_label,
        "hotspot_pressure_mpa_control": hotspot_pressure,
        "target_transfer_norm": float(np.linalg.norm(target_transfer)),
        "conventional_predicted_target_response_abs": float(abs(target_response)),
        "source_mask_points": int(mask.sum()),
        "source_mask_sha256": hashlib.sha256(mask.tobytes(order="C")).hexdigest(),
        "element_signals_sha256": sha256(signals_path),
        "required_future_artifact": "hotspot_transfer_steering.npz with exact source mask hash and C-order rows",
        "implementation_prerequisite": "calibration point override independent of frozen bowl aim/geometry",
        "hotspot_calibration_pressure_authorized": False,
        "constrained_refocus_authorized": False,
        "next_solver": "null_projected_weights(target_transfer, hotspot_transfer, preregistered_regularization_fraction)",
        "claim_boundary": "design_only_not_execution_evidence",
    }
    (OUTPUT / "hotspot_calibration_request.json").write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Dual-Point Hotspot-Constrained TR Design",
        "",
        f"- Target full index: `{request['target_full_ijk']}`",
        f"- Hotspot full index: `{request['hotspot_full_ijk']}` (label {hotspot_label}, {hotspot_pressure:.3f} MPa in control)",
        f"- Frozen source rows: {request['element_count']}",
        f"- Source mask SHA256: `{request['source_mask_sha256']}`",
        "",
        "The existing target calibration has been converted to a 500-kHz complex steering vector. A second transfer vector from the frozen skull hotspot to the exact same bowl rows is required before constrained weights can be computed.",
        "",
        "No pressure is authorized by this design packet. The next implementation must separate calibration-point position from bowl geometry, then pass exact mask/grid/dt/hash checks.",
    ]
    (OUTPUT / "design.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": request["status"], "target": request["target_full_ijk"], "hotspot": request["hotspot_full_ijk"], "elements": request["element_count"]}))


if __name__ == "__main__":
    main()
