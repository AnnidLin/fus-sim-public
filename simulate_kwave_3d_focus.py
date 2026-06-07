from __future__ import annotations

import argparse
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parent
RUNTIME_TMP = PROJECT_ROOT / ".tmp"
MPLCONFIGDIR = RUNTIME_TMP / f"mplconfig-kwave3d-runtime-{os.getpid()}"
RUNTIME_TMP.mkdir(parents=True, exist_ok=True)
MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(RUNTIME_TMP)
os.environ["TMP"] = str(RUNTIME_TMP)
os.environ["MPLCONFIGDIR"] = str(MPLCONFIGDIR)
logging.getLogger("matplotlib").setLevel(logging.ERROR)

from kwave.data import Vector
from kwave.kgrid import kWaveGrid
from kwave.kmedium import kWaveMedium
from kwave.ksensor import kSensor
from kwave.ksource import kSource
from kwave.kspaceFirstOrder import kspaceFirstOrder, reshape_to_grid
from kwave.utils.mapgen import make_bowl
from kwave.utils.signals import tone_burst

from simulation_environment import build_environment_record
from simulation_quality import build_simulation_quality, write_quality_dry_run_summary


REQUIRED_MODEL_KEYS = {
    "sound_speed",
    "density",
    "alpha_coeff",
    "dx_m",
    "target_index_ijk",
}


@dataclass(frozen=True)
class KWave3DConfig:
    model_path: Path = PROJECT_ROOT / "outputs" / "skull_model_3d" / "acoustic_model_3d.npz"
    entry_plan_path: Path | None = None
    target_index_override: tuple[int, int, int] | None = None
    frequency_hz: float = 500_000.0
    source_pressure_pa: float = 1_000_000.0
    transducer_radius_m: float = 30e-3
    aperture_diameter_m: float = 25e-3
    tone_burst_cycles: int = 6
    cfl: float = 0.20
    simulation_time_s: float = 45e-6
    pml_size: int = 8
    preset: str = "quick"
    backend: str = "python"
    device: str = "cpu"
    quick_mode: bool = True
    quick_lateral_half_width_m: float | None = None
    quick_post_target_margin_m: float | None = None
    alpha_power: float = 1.5
    nearfield_exclusion_m: float = 10e-3
    record_target_waveform: bool = False


@dataclass(frozen=True)
class LoadedModel:
    labels: np.ndarray | None
    sound_speed: np.ndarray
    density: np.ndarray
    alpha_coeff: np.ndarray
    dx_m: float
    target_index_ijk: np.ndarray
    source_center_index_ijk: np.ndarray | None
    entry_index_ijk: np.ndarray | None
    beam_axis: np.ndarray | None
    entry_plan: dict[str, object] | None
    crop_origin_ijk: np.ndarray
    source_model_shape: tuple[int, int, int]
    alpha_power: float | None = None
    alpha_mode: str | None = None
    alpha_unit_semantics: str | None = None
    alpha_coeff_kind: str | None = None
    alpha_source_route: str | None = None
    alpha_semantics_status: str | None = None
    alpha_pressure_allowed: bool | None = None


def parse_index(value: str) -> tuple[int, int, int]:
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("index must be formatted as i,j,k")
    return tuple(parts)


def load_entry_plan(path: Path | None) -> dict[str, object] | None:
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"Missing entry plan: {path}")
    plan = json.loads(path.read_text(encoding="utf-8"))
    required = {"target_index_ijk", "source_center_index_ijk", "entry_index_ijk", "beam_axis"}
    missing = required - set(plan)
    if missing:
        raise ValueError(f"Entry plan is missing required keys: {sorted(missing)}")
    beam_axis = np.array(plan["beam_axis"], dtype=int)
    if beam_axis.shape != (3,) or int(beam_axis[0]) <= 0:
        raise ValueError("Only left-side entry plans with a positive x-directed beam are supported in this first version.")
    return plan


def optional_npz_string(data: np.lib.npyio.NpzFile, key: str) -> str | None:
    if key not in data.files:
        return None
    value = data[key]
    try:
        text = str(value.item())
    except ValueError:
        text = str(value.tolist())
    text = text.strip()
    return text if text else None


