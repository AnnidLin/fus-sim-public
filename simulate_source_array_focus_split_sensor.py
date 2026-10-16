from __future__ import annotations

import gc
import time
from pathlib import Path

import numpy as np

import simulate_source_array_focus as base


def build_pressure_sensor(model: base.LoadedModel, record_target_waveform: bool):
    if not record_target_waveform:
        return base.kSensor(
            mask=np.ones(model.sound_speed.shape, dtype=bool),
            record=["p_max", "p_min"],
        )

    target = model.target_index_ijk.astype(int)
    mask = np.zeros(model.sound_speed.shape, dtype=bool)
    mask[tuple(target)] = True
    return base.kSensor(mask=mask, record=["p", "p_max_all", "p_min_all"])


def normalize_global_pressure_field(data: np.ndarray, grid_shape: tuple[int, int, int]) -> np.ndarray:
    field = np.asarray(data)
    if field.shape == grid_shape:
        return field
    if field.shape == tuple(reversed(grid_shape)):
        return np.transpose(field, (2, 1, 0))
    if field.size == int(np.prod(grid_shape)):
        return field.reshape(grid_shape)
    raise ValueError(f"Global pressure field shape {field.shape} does not match grid {grid_shape}.")


def extract_single_sensor_waveform(data: np.ndarray, nt: int) -> np.ndarray:
    waveform = np.asarray(data)
    if waveform.size != nt:
        raise ValueError(f"Expected one {nt}-sample target waveform, received shape {waveform.shape}.")
    return waveform.reshape(nt).astype(np.float32)


def run_kwave_source_array_split_sensor(
    model: base.LoadedModel,
    source_mask: np.ndarray,
    patch_ids: np.ndarray,
    config: base.SourceArrayConfig,
    record_target_waveform: bool = False,
    apodization_weights: np.ndarray | None = None,
) -> tuple[np.ndarray, float, dict[str, object], np.ndarray | None]:
    c_max = float(np.max(model.sound_speed))
    dt_s = config.cfl * model.dx_m / c_max
    nt = int(np.ceil(config.simulation_time_s / dt_s))

    kgrid = base.kWaveGrid(list(model.sound_speed.shape), [model.dx_m] * 3)
    kgrid.setTime(nt, dt_s)
    actual_alpha_power = model.alpha_power if model.alpha_power is not None else config.alpha_power
    medium = base.kWaveMedium(
        sound_speed=model.sound_speed,
        density=model.density,
        alpha_coeff=model.alpha_coeff,
        alpha_power=np.array(actual_alpha_power),
        alpha_mode=model.alpha_mode,
    )

    source = base.kSource()
    source.p_mask = source_mask
    patch_offsets = base.compute_patch_phase_offsets(model, config, source_mask, patch_ids, dt_s)
    voxel_offsets = patch_offsets[patch_ids]
    source_p_matrix = config.source_pressure_pa * base.tone_burst(
        1.0 / dt_s,
        config.frequency_hz,
        config.tone_burst_cycles,
        signal_length=nt,
        signal_offset=voxel_offsets,
    )
    if apodization_weights is not None:
        source_p_matrix = source_p_matrix * apodization_weights[:, None]
    source.p = source_p_matrix
    source.p_mode = "dirichlet"

    sensor = build_pressure_sensor(model, record_target_waveform)
    start = time.perf_counter()
    result = base.kspaceFirstOrder(
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

    if record_target_waveform:
        p_max = normalize_global_pressure_field(result["p_max_all"], model.sound_speed.shape)
        p_min = normalize_global_pressure_field(result["p_min_all"], model.sound_speed.shape)
    else:
        p_max = base.reshape_to_grid(result["p_max"], model.sound_speed.shape)
        p_min = base.reshape_to_grid(result["p_min"], model.sound_speed.shape)
    pressure_mpa = np.maximum(np.abs(p_max), np.abs(p_min)).astype(np.float32) / 1e6

    target_waveform = None
    if record_target_waveform and "p" in result:
        target_waveform = extract_single_sensor_waveform(result["p"], nt)
    if "p" in result:
        del result["p"]
    del result
    gc.collect()

    return pressure_mpa, runtime_s, {
        "dt_s": dt_s,
        "nt": nt,
        "c_max_m_s": c_max,
        "backend": config.backend,
        "device": config.device,
        "sensor_recording_architecture": (
            "target_point_p_plus_full_domain_p_max_all_p_min_all"
            if record_target_waveform
            else "full_domain_p_max_p_min"
        ),
    }, target_waveform


def main() -> None:
    args = base.parse_args()
    base.run_kwave_source_array = run_kwave_source_array_split_sensor
    base.run(
        base.SourceArrayConfig(
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


if __name__ == "__main__":
    main()

