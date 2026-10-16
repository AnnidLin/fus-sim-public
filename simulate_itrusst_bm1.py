#!/usr/bin/env python3
"""Run focused-bowl ITRUSST Phase-I axisymmetric harmonic benchmarks."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from kwave.data import Vector
from kwave.kgrid import kWaveGrid
from kwave.kmedium import kWaveMedium
from kwave.ksensor import kSensor
from kwave.ksource import kSource
from kwave.kspaceFirstOrder import kspaceFirstOrder
from kwave.kspaceFirstOrderAS import kspaceFirstOrderAS
from kwave.options.simulation_execution_options import SimulationExecutionOptions
from kwave.options.simulation_options import SimulationOptions, SimulationType
from kwave.utils.checks import check_stability
from kwave.utils.mapgen import make_arc
from kwave.utils.signals import create_cw_signals


@dataclass(frozen=True)
class ItrusstBm1Config:
    preset: str
    benchmark: str = "BM1"
    coordinate_system: str = "cartesian_2d"
    frequency_hz: float = 500_000.0
    source_pressure_pa: float = 60_000.0
    sound_speed_m_per_s: float = 1500.0
    density_kg_per_m3: float = 1000.0
    bowl_radius_mm: float = 64.0
    bowl_aperture_mm: float = 64.0
    axial_size_mm: float = 120.0
    lateral_size_mm: float = 70.0
    comparison_dx_mm: float = 0.5
    dx_mm: float = 0.25
    points_per_period: int = 25
    simulation_time_us: float = 120.0
    record_cycles: int = 4
    ramp_cycles: int = 4
    pml_axial: int = 20
    pml_lateral: int = 12
    omp_threads: int = 6
    bone_front_mm: float = 30.0
    bone_thickness_mm: float = 6.5
    bone_sound_speed_m_per_s: float = 2800.0
    bone_density_kg_per_m3: float = 1850.0
    bone_attenuation_db_per_cm_at_500khz: float = 4.0
    skin_front_mm: float = 26.0
    skin_thickness_mm: float = 4.0
    skin_sound_speed_m_per_s: float = 1610.0
    skin_density_kg_per_m3: float = 1090.0
    skin_attenuation_db_per_cm_at_500khz: float = 0.2
    outer_cortical_thickness_mm: float = 1.5
    trabecular_thickness_mm: float = 4.0
    inner_cortical_thickness_mm: float = 1.0
    trabecular_sound_speed_m_per_s: float = 2300.0
    trabecular_density_kg_per_m3: float = 1700.0
    trabecular_attenuation_db_per_cm_at_500khz: float = 8.0
    brain_front_mm: float = 36.5
    brain_sound_speed_m_per_s: float = 1560.0
    brain_density_kg_per_m3: float = 1040.0
    brain_attenuation_db_per_cm_at_500khz: float = 0.3
    alpha_power: float = 2.0
    alpha_mode: str | None = None

    @property
    def nx(self) -> int:
        return int(round(self.axial_size_mm / self.dx_mm)) + 1

    @property
    def ny(self) -> int:
        return int(round(self.lateral_size_mm / self.dx_mm)) + 1

    @property
    def dt_s(self) -> float:
        return 1.0 / (self.frequency_hz * self.points_per_period)

    @property
    def nt(self) -> int:
        return int(round(self.simulation_time_us * 1e-6 / self.dt_s))

    @property
    def cfl(self) -> float:
        return self.sound_speed_m_per_s * self.dt_s / (self.dx_mm * 1e-3)

    @property
    def ppw(self) -> float:
        wavelength_mm = self.sound_speed_m_per_s / self.frequency_hz * 1e3
        return wavelength_mm / self.dx_mm

    @property
    def recorded_samples(self) -> int:
        return self.record_cycles * self.points_per_period

    @property
    def expanded_shape(self) -> tuple[int, int]:
        if self.coordinate_system == "axisymmetric":
            radial_points = (self.ny + 1) // 2
            return (
                self.nx + 2 * self.pml_axial,
                radial_points + self.pml_lateral,
            )
        return (
            self.nx + 2 * self.pml_axial,
            self.ny + 2 * self.pml_lateral,
        )


def config_for_preset(
    preset: str,
    coordinate_system: str = "cartesian_2d",
    benchmark: str = "BM1",
    omp_threads: int = 6,
) -> ItrusstBm1Config:
    if coordinate_system not in {"cartesian_2d", "axisymmetric"}:
        raise ValueError(f"Unsupported coordinate system: {coordinate_system}")
    if benchmark not in {"BM1", "BM3", "BM4"}:
        raise ValueError(f"Unsupported benchmark: {benchmark}")
    points_per_period = {"BM1": 25, "BM3": 96, "BM4": 144}[benchmark]
    if preset == "benchmark-nominal":
        return ItrusstBm1Config(
            preset=preset,
            benchmark=benchmark,
            coordinate_system=coordinate_system,
            points_per_period=points_per_period,
            omp_threads=omp_threads,
        )
    if preset == "smoke":
        return ItrusstBm1Config(
            preset=preset,
            benchmark=benchmark,
            coordinate_system=coordinate_system,
            dx_mm=0.5 if benchmark in {"BM3", "BM4"} else 1.0,
            comparison_dx_mm=0.5 if benchmark in {"BM3", "BM4"} else 1.0,
            points_per_period=(
                96 if benchmark == "BM4" else 48 if benchmark == "BM3" else 25
            ),
            pml_axial=5,
            pml_lateral=3,
            omp_threads=omp_threads,
        )
    raise ValueError(f"Unsupported preset: {preset}")


def odd_grid_points(length_mm: float, dx_mm: float) -> int:
    points = int(round(length_mm / dx_mm)) + 1
    return points if points % 2 == 1 else points + 1


def build_source_mask(config: ItrusstBm1Config) -> np.ndarray:
    radius_points = int(round(config.bowl_radius_mm / config.dx_mm))
    diameter_points = odd_grid_points(config.bowl_aperture_mm, config.dx_mm)
    arc_position = Vector([1, config.ny // 2 + 1])
    focus_position = Vector([1 + radius_points, config.ny // 2 + 1])
    return make_arc(
        Vector([config.nx, config.ny]),
        arc_position,
        radius_points,
        diameter_points,
        focus_position,
    ).astype(bool)


def comparison_indices(config: ItrusstBm1Config) -> tuple[np.ndarray, np.ndarray]:
    stride_float = config.comparison_dx_mm / config.dx_mm
    stride = int(round(stride_float))
    if not math.isclose(stride_float, stride, rel_tol=0, abs_tol=1e-12):
        raise ValueError("comparison_dx_mm must be an integer multiple of dx_mm")
    axial = np.arange(0, config.nx, stride, dtype=int)
    lateral = np.arange(0, config.ny, stride, dtype=int)
    expected_axial = int(round(config.axial_size_mm / config.comparison_dx_mm)) + 1
    expected_lateral = int(round(config.lateral_size_mm / config.comparison_dx_mm)) + 1
    if axial.size != expected_axial or lateral.size != expected_lateral:
        raise ValueError("comparison-grid dimensions do not match the physical domain")
    return axial, lateral


def build_sensor_mask(config: ItrusstBm1Config) -> np.ndarray:
    axial, lateral = comparison_indices(config)
    mask = np.zeros((config.nx, config.ny), dtype=bool)
    mask[np.ix_(axial, lateral)] = True
    return mask


def build_axisymmetric_source_mask(config: ItrusstBm1Config) -> np.ndarray:
    full_mask = build_source_mask(config)
    return full_mask[:, config.ny // 2 :]


def build_axisymmetric_sensor_mask(config: ItrusstBm1Config) -> np.ndarray:
    axial, lateral = comparison_indices(config)
    nonnegative_lateral = lateral[lateral >= config.ny // 2]
    radial = nonnegative_lateral - config.ny // 2
    mask = np.zeros((config.nx, (config.ny + 1) // 2), dtype=bool)
    mask[np.ix_(axial, radial)] = True
    return mask


def source_geometry(config: ItrusstBm1Config, source_mask: np.ndarray) -> dict[str, Any]:
    axial, lateral = np.where(source_mask)
    return {
        "source_points": int(np.count_nonzero(source_mask)),
        "axial_index_min": int(axial.min()),
        "axial_index_max": int(axial.max()),
        "axial_mm_min": float(axial.min() * config.dx_mm),
        "axial_mm_max": float(axial.max() * config.dx_mm),
        "lateral_index_min": int(lateral.min()),
        "lateral_index_max": int(lateral.max()),
        "source_exit_comparison_index": int(
            math.ceil(float(axial.max() * config.dx_mm) / config.comparison_dx_mm)
        ),
        "geometric_focus_axial_mm": config.bowl_radius_mm,
    }


def build_medium_arrays(
    config: ItrusstBm1Config,
    grid_shape: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sound_speed = np.full(
        grid_shape,
        config.sound_speed_m_per_s,
        dtype=np.float32,
    )
    density = np.full(
        grid_shape,
        config.density_kg_per_m3,
        dtype=np.float32,
    )
    alpha_coeff = np.zeros(grid_shape, dtype=np.float32)
    axial_mm = np.arange(grid_shape[0], dtype=np.float64) * config.dx_mm

    def apply_layer(
        start_mm: float,
        stop_mm: float | None,
        sound_speed_value: float,
        density_value: float,
        attenuation_at_500khz: float,
    ) -> None:
        axial_mask = axial_mm >= start_mm
        if stop_mm is not None:
            axial_mask &= axial_mm < stop_mm
        sound_speed[axial_mask, :] = sound_speed_value
        density[axial_mask, :] = density_value
        alpha_coeff[axial_mask, :] = attenuation_at_500khz / (
            (config.frequency_hz / 1e6) ** config.alpha_power
        )

    if config.benchmark == "BM3":
        apply_layer(
            config.bone_front_mm,
            config.bone_front_mm + config.bone_thickness_mm,
            config.bone_sound_speed_m_per_s,
            config.bone_density_kg_per_m3,
            config.bone_attenuation_db_per_cm_at_500khz,
        )
    elif config.benchmark == "BM4":
        outer_cortical_front_mm = config.bone_front_mm
        trabecular_front_mm = (
            outer_cortical_front_mm + config.outer_cortical_thickness_mm
        )
        inner_cortical_front_mm = (
            trabecular_front_mm + config.trabecular_thickness_mm
        )
        apply_layer(
            config.skin_front_mm,
            config.skin_front_mm + config.skin_thickness_mm,
            config.skin_sound_speed_m_per_s,
            config.skin_density_kg_per_m3,
            config.skin_attenuation_db_per_cm_at_500khz,
        )
        apply_layer(
            outer_cortical_front_mm,
            trabecular_front_mm,
            config.bone_sound_speed_m_per_s,
            config.bone_density_kg_per_m3,
            config.bone_attenuation_db_per_cm_at_500khz,
        )
        apply_layer(
            trabecular_front_mm,
            inner_cortical_front_mm,
            config.trabecular_sound_speed_m_per_s,
            config.trabecular_density_kg_per_m3,
            config.trabecular_attenuation_db_per_cm_at_500khz,
        )
        apply_layer(
            inner_cortical_front_mm,
            config.brain_front_mm,
            config.bone_sound_speed_m_per_s,
            config.bone_density_kg_per_m3,
            config.bone_attenuation_db_per_cm_at_500khz,
        )
        apply_layer(
            config.brain_front_mm,
            None,
            config.brain_sound_speed_m_per_s,
            config.brain_density_kg_per_m3,
            config.brain_attenuation_db_per_cm_at_500khz,
        )
    return sound_speed, density, alpha_coeff


def material_geometry(
    config: ItrusstBm1Config,
    sound_speed: np.ndarray,
    density: np.ndarray,
    alpha_coeff: np.ndarray,
) -> dict[str, Any]:
    def summarize_layer(
        name: str,
        start_mm: float,
        stop_mm: float | None,
        sound_speed_value: float,
        density_value: float,
        attenuation_at_500khz: float,
    ) -> dict[str, Any]:
        axial_mm = np.arange(sound_speed.shape[0], dtype=np.float64) * config.dx_mm
        mask = axial_mm >= start_mm
        if stop_mm is not None:
            mask &= axial_mm < stop_mm
        indices = np.flatnonzero(mask)
        return {
            "name": name,
            "axial_index_start": int(indices[0]) if indices.size else None,
            "axial_index_stop_exclusive": (
                int(indices[-1] + 1) if indices.size else None
            ),
            "front_mm": start_mm,
            "stop_mm": stop_mm,
            "represented_thickness_mm": (
                indices.size * config.dx_mm if stop_mm is not None else None
            ),
            "sound_speed_m_per_s": sound_speed_value,
            "density_kg_per_m3": density_value,
            "attenuation_db_per_cm_at_500khz": attenuation_at_500khz,
            "alpha_coeff_db_per_mhz_power_cm": attenuation_at_500khz
            / ((config.frequency_hz / 1e6) ** config.alpha_power),
            "alpha_power": config.alpha_power,
            "alpha_mode": config.alpha_mode,
        }

    bone_mask = sound_speed == config.bone_sound_speed_m_per_s
    bone_axial_indices = np.flatnonzero(np.any(bone_mask, axis=1))
    represented_thickness_mm = bone_axial_indices.size * config.dx_mm
    result = {
        "benchmark": config.benchmark,
        "background": {
            "sound_speed_m_per_s": config.sound_speed_m_per_s,
            "density_kg_per_m3": config.density_kg_per_m3,
            "alpha_coeff_db_per_mhz_power_cm": 0.0,
        },
        "bone": {
            "aggregate_semantics": (
                "cortical_material_only_legacy_compatibility"
                if config.benchmark == "BM4"
                else "homogeneous_total_bone_layer"
            ),
            "axial_index_start": (
                int(bone_axial_indices[0]) if bone_axial_indices.size else None
            ),
            "axial_index_stop_exclusive": (
                int(bone_axial_indices[-1] + 1) if bone_axial_indices.size else None
            ),
            "front_mm": config.bone_front_mm if bone_axial_indices.size else None,
            "represented_thickness_mm": represented_thickness_mm,
            "sound_speed_m_per_s": (
                float(np.max(sound_speed)) if bone_axial_indices.size else None
            ),
            "density_kg_per_m3": (
                float(np.max(density)) if bone_axial_indices.size else None
            ),
            "attenuation_db_per_cm_at_500khz": (
                config.bone_attenuation_db_per_cm_at_500khz
                if bone_axial_indices.size
                else None
            ),
            "alpha_coeff_db_per_mhz_power_cm": (
                float(np.max(alpha_coeff)) if bone_axial_indices.size else None
            ),
            "alpha_power": config.alpha_power if bone_axial_indices.size else None,
            "alpha_mode": config.alpha_mode if bone_axial_indices.size else None,
        },
    }
    if config.benchmark == "BM4":
        osseous_start = int(round(config.bone_front_mm / config.dx_mm))
        osseous_stop = int(round(config.brain_front_mm / config.dx_mm))
        result["osseous_compartment"] = {
            "axial_index_start": osseous_start,
            "axial_index_stop_exclusive": osseous_stop,
            "front_mm": config.bone_front_mm,
            "stop_mm": config.brain_front_mm,
            "represented_thickness_mm": (
                osseous_stop - osseous_start
            )
            * config.dx_mm,
            "heterogeneous": True,
            "authoritative_properties": "layers",
        }
        result["layers"] = [
            summarize_layer(
                "water",
                0.0,
                config.skin_front_mm,
                config.sound_speed_m_per_s,
                config.density_kg_per_m3,
                0.0,
            ),
            summarize_layer(
                "skin",
                config.skin_front_mm,
                config.bone_front_mm,
                config.skin_sound_speed_m_per_s,
                config.skin_density_kg_per_m3,
                config.skin_attenuation_db_per_cm_at_500khz,
            ),
            summarize_layer(
                "outer_cortical_bone",
                config.bone_front_mm,
                config.bone_front_mm + config.outer_cortical_thickness_mm,
                config.bone_sound_speed_m_per_s,
                config.bone_density_kg_per_m3,
                config.bone_attenuation_db_per_cm_at_500khz,
            ),
            summarize_layer(
                "trabecular_bone",
                config.bone_front_mm + config.outer_cortical_thickness_mm,
                config.bone_front_mm
                + config.outer_cortical_thickness_mm
                + config.trabecular_thickness_mm,
                config.trabecular_sound_speed_m_per_s,
                config.trabecular_density_kg_per_m3,
                config.trabecular_attenuation_db_per_cm_at_500khz,
            ),
            summarize_layer(
                "inner_cortical_bone",
                config.bone_front_mm
                + config.outer_cortical_thickness_mm
                + config.trabecular_thickness_mm,
                config.brain_front_mm,
                config.bone_sound_speed_m_per_s,
                config.bone_density_kg_per_m3,
                config.bone_attenuation_db_per_cm_at_500khz,
            ),
            summarize_layer(
                "brain",
                config.brain_front_mm,
                None,
                config.brain_sound_speed_m_per_s,
                config.brain_density_kg_per_m3,
                config.brain_attenuation_db_per_cm_at_500khz,
            ),
        ]
    return result


def _bm4_material_contract_passes(
    config: ItrusstBm1Config,
    material: dict[str, Any],
    sound_speed: np.ndarray,
    density: np.ndarray,
    alpha_coeff: np.ndarray,
) -> bool:
    layers = material.get("layers")
    if not isinstance(layers, list):
        return False
    expected = [
        ("water", 0.0, 26.0, 1500.0, 1000.0, 0.0),
        ("skin", 26.0, 30.0, 1610.0, 1090.0, 0.8),
        ("outer_cortical_bone", 30.0, 31.5, 2800.0, 1850.0, 16.0),
        ("trabecular_bone", 31.5, 35.5, 2300.0, 1700.0, 32.0),
        ("inner_cortical_bone", 35.5, 36.5, 2800.0, 1850.0, 16.0),
        ("brain", 36.5, None, 1560.0, 1040.0, 1.2),
    ]
    if len(layers) != len(expected):
        return False
    for layer, (
        name,
        start_mm,
        stop_mm,
        expected_sound_speed,
        expected_density,
        expected_alpha_coeff,
    ) in zip(layers, expected, strict=True):
        if (
            layer["name"] != name
            or not math.isclose(layer["front_mm"], start_mm, abs_tol=1e-12)
            or layer["stop_mm"] != stop_mm
            or layer["sound_speed_m_per_s"] != expected_sound_speed
            or layer["density_kg_per_m3"] != expected_density
            or not math.isclose(
                layer["alpha_coeff_db_per_mhz_power_cm"],
                expected_alpha_coeff,
                abs_tol=1e-12,
            )
            or layer["alpha_power"] != 2.0
            or layer["alpha_mode"] is not None
        ):
            return False
        start_index = int(round(start_mm / config.dx_mm))
        stop_index = (
            sound_speed.shape[0]
            if stop_mm is None
            else int(round(stop_mm / config.dx_mm))
        )
        if (
            layer["axial_index_start"] != start_index
            or layer["axial_index_stop_exclusive"] != stop_index
        ):
            return False
        if stop_mm is not None and not math.isclose(
            layer["represented_thickness_mm"],
            stop_mm - start_mm,
            abs_tol=1e-12,
        ):
            return False
        if (
            not np.allclose(
                sound_speed[start_index:stop_index],
                expected_sound_speed,
            )
            or not np.allclose(
                density[start_index:stop_index],
                expected_density,
            )
            or not np.allclose(
                alpha_coeff[start_index:stop_index],
                expected_alpha_coeff,
            )
        ):
            return False
    return True


def resource_gate(config: ItrusstBm1Config) -> dict[str, Any]:
    source_mask = build_source_mask(config)
    sensor_mask = (
        build_axisymmetric_sensor_mask(config)
        if config.coordinate_system == "axisymmetric"
        else build_sensor_mask(config)
    )
    expanded_points = int(np.prod(config.expanded_shape))
    fft_work_points = (
        config.expanded_shape[0] * config.expanded_shape[1] * 4
        if config.coordinate_system == "axisymmetric"
        else expanded_points
    )
    sensor_points = int(np.count_nonzero(sensor_mask))
    time_series_bytes = sensor_points * config.recorded_samples * 8
    # Conservative accounting for real fields, complex FFT workspaces, PML
    # operators and retained sensor data in the pure-Python solver.
    working_memory_bytes_upper_estimate = (
        expanded_points * 20 * 8 + fft_work_points * 10 * 16 + time_series_bytes * 3
    )
    geometry = source_geometry(config, source_mask)
    internal_shape = (
        (config.nx, (config.ny + 1) // 2)
        if config.coordinate_system == "axisymmetric"
        else (config.nx, config.ny)
    )
    sound_speed, density, alpha_coeff = build_medium_arrays(config, internal_shape)
    material = material_geometry(config, sound_speed, density, alpha_coeff)
    bone = material["bone"]
    stability_dt_limit_s = None
    if config.benchmark in {"BM3", "BM4"}:
        stability_grid = kWaveGrid(
            list(internal_shape),
            [config.dx_mm * 1e-3] * 2,
        )
        stability_medium = kWaveMedium(
            sound_speed=sound_speed,
            density=density,
            alpha_coeff=alpha_coeff,
            alpha_power=np.array(config.alpha_power),
        )
        stability_dt_limit_s = float(
            check_stability(stability_grid, stability_medium)
        )
    expected_shape = [
        int(round(config.lateral_size_mm / config.comparison_dx_mm)) + 1,
        int(round(config.axial_size_mm / config.comparison_dx_mm)) + 1,
    ]
    checks = {
        "benchmark_supported": config.benchmark in {"BM1", "BM3", "BM4"},
        "frequency_500khz": config.frequency_hz == 500_000.0,
        "source_pressure_60kpa": config.source_pressure_pa == 60_000.0,
        "water_contract": (
            config.sound_speed_m_per_s == 1500.0
            and config.density_kg_per_m3 == 1000.0
        ),
        "bowl_64mm_by_64mm": (
            config.bowl_radius_mm == 64.0
            and config.bowl_aperture_mm == 64.0
        ),
        "ppw_at_least_12_for_nominal": (
            config.preset != "benchmark-nominal" or config.ppw >= 12.0
        ),
        "comparison_shape_141x241_for_nominal": (
            config.preset != "benchmark-nominal" or expected_shape == [141, 241]
        ),
        "source_before_official_exit_plane": (
            geometry["source_exit_comparison_index"] <= 19
        ),
        "record_four_complete_cycles": (
            config.recorded_samples == 4 * config.points_per_period
        ),
        "record_window_fits": config.recorded_samples < config.nt,
        "memory_estimate_below_2gib": working_memory_bytes_upper_estimate < 2 * 1024**3,
        "omp_threads_leave_device_headroom": (
            1
            <= config.omp_threads
            <= max(1, (os.cpu_count() or 1) // 2)
        ),
        "bm3_axisymmetric_only": (
            config.benchmark != "BM3" or config.coordinate_system == "axisymmetric"
        ),
        "bm3_material_contract": (
            config.benchmark != "BM3"
            or (
                bone["front_mm"] == 30.0
                and math.isclose(
                    bone["represented_thickness_mm"],
                    6.5,
                    rel_tol=0,
                    abs_tol=1e-12,
                )
                and bone["sound_speed_m_per_s"] == 2800.0
                and bone["density_kg_per_m3"] == 1850.0
                and bone["attenuation_db_per_cm_at_500khz"] == 4.0
                and bone["alpha_coeff_db_per_mhz_power_cm"] == 16.0
                and bone["alpha_power"] == 2.0
                and bone["alpha_mode"] is None
            )
        ),
        "bm3_time_contract": (
            config.benchmark != "BM3"
            or (
                (
                    config.preset == "benchmark-nominal"
                    and config.points_per_period == 96
                    and config.nt == 5760
                    and math.isclose(
                        config.cfl,
                        0.125,
                        rel_tol=0,
                        abs_tol=1e-12,
                    )
                )
                or (
                    config.preset == "smoke"
                    and config.points_per_period == 48
                    and config.nt == 2880
                    and config.cfl <= 0.25
                )
            )
        ),
        "bm3_solver_stability_dt": (
            config.benchmark != "BM3"
            or (
                stability_dt_limit_s is not None
                and config.dt_s <= stability_dt_limit_s
            )
        ),
        "bm4_axisymmetric_only": (
            config.benchmark != "BM4" or config.coordinate_system == "axisymmetric"
        ),
        "bm4_material_contract": (
            config.benchmark != "BM4"
            or _bm4_material_contract_passes(
                config,
                material,
                sound_speed,
                density,
                alpha_coeff,
            )
        ),
        "bm4_time_candidate_is_stable": (
            config.benchmark != "BM4"
            or (
                stability_dt_limit_s is not None
                and config.dt_s <= stability_dt_limit_s
            )
        ),
        "bm4_time_contract": (
            config.benchmark != "BM4"
            or (
                (
                    config.preset == "benchmark-nominal"
                    and config.points_per_period == 144
                    and config.nt == 8640
                    and math.isclose(
                        config.cfl,
                        1.0 / 12.0,
                        rel_tol=0,
                        abs_tol=1e-12,
                    )
                )
                or (
                    config.preset == "smoke"
                    and config.points_per_period == 96
                    and config.nt == 5760
                    and config.cfl <= 0.125
                )
            )
        ),
    }
    maximum_authorized_minutes = (
        600 if config.benchmark in {"BM3", "BM4"} else 480
    )
    return {
        "schema_version": "1.0",
        "status": "passed" if all(checks.values()) else "failed",
        "pressure_execution_allowed": all(checks.values()),
        "claim_level": (
            "workflow_smoke_only"
            if config.preset == "smoke"
            else "engineering_benchmark_nominal_protocol"
        ),
        "config": asdict(config),
        "derived": {
            "coordinate_system": config.coordinate_system,
            "grid_axes_internal": [
                "axial",
                "radial" if config.coordinate_system == "axisymmetric" else "lateral",
            ],
            "grid_shape_internal": list(internal_shape),
            "comparison_domain_grid_shape_axial_lateral": [config.nx, config.ny],
            "pml_axes": [
                "axial",
                "radial" if config.coordinate_system == "axisymmetric" else "lateral",
            ],
            "pml_outside": [
                config.pml_axial,
                config.pml_lateral,
            ],
            "grid_shape_expanded": list(config.expanded_shape),
            "grid_points_expanded": expanded_points,
            "fft_work_points_estimate": fft_work_points,
            "ppw": config.ppw,
            "points_per_period": config.points_per_period,
            "dt_s": config.dt_s,
            "cfl": config.cfl,
            "maximum_material_cfl": (
                float(np.max(sound_speed)) * config.dt_s / (config.dx_mm * 1e-3)
            ),
            "stability_dt_limit_s": stability_dt_limit_s,
            "dt_to_stability_limit_ratio": (
                config.dt_s / stability_dt_limit_s
                if stability_dt_limit_s is not None
                else None
            ),
            "nt": config.nt,
            "simulation_time_us": config.nt * config.dt_s * 1e6,
            "sensor_points": sensor_points,
            "recorded_samples": config.recorded_samples,
            "sensor_time_series_bytes_float64": time_series_bytes,
            "working_memory_bytes_upper_estimate": working_memory_bytes_upper_estimate,
            "logical_cpu_count": os.cpu_count(),
            "omp_threads": config.omp_threads,
            "omp_thread_fraction": config.omp_threads / (os.cpu_count() or 1),
            "comparison_shape_lateral_axial": expected_shape,
            "source": geometry,
            "material": material,
        },
        "checks": checks,
        "runtime_estimate": {
            "status": "requires_smoke_measurement",
            "maximum_authorized_minutes": maximum_authorized_minutes,
        },
        "stop_conditions": [
            "non_finite_field",
            "zero_or_negative_amplitude_peak",
            "wrong_comparison_shape",
            "source_after_official_exit_plane",
            "stall_without_log_or_progress_for_20_minutes",
            f"maximum_{maximum_authorized_minutes}_minutes",
        ],
    }


def extract_harmonic(
    pressure_time_series: np.ndarray,
    dt_s: float,
    frequency_hz: float,
) -> tuple[np.ndarray, np.ndarray]:
    data = np.asarray(pressure_time_series, dtype=np.float64)
    if data.ndim != 2:
        raise ValueError("pressure_time_series must be sensor-by-time")
    count = data.shape[1]
    time_values = np.arange(count, dtype=np.float64) * dt_s
    omega_t = 2.0 * np.pi * frequency_hz * time_values
    sin_coefficient = (2.0 / count) * (data @ np.sin(omega_t))
    cos_coefficient = (2.0 / count) * (data @ np.cos(omega_t))
    amplitude = np.hypot(sin_coefficient, cos_coefficient)
    phase = np.arctan2(cos_coefficient, sin_coefficient)
    return amplitude, phase


def reshape_comparison_values(
    values: np.ndarray,
    config: ItrusstBm1Config,
) -> np.ndarray:
    axial, lateral = comparison_indices(config)
    flat = np.asarray(values)
    if flat.size != axial.size * lateral.size:
        raise ValueError("sensor value count does not match comparison grid")
    axial_lateral = flat.reshape((axial.size, lateral.size), order="C")
    return axial_lateral.T


def reshape_axisymmetric_comparison_values(
    values: np.ndarray,
    config: ItrusstBm1Config,
) -> np.ndarray:
    axial, lateral = comparison_indices(config)
    radial_count = (lateral.size + 1) // 2
    flat = np.asarray(values)
    if flat.size != axial.size * radial_count:
        raise ValueError("axisymmetric sensor count does not match comparison grid")
    # The legacy axisymmetric solver follows MATLAB/Fortran sensor ordering.
    axial_radial = flat.reshape((axial.size, radial_count), order="F")
    full_axial_lateral = np.concatenate(
        [axial_radial[:, 1:][:, ::-1], axial_radial],
        axis=1,
    )
    return full_axial_lateral.T


def orient_pressure_time_series(
    pressure: np.ndarray,
    sensor_points: int,
    recorded_samples: int,
) -> np.ndarray:
    """Return pressure in sensor-by-time orientation for harmonic extraction."""
    data = np.asarray(pressure, dtype=np.float64)
    expected = (sensor_points, recorded_samples)
    if data.shape == expected:
        return data
    if data.shape == expected[::-1]:
        return data.T
    raise ValueError(
        f"unexpected pressure shape {data.shape}; expected {expected} or {expected[::-1]}"
    )


def transmitted_region_metrics(
    p_amp: np.ndarray,
    config: ItrusstBm1Config,
) -> dict[str, Any]:
    field = np.asarray(p_amp, dtype=np.float64)
    expected_shape = (
        int(round(config.lateral_size_mm / config.comparison_dx_mm)) + 1,
        int(round(config.axial_size_mm / config.comparison_dx_mm)) + 1,
    )
    if field.shape != expected_shape:
        raise ValueError(
            f"wrong comparison shape {field.shape}, expected {expected_shape}"
        )
    if config.benchmark in {"BM3", "BM4"}:
        # Use the first sample strictly beyond the 36.5 mm skull/brain
        # interface, matching the official post-interface comparison mask.
        start_index = int(
            math.floor(config.brain_front_mm / config.comparison_dx_mm)
        ) + 1
    else:
        start_index = 0
    region = field[:, start_index:]
    finite = bool(np.all(np.isfinite(region)))
    positive_voxels = int(np.count_nonzero(region > 0))
    peak_pa = float(np.max(region)) if region.size else 0.0
    return {
        "axial_index_start": start_index,
        "axial_mm_start": start_index * config.comparison_dx_mm,
        "voxel_count": int(region.size),
        "finite": finite,
        "positive_voxels": positive_voxels,
        "peak_pa": peak_pa,
        "passed": finite and positive_voxels > 0 and peak_pa > 0,
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def execute(config: ItrusstBm1Config, output_dir: Path) -> dict[str, Any]:
    gate = resource_gate(config)
    write_json(output_dir / "dry_run_quality.json", gate)
    if not gate["pressure_execution_allowed"]:
        raise RuntimeError("dry-run quality gate failed")

    write_json(
        output_dir / "run_status.json",
        {
            "status": "running",
            "preset": config.preset,
            "started_unix_s": time.time(),
            "stage": "pressure",
        },
    )
    radial_points = (config.ny + 1) // 2
    grid_shape = (
        [config.nx, radial_points]
        if config.coordinate_system == "axisymmetric"
        else [config.nx, config.ny]
    )
    kgrid = kWaveGrid(grid_shape, [config.dx_mm * 1e-3] * 2)
    kgrid.setTime(config.nt, config.dt_s)
    sound_speed, density, alpha_coeff = build_medium_arrays(
        config,
        tuple(grid_shape),
    )
    if config.benchmark in {"BM3", "BM4"}:
        medium = kWaveMedium(
            sound_speed=sound_speed,
            density=density,
            alpha_coeff=alpha_coeff,
            alpha_power=np.array(config.alpha_power),
        )
    else:
        medium = kWaveMedium(
            sound_speed=np.array(config.sound_speed_m_per_s),
            density=np.array(config.density_kg_per_m3),
        )
    source_mask = (
        build_axisymmetric_source_mask(config)
        if config.coordinate_system == "axisymmetric"
        else build_source_mask(config)
    )
    source = kSource()
    source.p_mask = source_mask
    time_values = np.arange(config.nt, dtype=np.float64) * config.dt_s
    source.p = create_cw_signals(
        time_values,
        config.frequency_hz,
        np.array([config.source_pressure_pa]),
        np.array([0.0]),
        ramp_length=config.ramp_cycles,
    )
    source.p_mode = "dirichlet"

    sensor_mask = (
        build_axisymmetric_sensor_mask(config)
        if config.coordinate_system == "axisymmetric"
        else build_sensor_mask(config)
    )
    sensor = kSensor(mask=sensor_mask, record=["p"])
    sensor.record_start_index = config.nt - config.recorded_samples + 1
    start = time.perf_counter()
    if config.coordinate_system == "axisymmetric":
        cpp_data_dir = output_dir / "axisymmetric_cpp"
        cpp_data_dir.mkdir(parents=True, exist_ok=True)
        simulation_options = SimulationOptions(
            simulation_type=SimulationType.AXISYMMETRIC,
            pml_inside=False,
            pml_size=[config.pml_axial, config.pml_lateral],
            radial_symmetry="WSWA-FFT",
            smooth_p0=False,
            data_cast="single",
            save_to_disk=True,
            data_path=str(cpp_data_dir),
            input_filename="input.h5",
            output_filename="output.h5",
        )
        execution_options = SimulationExecutionOptions(
            is_gpu_simulation=False,
            backend="OMP",
            kwave_function_name="kspaceFirstOrderAS",
            num_threads=config.omp_threads,
            delete_data=False,
            show_sim_log=True,
        )
        previous_omp_threads = os.environ.get("OMP_NUM_THREADS")
        os.environ["OMP_NUM_THREADS"] = str(config.omp_threads)
        try:
            result = kspaceFirstOrderAS(
                kgrid=kgrid,
                medium=medium,
                source=source,
                sensor=sensor,
                simulation_options=simulation_options,
                execution_options=execution_options,
            )
        finally:
            if previous_omp_threads is None:
                os.environ.pop("OMP_NUM_THREADS", None)
            else:
                os.environ["OMP_NUM_THREADS"] = previous_omp_threads
    else:
        result = kspaceFirstOrder(
            kgrid,
            medium,
            source,
            sensor,
            backend="python",
            device="cpu",
            pml_size=(config.pml_axial, config.pml_lateral),
            pml_inside=False,
            quiet=False,
        )
    runtime_s = time.perf_counter() - start
    pressure = orient_pressure_time_series(
        result["p"],
        int(np.count_nonzero(sensor_mask)),
        config.recorded_samples,
    )
    amplitude, phase = extract_harmonic(
        pressure,
        config.dt_s,
        config.frequency_hz,
    )
    reshape_values = (
        reshape_axisymmetric_comparison_values
        if config.coordinate_system == "axisymmetric"
        else reshape_comparison_values
    )
    p_amp = reshape_values(amplitude, config).astype(np.float32)
    p_phase = reshape_values(phase, config).astype(np.float32)
    expected_shape = (
        int(round(config.lateral_size_mm / config.comparison_dx_mm)) + 1,
        int(round(config.axial_size_mm / config.comparison_dx_mm)) + 1,
    )
    if p_amp.shape != expected_shape:
        raise ValueError(f"wrong comparison shape {p_amp.shape}, expected {expected_shape}")
    if not np.all(np.isfinite(p_amp)) or np.any(p_amp < 0):
        raise ValueError("p_amp contains invalid values")
    if float(np.max(p_amp)) <= 0:
        raise ValueError("p_amp peak is not positive")
    transmitted = transmitted_region_metrics(p_amp, config)
    if not transmitted["passed"]:
        raise ValueError("post-interface transmitted field gate failed")
    peak = tuple(int(item) for item in np.unravel_index(np.argmax(p_amp), p_amp.shape))
    np.savez_compressed(
        output_dir / "p_amp.npz",
        p_amp=p_amp,
        p_phase=p_phase,
    )
    summary = {
        "schema_version": "1.0",
        "status": "completed",
        "claim_level": gate["claim_level"],
        "benchmark": config.benchmark,
        "source": 1,
        "config": asdict(config),
        "derived": gate["derived"],
        "runtime_s": runtime_s,
        "transmitted_region": transmitted,
        "output": {
            "path": str((output_dir / "p_amp.npz").resolve()),
            "p_amp_shape_lateral_axial": list(p_amp.shape),
            "p_amp_peak_pa": float(np.max(p_amp)),
            "peak_index_lateral_axial": list(peak),
            "peak_lateral_mm": (peak[0] - (p_amp.shape[0] - 1) / 2)
            * config.comparison_dx_mm,
            "peak_axial_mm": peak[1] * config.comparison_dx_mm,
        },
        "limitations": [
            "This is a nominal-protocol independent reproduction, not the native PPW60 official k-Wave run.",
            f"{config.benchmark} alone does not establish transcranial or clinical validity.",
        ],
    }
    write_json(output_dir / "summary.json", summary)
    write_json(
        output_dir / "run_status.json",
        {
            "status": "completed",
            "preset": config.preset,
            "runtime_s": runtime_s,
            "summary": str((output_dir / "summary.json").resolve()),
        },
    )
    return summary


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preset",
        choices=("smoke", "benchmark-nominal"),
        default="benchmark-nominal",
    )
    parser.add_argument(
        "--coordinate-system",
        choices=("cartesian_2d", "axisymmetric"),
        default="cartesian_2d",
    )
    parser.add_argument(
        "--benchmark",
        choices=("BM1", "BM3", "BM4"),
        default="BM1",
    )
    parser.add_argument(
        "--omp-threads",
        type=int,
        default=6,
        help="OMP threads; the dry-run gate rejects values above half the logical CPUs.",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--stage",
        choices=("itrusst_bm1",),
        default="itrusst_bm1",
        help="Stage label consumed by the stage-aware process monitor.",
    )
    parser.add_argument("--dry-run-quality", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.dry_run_quality == args.execute:
        parser.error("choose exactly one of --dry-run-quality or --execute")
    config = config_for_preset(
        args.preset,
        args.coordinate_system,
        args.benchmark,
        args.omp_threads,
    )
    output_dir = Path(args.output_dir).resolve()
    if args.dry_run_quality:
        report = resource_gate(config)
        write_json(output_dir / "dry_run_quality.json", report)
        print(json.dumps({"status": report["status"], "output_dir": str(output_dir)}))
        return 0 if report["status"] == "passed" else 1
    try:
        summary = execute(config, output_dir)
    except Exception as exc:
        write_json(
            output_dir / "run_status.json",
            {
                "status": "failed",
                "preset": config.preset,
                "coordinate_system": config.coordinate_system,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise
    print(
        json.dumps(
            {
                "status": summary["status"],
                "runtime_s": summary["runtime_s"],
                "output_dir": str(output_dir),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