def optional_npz_bool(data: np.lib.npyio.NpzFile, key: str) -> bool | None:
    if key not in data.files:
        return None
    value = data[key]
    try:
        raw = value.item()
    except ValueError:
        raw = value.tolist()
    if isinstance(raw, (bool, np.bool_)):
        return bool(raw)
    text = str(raw).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def load_model(config: KWave3DConfig) -> LoadedModel:
    if not config.model_path.exists():
        raise FileNotFoundError(f"Missing 3D acoustic model: {config.model_path}")

    entry_plan = load_entry_plan(config.entry_plan_path)
    data = np.load(config.model_path)
    missing = REQUIRED_MODEL_KEYS - set(data.files)
    if missing:
        raise ValueError(f"Model is missing required keys: {sorted(missing)}")

    sound_speed = np.asarray(data["sound_speed"], dtype=np.float32)
    density = np.asarray(data["density"], dtype=np.float32)
    alpha_coeff = np.asarray(data["alpha_coeff"], dtype=np.float32)
    labels = np.asarray(data["labels"], dtype=np.uint8) if "labels" in data.files else None
    dx_m = float(np.asarray(data["dx_m"]).item())
    target = np.asarray(data["target_index_ijk"], dtype=np.int32)

    alpha_power = None
    if "alpha_power" in data.files:
        val = data["alpha_power"].item()
        if not np.isnan(val):
            alpha_power = float(val)
    alpha_mode = optional_npz_string(data, "alpha_mode")
    alpha_unit_semantics = optional_npz_string(data, "alpha_unit_semantics")
    alpha_coeff_kind = optional_npz_string(data, "alpha_coeff_kind")
    alpha_source_route = optional_npz_string(data, "alpha_source_route")
    alpha_semantics_status = optional_npz_string(data, "alpha_semantics_status")
    alpha_pressure_allowed = optional_npz_bool(data, "alpha_pressure_allowed")
    source_center = None
    entry_index = None
    beam_axis = None

    if entry_plan is not None:
        target = np.asarray(entry_plan["target_index_ijk"], dtype=np.int32)
        source_center = np.asarray(entry_plan["source_center_index_ijk"], dtype=np.int32)
        entry_index = np.asarray(entry_plan["entry_index_ijk"], dtype=np.int32)
        beam_axis = np.asarray(entry_plan["beam_axis"], dtype=np.int32)
    if config.target_index_override is not None:
        override_target = np.asarray(config.target_index_override, dtype=np.int32)
        if entry_plan is not None and not np.array_equal(override_target, target):
            raise ValueError("--target-index must match entry_plan target_index_ijk when --entry-plan is used.")
        target = override_target

    if sound_speed.shape != density.shape or sound_speed.shape != alpha_coeff.shape:
        raise ValueError("sound_speed, density, and alpha_coeff must have matching shapes.")
    if target.shape != (3,):
        raise ValueError("target_index_ijk must contain exactly 3 entries.")
    if np.any(target < 0) or np.any(target >= np.array(sound_speed.shape)):
        raise ValueError(f"target_index_ijk {target.tolist()} is outside model shape {sound_speed.shape}.")
    if source_center is not None and (source_center.shape != (3,) or np.any(source_center < 0) or np.any(source_center >= np.array(sound_speed.shape))):
        raise ValueError(f"source_center_index_ijk {source_center.tolist()} is outside model shape {sound_speed.shape}.")
    if entry_index is not None and (entry_index.shape != (3,) or np.any(entry_index < 0) or np.any(entry_index >= np.array(sound_speed.shape))):
        raise ValueError(f"entry_index_ijk {entry_index.tolist()} is outside model shape {sound_speed.shape}.")

    crop_origin = np.zeros(3, dtype=np.int32)
    source_shape = tuple(int(v) for v in sound_speed.shape)

    if config.quick_mode:
        radius_gp = int(round(config.transducer_radius_m / dx_m))
        if config.quick_lateral_half_width_m is None:
            lateral_half_width = max(int(round(config.aperture_diameter_m / dx_m)), 24)
        else:
            lateral_half_width = max(8, int(round(config.quick_lateral_half_width_m / dx_m)))
        if config.quick_post_target_margin_m is None:
            post_target_margin_gp = radius_gp + 8
        else:
            post_target_margin_gp = max(4, int(round(config.quick_post_target_margin_m / dx_m)))
        if source_center is not None:
            anchor_min = np.minimum(target, source_center)
            anchor_max = np.maximum(target, source_center)
            x0 = max(0, int(anchor_min[0]) - config.pml_size - 4)
            x1 = min(sound_speed.shape[0], int(anchor_max[0]) + post_target_margin_gp)
            y0 = max(0, int(anchor_min[1]) - lateral_half_width)
            y1 = min(sound_speed.shape[1], int(anchor_max[1]) + lateral_half_width + 1)
            z0 = max(0, int(anchor_min[2]) - lateral_half_width)
            z1 = min(sound_speed.shape[2], int(anchor_max[2]) + lateral_half_width + 1)
        else:
            x0 = max(0, int(target[0]) - radius_gp - 4)
            x1 = min(sound_speed.shape[0], int(target[0]) + post_target_margin_gp)
            y0 = max(0, int(target[1]) - lateral_half_width)
            y1 = min(sound_speed.shape[1], int(target[1]) + lateral_half_width + 1)
            z0 = max(0, int(target[2]) - lateral_half_width)
            z1 = min(sound_speed.shape[2], int(target[2]) + lateral_half_width + 1)
        crop = (slice(x0, x1), slice(y0, y1), slice(z0, z1))
        crop_origin = np.array([x0, y0, z0], dtype=np.int32)

        sound_speed = sound_speed[crop]
        density = density[crop]
        alpha_coeff = alpha_coeff[crop]
        labels = labels[crop] if labels is not None else None
        target = target - crop_origin
        if source_center is not None:
            source_center = source_center - crop_origin
        if entry_index is not None:
            entry_index = entry_index - crop_origin

    return LoadedModel(
        labels=labels,
        sound_speed=sound_speed,
        density=density,
        alpha_coeff=alpha_coeff,
        dx_m=dx_m,
        target_index_ijk=target.astype(np.int32),
        source_center_index_ijk=None if source_center is None else source_center.astype(np.int32),
        entry_index_ijk=None if entry_index is None else entry_index.astype(np.int32),
        beam_axis=None if beam_axis is None else beam_axis.astype(np.int32),
        entry_plan=entry_plan,
        crop_origin_ijk=crop_origin,
        source_model_shape=source_shape,
        alpha_power=alpha_power,
        alpha_mode=alpha_mode,
        alpha_unit_semantics=alpha_unit_semantics,
        alpha_coeff_kind=alpha_coeff_kind,
        alpha_source_route=alpha_source_route,
        alpha_semantics_status=alpha_semantics_status,
        alpha_pressure_allowed=alpha_pressure_allowed,
    )


def odd_grid_points(length_m: float, dx_m: float) -> int:
    points = int(round(length_m / dx_m))
    return points if points % 2 == 1 else points + 1


