from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from simulate_kwave_3d_focus import (
    PROJECT_ROOT,
    LoadedModel,
    compute_focus_metrics,
    save_axis_profile,
    save_pressure_slices,
    write_focus_metrics,
)


def load_analysis_inputs(input_dir: Path, nearfield_mm: float) -> tuple[np.ndarray, np.ndarray, LoadedModel, float]:
    pressure_path = input_dir / "pressure_max_mpa.npz"
    if not pressure_path.exists():
        raise FileNotFoundError(f"Missing pressure output: {pressure_path}")

    data = np.load(pressure_path)
    required = {"pressure_max_mpa", "dx_m", "target_index_ijk", "source_mask"}
    missing = required - set(data.files)
    if missing:
        raise ValueError(f"Pressure output is missing required keys: {sorted(missing)}")

    pressure_mpa = np.asarray(data["pressure_max_mpa"], dtype=np.float32)
    source_mask = np.asarray(data["source_mask"], dtype=bool)
    dx_m = float(np.asarray(data["dx_m"]).item())
    target_index_ijk = np.asarray(data["target_index_ijk"], dtype=np.int32)
    crop_origin_ijk = np.asarray(data["crop_origin_ijk"], dtype=np.int32) if "crop_origin_ijk" in data.files else np.zeros(3, dtype=np.int32)

    if pressure_mpa.shape != source_mask.shape:
        raise ValueError("pressure_max_mpa and source_mask must have matching shapes.")
    if target_index_ijk.shape != (3,):
        raise ValueError("target_index_ijk must contain exactly 3 entries.")
    if np.any(target_index_ijk < 0) or np.any(target_index_ijk >= np.array(pressure_mpa.shape)):
        raise ValueError(f"target_index_ijk {target_index_ijk.tolist()} is outside pressure shape {pressure_mpa.shape}.")

    labels = np.asarray(data["labels"], dtype=np.uint8) if "labels" in data.files else None
    model_path = PROJECT_ROOT / "outputs" / "skull_model_3d" / "acoustic_model_3d.npz"
    if labels is None and model_path.exists():
        model_data = np.load(model_path)
        if "labels" in model_data.files:
            labels_full = np.asarray(model_data["labels"], dtype=np.uint8)
            x0, y0, z0 = crop_origin_ijk
            x1, y1, z1 = crop_origin_ijk + np.array(pressure_mpa.shape)
            if x1 <= labels_full.shape[0] and y1 <= labels_full.shape[1] and z1 <= labels_full.shape[2]:
                labels = labels_full[x0:x1, y0:y1, z0:z1]

    zeros = np.zeros(pressure_mpa.shape, dtype=np.float32)
    model = LoadedModel(
        labels=labels,
        sound_speed=zeros,
        density=zeros,
        alpha_coeff=zeros,
        dx_m=dx_m,
        target_index_ijk=target_index_ijk,
        source_center_index_ijk=None,
        entry_index_ijk=None,
        beam_axis=None,
        entry_plan=None,
        crop_origin_ijk=crop_origin_ijk,
        source_model_shape=tuple(int(v) for v in pressure_mpa.shape),
    )
    return pressure_mpa, source_mask, model, nearfield_mm * 1e-3


def write_analysis_summary(input_dir: Path, metrics: dict[str, object]) -> None:
    with (input_dir / "focus_metrics.txt").open("w", encoding="utf-8") as handle:
        for key, value in metrics.items():
            handle.write(f"{key}={value}\n")
    (input_dir / "focus_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")


def analyze(input_dir: Path, nearfield_mm: float) -> None:
    pressure_mpa, source_mask, model, nearfield_m = load_analysis_inputs(input_dir, nearfield_mm)
    metrics = compute_focus_metrics(
        pressure_mpa,
        source_mask,
        model.target_index_ijk,
        model.dx_m,
        nearfield_m,
    )
    save_pressure_slices(input_dir, pressure_mpa, source_mask, model, metrics)
    save_axis_profile(input_dir, pressure_mpa, model, metrics)
    write_focus_metrics(input_dir, metrics)
    write_analysis_summary(input_dir, metrics)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze an existing 3D k-Wave tFUS pressure output.")
    parser.add_argument(
        "--input-dir",
        default=str(PROJECT_ROOT / "outputs" / "kwave_3d_focus"),
        help="Directory containing pressure_max_mpa.npz.",
    )
    parser.add_argument("--nearfield-mm", type=float, default=10.0, help="Nearfield distance after source mask to exclude.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    analyze(Path(args.input_dir), args.nearfield_mm)
