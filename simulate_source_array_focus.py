from __future__ import annotations

import argparse
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parent
RUNTIME_TMP = PROJECT_ROOT / ".tmp"
MPLCONFIGDIR = RUNTIME_TMP / f"mplconfig-kwave3d-sourcearray-{os.getpid()}"
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
class SourceArrayConfig:
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
    allow_entry_plan_resolution_mismatch: bool = False
    allow_short_memory_smoke: bool = False
    free_field: bool = False
    free_field_sound_speed_m_s: float = 1500.0
    free_field_density_kg_m3: float = 1000.0
    free_field_alpha_coeff: float = 0.0
    # Source-array specific parameters
    array_elements_y: int = 7
    array_elements_z: int = 7
    phase_model: str = "geometric_soft_tissue"
    phase_sound_speed_m_s: float = 1540.0
    phase_path_samples: int = 128
    apodization_window: str = "none"
    apodization_param: float = 0.5


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
    alpha_pressure_allowed_state: str | None = None


def parse_index(value: str) -> tuple[int, int, int]:
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("index must be formatted as i,j,k")
    return tuple(parts)


def normalize_alpha_pressure_permission(
    status: str | None,
    state: str | None,
    allowed: bool | None,
) -> bool | None:
    """Treat legacy missing permission as unspecified, not an explicit denial."""
    normalized_state = None if state is None else state.strip().lower()
    normalized_status = None if status is None else status.strip().lower()
    if normalized_state in {"unspecified", "none", "null"}:
        return None
    if allowed is False and (
        normalized_status in {"missing_alpha_semantics", "legacy_unspecified"}
        or (normalized_status is not None and normalized_status.startswith("inferred_"))
    ):
        return None
    return allowed


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


def validate_entry_plan_resolution(
    entry_plan: dict[str, object] | None,
    model_path: Path,
    model_dx_m: float,
    model_shape: tuple[int, ...],
) -> None:
    if entry_plan is None:
        return
    plan_dx_m = float(entry_plan.get("dx_m", model_dx_m))
    plan_shape = tuple(int(v) for v in entry_plan.get("model_shape", model_shape))
    if not np.isclose(plan_dx_m, model_dx_m) or plan_shape != tuple(model_shape):
        raise ValueError(
            f"Entry plan resolution mismatch: plan dx={plan_dx_m}, shape={plan_shape}; "
            f"model dx={model_dx_m}, shape={model_shape}"
        )


def load_model(config: SourceArrayConfig) -> LoadedModel:
    if not config.model_path.exists():
        raise FileNotFoundError(f"Acoustic model not found: {config.model_path}")
    data = np.load(config.model_path, allow_pickle=True)
    missing = REQUIRED_MODEL_KEYS - set(data.files)
    if missing:
        raise ValueError(f"Acoustic model is missing required keys: {sorted(missing)}")

    dx_m = float(data["dx_m"])
    sound_speed = np.asarray(data["sound_speed"], dtype=np.float32)
    density = np.asarray(data["density"], dtype=np.float32)
    alpha_coeff = np.asarray(data["alpha_coeff"], dtype=np.float32)
    labels = np.asarray(data["labels"], dtype=np.uint8) if "labels" in data.files else None

    entry_plan = load_entry_plan(config.entry_plan_path)
    target_index_ijk = np.asarray(data["target_index_ijk"], dtype=int)
    if config.target_index_override is not None:
        target_index_ijk = np.array(config.target_index_override, dtype=int)
    elif entry_plan is not None:
        target_index_ijk = np.array(entry_plan["target_index_ijk"], dtype=int)

    source_center_index_ijk = None
    entry_index_ijk = None
    beam_axis = None
    if entry_plan is not None:
        source_center_index_ijk = np.array(entry_plan["source_center_index_ijk"], dtype=int)
        entry_index_ijk = np.array(entry_plan["entry_index_ijk"], dtype=int)
        beam_axis = np.array(entry_plan["beam_axis"], dtype=int)

    if "crop_origin_ijk" in data.files:
        crop_origin_ijk = np.asarray(data["crop_origin_ijk"], dtype=int)
    if "source_model_shape" in data.files:
        source_model_shape = tuple(int(v) for v in np.asarray(data["source_model_shape"], dtype=int))

    if config.entry_plan_path is not None and not config.allow_entry_plan_resolution_mismatch:
        validate_entry_plan_resolution(entry_plan, config.model_path, dx_m, sound_speed.shape)

    source_shape = tuple(int(v) for v in sound_speed.shape)
    crop_origin = np.zeros(3, dtype=np.int32)

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
        if source_center_index_ijk is not None:
            anchor_min = np.minimum(target_index_ijk, source_center_index_ijk)
            anchor_max = np.maximum(target_index_ijk, source_center_index_ijk)
            x0 = max(0, int(anchor_min[0]) - config.pml_size - 4)
            x1 = min(sound_speed.shape[0], int(anchor_max[0]) + post_target_margin_gp)
            y0 = max(0, int(anchor_min[1]) - lateral_half_width)
            y1 = min(sound_speed.shape[1], int(anchor_max[1]) + lateral_half_width + 1)
            z0 = max(0, int(anchor_min[2]) - lateral_half_width)
            z1 = min(sound_speed.shape[2], int(anchor_max[2]) + lateral_half_width + 1)
        else:
            x0 = max(0, int(target_index_ijk[0]) - radius_gp - 4)
            x1 = min(sound_speed.shape[0], int(target_index_ijk[0]) + post_target_margin_gp)
            y0 = max(0, int(target_index_ijk[1]) - lateral_half_width)
            y1 = min(sound_speed.shape[1], int(target_index_ijk[1]) + lateral_half_width + 1)
            z0 = max(0, int(target_index_ijk[2]) - lateral_half_width)
            z1 = min(sound_speed.shape[2], int(target_index_ijk[2]) + lateral_half_width + 1)
        crop = (slice(x0, x1), slice(y0, y1), slice(z0, z1))
        crop_origin = np.array([x0, y0, z0], dtype=np.int32)

        sound_speed = sound_speed[crop]
        density = density[crop]
        alpha_coeff = alpha_coeff[crop]
        labels = labels[crop] if labels is not None else None
        target_index_ijk = target_index_ijk - crop_origin
        if source_center_index_ijk is not None:
            source_center_index_ijk = source_center_index_ijk - crop_origin
        if entry_index_ijk is not None:
            entry_index_ijk = entry_index_ijk - crop_origin

    def _str(key: str) -> str | None:
        if key in data.files:
            value = data[key]
            if isinstance(value, np.ndarray):
                value = value.item() if value.size == 1 else value
            return str(value) if value is not None else None
        return None

    raw_alpha_power = float(data["alpha_power"]) if "alpha_power" in data.files else None
    if raw_alpha_power is not None and (np.isnan(raw_alpha_power) or np.isinf(raw_alpha_power)):
        raw_alpha_power = None

    return LoadedModel(
        labels=labels,
        sound_speed=sound_speed,
        density=density,
        alpha_coeff=alpha_coeff,
        dx_m=dx_m,
        target_index_ijk=target_index_ijk,
        source_center_index_ijk=source_center_index_ijk,
        entry_index_ijk=entry_index_ijk,
        beam_axis=beam_axis,
        entry_plan=entry_plan,
        crop_origin_ijk=crop_origin,
        source_model_shape=source_shape,
        alpha_power=raw_alpha_power,
        alpha_mode=_str("alpha_mode"),
        alpha_unit_semantics=_str("alpha_unit_semantics"),
        alpha_coeff_kind=_str("alpha_coeff_kind"),
        alpha_source_route=_str("alpha_source_route"),
        alpha_semantics_status=_str("alpha_semantics_status"),
        alpha_pressure_allowed=normalize_alpha_pressure_permission(
            _str("alpha_semantics_status"),
            _str("alpha_pressure_allowed_state"),
            bool(np.asarray(data["alpha_pressure_allowed"]).item()) if "alpha_pressure_allowed" in data.files else None,
        ),
        alpha_pressure_allowed_state=_str("alpha_pressure_allowed_state"),
    )


