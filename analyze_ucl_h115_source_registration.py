"""Bounded H115 source, registration, and hydrophone-aperture sensitivity."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from analyze_ucl_h115_water_validation import (
    frozen_measured_transverse_widths,
    linear_scale,
    normalized_metrics,
    simulation_line,
    simulation_transverse,
    transverse_widths,
)
from summarize_ucl_270khz_freefield import refined_peak_coordinate


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_simulation(simulation_dir: Path) -> tuple[np.ndarray, float, np.ndarray]:
    with np.load(simulation_dir / "pressure_max_mpa.npz") as data:
        pressure_pa = np.asarray(data["pressure_max_mpa"], dtype=float) * 1e6
        dx_m = float(np.asarray(data["dx_m"]).item())
    summary = load_json(simulation_dir / "summary.json")
    entry = load_json(Path(summary["config"]["entry_plan_path"]))
    return pressure_pa, dx_m, np.asarray(entry["source_center_index_ijk"], dtype=float)


def registration_sweep(
    pressure_pa: np.ndarray,
    source: np.ndarray,
    dx_m: float,
    measured_distance_m: np.ndarray,
    measured_pressure_pa: np.ndarray,
    offsets_mm: list[float],
) -> list[dict[str, float]]:
    measured_peak_mm = float(refined_peak_coordinate(measured_distance_m, measured_pressure_pa) * 1e3)
    arms: list[dict[str, float]] = []
    for offset_mm in offsets_mm:
        sampled = simulation_line(
            pressure_pa, source, dx_m, measured_distance_m + float(offset_mm) * 1e-3
        )
        scale = linear_scale(sampled, float(measured_pressure_pa.max()))
        metrics = normalized_metrics(measured_pressure_pa, sampled * scale)
        simulated_peak_mm = float(refined_peak_coordinate(measured_distance_m, sampled) * 1e3)
        arms.append({
            "offset_mm": float(offset_mm),
            "scale_factor": scale,
            "simulated_peak_on_measurement_axis_mm": simulated_peak_mm,
            "peak_position_difference_mm": abs(simulated_peak_mm - measured_peak_mm),
            **metrics,
        })
    return arms


def disk_offsets(diameter_mm: float, samples_per_axis: int = 5) -> np.ndarray:
    if diameter_mm < 0:
        raise ValueError("hydrophone diameter cannot be negative")
    if diameter_mm == 0:
        return np.zeros((1, 2), dtype=float)
    radius_m = diameter_mm * 0.5e-3
    axis = np.linspace(-radius_m, radius_m, samples_per_axis)
    yy, zz = np.meshgrid(axis, axis)
    offsets = np.column_stack((yy.ravel(), zz.ravel()))
    return offsets[np.sum(offsets**2, axis=1) <= radius_m**2 * (1 + 1e-12)]


def aperture_average(
    pressure_pa: np.ndarray,
    source: np.ndarray,
    dx_m: float,
    distance_m: float,
    x_m: np.ndarray,
    y_m: np.ndarray,
    diameter_mm: float,
) -> np.ndarray:
    samples = [
        simulation_transverse(pressure_pa, source, dx_m, distance_m, x_m + dy, y_m + dz)
        for dy, dz in disk_offsets(diameter_mm)
    ]
    stack = np.vstack(samples)
    valid = np.all(np.isfinite(stack), axis=0)
    averaged = np.full(x_m.shape, np.nan, dtype=float)
    averaged[valid] = np.mean(stack[:, valid], axis=0)
    return averaged


def hydrophone_sweep(
    pressure_pa: np.ndarray,
    source: np.ndarray,
    dx_m: float,
    transverse_coordinates_m: np.ndarray,
    measured_pressure_pa: np.ndarray,
    measured_summary: dict,
    scale: float,
    diameters_mm: list[float],
) -> list[dict[str, object]]:
    measured_width = frozen_measured_transverse_widths(measured_summary)
    distance_m = abs(float(transverse_coordinates_m[0, 2]))
    arms: list[dict[str, object]] = []
    for diameter_mm in diameters_mm:
        simulated = aperture_average(
            pressure_pa, source, dx_m, distance_m,
            transverse_coordinates_m[:, 0], transverse_coordinates_m[:, 1], diameter_mm,
        ) * scale
        common = np.isfinite(simulated)
        metrics = normalized_metrics(measured_pressure_pa[common], simulated[common])
        widths = transverse_widths(
            transverse_coordinates_m[common, 0], transverse_coordinates_m[common, 1], simulated[common]
        )
        arms.append({
            "diameter_mm": float(diameter_mm),
            "sample_count": int(disk_offsets(diameter_mm).shape[0]),
            "common_points": int(common.sum()),
            **metrics,
            "x_width_error_percent": 100.0 * (widths["minus6db_x_width_mm"] - measured_width["minus6db_x_width_mm"]) / measured_width["minus6db_x_width_mm"],
            "y_width_error_percent": 100.0 * (widths["minus6db_y_width_mm"] - measured_width["minus6db_y_width_mm"]) / measured_width["minus6db_y_width_mm"],
        })
    return arms


def run(
    effective_dir: Path,
    nominal_dir: Path,
    measurement_dir: Path,
    brief_path: Path,
    effective_comparison_path: Path | None = None,
) -> dict:
    brief = load_json(brief_path)
    measurement_summary = load_json(measurement_dir / "summary.json")
    effective_comparison = load_json(
        effective_comparison_path or effective_dir / "comparison_coordinate_audit_20260825.json"
    )
    nominal_comparison = load_json(nominal_dir / "comparison.json")
    with np.load(measurement_dir / "qcw_axial_profile.npz") as data:
        axial_distance_m = np.abs(np.asarray(data["coordinates_m"], dtype=float)[:, 2])
        axial_measured_pa = np.asarray(data["pressure_amplitude_pa"], dtype=float)
    with np.load(measurement_dir / "qcw_transverse_map.npz") as data:
        transverse_coordinates_m = np.asarray(data["coordinates_m"], dtype=float)
        transverse_measured_pa = np.asarray(data["pressure_amplitude_pa"], dtype=float)

    simulations: dict[str, dict] = {}
    for name, directory, comparison in (
        ("effective", effective_dir, effective_comparison),
        ("nominal", nominal_dir, nominal_comparison),
    ):
        pressure, dx_m, source = load_simulation(directory)
        simulations[name] = {
            "registration": registration_sweep(
                pressure, source, dx_m, axial_distance_m, axial_measured_pa,
                [float(value) for value in brief["registration_offsets_mm"]],
            ),
            "hydrophone_aperture": hydrophone_sweep(
                pressure, source, dx_m, transverse_coordinates_m, transverse_measured_pa,
                measurement_summary, float(comparison["amplitude_fit"]["scale_factor"]),
                [float(value) for value in brief["hydrophone_diameters_mm"]],
            ),
        }

    effective_axial = effective_comparison["axial_held_out"]
    nominal_axial = nominal_comparison["axial_held_out"]
    effective_transverse = effective_comparison["transverse_held_out"]
    nominal_transverse = nominal_comparison["transverse_held_out"]
    changes = {
        "axial_peak_error_change_mm": nominal_axial["peak_position_difference_mm"] - effective_axial["peak_position_difference_mm"],
        "transverse_normalized_l2_change_percentage_points": nominal_transverse["normalized_relative_l2_percent"] - effective_transverse["normalized_relative_l2_percent"],
        "transverse_x_width_error_change_percentage_points": nominal_transverse["x_width_error_percent"] - effective_transverse["x_width_error_percent"],
        "transverse_y_width_error_change_percentage_points": nominal_transverse["y_width_error_percent"] - effective_transverse["y_width_error_percent"],
    }
    thresholds = brief["material_explanation_thresholds"]
    material = {
        "axial_peak": abs(changes["axial_peak_error_change_mm"]) >= thresholds["axial_peak_error_change_mm"],
        "transverse_l2": abs(changes["transverse_normalized_l2_change_percentage_points"]) >= thresholds["transverse_normalized_l2_change_percentage_points"],
        "transverse_x_width": abs(changes["transverse_x_width_error_change_percentage_points"]) >= thresholds["transverse_width_error_change_percentage_points"],
        "transverse_y_width": abs(changes["transverse_y_width_error_change_percentage_points"]) >= thresholds["transverse_width_error_change_percentage_points"],
    }
    for value in simulations.values():
        passing = [arm for arm in value["registration"] if arm["peak_position_difference_mm"] <= 1.0]
        value["registration_summary"] = {
            "smallest_absolute_offset_passing_peak_gate_mm": None if not passing else min(passing, key=lambda arm: abs(arm["offset_mm"]))["offset_mm"],
            "primary_result_replaced": False,
        }
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed_descriptive_sensitivity",
        "source_geometry_change_nominal_minus_effective": changes,
        "material_explanation_checks": material,
        "source_geometry_materially_explanatory": bool(any(material.values())),
        "simulations": simulations,
        "interpretation_guardrails": [
            "registration and aperture arms are secondary and do not replace the unshifted point-sampled endpoints",
            "aperture averaging is performed on pressure-max amplitude, not complex pressure, and is descriptive only",
            "no per-ring acoustic amplitude or phase was fitted",
        ],
        "claim_boundary": brief["claim_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--effective-dir", type=Path, required=True)
    parser.add_argument("--nominal-dir", type=Path, required=True)
    parser.add_argument("--measurement-dir", type=Path, required=True)
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--effective-comparison", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(
        args.effective_dir, args.nominal_dir, args.measurement_dir, args.brief,
        effective_comparison_path=args.effective_comparison,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
