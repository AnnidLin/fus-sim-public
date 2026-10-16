from __future__ import annotations

import importlib
import time

import numpy as np

import simulate_source_array_focus as base
import simulate_source_array_focus_split_sensor as split
from kwave.solvers.kspace_solver import Simulation
from kwave.solvers.validation import validate_simulation


def _crop_external_pml(field: np.ndarray, pml_size: tuple[int, ...]) -> np.ndarray:
    interior = tuple(slice(size, -size if size else None) for size in pml_size)
    return field[interior]


def run_kwave_source_array_point_waveform(
    model: base.LoadedModel,
    source_mask: np.ndarray,
    patch_ids: np.ndarray,
    config: base.SourceArrayConfig,
    record_target_waveform: bool = False,
    apodization_weights: np.ndarray | None = None,
) -> tuple[np.ndarray, float, dict[str, object], np.ndarray | None]:
    if not record_target_waveform:
        return base.run_kwave_source_array(
            model,
            source_mask,
            patch_ids,
            config,
            record_target_waveform=False,
            apodization_weights=apodization_weights,
        )
    if config.backend != "python" or config.device != "cpu":
        raise ValueError("Point-waveform online-extrema recording requires backend=python and device=cpu.")

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

    sensor = split.build_pressure_sensor(model, record_target_waveform=True)
    sensor.record = ["p"]
    pml_size = (config.pml_size,) * 3
    validate_simulation(kgrid, medium, source, sensor, pml_size=pml_size)
    kspace_module = importlib.import_module("kwave.kspaceFirstOrder")
    kgrid, medium, source, sensor = kspace_module._expand_for_pml_outside(
        kgrid, medium, source, sensor, pml_size
    )

    simulation = Simulation(
        kgrid,
        medium,
        source,
        sensor,
        device="cpu",
        use_sg=True,
        use_kspace=True,
        smooth_p0=False,
        pml_size=pml_size,
        pml_alpha=(2.0,) * 3,
        quiet=True,
    )
    simulation.setup()
    p_max = np.full(simulation.grid_shape, -np.inf, dtype=float)
    p_min = np.full(simulation.grid_shape, np.inf, dtype=float)

    start = time.perf_counter()
    while simulation.t < simulation.Nt:
        simulation.step()
        np.maximum(p_max, simulation.p, out=p_max)
        np.minimum(p_min, simulation.p, out=p_min)
    runtime_s = time.perf_counter() - start

    waveform = split.extract_single_sensor_waveform(simulation.sensor_data["p"], nt)
    p_max = _crop_external_pml(p_max, pml_size)
    p_min = _crop_external_pml(p_min, pml_size)
    if p_max.shape != model.sound_speed.shape or p_min.shape != model.sound_speed.shape:
        raise ValueError(
            f"Cropped extrema shape {p_max.shape}/{p_min.shape} does not match {model.sound_speed.shape}."
        )
    pressure_mpa = np.maximum(np.abs(p_max), np.abs(p_min)).astype(np.float32) / 1e6
    return pressure_mpa, runtime_s, {
        "dt_s": dt_s,
        "nt": nt,
        "c_max_m_s": c_max,
        "backend": config.backend,
        "device": config.device,
        "sensor_recording_architecture": "target_point_p_plus_online_full_domain_extrema",
    }, waveform


def main() -> None:
    split.run_kwave_source_array_split_sensor = run_kwave_source_array_point_waveform
    split.main()


if __name__ == "__main__":
    main()