def alpha_semantics_summary(model: LoadedModel, actual_alpha_power: float) -> dict[str, object]:
    status = model.alpha_semantics_status
    pressure_allowed = model.alpha_pressure_allowed
    if pressure_allowed is None:
        pressure_allowed = not (status and "review_pending" in status)
    notes: list[str] = []
    if model.alpha_pressure_allowed is False:
        notes.append("Mapping profile explicitly sets pressure_allowed=false.")
    if status and "review_pending" in status:
        notes.append("Mapping alpha semantics are review-pending; do not use this model for pressure conclusions.")
    if actual_alpha_power == 1.0 and model.alpha_mode is None:
        notes.append("alpha_power=1.0 with alpha_mode unset requires dispersion/no_dispersion review before pressure use.")
        pressure_allowed = False
    return {
        "alpha_power": actual_alpha_power,
        "alpha_mode": model.alpha_mode,
        "alpha_unit_semantics": model.alpha_unit_semantics,
        "alpha_coeff_kind": model.alpha_coeff_kind,
        "alpha_source_route": model.alpha_source_route,
        "alpha_semantics_status": model.alpha_semantics_status,
        "alpha_pressure_allowed_metadata": model.alpha_pressure_allowed,
        "pressure_allowed_by_alpha_semantics": pressure_allowed,
        "notes": notes,
    }


def choose_bowl_position(model: LoadedModel, config: KWave3DConfig) -> tuple[np.ndarray, np.ndarray, int, int]:
    radius_gp = int(round(config.transducer_radius_m / model.dx_m))
    diameter_gp = odd_grid_points(config.aperture_diameter_m, model.dx_m)
    target_one = model.target_index_ijk.astype(int) + 1
    if model.source_center_index_ijk is not None:
        bowl_one = model.source_center_index_ijk.astype(int) + 1
    else:
        bowl_one = target_one - np.array([radius_gp, 0, 0], dtype=int)
    bowl_one[0] = max(1, min(int(model.sound_speed.shape[0]), int(bowl_one[0])))
    bowl_one[1] = max(1, min(int(model.sound_speed.shape[1]), int(bowl_one[1])))
    bowl_one[2] = max(1, min(int(model.sound_speed.shape[2]), int(bowl_one[2])))
    return bowl_one, target_one, radius_gp, diameter_gp


def build_source_mask(model: LoadedModel, config: KWave3DConfig) -> tuple[np.ndarray, dict[str, object]]:
    bowl_one, target_one, radius_gp, diameter_gp = choose_bowl_position(model, config)
    grid_size = Vector(list(model.sound_speed.shape))
    source_mask = make_bowl(
        grid_size,
        Vector(bowl_one.tolist()),
        radius_gp,
        diameter_gp,
        Vector(target_one.tolist()),
        binary=True,
        remove_overlap=True,
    ).astype(bool)

    if not np.any(source_mask):
        raise ValueError("Generated 3D bowl source mask is empty.")

    metadata = {
        "bowl_index_ijk": (bowl_one - 1).astype(int).tolist(),
        "target_index_ijk": model.target_index_ijk.astype(int).tolist(),
        "radius_grid_points": int(radius_gp),
        "diameter_grid_points": int(diameter_gp),
        "source_points": int(np.sum(source_mask)),
    }
    if model.source_center_index_ijk is not None:
        metadata["source_center_index_ijk"] = model.source_center_index_ijk.astype(int).tolist()
    if model.entry_index_ijk is not None:
        metadata["entry_index_ijk"] = model.entry_index_ijk.astype(int).tolist()
    if model.beam_axis is not None:
        metadata["beam_axis"] = model.beam_axis.astype(int).tolist()
    if model.labels is not None:
        labels_at_source = model.labels[source_mask]
        unique, counts = np.unique(labels_at_source, return_counts=True)
        metadata["source_label_counts"] = {str(int(k)): int(v) for k, v in zip(unique, counts)}
    return source_mask, metadata


def run_kwave(model: LoadedModel, source_mask: np.ndarray, config: KWave3DConfig, record_target_waveform: bool = False) -> tuple[np.ndarray, float, dict[str, object], np.ndarray | None]:
    c_max = float(np.max(model.sound_speed))
    dt_s = config.cfl * model.dx_m / c_max
    nt = int(np.ceil(config.simulation_time_s / dt_s))

    kgrid = kWaveGrid(list(model.sound_speed.shape), [model.dx_m, model.dx_m, model.dx_m])
    kgrid.setTime(nt, dt_s)

    actual_alpha_power = model.alpha_power if model.alpha_power is not None else config.alpha_power
    medium = kWaveMedium(
        sound_speed=model.sound_speed,
        density=model.density,
        alpha_coeff=model.alpha_coeff,
        alpha_power=np.array(actual_alpha_power),
        alpha_mode=model.alpha_mode,
    )

    source = kSource()
    source.p_mask = source_mask
    source.p = config.source_pressure_pa * tone_burst(
        1.0 / dt_s,
        config.frequency_hz,
        config.tone_burst_cycles,
        signal_length=nt,
    )
    source.p_mode = "dirichlet"

    record_list = ["p_max", "p_min"]
    if record_target_waveform:
        record_list.append("p")
    sensor = kSensor(
        mask=np.ones(model.sound_speed.shape, dtype=bool),
        record=record_list,
    )

    start = time.perf_counter()
    result = kspaceFirstOrder(
        kgrid,
        medium,
        source,
        sensor,
        backend=config.backend,
        device=config.device,
        pml_size=config.pml_size,
        pml_inside=False,
        quiet=True,
    )
    runtime_s = time.perf_counter() - start

    p_max = reshape_to_grid(result["p_max"], model.sound_speed.shape)
    p_min = reshape_to_grid(result["p_min"], model.sound_speed.shape)
    pressure_mpa = np.maximum(np.abs(p_max), np.abs(p_min)).astype(np.float32) / 1e6

    target_waveform = None
    if record_target_waveform and "p" in result:
        target = model.target_index_ijk.astype(int)
        flat_idx = np.ravel_multi_index(target, model.sound_speed.shape)
        target_waveform = np.asarray(result["p"][flat_idx, :], dtype=np.float32)

    # Clean up massive 3D full-grid time series to prevent OOM
    if "p" in result:
        del result["p"]
    del result
    import gc
    gc.collect()

    runtime_metadata = {
        "dt_s": dt_s,
        "nt": nt,
        "c_max_m_s": c_max,
        "backend": config.backend,
        "device": config.device,
    }
    return pressure_mpa, runtime_s, runtime_metadata, target_waveform