def build_freefield_model(config: SourceArrayConfig) -> LoadedModel:
    """Build a homogeneous water model from the entry plan geometry for free-field focus validation."""
    entry_plan = load_entry_plan(config.entry_plan_path)
    if entry_plan is None:
        raise ValueError("Free-field mode requires --entry-plan to define target and source geometry.")

    dx_m = float(entry_plan.get("dx_m", 0.75e-3))
    full_shape = tuple(int(v) for v in entry_plan.get("model_shape", [267, 267, 267]))
    target_index_ijk = np.array(entry_plan["target_index_ijk"], dtype=int)
    source_center_index_ijk = np.array(entry_plan["source_center_index_ijk"], dtype=int)
    entry_index_ijk = np.array(entry_plan["entry_index_ijk"], dtype=int)
    beam_axis = np.array(entry_plan["beam_axis"], dtype=int)

    crop_origin = np.zeros(3, dtype=np.int32)
    model_shape = full_shape

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

        anchor_min = np.minimum(target_index_ijk, source_center_index_ijk)
        anchor_max = np.maximum(target_index_ijk, source_center_index_ijk)
        x0 = max(0, int(anchor_min[0]) - config.pml_size - 4)
        x1 = min(full_shape[0], int(anchor_max[0]) + post_target_margin_gp)
        y0 = max(0, int(anchor_min[1]) - lateral_half_width)
        y1 = min(full_shape[1], int(anchor_max[1]) + lateral_half_width + 1)
        z0 = max(0, int(anchor_min[2]) - lateral_half_width)
        z1 = min(full_shape[2], int(anchor_max[2]) + lateral_half_width + 1)
        crop = (slice(x0, x1), slice(y0, y1), slice(z0, z1))
        crop_origin = np.array([x0, y0, z0], dtype=np.int32)
        model_shape = (x1 - x0, y1 - y0, z1 - z0)

        target_index_ijk = target_index_ijk - crop_origin
        source_center_index_ijk = source_center_index_ijk - crop_origin
        entry_index_ijk = entry_index_ijk - crop_origin

    sound_speed = np.full(model_shape, config.free_field_sound_speed_m_s, dtype=np.float32)
    density = np.full(model_shape, config.free_field_density_kg_m3, dtype=np.float32)
    alpha_coeff = np.full(model_shape, config.free_field_alpha_coeff, dtype=np.float32)
    labels = np.zeros(model_shape, dtype=np.uint8)

    return LoadedModel(
        labels=labels,
        sound_speed=sound_speed,
        density=density,
        alpha_coeff=alpha_coeff,
        dx_m=dx_m,
        target_index_ijk=target_index_ijk,
        source_center_index_ijk=source_center_index_ijk,
        entry_index_ijk=entry_index_ijk,
        beam_axis=beam_axis,
        entry_plan=entry_plan,
        crop_origin_ijk=crop_origin,
        source_model_shape=full_shape,
        alpha_power=None,
        alpha_mode=None,
        alpha_unit_semantics=None,
        alpha_coeff_kind="free_field_homogeneous",
        alpha_source_route="free_field",
        alpha_semantics_status="free_field",
        alpha_pressure_allowed=True,
        alpha_pressure_allowed_state="allowed",
    )


