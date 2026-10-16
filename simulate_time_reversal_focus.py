"""Two-stage full-waveform time-reversal (TR) focusing simulation for fus-sim.

Reference method for phase-correction effectiveness (AI_TODO A.3):

- Stage ``calibrate``: a point source at ``target_index_ijk`` emits a short
  tone burst.  The arriving wavefield is recorded on every grid point of the
  transducer bowl surface (``sensor.mask = bowl_mask``, ``record=['p']``).
  The recorded signals are stored in ``element_signals.npz`` together with the
  exact bowl mask, grid metadata, and entry-plan summary so that the refocus
  stage can verify mask/grid/time consistency before replaying.
- Stage ``refocus``: the recorded signals are time-reversed (``np.fliplr``)
  and re-emitted from the same bowl surface as a Dirichlet pressure source
  (``source.p_mask = bowl_mask``).  Optionally all signals are normalised so
  that ``max(abs(signals)) == --source-pressure-pa`` (default 1e6 Pa); the
  scale factor is recorded.  The sensor records ``p_max``/``p_min`` over the
  full grid plus the ``p`` waveform at the target voxel.
- Stage ``auto``: runs ``calibrate`` then ``refocus`` in one process.

Mask/signal ordering convention
-------------------------------
With ``backend='python'`` (the only backend supported here) k-Wave indexes
binary mask points in NumPy C-order (row-major): ``source.p`` row ``i``
corresponds to the i-th nonzero element of ``p_mask.ravel(order='C')`` and
``result['p']`` row ``i`` corresponds to the i-th nonzero element of
``sensor.mask.ravel(order='C')``.  Calibrate and refocus therefore share one
canonical ordering (``np.argwhere(mask)`` / ``np.ravel_multi_index``) and the
TR mapping is exact.  The C++ backend uses MATLAB/F-order and is explicitly
rejected by this script to avoid silently scrambling element signals.

Time alignment / nt handling
----------------------------
Recorded signals have length ``nt_recorded`` (from the calibrate kgrid).  On
refocus the reversed signal reaches its focus at ``t ~= nt_recorded * dt``
after replay start, so the refocus simulation must run at least that long.
The refocus time base is ``nt_sim = max(nt(--sim-time-us), nt_recorded +
REFOCUS_MARGIN_SAMPLES)``; recorded signals are zero-padded at the end when
``nt_sim > nt_recorded``.  Any extension/padding is recorded in
``summary.json['time_alignment']``.  Signals are never silently truncated.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent
RUNTIME_TMP = PROJECT_ROOT / ".tmp"
MPLCONFIGDIR = RUNTIME_TMP / f"mplconfig-kwave3d-timereversal-{os.getpid()}"
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

from simulate_source_array_focus import (
    LoadedModel,
    SourceArrayConfig,
    alpha_semantics_summary,
    choose_bowl_position,
    compute_focus_metrics,
    load_model,
    model_summary,
    parse_index,
    save_axis_profile,
    save_layout_image,
    save_pressure_slices,
    write_focus_metrics,
)


DEFAULT_MODEL_PATH = PROJECT_ROOT / "outputs" / "ct_acoustic_model_3d_profile_hu300_dx0p75" / "acoustic_model_3d.npz"
ELEMENT_SIGNALS_FILENAME = "element_signals.npz"
# Extra samples appended after the recorded signal length so the refocused
# peak (which forms at t ~= nt_recorded * dt) is safely inside the time base.
REFOCUS_MARGIN_SAMPLES = 16


@dataclass(frozen=True)
class TimeReversalConfig:
    model_path: Path = DEFAULT_MODEL_PATH
    entry_plan_path: Path | None = None
    target_index_override: tuple[int, int, int] | None = None
    calibration_point_override: tuple[int, int, int] | None = None
    stage: str = "auto"  # calibrate | refocus | auto
    frequency_hz: float = 500_000.0
    calibration_pressure_pa: float = 1_000_000.0
    source_pressure_pa: float = 1_000_000.0
    normalize_source: bool = True
    transducer_radius_m: float = 35e-3
    aperture_diameter_m: float = 30e-3
    tone_burst_cycles: int = 2
    cfl: float = 0.20
    simulation_time_s: float = 100e-6
    pml_size: int = 12
    preset: str = "standard"
    backend: str = "python"
    device: str = "cpu"
    quick_mode: bool = True
    quick_lateral_half_width_m: float | None = 17e-3
    quick_post_target_margin_m: float | None = 8e-3
    alpha_power: float = 1.5
    nearfield_exclusion_m: float = 10e-3
    record_target_waveform: bool = True
    allow_entry_plan_resolution_mismatch: bool = False


def _loader_config(config: TimeReversalConfig) -> SourceArrayConfig:
    """Adapt the TR config to the shared model loader (same crop semantics)."""
    return SourceArrayConfig(
        model_path=config.model_path,
        entry_plan_path=config.entry_plan_path,
        target_index_override=config.target_index_override,
        quick_mode=config.quick_mode,
        quick_lateral_half_width_m=config.quick_lateral_half_width_m,
        quick_post_target_margin_m=config.quick_post_target_margin_m,
        transducer_radius_m=config.transducer_radius_m,
        aperture_diameter_m=config.aperture_diameter_m,
        pml_size=config.pml_size,
        allow_entry_plan_resolution_mismatch=config.allow_entry_plan_resolution_mismatch,
    )


def _require_python_backend(config: TimeReversalConfig) -> None:
    if config.backend != "python":
        raise ValueError(
            "Time-reversal stages require backend='python': mask point ordering for "
            "source.p / sensor 'p' is only guaranteed (C-order) for the python backend."
        )


def build_bowl_mask(
    model: LoadedModel, config: TimeReversalConfig
) -> tuple[np.ndarray, dict[str, object]]:
    """Build the transducer bowl mask identical to the single-bowl baseline.

    Returns the binary mask (bool, same shape as the cropped model) and a
    metadata dict.  The same function is used as sensor mask in ``calibrate``
    and as ``source.p_mask`` in ``refocus``, guaranteeing mask consistency.
    """
    loader_config = _loader_config(config)
    bowl_one, target_one, radius_gp, diameter_gp = choose_bowl_position(model, loader_config)
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
        raise ValueError("Generated 3D bowl mask is empty.")

    metadata: dict[str, object] = {
        "bowl_index_ijk": (bowl_one - 1).astype(int).tolist(),
        "target_index_ijk": model.target_index_ijk.astype(int).tolist(),
        "radius_grid_points": int(radius_gp),
        "diameter_grid_points": int(diameter_gp),
        "aperture_diameter_m": float(config.aperture_diameter_m),
        "transducer_radius_m": float(config.transducer_radius_m),
        "source_points": int(np.sum(source_mask)),
        "mask_point_ordering": "numpy_c_order_argwhere",
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
    return source_mask, metadata


def _make_kgrid(model: LoadedModel, config: TimeReversalConfig) -> tuple[kWaveGrid, float, int]:
    c_max = float(np.max(model.sound_speed))
    dt_s = config.cfl * model.dx_m / c_max
    nt = int(np.ceil(config.simulation_time_s / dt_s))
    kgrid = kWaveGrid(list(model.sound_speed.shape), [model.dx_m, model.dx_m, model.dx_m])
    kgrid.setTime(nt, dt_s)
    return kgrid, dt_s, nt


def _make_medium(model: LoadedModel, config: TimeReversalConfig) -> tuple[kWaveMedium, float]:
    actual_alpha_power = model.alpha_power if model.alpha_power is not None else config.alpha_power
    medium = kWaveMedium(
        sound_speed=model.sound_speed,
        density=model.density,
        alpha_coeff=model.alpha_coeff,
        alpha_power=np.array(actual_alpha_power),
        alpha_mode=model.alpha_mode,
    )
    return medium, actual_alpha_power


def _check_target_not_in_skull(model: LoadedModel) -> None:
    if model.labels is None:
        return
    target_idx = model.target_index_ijk.astype(int)
    if (
        0 <= target_idx[0] < model.labels.shape[0]
        and 0 <= target_idx[1] < model.labels.shape[1]
        and 0 <= target_idx[2] < model.labels.shape[2]
    ):
        if model.labels[tuple(target_idx)] == 2:
            raise ValueError(
                f"Safety Gate Violation: Target voxel {target_idx.tolist()} is located inside the skull bone (Label 2). "
                "Check coordinate alignment or entry plan."
            )


def calibration_point_metadata(
    model: LoadedModel, config: TimeReversalConfig
) -> tuple[np.ndarray, dict[str, object]]:
    """Resolve a calibration point without changing bowl geometry or model target.

    The calibration-point override uses full-model coordinates so a point from a
    pressure field can be replayed unambiguously after quick-domain cropping.
    """
    model_target_local = model.target_index_ijk.astype(int)
    model_target_full = model_target_local + model.crop_origin_ijk.astype(int)
    if config.calibration_point_override is None:
        point_full = model_target_full
        mode = "model_target"
    else:
        point_full = np.asarray(config.calibration_point_override, dtype=int)
        if point_full.shape != (3,):
            raise ValueError("Calibration point override must contain exactly three full-model indices.")
        mode = "full_index_override_bowl_geometry_frozen"

    point_local = point_full - model.crop_origin_ijk.astype(int)
    shape = np.asarray(model.sound_speed.shape, dtype=int)
    if np.any(point_local < 0) or np.any(point_local >= shape):
        raise ValueError(
            f"Calibration point full index {point_full.tolist()} maps outside cropped grid "
            f"at local index {point_local.tolist()} for shape {shape.tolist()}."
        )

    material_label = None
    if model.labels is not None:
        material_label = int(model.labels[tuple(point_local)])
    metadata: dict[str, object] = {
        "mode": mode,
        "local_index_ijk": point_local.tolist(),
        "full_index_ijk": point_full.tolist(),
        "material_label": material_label,
        "bowl_geometry_target_local_ijk": model_target_local.tolist(),
        "bowl_geometry_target_full_ijk": model_target_full.tolist(),
        "independent_of_bowl_geometry": True,
    }
    return point_local, metadata

def _enforce_calibrate_sim_time(config: TimeReversalConfig, model: LoadedModel) -> TimeReversalConfig:
    """Calibrate must record until the pulse has passed the bowl surface."""
    distance_m = config.transducer_radius_m
    if model.entry_plan is not None:
        distance_m = float(model.entry_plan.get("source_to_target_distance_mm", config.transducer_radius_m * 1e3)) * 1e-3
    c_min = float(np.min(model.sound_speed))
    arrival_time_s = distance_m / c_min
    min_required_time_s = arrival_time_s + (config.tone_burst_cycles * 2.0 / config.frequency_hz) + 16.0e-6
    if config.simulation_time_s >= min_required_time_s:
        return config
    if config.preset in {"standard", "paper_grade"}:
        raise ValueError(
            f"Simulation Time Truncation Danger: Configured calibration time ({config.simulation_time_s * 1e6:.2f} us) "
            f"is less than the estimated minimum safe recording time ({min_required_time_s * 1e6:.2f} us). "
            f"Please increase --sim-time-us to at least {min_required_time_s * 1e6:.2f}."
        )
    print(
        f"WARNING: Configured calibration time {config.simulation_time_s * 1e6:.2f} us is too short. "
        f"Auto-correcting to {min_required_time_s * 1e6:.2f} us to avoid truncation."
    )
    return TimeReversalConfig(**{**asdict(config), "simulation_time_s": min_required_time_s})


def quality_metadata(
    model: LoadedModel,
    config: TimeReversalConfig,
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


def config_summary(config: TimeReversalConfig) -> dict[str, object]:
    summary = asdict(config)
    summary["model_path"] = str(config.model_path)
    summary["entry_plan_path"] = None if config.entry_plan_path is None else str(config.entry_plan_path)
    return summary


def _entry_plan_summary(model: LoadedModel) -> dict[str, object] | None:
    if model.entry_plan is None:
        return None
    return {
        "target_index_ijk": model.entry_plan.get("target_index_ijk"),
        "source_center_index_ijk": model.entry_plan.get("source_center_index_ijk"),
        "entry_index_ijk": model.entry_plan.get("entry_index_ijk"),
        "beam_axis": model.entry_plan.get("beam_axis"),
        "source_to_target_distance_mm": model.entry_plan.get("source_to_target_distance_mm"),
        "entry_offset_mm": model.entry_plan.get("entry_offset_mm"),
    }


def run_calibrate(config: TimeReversalConfig, output_dir: Path, dry_run_quality: bool = False) -> dict[str, object]:
    """Stage 1: point source at the target; record p on the full bowl mask."""
    _require_python_backend(config)
    output_dir.mkdir(parents=True, exist_ok=True)
    model = load_model(_loader_config(config))
    _check_target_not_in_skull(model)
    config = _enforce_calibrate_sim_time(config, model)
    source_mask, source_metadata = build_bowl_mask(model, config)
    calibration_point, calibration_metadata = calibration_point_metadata(model, config)
    source_metadata["calibration_point"] = calibration_metadata

    if model.alpha_power is not None:
        print(f"INFO: Loaded alpha_power={model.alpha_power} from model NPZ (overriding config/default {config.alpha_power}).")
    actual_alpha_power = model.alpha_power if model.alpha_power is not None else config.alpha_power

    if dry_run_quality:
        cfg_sum = config_summary(config)
        cfg_sum["alpha_power"] = actual_alpha_power
        cfg_sum["alpha_mode"] = model.alpha_mode
        cfg_sum["alpha_semantics_status"] = model.alpha_semantics_status
        write_quality_dry_run_summary(
            output_dir,
            description="Time-reversal calibrate stage quality dry run (independent point source, frozen bowl-mask recording).",
            config=cfg_sum,
            model=model_summary(model, actual_alpha_power),
            source=source_metadata,
            simulation_quality=quality_metadata(model, config),
            environment_record=build_environment_record(backend=config.backend, device=config.device),
        )
        return {"stage": "calibrate", "dry_run_quality_only": True}

    kgrid, dt_s, nt = _make_kgrid(model, config)
    medium, _ = _make_medium(model, config)

    print(f"DEBUG: Creating calibration point source at {calibration_point.tolist()}...", flush=True)
    point_mask = np.zeros(model.sound_speed.shape, dtype=bool)
    point_mask[tuple(calibration_point)] = True
    source = kSource()
    source.p_mask = point_mask
    source.p = config.calibration_pressure_pa * tone_burst(
        1.0 / dt_s,
        config.frequency_hz,
        config.tone_burst_cycles,
        signal_length=nt,
    )
    source.p_mode = "dirichlet"

    sensor = kSensor(mask=source_mask, record=["p"])

    print("DEBUG: Calling kspaceFirstOrder (calibrate)...", flush=True)
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
    runtime_s = time.perf_counter() - start

    signals = np.asarray(result["p"], dtype=np.float32)
    del result
    import gc

    gc.collect()

    n_points = int(np.sum(source_mask))
    if signals.shape[0] != n_points:
        raise ValueError(
            f"Recorded signal rows ({signals.shape[0]}) do not match bowl mask points ({n_points})."
        )
    if not np.all(np.isfinite(signals)):
        raise ValueError("Calibration signals contain NaN or infinite values.")

    # Canonical C-order flat indices of the bowl mask points (python-backend
    # convention; refocus validates its rebuilt mask against the saved one).
    mask_point_flat_index_c = np.flatnonzero(source_mask.ravel(order="C")).astype(np.int64)

    np.savez_compressed(
        output_dir / ELEMENT_SIGNALS_FILENAME,
        signals=signals,
        dt_s=np.array(dt_s, dtype=np.float64),
        nt_recorded=np.array(nt, dtype=np.int64),
        source_mask=source_mask.astype(np.uint8),
        mask_point_flat_index_c=mask_point_flat_index_c,
        mask_point_ijk=np.argwhere(source_mask).astype(np.int32),
        grid_shape=np.array(model.sound_speed.shape, dtype=np.int64),
        dx_m=np.array(model.dx_m, dtype=np.float64),
        target_index_ijk=model.target_index_ijk.astype(np.int32),
        calibration_point_local_ijk=calibration_point.astype(np.int32),
        calibration_point_full_ijk=np.asarray(calibration_metadata["full_index_ijk"], dtype=np.int32),
        calibration_point_mode=np.array(calibration_metadata["mode"]),
        crop_origin_ijk=model.crop_origin_ijk.astype(np.int32),
        bowl_index_ijk=np.array(source_metadata["bowl_index_ijk"], dtype=np.int32),
        frequency_hz=np.array(config.frequency_hz, dtype=np.float64),
        tone_burst_cycles=np.array(config.tone_burst_cycles, dtype=np.int64),
        calibration_pressure_pa=np.array(config.calibration_pressure_pa, dtype=np.float64),
        cfl=np.array(config.cfl, dtype=np.float64),
        pml_size=np.array(config.pml_size, dtype=np.int64),
        model_path=np.array(str(config.model_path)),
        entry_plan_summary=np.array(json.dumps(_entry_plan_summary(model), ensure_ascii=False)),
        config_json=np.array(json.dumps(config_summary(config), ensure_ascii=False)),
    )

    runtime_metadata = {
        "dt_s": dt_s,
        "nt": nt,
        "c_max_m_s": float(np.max(model.sound_speed)),
        "backend": config.backend,
        "device": config.device,
    }
    simulation_quality = quality_metadata(
        model,
        config,
        runtime_s=runtime_s,
        output_completeness={"element_signals_npz": True, "summary_calibrate_json": True},
    )
    summary = {
        "description": "Time-reversal calibrate stage: independent point source, frozen bowl-mask p recording.",
        "stage": "calibrate",
        "config": config_summary(config),
        "model": model_summary(model, actual_alpha_power),
        "source": source_metadata,
        "runtime": {**runtime_metadata, "runtime_s": runtime_s},
        "simulation_quality": simulation_quality,
        "environment_record": build_environment_record(backend=config.backend, device=config.device),
        "alpha_semantics": alpha_semantics_summary(model, actual_alpha_power),
        "calibration_signal_stats": {
            "n_points": n_points,
            "nt_recorded": nt,
            "dt_s": dt_s,
            "duration_us": float(nt * dt_s * 1e6),
            "max_abs_pa": float(np.max(np.abs(signals))),
            "max_pa": float(np.max(signals)),
            "min_pa": float(np.min(signals)),
            "rms_pa": float(np.sqrt(np.mean(signals.astype(np.float64) ** 2))),
        },
        "run_command": _run_command("calibrate", config, output_dir),
    }
    (output_dir / "summary_calibrate.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"INFO: Calibration complete. signals shape={signals.shape}, saved to {output_dir / ELEMENT_SIGNALS_FILENAME}", flush=True)
    return summary


def load_element_signals(output_dir: Path) -> dict[str, np.ndarray]:
    path = output_dir / ELEMENT_SIGNALS_FILENAME
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {ELEMENT_SIGNALS_FILENAME} in {output_dir}. Run --stage calibrate first."
        )
    return dict(np.load(path, allow_pickle=False))


def _validate_replay_consistency(
    stored: dict[str, np.ndarray],
    model: LoadedModel,
    config: TimeReversalConfig,
    source_mask: np.ndarray,
) -> tuple[np.ndarray, float, int, str]:
    """Validate that the refocus grid/mask/time base matches the calibration.

    Returns (signals, dt_s, nt_recorded, mask_check_note).  Raises on any
    mismatch that would break the TR mapping.
    """
    saved_mask = np.asarray(stored["source_mask"]).astype(bool)
    if saved_mask.shape != source_mask.shape or not np.array_equal(saved_mask, source_mask):
        raise ValueError(
            "Refocus bowl mask mismatch: rebuilt mask differs from the mask stored in "
            f"{ELEMENT_SIGNALS_FILENAME} (shape stored={saved_mask.shape}, rebuilt={source_mask.shape}). "
            "Use the same --model/--entry-plan/crop/aperture/radius/pml settings as the calibrate stage."
        )
    stored_shape = tuple(int(v) for v in np.asarray(stored["grid_shape"]))
    if stored_shape != tuple(int(v) for v in model.sound_speed.shape):
        raise ValueError(
            f"Grid shape mismatch: stored {stored_shape} vs current model {tuple(model.sound_speed.shape)}."
        )
    signals = np.asarray(stored["signals"], dtype=np.float32)
    n_points = int(np.sum(source_mask))
    if signals.shape[0] != n_points:
        raise ValueError(f"Stored signals rows ({signals.shape[0]}) != bowl mask points ({n_points}).")

    dt_s = float(np.asarray(stored["dt_s"]))
    c_max = float(np.max(model.sound_speed))
    dt_current = config.cfl * model.dx_m / c_max
    if not np.isclose(dt_s, dt_current, rtol=1e-9, atol=1e-15):
        raise ValueError(
            f"Time step mismatch: stored dt={dt_s:.6e} s vs current dt={dt_current:.6e} s. "
            "Use the same --cfl and model as the calibrate stage."
        )
    if not np.isclose(float(np.asarray(stored["dx_m"])), model.dx_m):
        raise ValueError("dx mismatch between stored signals and current model.")
    stored_target = np.asarray(stored["target_index_ijk"], dtype=int)
    if not np.array_equal(stored_target, model.target_index_ijk.astype(int)):
        raise ValueError(
            f"Target mismatch: stored {stored_target.tolist()} vs current {model.target_index_ijk.astype(int).tolist()}."
        )
    return signals, dt_s, int(np.asarray(stored["nt_recorded"])), "mask_grid_dt_target_exact_match"


def run_refocus(config: TimeReversalConfig, output_dir: Path, dry_run_quality: bool = False) -> dict[str, object]:
    """Stage 2: replay time-reversed bowl signals; record the refocused field."""
    _require_python_backend(config)
    output_dir.mkdir(parents=True, exist_ok=True)
    model = load_model(_loader_config(config))
    _check_target_not_in_skull(model)
    source_mask, source_metadata = build_bowl_mask(model, config)
    actual_alpha_power = model.alpha_power if model.alpha_power is not None else config.alpha_power

    stored: dict[str, np.ndarray] | None = None
    signals: np.ndarray | None = None
    nt_recorded: int | None = None
    dt_recorded: float | None = None
    mask_check_note = "not_checked_dry_run"
    signals_path = output_dir / ELEMENT_SIGNALS_FILENAME
    if signals_path.exists():
        stored = load_element_signals(output_dir)
        signals, dt_recorded, nt_recorded, mask_check_note = _validate_replay_consistency(
            stored, model, config, source_mask
        )

    if dry_run_quality:
        cfg_sum = config_summary(config)
        cfg_sum["alpha_power"] = actual_alpha_power
        cfg_sum["alpha_mode"] = model.alpha_mode
        cfg_sum["alpha_semantics_status"] = model.alpha_semantics_status
        cfg_sum["element_signals_available"] = stored is not None
        cfg_sum["nt_recorded"] = nt_recorded
        dry_source = dict(source_metadata)
        dry_source["time_reversal"] = {
            "normalize_source": config.normalize_source,
            "source_pressure_pa": config.source_pressure_pa,
            "mask_check": mask_check_note,
        }
        write_quality_dry_run_summary(
            output_dir,
            description="Time-reversal refocus stage quality dry run (reversed bowl replay, p_max/p_min field).",
            config=cfg_sum,
            model=model_summary(model, actual_alpha_power),
            source=dry_source,
            simulation_quality=quality_metadata(model, config),
            environment_record=build_environment_record(backend=config.backend, device=config.device),
        )
        return {"stage": "refocus", "dry_run_quality_only": True}

    if stored is None or signals is None or nt_recorded is None or dt_recorded is None:
        raise FileNotFoundError(
            f"Missing {ELEMENT_SIGNALS_FILENAME} in {output_dir}. Run --stage calibrate first."
        )

    # --- Time reversal, normalisation, and explicit nt handling -------------
    reversed_signals = np.fliplr(signals).astype(np.float64)
    recorded_max_abs_pa = float(np.max(np.abs(signals)))
    if config.normalize_source:
        if recorded_max_abs_pa <= 0:
            raise ValueError("Recorded signals are all zero; cannot normalise.")
        scale_factor = config.source_pressure_pa / recorded_max_abs_pa
    else:
        scale_factor = 1.0
    reversed_signals *= scale_factor

    kgrid, dt_s, nt_from_sim_time = _make_kgrid(model, config)
    nt_required = nt_recorded + REFOCUS_MARGIN_SAMPLES
    if nt_from_sim_time < nt_required:
        nt = nt_required
        kgrid.setTime(nt, dt_s)
        time_alignment = {
            "policy": "extended_sim_time_to_cover_recorded_signals",
            "nt_from_sim_time_us": int(nt_from_sim_time),
            "nt_recorded": int(nt_recorded),
            "refocus_margin_samples": REFOCUS_MARGIN_SAMPLES,
            "nt_final": int(nt),
            "note": "Refocus peak forms near t = nt_recorded * dt; sim time extended so it is captured.",
        }
    else:
        nt = nt_from_sim_time
        time_alignment = {
            "policy": "sim_time_covers_recorded_signals",
            "nt_from_sim_time_us": int(nt_from_sim_time),
            "nt_recorded": int(nt_recorded),
            "refocus_margin_samples": REFOCUS_MARGIN_SAMPLES,
            "nt_final": int(nt),
            "note": "Recorded signals zero-padded at the end of replay; focus at t ~= nt_recorded * dt lies inside the time base.",
        }
    if nt_recorded < nt:
        padding = np.zeros((reversed_signals.shape[0], nt - nt_recorded), dtype=np.float64)
        source_p_matrix = np.concatenate([reversed_signals, padding], axis=1)
        time_alignment["replay_zero_padding_samples"] = int(nt - nt_recorded)
    else:
        source_p_matrix = reversed_signals
        time_alignment["replay_zero_padding_samples"] = 0
    source_p_matrix = source_p_matrix.astype(np.float32)

    medium, _ = _make_medium(model, config)

    print("DEBUG: Creating time-reversed bowl replay source...", flush=True)
    source = kSource()
    source.p_mask = source_mask
    source.p = source_p_matrix
    source.p_mode = "dirichlet"

    record_list = ["p_max", "p_min"]
    if config.record_target_waveform:
        record_list.append("p")
    sensor = kSensor(mask=np.ones(model.sound_speed.shape, dtype=bool), record=record_list)

    print("DEBUG: Calling kspaceFirstOrder (refocus)...", flush=True)
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
    runtime_s = time.perf_counter() - start

    p_max = reshape_to_grid(result["p_max"], model.sound_speed.shape)
    p_min = reshape_to_grid(result["p_min"], model.sound_speed.shape)
    pressure_mpa = np.maximum(np.abs(p_max), np.abs(p_min)).astype(np.float32) / 1e6

    target_waveform = None
    if config.record_target_waveform and "p" in result:
        target = model.target_index_ijk.astype(int)
        flat_idx = np.ravel_multi_index(target, model.sound_speed.shape)
        target_waveform = np.asarray(result["p"][flat_idx, :], dtype=np.float32)
    if "p" in result:
        del result["p"]
    del result
    import gc

    gc.collect()

    if not np.all(np.isfinite(pressure_mpa)):
        raise ValueError("Refocus pressure field contains NaN or infinite values.")
    if float(np.max(pressure_mpa)) <= 0:
        raise ValueError("Refocus pressure field is all zero.")

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

    runtime_metadata = {
        "dt_s": dt_s,
        "nt": nt,
        "c_max_m_s": float(np.max(model.sound_speed)),
        "backend": config.backend,
        "device": config.device,
    }
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

    tuning_note = "ok"
    peak = np.array(pressure_metadata["global_peak_index_ijk"], dtype=int)
    if np.any(peak <= 1) or np.any(peak >= np.array(model.sound_speed.shape) - 2):
        tuning_note = "peak is close to a model boundary; source placement or runtime may need tuning"
    if pressure_metadata["effective_peak_to_target_distance_mm"] > 15.0:
        tuning_note = "peak is far from target; this run validates plumbing but needs acoustic tuning"

    summary = {
        "description": "Time-reversal refocus stage: full-waveform reversed replay from the transducer bowl.",
        "stage": "refocus",
        "config": config_summary(config),
        "model": model_summary(model, actual_alpha_power),
        "source": source_metadata,
        "time_reversal": {
            "element_signals_file": str(signals_path),
            "mask_consistency_check": mask_check_note,
            "nt_recorded": int(nt_recorded),
            "dt_recorded_s": float(dt_recorded),
            "expected_focus_time_us": float(nt_recorded * dt_recorded * 1e6),
            "recorded_max_abs_pa": recorded_max_abs_pa,
            "normalize_source": bool(config.normalize_source),
            "scale_factor": float(scale_factor),
            "replay_max_abs_pa": float(np.max(np.abs(source_p_matrix))),
            "reversal": "np.fliplr over the time axis",
        },
        "time_alignment": time_alignment,
        "runtime": {**runtime_metadata, "runtime_s": runtime_s},
        "simulation_quality": simulation_quality,
        "environment_record": build_environment_record(backend=config.backend, device=config.device),
        "alpha_semantics": alpha_semantics_summary(model, actual_alpha_power),
        "pressure": pressure_metadata,
        "entry_plan": model.entry_plan,
        "tuning_note": tuning_note,
        "run_command": _run_command("refocus", config, output_dir),
    }
    if target_waveform is not None:
        summary["target_waveform_stats"] = {
            "recorded": True,
            "length": len(target_waveform),
            "max_pa": float(np.max(target_waveform)),
            "min_pa": float(np.min(target_waveform)),
            "rms_pa": float(np.sqrt(np.mean(target_waveform.astype(np.float64) ** 2))),
        }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"INFO: Refocus complete. global_peak={pressure_metadata['global_peak_mpa']:.4f} MPa, "
        f"target={pressure_metadata['target_pressure_mpa']:.4f} MPa, "
        f"effective distance={pressure_metadata['effective_peak_to_target_distance_mm']:.3f} mm",
        flush=True,
    )
    return summary


def _run_command(stage: str, config: TimeReversalConfig, output_dir: Path) -> str:
    parts = [
        str(Path("python")),
        str(Path(__file__).name),
        "--stage",
        stage,
        "--model",
        str(config.model_path),
        "--output-dir",
        str(output_dir),
        "--preset",
        config.preset,
        "--sim-time-us",
        f"{config.simulation_time_s * 1e6:.3f}",
        "--cycles",
        str(config.tone_burst_cycles),
        "--pml-size",
        str(config.pml_size),
        "--cfl",
        f"{config.cfl:.4f}",
        "--aperture-mm",
        f"{config.aperture_diameter_m * 1e3:.3f}",
        "--radius-mm",
        f"{config.transducer_radius_m * 1e3:.3f}",
    ]
    if config.entry_plan_path is not None:
        parts += ["--entry-plan", str(config.entry_plan_path)]
    if config.calibration_point_override is not None:
        parts += ["--calibration-point-index", ",".join(str(v) for v in config.calibration_point_override)]
    if config.quick_lateral_half_width_m is not None:
        parts += ["--quick-lateral-mm", f"{config.quick_lateral_half_width_m * 1e3:.3f}"]
    if config.quick_post_target_margin_m is not None:
        parts += ["--quick-post-target-mm", f"{config.quick_post_target_margin_m * 1e3:.3f}"]
    if not config.normalize_source:
        parts.append("--no-normalize")
    if not config.record_target_waveform:
        parts.append("--no-record-target-waveform")
    return " ".join(parts)


def run(config: TimeReversalConfig, output_dir: Path, dry_run_quality: bool = False) -> None:
    if config.calibration_point_override is not None and config.stage != "calibrate":
        raise ValueError("Calibration-point override is restricted to stage=calibrate; refocus requires separately gated constrained weights.")
    if config.stage == "calibrate":
        run_calibrate(config, output_dir, dry_run_quality=dry_run_quality)
    elif config.stage == "refocus":
        run_refocus(config, output_dir, dry_run_quality=dry_run_quality)
    elif config.stage == "auto":
        run_calibrate(config, output_dir, dry_run_quality=dry_run_quality)
        run_refocus(config, output_dir, dry_run_quality=dry_run_quality)
    else:
        raise ValueError(f"Unknown stage: {config.stage!r}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Two-stage full-waveform time-reversal focusing simulation (reference method for phase correction)."
    )
    parser.add_argument("--stage", choices=["calibrate", "refocus", "auto"], default="auto", help="Which TR stage to run.")
    parser.add_argument("--model", default=str(DEFAULT_MODEL_PATH), help="Path to a 3D acoustic model .npz file.")
    parser.add_argument("--entry-plan", default=None, help="Optional CT entry plan JSON from plan_ct_target_entry.py.")
    parser.add_argument("--target-index", type=parse_index, default=None, help="Optional target index formatted as i,j,k.")
    parser.add_argument(
        "--calibration-point-index",
        type=parse_index,
        default=None,
        help="Optional full-model calibration point i,j,k; bowl geometry remains aimed at the frozen target.",
    )
    parser.add_argument("--output-dir", required=True, help="Directory where simulation outputs are written.")
    parser.add_argument("--preset", choices=["smoke", "quick", "standard", "paper_grade"], default="standard", help="Simulation quality preset label.")
    parser.add_argument("--sim-time-us", type=float, default=100.0, help="Simulation duration in microseconds (per stage).")
    parser.add_argument("--frequency-hz", type=float, default=500_000.0, help="Calibration tone burst frequency in Hz.")
    parser.add_argument("--cycles", type=int, default=2, help="Tone burst cycles used by the calibration point source.")
    parser.add_argument("--calibration-pressure-pa", type=float, default=1_000_000.0, help="Calibration point source amplitude in Pa.")
    parser.add_argument("--source-pressure-pa", type=float, default=1_000_000.0, help="Refocus replay peak amplitude in Pa (normalisation target).")
    parser.add_argument("--normalize", action=argparse.BooleanOptionalAction, default=True, help="Normalise reversed signals so max(abs) == --source-pressure-pa (use --no-normalize to keep recorded amplitudes).")
    parser.add_argument("--cfl", type=float, default=0.20, help="CFL number for k-Wave time step estimation.")
    parser.add_argument("--pml-size", type=int, default=12, help="PML thickness in grid points.")
    parser.add_argument("--aperture-mm", type=float, default=30.0, help="Transducer aperture diameter in millimeters.")
    parser.add_argument("--radius-mm", type=float, default=35.0, help="Transducer curvature radius in millimeters.")
    parser.add_argument("--nearfield-mm", type=float, default=10.0, help="Distance after the source mask to exclude when measuring effective focus.")
    parser.add_argument("--full", action="store_true", help="Use the full 3D acoustic model instead of the quick cropped domain.")
    parser.add_argument("--quick-lateral-mm", type=float, default=17.0, help="Quick-crop half-width around the beam axis in millimeters.")
    parser.add_argument("--quick-post-target-mm", type=float, default=8.0, help="Quick-crop margin after the target in millimeters.")
    parser.add_argument("--dry-run-quality", action="store_true", help="Write quality metadata without running k-Wave.")
    parser.add_argument("--record-target-waveform", action=argparse.BooleanOptionalAction, default=True, help="Record the pressure waveform at the focal point (default on).")
    parser.add_argument(
        "--allow-entry-plan-resolution-mismatch",
        action="store_true",
        help="Bypass entry_plan dx/model_shape compatibility checks for explicit diagnostic runs only.",
    )
    parser.add_argument("--backend", choices=["python"], default="python", help="k-Wave backend (TR requires 'python' for mask-ordering guarantees).")
    parser.add_argument("--device", choices=["cpu", "gpu"], default="cpu", help="Device to run k-Wave on (cpu or gpu).")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        TimeReversalConfig(
            model_path=Path(args.model),
            entry_plan_path=None if args.entry_plan is None else Path(args.entry_plan),
            target_index_override=args.target_index,
            calibration_point_override=args.calibration_point_index,
            stage=args.stage,
            frequency_hz=args.frequency_hz,
            calibration_pressure_pa=args.calibration_pressure_pa,
            source_pressure_pa=args.source_pressure_pa,
            normalize_source=args.normalize,
            transducer_radius_m=args.radius_mm * 1e-3,
            aperture_diameter_m=args.aperture_mm * 1e-3,
            tone_burst_cycles=args.cycles,
            cfl=args.cfl,
            simulation_time_s=args.sim_time_us * 1e-6,
            pml_size=args.pml_size,
            preset=args.preset,
            backend=args.backend,
            device=args.device,
            quick_mode=not args.full,
            quick_lateral_half_width_m=None if args.quick_lateral_mm is None else args.quick_lateral_mm * 1e-3,
            quick_post_target_margin_m=None if args.quick_post_target_mm is None else args.quick_post_target_mm * 1e-3,
            nearfield_exclusion_m=args.nearfield_mm * 1e-3,
            record_target_waveform=args.record_target_waveform,
            allow_entry_plan_resolution_mismatch=args.allow_entry_plan_resolution_mismatch,
        ),
        Path(args.output_dir),
        dry_run_quality=args.dry_run_quality,
    )