def viridis_like(values: np.ndarray) -> np.ndarray:
    stops = np.array(
        [
            [68, 1, 84],
            [59, 82, 139],
            [33, 145, 140],
            [94, 201, 98],
            [253, 231, 37],
        ],
        dtype=float,
    )
    scaled = np.clip(values, 0.0, 1.0) * (len(stops) - 1)
    low = np.floor(scaled).astype(int)
    high = np.clip(low + 1, 0, len(stops) - 1)
    blend = scaled[..., None] - low[..., None]
    return ((1.0 - blend) * stops[low] + blend * stops[high]).astype(np.uint8)


def pressure_slice_image(slice_2d: np.ndarray) -> Image.Image:
    vmax = float(np.max(slice_2d))
    scaled = slice_2d / vmax if vmax > 0 else slice_2d
    return Image.fromarray(viridis_like(scaled), mode="RGB")


def overlay_mask(image: Image.Image, mask_2d: np.ndarray, color: tuple[int, int, int]) -> Image.Image:
    rgb = np.asarray(image).copy()
    rgb[mask_2d] = (0.30 * rgb[mask_2d] + 0.70 * np.array(color)).astype(np.uint8)
    return Image.fromarray(rgb, mode="RGB")


def annotate(image: Image.Image, title: str, markers: list[tuple[int, int, tuple[int, int, int], str]]) -> Image.Image:
    scale = 5
    image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (image.width, image.height + 34), "white")
    canvas.paste(image, (0, 34))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 10), title, fill=(0, 0, 0))
    for x, y, color, label in markers:
        x *= scale
        y = y * scale + 34
        draw.line((x - 8, y, x + 8, y), fill=color, width=2)
        draw.line((x, y - 8, x, y + 8), fill=color, width=2)
        draw.text((x + 10, y - 8), label, fill=color)
    return canvas


def compute_focus_metrics(
    pressure_mpa: np.ndarray,
    source_mask: np.ndarray,
    target_index_ijk: np.ndarray,
    dx_m: float,
    nearfield_exclusion_m: float,
) -> dict[str, object]:
    peak = np.array(np.unravel_index(np.argmax(pressure_mpa), pressure_mpa.shape), dtype=int)
    target = target_index_ijk.astype(int)
    distance_mm = float(np.linalg.norm((peak - target) * dx_m) * 1e3)
    window_radius = 3
    window_slices = tuple(
        slice(max(0, int(t) - window_radius), min(int(t) + window_radius + 1, pressure_mpa.shape[axis]))
        for axis, t in enumerate(target)
    )
    target_window = pressure_mpa[window_slices]
    target_window_local_peak = np.array(np.unravel_index(np.argmax(target_window), target_window.shape), dtype=int)
    target_window_origin = np.array([s.start for s in window_slices], dtype=int)
    target_window_peak = target_window_origin + target_window_local_peak

    source_x = np.where(source_mask)[0]
    source_x_max = int(np.max(source_x)) if source_x.size else 0
    nearfield_grid_points = max(0, int(round(nearfield_exclusion_m / dx_m)))
    effective_start_x = min(pressure_mpa.shape[0] - 1, source_x_max + nearfield_grid_points)
    effective_field = pressure_mpa[effective_start_x:, :, :]
    effective_local_peak = np.array(np.unravel_index(np.argmax(effective_field), effective_field.shape), dtype=int)
    effective_peak = effective_local_peak + np.array([effective_start_x, 0, 0], dtype=int)
    effective_distance_mm = float(np.linalg.norm((effective_peak - target) * dx_m) * 1e3)

    target_pressure = float(pressure_mpa[tuple(target)])
    global_peak_pressure = float(pressure_mpa[tuple(peak)])
    effective_peak_pressure = float(pressure_mpa[tuple(effective_peak)])

    return {
        "global_peak_index_ijk": peak.tolist(),
        "global_peak_mpa": global_peak_pressure,
        "global_peak_to_target_distance_mm": distance_mm,
        "target_pressure_mpa": target_pressure,
        "target_window_radius_grid_points": window_radius,
        "target_window_peak_index_ijk": target_window_peak.tolist(),
        "target_window_peak_mpa": float(pressure_mpa[tuple(target_window_peak)]),
        "nearfield_exclusion_mm": float(nearfield_exclusion_m * 1e3),
        "nearfield_exclusion_grid_points": int(nearfield_grid_points),
        "effective_start_x_index": int(effective_start_x),
        "effective_peak_index_ijk": effective_peak.tolist(),
        "effective_peak_mpa": effective_peak_pressure,
        "effective_peak_to_target_distance_mm": effective_distance_mm,
        "target_to_global_peak_ratio": target_pressure / global_peak_pressure if global_peak_pressure > 0 else 0.0,
        "target_to_effective_peak_ratio": target_pressure / effective_peak_pressure if effective_peak_pressure > 0 else 0.0,
    }