def odd_grid_points(physical_size_m: float, dx_m: float) -> int:
    n = int(round(physical_size_m / dx_m))
    return n if n % 2 == 1 else n + 1


def choose_bowl_position(model: LoadedModel, config: SourceArrayConfig) -> tuple[np.ndarray, np.ndarray, int, int]:
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


def alpha_semantics_summary(model: LoadedModel, actual_alpha_power: float) -> dict[str, object]:
    import math

    alpha_mode = model.alpha_mode
    alpha_coeff_kind = model.alpha_coeff_kind or "unspecified"
    alpha_semantics_status = model.alpha_semantics_status or "legacy_unspecified"

    if alpha_semantics_status == "free_field":
        return {
            "alpha_mode": None,
            "alpha_power": float(actual_alpha_power),
            "alpha_coeff_kind": alpha_coeff_kind,
            "alpha_unit_semantics": model.alpha_unit_semantics,
            "alpha_source_route": model.alpha_source_route,
            "alpha_semantics_status": alpha_semantics_status,
            "alpha_pressure_allowed_metadata": model.alpha_pressure_allowed,
            "alpha_pressure_allowed_state": model.alpha_pressure_allowed_state,
            "pressure_allowed_by_alpha_semantics": True,
            "notes": "Free-field homogeneous water model; alpha semantics not applicable.",
        }

    # Handle NaN alpha_power from legacy model files
    raw_alpha_power = model.alpha_power
    if raw_alpha_power is not None and (math.isnan(float(raw_alpha_power)) or math.isinf(float(raw_alpha_power))):
        raw_alpha_power = None

    effective_alpha_power = raw_alpha_power if raw_alpha_power is not None else actual_alpha_power

    alpha_pressure_allowed = model.alpha_pressure_allowed
    if alpha_pressure_allowed is None:
        alpha_pressure_allowed = not (alpha_semantics_status and "review_pending" in alpha_semantics_status)

    notes: list[str] = []
    if model.alpha_pressure_allowed is False:
        notes.append("Mapping profile explicitly sets pressure_allowed=false.")
    if alpha_semantics_status and "review_pending" in alpha_semantics_status:
        notes.append("Mapping alpha semantics are review-pending; do not use this model for pressure conclusions.")
    if effective_alpha_power == 1.0 and alpha_mode is None:
        notes.append("alpha_power=1.0 with alpha_mode unset requires dispersion/no_dispersion review before pressure use.")
        alpha_pressure_allowed = False
    if not notes:
        notes.append("Inferred from model NPZ alpha semantics metadata.")

    return {
        "alpha_mode": alpha_mode,
        "alpha_power": float(effective_alpha_power),
        "alpha_coeff_kind": alpha_coeff_kind,
        "alpha_unit_semantics": model.alpha_unit_semantics,
        "alpha_source_route": model.alpha_source_route,
        "alpha_semantics_status": alpha_semantics_status,
        "alpha_pressure_allowed_metadata": model.alpha_pressure_allowed,
        "alpha_pressure_allowed_state": model.alpha_pressure_allowed_state,
        "pressure_allowed_by_alpha_semantics": bool(alpha_pressure_allowed),
        "notes": "; ".join(notes),
    }


def compute_apodization_weights(
    theta: np.ndarray,
    theta_max: float,
    window: str,
    param: float,
) -> np.ndarray:
    """Return per-active-voxel amplitude weights for a source apodization window.

    The windows are mapped to the polar angle ``theta`` measured from the bowl
    axis (theta=0 at the bowl centre, theta=theta_max at the rim).  Center-weighted
    windows suppress energy near the rim, which reduces edge diffraction and the
    source-proximal global peak.
    """
    theta = np.asarray(theta, dtype=float)
    window = window.lower().strip()
    if window in ("", "none") or theta_max <= 0 or theta.size == 0:
        return np.ones_like(theta, dtype=float)

    u = np.clip(theta / theta_max, 0.0, 1.0)

    if window == "hann":
        return 0.5 * (1.0 + np.cos(np.pi * u))
    if window == "hamming":
        return 0.54 + 0.46 * np.cos(np.pi * u)
    if window == "tukey":
        alpha = float(np.clip(param, 0.0, 1.0))
        if alpha <= 0.0:
            return np.ones_like(theta, dtype=float)
        if alpha >= 1.0:
            return 0.5 * (1.0 + np.cos(np.pi * u))
        w = np.ones_like(u, dtype=float)
        taper_start = 1.0 - alpha
        rim = u > taper_start
        rim_position = (u[rim] - taper_start) / alpha
        w[rim] = 0.5 * (1.0 + np.cos(np.pi * rim_position))
        return w
    if window == "gaussian":
        beta = max(float(param), 1e-6)
        return np.exp(-(u * beta) ** 2)

    raise ValueError(f"Unknown apodization window: {window!r}")


