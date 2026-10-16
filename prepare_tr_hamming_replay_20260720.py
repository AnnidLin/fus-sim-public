from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from simulate_source_array_focus import compute_apodization_weights


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "offset_y-10p0_z-02p5" / "tr"
OUTPUT = ROOT / "outputs" / "a5_hotspot_suppression_hamming_20260720" / "offset_y-10p0_z-02p5" / "tr"


def bowl_polar_angles(stored: dict[str, np.ndarray]) -> np.ndarray:
    active = np.asarray(stored["mask_point_ijk"], dtype=float)
    bowl = np.asarray(stored["bowl_index_ijk"], dtype=float)
    target = np.asarray(stored["target_index_ijk"], dtype=float)
    # The geometric radius, not the rasterized target distance, is stored in config JSON.
    config = json.loads(str(np.asarray(stored["config_json"]).item()))
    dx_m = float(np.asarray(stored["dx_m"]).item())
    radius_gp = float(config["transducer_radius_m"]) / dx_m
    axis = target - bowl
    axis /= np.linalg.norm(axis)
    sphere_center = bowl + radius_gp * axis
    relative = active - sphere_center
    local_axis = relative @ (-axis)
    return np.arccos(np.clip(local_axis / radius_gp, -1.0, 1.0))


def prepare(source_dir: Path, output_dir: Path) -> dict:
    source_path = source_dir / "element_signals.npz"
    with np.load(source_path, allow_pickle=False) as loaded:
        stored = {key: loaded[key] for key in loaded.files}
    signals = np.asarray(stored["signals"], dtype=np.float32)
    theta = bowl_polar_angles(stored)
    if len(theta) != signals.shape[0]:
        raise ValueError("Mask-point and signal-row counts differ")
    weights = compute_apodization_weights(theta, float(np.max(theta)), "hamming", 0.5).astype(np.float32)
    weighted = signals * weights[:, None]
    if not np.all(np.isfinite(weighted)):
        raise ValueError("Weighted signals are not finite")

    output_dir.mkdir(parents=True, exist_ok=True)
    stored.update(
        {
            "signals": weighted,
            "apodization_window": np.array("hamming"),
            "apodization_weights": weights,
            "apodization_theta_rad": theta.astype(np.float32),
            "source_element_signals_path": np.array(str(source_path.relative_to(ROOT)).replace("\\", "/")),
        }
    )
    np.savez_compressed(output_dir / "element_signals.npz", **stored)
    shutil.copy2(source_dir / "summary_calibrate.json", output_dir / "summary_calibrate_reference.json")

    metadata = {
        "status": "prepared",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_element_signals": str(source_path.relative_to(ROOT)).replace("\\", "/"),
        "output_element_signals": str((output_dir / "element_signals.npz").relative_to(ROOT)).replace("\\", "/"),
        "window": "hamming",
        "signal_shape": list(signals.shape),
        "weight_min": float(weights.min()),
        "weight_max": float(weights.max()),
        "weight_mean": float(weights.mean()),
        "weighted_to_unweighted_rms_ratio": float(np.sqrt(np.mean(weighted.astype(np.float64) ** 2)) / np.sqrt(np.mean(signals.astype(np.float64) ** 2))),
        "phase_and_time_samples_preserved": True,
        "normalization_deferred_to_refocus": True,
        "pressure_execution_authorized": True,
        "protocol": "outputs/evidence_briefs/a5_hotspot_suppression_hamming/evidence_brief.md",
    }
    (output_dir / "hamming_replay_preparation.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=SOURCE)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source_dir.resolve(), args.output_dir.resolve())))


if __name__ == "__main__":
    main()