def save_pressure_slices(
    output_dir: Path,
    pressure_mpa: np.ndarray,
    source_mask: np.ndarray,
    model: LoadedModel,
    pressure_metadata: dict[str, object],
) -> None:
    global_peak = np.array(pressure_metadata["global_peak_index_ijk"], dtype=int)
    effective_peak = np.array(pressure_metadata["effective_peak_index_ijk"], dtype=int)
    target = model.target_index_ijk.astype(int)

    axial = pressure_slice_image(pressure_mpa[:, :, target[2]].T)
    axial = overlay_mask(axial, source_mask[:, :, target[2]].T, (255, 255, 255))
    annotate(
        axial,
        "3D pressure max axial slice",
        [
            (int(target[0]), int(target[1]), (255, 255, 255), "target"),
            (int(global_peak[0]), int(global_peak[1]), (255, 0, 0), "global"),
            (int(effective_peak[0]), int(effective_peak[1]), (255, 210, 0), "effective"),
        ],
    ).save(output_dir / "pressure_max_axial.png")

    coronal = pressure_slice_image(pressure_mpa[:, target[1], :].T)
    coronal = overlay_mask(coronal, source_mask[:, target[1], :].T, (255, 255, 255))
    annotate(
        coronal,
        "3D pressure max coronal slice",
        [
            (int(target[0]), int(target[2]), (255, 255, 255), "target"),
            (int(global_peak[0]), int(global_peak[2]), (255, 0, 0), "global"),
            (int(effective_peak[0]), int(effective_peak[2]), (255, 210, 0), "effective"),
        ],
    ).save(output_dir / "pressure_max_coronal.png")

    sagittal = pressure_slice_image(pressure_mpa[target[0], :, :].T)
    sagittal = overlay_mask(sagittal, source_mask[target[0], :, :].T, (255, 255, 255))
    annotate(
        sagittal,
        "3D pressure max sagittal slice",
        [
            (int(target[1]), int(target[2]), (255, 255, 255), "target"),
            (int(global_peak[1]), int(global_peak[2]), (255, 0, 0), "global"),
            (int(effective_peak[1]), int(effective_peak[2]), (255, 210, 0), "effective"),
        ],
    ).save(output_dir / "pressure_max_sagittal.png")