def build_source_array_mask(
    model: LoadedModel, config: SourceArrayConfig
) -> tuple[np.ndarray, np.ndarray, dict[str, object], np.ndarray]:
    """Build a bowl-shaped source array partitioned into NxM phase patches.

    The bowl geometry matches the single-element baseline (`simulate_kwave_3d_focus.py`),
    but each patch is driven with an independent phase delay so the field can be steered
    toward the target.  The total number of active source voxels is therefore the same as
    the standard bowl mask; only the temporal excitation varies per patch.

    Returns:
        source_mask: binary 3D mask (same size as the standard bowl mask)
        phase_indices: (n_active_voxels,) integer array mapping each active voxel to its patch
        metadata: dict with array geometry and per-patch info
        apodization_weights: (n_active_voxels,) float array of per-voxel amplitude weights
    """
    bowl_one, target_one, radius_gp, diameter_gp = choose_bowl_position(model, config)
    grid_size = Vector(list(model.sound_speed.shape))

    # Build the standard bowl mask so source voxel count and geometry match the baseline
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

    # Bowl center (source center / bowl geometric centre) and target in 0-based grid coords
    bowl_center = (bowl_one - 1).astype(float)
    target_center = (target_one - 1).astype(float)

    z_axis = target_center - bowl_center
    z_norm = float(np.linalg.norm(z_axis))
    if z_norm <= 0:
        raise ValueError("Bowl center and target must differ.")
    z_axis = z_axis / z_norm

    # Local basis for phase-patch partitioning.  Theta/phi are defined relative
    # to the target direction (z_axis).  This happens to align the phase patches
    # with the dominant distance-to-target variation on the bowl surface, which
    # gives stable geometric phase correction.
    arbitrary = np.array([1.0, 0.0, 0.0], dtype=float)
    if abs(np.dot(z_axis, arbitrary)) > 0.95:
        arbitrary = np.array([0.0, 1.0, 0.0], dtype=float)
    x_axis = np.cross(arbitrary, z_axis)
    x_axis /= float(np.linalg.norm(x_axis))
    y_axis = np.cross(z_axis, x_axis)

    # Active voxel coordinates and their local-frame coordinates on the bowl surface
    active_ijk = np.argwhere(source_mask).astype(float)
    active_world = active_ijk * model.dx_m
    relative = active_world - bowl_center * model.dx_m
    local_x = np.dot(relative, x_axis)
    local_y = np.dot(relative, y_axis)
    local_z = np.dot(relative, z_axis)

    radius_m = config.transducer_radius_m
    n_y = max(1, config.array_elements_y)
    n_z = max(1, config.array_elements_z)

    # Partition the circular aperture in its local tangent plane. Polar-angle
    # bins measured from the bowl vertex collapse for shallow caps (large radius),
    # leaving only one radial row active.
    x_edges = np.linspace(float(np.min(local_x)), float(np.max(local_x)), n_y + 1)
    y_edges = np.linspace(float(np.min(local_y)), float(np.max(local_y)), n_z + 1)
    x_bins = np.digitize(local_x, x_edges[1:-1])
    y_bins = np.digitize(local_y, y_edges[1:-1])
    patch_ids = x_bins * n_z + y_bins

    n_patches = n_y * n_z
    patch_sizes = np.zeros(n_patches, dtype=int)
    for pid in range(n_patches):
        patch_sizes[pid] = int(np.count_nonzero(patch_ids == pid))

    # Apodization uses the true bowl-axis polar angle (from the geometric sphere
    # centre toward the bowl/source centre).  This is independent of the patch
    # partitioning used for phase delays.
    radius_gp = float(radius_gp)
    sphere_center = bowl_center + radius_gp * z_axis
    relative_apod = active_world - sphere_center * model.dx_m
    local_z_apod = np.dot(relative_apod, -z_axis)
    theta_apod = np.arccos(np.clip(local_z_apod / radius_m, -1.0, 1.0))
    theta_apod_max = float(np.max(theta_apod)) if theta_apod.size else 0.0
    apodization_weights = compute_apodization_weights(
        theta_apod, theta_apod_max, config.apodization_window, config.apodization_param
    )

    metadata = {
        "bowl_index_ijk": (bowl_one - 1).astype(int).tolist(),
        "target_index_ijk": model.target_index_ijk.astype(int).tolist(),
        "radius_grid_points": int(radius_gp),
        "diameter_grid_points": int(diameter_gp),
        "source_points": int(np.sum(source_mask)),
        "array_elements_y": n_y,
        "array_elements_z": n_z,
        "n_patches": int(n_patches),
        "phase_model": config.phase_model,
        "phase_sound_speed_m_s": float(config.phase_sound_speed_m_s),
        "phase_path_samples": int(config.phase_path_samples),
        "apodization_window": config.apodization_window,
        "apodization_param": float(config.apodization_param),
        "apodization_theta_max_rad": theta_apod_max,
        "apodization_weight_min": float(np.min(apodization_weights)) if apodization_weights.size else 0.0,
        "apodization_weight_max": float(np.max(apodization_weights)) if apodization_weights.size else 0.0,
        "apodization_weight_mean": float(np.mean(apodization_weights)) if apodization_weights.size else 0.0,
        "patch_sizes": patch_sizes.tolist(),
    }
    if model.source_center_index_ijk is not None:
        metadata["source_center_index_ijk"] = model.source_center_index_ijk.astype(int).tolist()
    if model.entry_index_ijk is not None:
        metadata["entry_index_ijk"] = model.entry_index_ijk.astype(int).tolist()
    if model.beam_axis is not None:
        metadata["beam_axis"] = model.beam_axis.astype(int).tolist()
    if model.labels is not None:
        labels_at_source = model.labels[source_mask]
        unique_labels, counts = np.unique(labels_at_source, return_counts=True)
        metadata["source_label_counts"] = {str(int(k)): int(v) for k, v in zip(unique_labels, counts)}

    return source_mask, patch_ids, metadata, apodization_weights


def compute_patch_phase_offsets(
    model: LoadedModel,
    config: SourceArrayConfig,
    source_mask: np.ndarray,
    patch_ids: np.ndarray,
    dt_s: float,
) -> np.ndarray:
    """Compute per-patch time-sample offsets for source-array phase focusing."""
    n_patches = config.array_elements_y * config.array_elements_z
    target_world = model.target_index_ijk.astype(float) * model.dx_m
    active_ijk = np.argwhere(source_mask).astype(float)
    active_world = active_ijk * model.dx_m

    travel_time_samples = np.zeros(n_patches, dtype=int)
    active_patches = np.zeros(n_patches, dtype=bool)

    for pid in range(n_patches):
        mask_pid = patch_ids == pid
        if not np.any(mask_pid):
            continue
        centroid_world = np.mean(active_world[mask_pid], axis=0)

        if config.phase_model == "geometric_soft_tissue":
            distance_m = float(np.linalg.norm(centroid_world - target_world))
            delay_s = distance_m / config.phase_sound_speed_m_s
        elif config.phase_model == "acoustic_path_integral":
            direction = target_world - centroid_world
            distance_m = float(np.linalg.norm(direction))
            if distance_m <= 0:
                delay_s = 0.0
            else:
                direction = direction / distance_m
                n_samples = max(2, config.phase_path_samples)
                sample_positions = np.linspace(0.0, distance_m, n_samples)
                # Convert world positions to grid indices
                grid_positions = (centroid_world[:, None] + direction[:, None] * sample_positions[None, :]) / model.dx_m
                grid_indices = np.rint(grid_positions).astype(int)
                # Clamp to valid grid range
                shape = np.array(model.sound_speed.shape)[:, None]
                grid_indices = np.clip(grid_indices, 0, shape - 1)
                # Sample sound speed along ray
                i, j, k = grid_indices[0], grid_indices[1], grid_indices[2]
                c_local = model.sound_speed[i, j, k]
                # Acoustic travel time: integral of ds / c(s)
                ds = distance_m / (n_samples - 1)
                delay_s = float(np.sum(ds / c_local))
        else:
            raise ValueError(f"Unknown phase model: {config.phase_model!r}")

        travel_time_samples[pid] = int(np.rint(delay_s / dt_s))
        active_patches[pid] = True

    patch_offsets = np.zeros(n_patches, dtype=int)
    if np.any(active_patches):
        latest_arrival = int(np.max(travel_time_samples[active_patches]))
        patch_offsets[active_patches] = latest_arrival - travel_time_samples[active_patches]
    return np.clip(patch_offsets, 0, max(0, int(np.ceil(config.simulation_time_s / dt_s)) - 1))