def save_axis_profile(output_dir: Path, pressure_mpa: np.ndarray, model: LoadedModel, pressure_metadata: dict[str, object]) -> None:
    target = model.target_index_ijk.astype(int)
    y_index = int(target[1])
    z_index = int(target[2])
    x_mm = (np.arange(pressure_mpa.shape[0]) - target[0]) * model.dx_m * 1e3
    profile = pressure_mpa[:, y_index, z_index]
    np.savetxt(
        output_dir / "axis_profile.csv",
        np.column_stack([np.arange(pressure_mpa.shape[0]), x_mm, profile]),
        delimiter=",",
        header="x_index,x_relative_to_target_mm,pressure_mpa",
        comments="",
        fmt=["%d", "%.6f", "%.6f"],
    )

    width, height = 900, 420
    margin_left, margin_right, margin_top, margin_bottom = 70, 24, 36, 62
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((margin_left, margin_top, margin_left + plot_w, margin_top + plot_h), outline=(0, 0, 0))
    draw.text((margin_left, 10), "Axis pressure profile through target center", fill=(0, 0, 0))
    draw.text((margin_left, height - 32), "x position relative to target [mm]", fill=(0, 0, 0))
    draw.text((8, margin_top + 8), "MPa", fill=(0, 0, 0))

    y_max = max(float(profile.max()), 1e-9)
    points = []
    for i, value in enumerate(profile):
        x = margin_left + int(round(i / max(len(profile) - 1, 1) * plot_w))
        y = margin_top + plot_h - int(round(float(value) / y_max * plot_h))
        points.append((x, y))
    if len(points) > 1:
        draw.line(points, fill=(30, 105, 190), width=2)

    def marker_x(index: int) -> int:
        return margin_left + int(round(index / max(len(profile) - 1, 1) * plot_w))

    markers = [
        (int(target[0]), "target", (255, 0, 0)),
        (int(pressure_metadata["global_peak_index_ijk"][0]), "global", (160, 0, 160)),
        (int(pressure_metadata["effective_peak_index_ijk"][0]), "effective", (230, 150, 0)),
    ]
    for index, label, color in markers:
        x = marker_x(index)
        draw.line((x, margin_top, x, margin_top + plot_h), fill=color, width=2)
        draw.text((x + 4, margin_top + 4), label, fill=color)

    for tick in range(0, len(profile), max(1, len(profile) // 6)):
        x = marker_x(tick)
        draw.line((x, margin_top + plot_h, x, margin_top + plot_h + 5), fill=(0, 0, 0))
        draw.text((x - 16, margin_top + plot_h + 10), f"{x_mm[tick]:.0f}", fill=(0, 0, 0))
    for frac in [0, 0.25, 0.5, 0.75, 1.0]:
        y = margin_top + plot_h - int(round(frac * plot_h))
        draw.line((margin_left - 5, y, margin_left, y), fill=(0, 0, 0))
        draw.text((margin_left - 62, y - 7), f"{frac * y_max:.2f}", fill=(0, 0, 0))

    image.save(output_dir / "axis_profile.png")


def write_focus_metrics(output_dir: Path, pressure_metadata: dict[str, object]) -> None:
    (output_dir / "focus_metrics.json").write_text(json.dumps(pressure_metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "focus_metrics.txt").open("w", encoding="utf-8") as handle:
        for key, value in pressure_metadata.items():
            handle.write(f"{key}={value}\n")


def save_layout_image(output_dir: Path, source_mask: np.ndarray, model: LoadedModel, source_metadata: dict[str, object]) -> None:
    target = model.target_index_ijk.astype(int)
    bowl = np.array(source_metadata["bowl_index_ijk"], dtype=int)
    labels = model.labels if model.labels is not None else np.zeros(model.sound_speed.shape, dtype=np.uint8)
    label_slice = labels[:, :, target[2]].T
    colors = np.array([[31, 43, 77], [66, 160, 121], [218, 204, 137]], dtype=np.uint8)
    image = Image.fromarray(colors[np.clip(label_slice, 0, len(colors) - 1)], mode="RGB")
    image = overlay_mask(image, source_mask[:, :, target[2]].T, (255, 255, 255))
    markers = [
        (int(bowl[0]), int(bowl[1]), (255, 255, 255), "source"),
        (int(target[0]), int(target[1]), (255, 0, 0), "target"),
    ]
    if model.entry_index_ijk is not None and int(model.entry_index_ijk[2]) == int(target[2]):
        entry = model.entry_index_ijk.astype(int)
        markers.insert(1, (int(entry[0]), int(entry[1]), (255, 160, 0), "entry"))
    annotate(
        image,
        "3D source, target, and skull layout",
        markers,
    ).save(output_dir / "source_target_layout.png")


def save_summary(
    output_dir: Path,
    model: LoadedModel,
    config: KWave3DConfig,
    source_metadata: dict[str, object],
    runtime_metadata: dict[str, object],
    pressure_metadata: dict[str, object],
    runtime_s: float,
    simulation_quality: dict[str, object],
    target_waveform: np.ndarray | None = None,
) -> None:
    tuning_note = "ok"
    peak = np.array(pressure_metadata["global_peak_index_ijk"], dtype=int)
    if np.any(peak <= 1) or np.any(peak >= np.array(model.sound_speed.shape) - 2):
        tuning_note = "peak is close to a model boundary; source placement or runtime may need tuning"
    if pressure_metadata["effective_peak_to_target_distance_mm"] > 15.0:
        tuning_note = "peak is far from target; this run validates plumbing but needs acoustic tuning"
    if source_metadata.get("source_label_counts", {}).get("2", 0):
        tuning_note = "source mask overlaps skull voxels; increase standoff or revise entry path"

    config_summary = asdict(config)
    config_summary["model_path"] = str(config.model_path)
    config_summary["entry_plan_path"] = None if config.entry_plan_path is None else str(config.entry_plan_path)

    actual_alpha_power = model.alpha_power if model.alpha_power is not None else config.alpha_power
    config_summary["alpha_power"] = actual_alpha_power
    alpha_semantics = alpha_semantics_summary(model, actual_alpha_power)

    summary = {
        "description": "Small 3D k-Wave pressure simulation for tFUS platform validation",
        "config": config_summary,
        "model_shape": list(model.sound_speed.shape),
        "source_model_shape": list(model.source_model_shape),
        "crop_origin_ijk": model.crop_origin_ijk.astype(int).tolist(),
        "dx_m": model.dx_m,
        "target_index_ijk": model.target_index_ijk.astype(int).tolist(),
        "sound_speed_range_m_s": [float(model.sound_speed.min()), float(model.sound_speed.max())],
        "density_range_kg_m3": [float(model.density.min()), float(model.density.max())],
        "alpha_range_db_mhz_cm": [float(model.alpha_coeff.min()), float(model.alpha_coeff.max())],
        "source": source_metadata,
        "runtime": {**runtime_metadata, "runtime_s": runtime_s},
        "simulation_quality": simulation_quality,
        "environment_record": build_environment_record(backend=config.backend, device=config.device),
        "alpha_semantics": alpha_semantics,
        "pressure": pressure_metadata,
        "entry_plan": model.entry_plan,
        "tuning_note": tuning_note,
    }
    if target_waveform is not None:
        summary["target_waveform_stats"] = {
            "recorded": True,
            "length": len(target_waveform),
            "max_pa": float(np.max(target_waveform)),
            "min_pa": float(np.min(target_waveform)),
            "rms_pa": float(np.sqrt(np.mean(target_waveform**2))),
        }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    with (output_dir / "summary.txt").open("w", encoding="utf-8") as handle:
        handle.write("Small 3D k-Wave focused ultrasound simulation\n")
        handle.write(f"quick_mode={config.quick_mode}\n")
        handle.write(f"entry_plan_path={config.entry_plan_path}\n")
        handle.write(f"model_shape={model.sound_speed.shape}\n")
        handle.write(f"source_model_shape={model.source_model_shape}\n")
        handle.write(f"crop_origin_ijk={tuple(int(v) for v in model.crop_origin_ijk)}\n")
        handle.write(f"dx_mm={model.dx_m * 1e3:.3f}\n")
        handle.write(f"dt_ns={runtime_metadata['dt_s'] * 1e9:.3f}\n")
        handle.write(f"nt={runtime_metadata['nt']}\n")
        handle.write(f"preset={simulation_quality['preset']}\n")
        handle.write(f"quality_level={simulation_quality['quality_level']}\n")
        handle.write(f"is_paper_grade={simulation_quality['is_paper_grade']}\n")
        handle.write(f"ppw_min_sound_speed={simulation_quality['ppw_min_sound_speed']:.3f}\n")
        handle.write(f"pml_size={simulation_quality['pml_size']}\n")
        handle.write(f"cfl={simulation_quality['cfl']}\n")
        handle.write(f"alpha_power={actual_alpha_power:.3f}\n")
        handle.write(f"alpha_mode={alpha_semantics['alpha_mode']}\n")
        handle.write(f"alpha_coeff_kind={alpha_semantics['alpha_coeff_kind']}\n")
        handle.write(f"alpha_semantics_status={alpha_semantics['alpha_semantics_status']}\n")
        handle.write(f"pressure_allowed_by_alpha_semantics={alpha_semantics['pressure_allowed_by_alpha_semantics']}\n")
        handle.write(f"backend={simulation_quality['backend']}\n")
        handle.write(f"device={simulation_quality['device']}\n")
        handle.write(f"memory_estimate_mb={simulation_quality['memory_estimate']['estimated_mb']:.3f}\n")
        handle.write(f"frequency_hz={config.frequency_hz:.0f}\n")
        handle.write(f"source_pressure_pa={config.source_pressure_pa:.0f}\n")
        handle.write(f"sound_speed_range_m_s={float(model.sound_speed.min()):.1f},{float(model.sound_speed.max()):.1f}\n")
        handle.write(f"density_range_kg_m3={float(model.density.min()):.1f},{float(model.density.max()):.1f}\n")
        handle.write(f"alpha_range_db_mhz_cm={float(model.alpha_coeff.min()):.3f},{float(model.alpha_coeff.max()):.3f}\n")
        handle.write(f"bowl_index_ijk={tuple(source_metadata['bowl_index_ijk'])}\n")
        if "entry_index_ijk" in source_metadata:
            handle.write(f"entry_index_ijk={tuple(source_metadata['entry_index_ijk'])}\n")
        if "source_center_index_ijk" in source_metadata:
            handle.write(f"source_center_index_ijk={tuple(source_metadata['source_center_index_ijk'])}\n")
        if "source_label_counts" in source_metadata:
            handle.write(f"source_label_counts={source_metadata['source_label_counts']}\n")
        handle.write(f"target_index_ijk={tuple(source_metadata['target_index_ijk'])}\n")
        handle.write(f"source_points={source_metadata['source_points']}\n")
        handle.write(f"global_peak_mpa={pressure_metadata['global_peak_mpa']:.6f}\n")
        handle.write(f"global_peak_index_ijk={tuple(pressure_metadata['global_peak_index_ijk'])}\n")
        handle.write(f"global_peak_to_target_distance_mm={pressure_metadata['global_peak_to_target_distance_mm']:.3f}\n")
        handle.write(f"effective_peak_mpa={pressure_metadata['effective_peak_mpa']:.6f}\n")
        handle.write(f"effective_peak_index_ijk={tuple(pressure_metadata['effective_peak_index_ijk'])}\n")
        handle.write(f"effective_peak_to_target_distance_mm={pressure_metadata['effective_peak_to_target_distance_mm']:.3f}\n")
        handle.write(f"target_pressure_mpa={pressure_metadata['target_pressure_mpa']:.6f}\n")
        handle.write(f"target_window_peak_mpa={pressure_metadata['target_window_peak_mpa']:.6f}\n")
        handle.write(f"target_window_peak_index_ijk={tuple(pressure_metadata['target_window_peak_index_ijk'])}\n")
        handle.write(f"target_to_global_peak_ratio={pressure_metadata['target_to_global_peak_ratio']:.6f}\n")
        handle.write(f"target_to_effective_peak_ratio={pressure_metadata['target_to_effective_peak_ratio']:.6f}\n")
        handle.write(f"runtime_s={runtime_s:.3f}\n")
        handle.write(f"tuning_note={tuning_note}\n")


def config_summary(config: KWave3DConfig) -> dict[str, object]:
    summary = asdict(config)
    summary["model_path"] = str(config.model_path)
    summary["entry_plan_path"] = None if config.entry_plan_path is None else str(config.entry_plan_path)
    return summary


def model_summary(model: LoadedModel, actual_alpha_power: float | None = None) -> dict[str, object]:
    if actual_alpha_power is None:
        actual_alpha_power = model.alpha_power if model.alpha_power is not None else np.nan
    return {
        "model_shape": list(model.sound_speed.shape),
        "source_model_shape": list(model.source_model_shape),
        "crop_origin_ijk": model.crop_origin_ijk.astype(int).tolist(),
        "dx_m": model.dx_m,
        "target_index_ijk": model.target_index_ijk.astype(int).tolist(),
        "sound_speed_range_m_s": [float(model.sound_speed.min()), float(model.sound_speed.max())],
        "density_range_kg_m3": [float(model.density.min()), float(model.density.max())],
        "alpha_range_db_mhz_cm": [float(model.alpha_coeff.min()), float(model.alpha_coeff.max())],
        "alpha_semantics": alpha_semantics_summary(model, float(actual_alpha_power)) if not np.isnan(actual_alpha_power) else None,
        "entry_plan": model.entry_plan,
    }


def quality_metadata(
    model: LoadedModel,
    config: KWave3DConfig,
    runtime_s: float | None = None,
    output_completeness: dict[str, bool] | None = None,
) -> dict[str, object]:
    return build_simulation_quality(
        preset_name=config.preset,
        sound_speed=model.sound_speed,
        dx_m=model.dx_m,
        frequency_hz=config.frequency_hz,
        cfl=config.cfl,
        pml_size=config.pml_size,
        simulation_time_s=config.simulation_time_s,
        backend=config.backend,
        device=config.device,
        runtime_s=runtime_s,
        output_completeness=output_completeness,
    )


def run(config: KWave3DConfig, output_dir: Path, dry_run_quality: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    model = load_model(config)

    actual_alpha_power = model.alpha_power if model.alpha_power is not None else config.alpha_power
    if model.alpha_power is not None:
        print(f"INFO: Loaded alpha_power={actual_alpha_power} from model NPZ (overriding config/default {config.alpha_power}).")
    else:
        print(f"INFO: Using default alpha_power={actual_alpha_power} (none found in model NPZ).")

    source_mask, source_metadata = build_source_mask(model, config)
    if dry_run_quality:
        cfg_sum = config_summary(config)
        cfg_sum["alpha_power"] = actual_alpha_power
        cfg_sum["alpha_mode"] = model.alpha_mode
        cfg_sum["alpha_semantics_status"] = model.alpha_semantics_status
        write_quality_dry_run_summary(
            output_dir,
            description="3D k-Wave quality dry run for tFUS platform validation.",
            config=cfg_sum,
            model=model_summary(model, actual_alpha_power),
            source=source_metadata,
            simulation_quality=quality_metadata(model, config),
            environment_record=build_environment_record(backend=config.backend, device=config.device),
        )
        return

    pressure_mpa, runtime_s, runtime_metadata, target_waveform = run_kwave(
        model, source_mask, config, record_target_waveform=config.record_target_waveform
    )

    if not np.all(np.isfinite(pressure_mpa)):
        raise ValueError("3D pressure field contains NaN or infinite values.")
    if float(np.max(pressure_mpa)) <= 0:
        raise ValueError("3D pressure field is all zero.")

    pressure_metadata = compute_focus_metrics(
        pressure_mpa,
        source_mask,
        model.target_index_ijk,
        model.dx_m,
        config.nearfield_exclusion_m,
    )
    save_pressure_slices(output_dir, pressure_mpa, source_mask, model, pressure_metadata)
    save_axis_profile(output_dir, pressure_mpa, model, pressure_metadata)
    write_focus_metrics(output_dir, pressure_metadata)
    save_layout_image(output_dir, source_mask, model, source_metadata)

    save_kwargs = {
        "pressure_max_mpa": pressure_mpa,
        "dx_m": np.array(model.dx_m, dtype=np.float32),
        "target_index_ijk": model.target_index_ijk.astype(np.int32),
        "crop_origin_ijk": model.crop_origin_ijk.astype(np.int32),
        "source_mask": source_mask.astype(np.uint8),
        "labels": np.zeros(pressure_mpa.shape, dtype=np.uint8) if model.labels is None else model.labels.astype(np.uint8),
        "nearfield_exclusion_m": np.array(config.nearfield_exclusion_m, dtype=np.float32),
    }
    if target_waveform is not None:
        save_kwargs["target_waveform"] = target_waveform

    np.savez_compressed(output_dir / "pressure_max_mpa.npz", **save_kwargs)

    simulation_quality = quality_metadata(
        model,
        config,
        runtime_s=runtime_s,
        output_completeness={
            "pressure_max_mpa_npz": True,
            "summary_json": True,
            "focus_metrics_json": True,
            "axis_profile_png": True,
            "pressure_slices": True,
        },
    )
    save_summary(output_dir, model, config, source_metadata, runtime_metadata, pressure_metadata, runtime_s, simulation_quality, target_waveform=target_waveform)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a small 3D k-Wave tFUS pressure simulation.")
    parser.add_argument(
        "--model",
        default=str(PROJECT_ROOT / "outputs" / "skull_model_3d" / "acoustic_model_3d.npz"),
        help="Path to a 3D acoustic model .npz file.",
    )
    parser.add_argument("--entry-plan", default=None, help="Optional CT entry plan JSON from plan_ct_target_entry.py.")
    parser.add_argument("--target-index", type=parse_index, default=None, help="Optional target index formatted as i,j,k.")
    parser.add_argument("--full", action="store_true", help="Use the full 3D acoustic model instead of the quick cropped domain.")
    parser.add_argument("--cycles", type=int, default=6, help="Tone burst cycles used by the pressure source.")
    parser.add_argument("--sim-time-us", type=float, default=45.0, help="Simulation duration in microseconds.")
    parser.add_argument("--cfl", type=float, default=0.20, help="CFL number for k-Wave time step estimation.")
    parser.add_argument("--nearfield-mm", type=float, default=10.0, help="Distance after the source mask to exclude when measuring effective focus.")
    parser.add_argument("--preset", choices=["smoke", "quick", "standard", "paper_grade"], default="quick", help="Simulation quality preset label.")
    parser.add_argument("--dry-run-quality", action="store_true", help="Write quality metadata without running k-Wave.")
    parser.add_argument("--record-target-waveform", action="store_true", help="Record the pressure waveform at the focal point.")
    parser.add_argument("--pml-size", type=int, default=8, help="PML thickness in grid points.")
    parser.add_argument("--aperture-mm", type=float, default=25.0, help="Transducer aperture diameter in millimeters.")
    parser.add_argument("--radius-mm", type=float, default=30.0, help="Transducer curvature radius in millimeters.")
    parser.add_argument("--quick-lateral-mm", type=float, default=None, help="Optional quick-crop half-width around the beam axis in millimeters.")
    parser.add_argument("--quick-post-target-mm", type=float, default=None, help="Optional quick-crop margin after the target in millimeters.")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs" / "kwave_3d_focus"),
        help="Directory where simulation outputs are written.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        KWave3DConfig(
            model_path=Path(args.model),
            entry_plan_path=None if args.entry_plan is None else Path(args.entry_plan),
            target_index_override=args.target_index,
            quick_mode=not args.full,
            quick_lateral_half_width_m=None if args.quick_lateral_mm is None else args.quick_lateral_mm * 1e-3,
            quick_post_target_margin_m=None if args.quick_post_target_mm is None else args.quick_post_target_mm * 1e-3,
            tone_burst_cycles=args.cycles,
            cfl=args.cfl,
            simulation_time_s=args.sim_time_us * 1e-6,
            pml_size=args.pml_size,
            nearfield_exclusion_m=args.nearfield_mm * 1e-3,
            aperture_diameter_m=args.aperture_mm * 1e-3,
            transducer_radius_m=args.radius_mm * 1e-3,
            preset=args.preset,
            record_target_waveform=args.record_target_waveform,
        ),
        Path(args.output_dir),
        dry_run_quality=args.dry_run_quality,
    )