def run_kwave_source_array(
    model: LoadedModel,
    source_mask: np.ndarray,
    patch_ids: np.ndarray,
    config: SourceArrayConfig,
    record_target_waveform: bool = False,
    apodization_weights: np.ndarray | None = None,
) -> tuple[np.ndarray, float, dict[str, object], np.ndarray | None]:
    print("DEBUG: Starting run_kwave_source_array...", flush=True)
    c_max = float(np.max(model.sound_speed))
    dt_s = config.cfl * model.dx_m / c_max
    nt = int(np.ceil(config.simulation_time_s / dt_s))

    print("DEBUG: Creating kWaveGrid...", flush=True)
    kgrid = kWaveGrid(list(model.sound_speed.shape), [model.dx_m, model.dx_m, model.dx_m])
    kgrid.setTime(nt, dt_s)

    print("DEBUG: Creating kWaveMedium...", flush=True)
    actual_alpha_power = model.alpha_power if model.alpha_power is not None else config.alpha_power
    medium = kWaveMedium(
        sound_speed=model.sound_speed,
        density=model.density,
        alpha_coeff=model.alpha_coeff,
        alpha_power=np.array(actual_alpha_power),
        alpha_mode=model.alpha_mode,
    )

    print("DEBUG: Creating kSource with per-patch delays...", flush=True)
    source = kSource()
    source.p_mask = source_mask

    patch_offsets = compute_patch_phase_offsets(model, config, source_mask, patch_ids, dt_s)

    # Map each active voxel to its patch offset in the order required by k-Wave
    # (row-major order of the flattened mask, matching np.argwhere(source_mask))
    voxel_offsets = patch_offsets[patch_ids]

    sample_freq = 1.0 / dt_s
    source_p_matrix = config.source_pressure_pa * tone_burst(
        sample_freq,
        config.frequency_hz,
        config.tone_burst_cycles,
        signal_length=nt,
        signal_offset=voxel_offsets,
    )
    if apodization_weights is not None:
        source_p_matrix = source_p_matrix * apodization_weights[:, None]
    source.p = source_p_matrix
    source.p_mode = "dirichlet"

    print("DEBUG: Creating kSensor...", flush=True)
    record_list = ["p_max", "p_min"]
    if record_target_waveform:
        record_list.append("p")
    sensor = kSensor(
        mask=np.ones(model.sound_speed.shape, dtype=bool),
        record=record_list,
    )

    print("DEBUG: Calling kspaceFirstOrder...", flush=True)
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
        quiet=False,
    )
    print("DEBUG: Finished kspaceFirstOrder successfully!", flush=True)
    runtime_s = time.perf_counter() - start

    p_max = reshape_to_grid(result["p_max"], model.sound_speed.shape)
    p_min = reshape_to_grid(result["p_min"], model.sound_speed.shape)
    pressure_mpa = np.maximum(np.abs(p_max), np.abs(p_min)).astype(np.float32) / 1e6

    target_waveform = None
    if record_target_waveform and "p" in result:
        target = model.target_index_ijk.astype(int)
        flat_idx = np.ravel_multi_index(target, model.sound_speed.shape)
        target_waveform = np.asarray(result["p"][flat_idx, :], dtype=np.float32)

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
    source_center_index_ijk: np.ndarray | None = None,
    entry_index_ijk: np.ndarray | None = None,
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

    metrics: dict[str, object] = {
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
        "legacy_effective_peak_semantics": "global_x_cut_after_source_mask_front",
        "metric_semantics_version": "1.0.0_legacy_only",
    }

    if source_center_index_ijk is None:
        return metrics

    source_center = np.asarray(source_center_index_ijk, dtype=float)
    if source_center.shape != (3,):
        raise ValueError("source_center_index_ijk must contain exactly 3 entries.")
    beam_vector = target.astype(float) - source_center
    beam_length_gp = float(np.linalg.norm(beam_vector))
    if beam_length_gp <= 0:
        raise ValueError("source_center_index_ijk and target_index_ijk must differ.")
    beam_unit = beam_vector / beam_length_gp
    coordinates = np.indices(pressure_mpa.shape, dtype=np.float32)
    axial_projection_gp = sum(
        (coordinates[axis] - float(source_center[axis])) * float(beam_unit[axis])
        for axis in range(3)
    )
    beam_valid = axial_projection_gp >= float(nearfield_grid_points)
    if not np.any(beam_valid):
        raise ValueError("Beam-axis nearfield exclusion leaves no valid pressure voxels.")
    beam_effective_flat = int(np.argmax(np.where(beam_valid, pressure_mpa, -np.inf)))
    beam_effective_peak = np.array(np.unravel_index(beam_effective_flat, pressure_mpa.shape), dtype=int)
    beam_effective_pressure = float(pressure_mpa[tuple(beam_effective_peak)])

    def geometry(point: np.ndarray) -> tuple[float, float, float]:
        relative = point.astype(float) - source_center
        axial_mm = float(np.dot(relative, beam_unit) * dx_m * 1e3)
        lateral_mm = float(np.linalg.norm(relative - np.dot(relative, beam_unit) * beam_unit) * dx_m * 1e3)
        shortfall_mm = float((beam_length_gp - np.dot(relative, beam_unit)) * dx_m * 1e3)
        return axial_mm, lateral_mm, shortfall_mm

    beam_axial_mm, beam_lateral_mm, beam_shortfall_mm = geometry(beam_effective_peak)
    global_axial_mm, global_lateral_mm, global_shortfall_mm = geometry(peak)
    legacy_axial_mm, legacy_lateral_mm, legacy_shortfall_mm = geometry(effective_peak)
    target_window_axial_mm, target_window_lateral_mm, target_window_shortfall_mm = geometry(target_window_peak)
    metrics.update(
        {
            "metric_semantics_version": "2.0.0",
            "beam_axis_source_center_index_ijk": source_center.astype(int).tolist(),
            "beam_axis_unit_vector": beam_unit.tolist(),
            "beam_axis_nearfield_semantics": "axial_projection_from_source_center_greater_than_or_equal_to_nearfield_exclusion",
            "beam_axis_effective_peak_index_ijk": beam_effective_peak.tolist(),
            "beam_axis_effective_peak_mpa": beam_effective_pressure,
            "beam_axis_effective_peak_to_target_distance_mm": float(np.linalg.norm((beam_effective_peak - target) * dx_m) * 1e3),
            "beam_axis_effective_peak_axial_from_source_mm": beam_axial_mm,
            "beam_axis_effective_peak_lateral_offset_mm": beam_lateral_mm,
            "beam_axis_effective_peak_axial_shortfall_to_target_mm": beam_shortfall_mm,
            "target_to_beam_axis_effective_peak_ratio": target_pressure / beam_effective_pressure if beam_effective_pressure > 0 else 0.0,
            "global_peak_axial_from_source_mm": global_axial_mm,
            "global_peak_lateral_offset_mm": global_lateral_mm,
            "global_peak_axial_shortfall_to_target_mm": global_shortfall_mm,
            "legacy_effective_peak_axial_from_source_mm": legacy_axial_mm,
            "legacy_effective_peak_lateral_offset_mm": legacy_lateral_mm,
            "legacy_effective_peak_axial_shortfall_to_target_mm": legacy_shortfall_mm,
            "target_window_peak_axial_from_source_mm": target_window_axial_mm,
            "target_window_peak_lateral_offset_mm": target_window_lateral_mm,
            "target_window_peak_axial_shortfall_to_target_mm": target_window_shortfall_mm,
        }
    )
    if entry_index_ijk is not None:
        entry = np.asarray(entry_index_ijk, dtype=float)
        if entry.shape != (3,):
            raise ValueError("entry_index_ijk must contain exactly 3 entries.")
        entry_axial_gp = float(np.dot(entry - source_center, beam_unit))
        post_entry_valid = axial_projection_gp >= entry_axial_gp
        post_entry_flat = int(np.argmax(np.where(post_entry_valid, pressure_mpa, -np.inf)))
        post_entry_peak = np.array(np.unravel_index(post_entry_flat, pressure_mpa.shape), dtype=int)
        post_entry_pressure = float(pressure_mpa[tuple(post_entry_peak)])
        post_entry_axial_mm, post_entry_lateral_mm, post_entry_shortfall_mm = geometry(post_entry_peak)
        metrics.update(
            {
                "post_entry_semantics": "axial_projection_at_or_beyond_entry_index",
                "entry_index_ijk": entry.astype(int).tolist(),
                "entry_axial_from_source_mm": float(entry_axial_gp * dx_m * 1e3),
                "post_entry_peak_index_ijk": post_entry_peak.tolist(),
                "post_entry_peak_mpa": post_entry_pressure,
                "post_entry_peak_to_target_distance_mm": float(np.linalg.norm((post_entry_peak - target) * dx_m) * 1e3),
                "post_entry_peak_axial_from_source_mm": post_entry_axial_mm,
                "post_entry_peak_lateral_offset_mm": post_entry_lateral_mm,
                "post_entry_peak_axial_shortfall_to_target_mm": post_entry_shortfall_mm,
                "target_to_post_entry_peak_ratio": target_pressure / post_entry_pressure if post_entry_pressure > 0 else 0.0,
            }
        )
    return metrics


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
        "3D pressure max axial slice (source array)",
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
        "3D pressure max coronal slice (source array)",
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
        "3D pressure max sagittal slice (source array)",
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
    draw.text((margin_left, 10), "Axis pressure profile through target center (source array)", fill=(0, 0, 0))
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
        "3D source array, target, and skull layout",
        markers,
    ).save(output_dir / "source_target_layout.png")


def save_summary(
    output_dir: Path,
    model: LoadedModel,
    config: SourceArrayConfig,
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
        "description": "3D k-Wave source-array focused ultrasound simulation for tFUS focus optimization",
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
        handle.write("3D k-Wave source-array focused ultrasound simulation\n")
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
        handle.write(f"array_elements_y={config.array_elements_y}\n")
        handle.write(f"array_elements_z={config.array_elements_z}\n")
        handle.write(f"phase_model={config.phase_model}\n")
        handle.write(f"phase_sound_speed_m_s={config.phase_sound_speed_m_s:.1f}\n")
        handle.write(f"apodization_window={config.apodization_window}\n")
        handle.write(f"apodization_param={config.apodization_param:.4f}\n")
        handle.write(f"apodization_weight_min={source_metadata.get('apodization_weight_min', 0.0):.6f}\n")
        handle.write(f"apodization_weight_mean={source_metadata.get('apodization_weight_mean', 0.0):.6f}\n")
        handle.write(f"apodization_weight_max={source_metadata.get('apodization_weight_max', 0.0):.6f}\n")
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


def config_summary(config: SourceArrayConfig) -> dict[str, object]:
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
    config: SourceArrayConfig,
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


def enforce_simulation_time(config: SourceArrayConfig, distance_m: float) -> SourceArrayConfig:
    arrival_time_s = distance_m / 1540.0
    min_required_time_s = arrival_time_s + (config.tone_burst_cycles * 2.0 / config.frequency_hz) + 16.0e-6
    if config.simulation_time_s >= min_required_time_s:
        return config
    if config.allow_short_memory_smoke:
        print(
            "WARNING: Explicit short memory-smoke mode bypasses propagation-time completeness; "
            "this run cannot support acoustic conclusions."
        )
        return config
    if config.preset in {"standard", "paper_grade"}:
        raise ValueError(
            f"Simulation Time Truncation Danger: Configured simulation time ({config.simulation_time_s * 1e6:.2f} us) "
            f"is less than the estimated minimum safe propagation time ({min_required_time_s * 1e6:.2f} us). "
            f"Please increase --sim-time-us to at least {min_required_time_s * 1e6:.2f}."
        )
    print(
        f"WARNING: Configured simulation time {config.simulation_time_s * 1e6:.2f} us is too short. "
        f"Auto-correcting to {min_required_time_s * 1e6:.2f} us to avoid truncation."
    )
    return replace(config, simulation_time_s=min_required_time_s)


def run(config: SourceArrayConfig, output_dir: Path, dry_run_quality: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    if config.free_field:
        model = build_freefield_model(config)
    else:
        model = load_model(config)

    if model.labels is not None:
        target_idx = model.target_index_ijk.astype(int)
        if 0 <= target_idx[0] < model.labels.shape[0] and            0 <= target_idx[1] < model.labels.shape[1] and            0 <= target_idx[2] < model.labels.shape[2]:
            if model.labels[tuple(target_idx)] == 2:
                raise ValueError(
                    f"Safety Gate Violation: Target voxel {target_idx.tolist()} is located inside the skull bone (Label 2). "
                    "Check coordinate alignment or entry plan."
                )

    distance_m = config.transducer_radius_m
    if model.entry_plan is not None:
        distance_m = float(model.entry_plan.get("source_to_target_distance_mm", config.transducer_radius_m * 1e3)) * 1e-3

    config = enforce_simulation_time(config, distance_m)

    actual_alpha_power = model.alpha_power if model.alpha_power is not None else config.alpha_power
    if model.alpha_power is not None:
        print(f"INFO: Loaded alpha_power={actual_alpha_power} from model NPZ (overriding config/default {config.alpha_power}).")
    else:
        print(f"INFO: Using default alpha_power={actual_alpha_power} (none found in model NPZ).")

    source_mask, patch_ids, source_metadata, apodization_weights = build_source_array_mask(model, config)
    if dry_run_quality:
        cfg_sum = config_summary(config)
        cfg_sum["alpha_power"] = actual_alpha_power
        cfg_sum["alpha_mode"] = model.alpha_mode
        cfg_sum["alpha_semantics_status"] = model.alpha_semantics_status
        write_quality_dry_run_summary(
            output_dir,
            description="3D k-Wave source-array quality dry run for tFUS focus optimization.",
            config=cfg_sum,
            model=model_summary(model, actual_alpha_power),
            source=source_metadata,
            simulation_quality=quality_metadata(model, config),
            environment_record=build_environment_record(backend=config.backend, device=config.device),
        )
        return

    pressure_mpa, runtime_s, runtime_metadata, target_waveform = run_kwave_source_array(
        model,
        source_mask,
        patch_ids,
        config,
        record_target_waveform=config.record_target_waveform,
        apodization_weights=apodization_weights,
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
        source_center_index_ijk=model.source_center_index_ijk,
        entry_index_ijk=model.entry_index_ijk,
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
    if model.source_center_index_ijk is not None:
        save_kwargs["source_center_index_ijk"] = model.source_center_index_ijk.astype(np.int32)
    if model.beam_axis is not None:
        save_kwargs["beam_axis"] = model.beam_axis.astype(np.int32)
    if model.entry_index_ijk is not None:
        save_kwargs["entry_index_ijk"] = model.entry_index_ijk.astype(np.int32)

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
    parser = argparse.ArgumentParser(description="Run a 3D k-Wave source-array tFUS pressure simulation for focus optimization.")
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
    parser.add_argument("--source-pressure-pa", type=float, default=1_000_000.0, help="Source pressure amplitude in Pa.")
    parser.add_argument("--cfl", type=float, default=0.20, help="CFL number for k-Wave time step estimation.")
    parser.add_argument("--nearfield-mm", type=float, default=10.0, help="Distance after the source mask to exclude when measuring effective focus.")
    parser.add_argument("--preset", choices=["smoke", "quick", "standard", "paper_grade"], default="quick", help="Simulation quality preset label.")
    parser.add_argument("--dry-run-quality", action="store_true", help="Write quality metadata without running k-Wave.")
    parser.add_argument("--record-target-waveform", action="store_true", help="Record the pressure waveform at the focal point.")
    parser.add_argument(
        "--allow-entry-plan-resolution-mismatch",
        action="store_true",
        help="Bypass entry_plan dx/model_shape compatibility checks for explicit diagnostic runs only.",
    )
    parser.add_argument(
        "--allow-short-memory-smoke",
        action="store_true",
        help="Bypass propagation-time completeness only for explicit full-grid memory initialization diagnostics.",
    )
    parser.add_argument("--pml-size", type=int, default=8, help="PML thickness in grid points.")
    parser.add_argument("--aperture-mm", type=float, default=25.0, help="Transducer aperture diameter in millimeters.")
    parser.add_argument("--radius-mm", type=float, default=30.0, help="Transducer curvature radius in millimeters.")
    parser.add_argument("--quick-lateral-mm", type=float, default=None, help="Optional quick-crop half-width around the beam axis in millimeters.")
    parser.add_argument("--quick-post-target-mm", type=float, default=None, help="Optional quick-crop margin after the target in millimeters.")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs" / "source_array_focus"),
        help="Directory where simulation outputs are written.",
    )
    parser.add_argument(
        "--backend",
        choices=["python", "cpp"],
        default="python",
        help="k-Wave computational backend (python or cpp).",
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "gpu"],
        default="cpu",
        help="Device to run k-Wave on (cpu or gpu).",
    )
    parser.add_argument("--array-elements-y", type=int, default=7, help="Number of source array elements along the polar direction.")
    parser.add_argument("--array-elements-z", type=int, default=7, help="Number of source array elements along the azimuthal direction.")
    parser.add_argument(
        "--phase-model",
        choices=["geometric_soft_tissue", "acoustic_path_integral"],
        default="geometric_soft_tissue",
        help="Phase delay model for source array excitation.",
    )
    parser.add_argument("--phase-sound-speed-m-s", type=float, default=1540.0, help="Sound speed used for geometric phase delay calculation.")
    parser.add_argument("--phase-path-samples", type=int, default=128, help="Number of samples along source-target ray for acoustic_path_integral model.")
    parser.add_argument(
        "--apodization-window",
        choices=["none", "hann", "hamming", "tukey", "gaussian"],
        default="none",
        help="Amplitude taper applied to source elements based on polar angle (none=huniform).",
    )
    parser.add_argument("--apodization-param", type=float, default=0.5, help="Window parameter: Tukey alpha (0=rect, 1=Hann) or Gaussian beta.")
    parser.add_argument("--free-field", action="store_true", help="Run in a homogeneous water model built from the entry plan geometry.")
    parser.add_argument("--free-field-sound-speed-m-s", type=float, default=1500.0, help="Sound speed for free-field homogeneous model.")
    parser.add_argument("--free-field-density-kg-m3", type=float, default=1000.0, help="Density for free-field homogeneous model.")
    parser.add_argument("--free-field-alpha-coeff", type=float, default=0.0, help="Attenuation coefficient for free-field homogeneous model.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        SourceArrayConfig(
            model_path=Path(args.model),
            entry_plan_path=None if args.entry_plan is None else Path(args.entry_plan),
            target_index_override=args.target_index,
            quick_mode=not args.full,
            quick_lateral_half_width_m=None if args.quick_lateral_mm is None else args.quick_lateral_mm * 1e-3,
            quick_post_target_margin_m=None if args.quick_post_target_mm is None else args.quick_post_target_mm * 1e-3,
            tone_burst_cycles=args.cycles,
            source_pressure_pa=args.source_pressure_pa,
            cfl=args.cfl,
            simulation_time_s=args.sim_time_us * 1e-6,
            pml_size=args.pml_size,
            nearfield_exclusion_m=args.nearfield_mm * 1e-3,
            aperture_diameter_m=args.aperture_mm * 1e-3,
            transducer_radius_m=args.radius_mm * 1e-3,
            preset=args.preset,
            record_target_waveform=args.record_target_waveform,
            allow_entry_plan_resolution_mismatch=args.allow_entry_plan_resolution_mismatch,
            allow_short_memory_smoke=args.allow_short_memory_smoke,
            backend=args.backend,
            device=args.device,
            array_elements_y=args.array_elements_y,
            array_elements_z=args.array_elements_z,
            phase_model=args.phase_model,
            phase_sound_speed_m_s=args.phase_sound_speed_m_s,
            phase_path_samples=args.phase_path_samples,
            apodization_window=args.apodization_window,
            apodization_param=args.apodization_param,
            free_field=args.free_field,
            free_field_sound_speed_m_s=args.free_field_sound_speed_m_s,
            free_field_density_kg_m3=args.free_field_density_kg_m3,
            free_field_alpha_coeff=args.free_field_alpha_coeff,
        ),
        Path(args.output_dir),
        dry_run_quality=args.dry_run_quality,
    )
