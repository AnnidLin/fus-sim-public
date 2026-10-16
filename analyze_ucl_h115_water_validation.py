"""Compare a guarded H115 water simulation with frozen UCL qCW measurements."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates

from summarize_ucl_270khz_freefield import MINUS_6DB_AMPLITUDE, continuous_threshold_width, refined_peak_coordinate


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def linear_scale(simulated: np.ndarray, measured_peak: float) -> float:
    peak = float(np.max(simulated))
    if not np.isfinite(peak) or peak <= 0:
        raise ValueError("simulation axial profile has no positive finite peak")
    return measured_peak / peak


def normalized_metrics(measured: np.ndarray, simulated: np.ndarray) -> dict[str, float]:
    measured = np.asarray(measured, dtype=float)
    simulated = np.asarray(simulated, dtype=float)
    if measured.shape != simulated.shape or measured.size == 0:
        raise ValueError("aligned measurement/simulation arrays are invalid")
    measured_norm = measured / float(measured.max())
    simulated_norm = simulated / float(simulated.max())
    correlation = float(np.corrcoef(measured_norm, simulated_norm)[0, 1])
    relative_l2 = float(np.linalg.norm(simulated_norm - measured_norm) / np.linalg.norm(measured_norm))
    return {"normalized_correlation": correlation, "normalized_relative_l2_percent": relative_l2 * 100.0}


def simulation_line(pressure: np.ndarray, source_index: np.ndarray, dx_m: float, distances_m: np.ndarray) -> np.ndarray:
    x = source_index[0] + distances_m / dx_m
    coordinates = np.vstack((x, np.full_like(x, source_index[1]), np.full_like(x, source_index[2])))
    return map_coordinates(pressure, coordinates, order=1, mode="nearest")


def simulation_transverse(pressure: np.ndarray, source_index: np.ndarray, dx_m: float, distance_m: float, x_m: np.ndarray, y_m: np.ndarray) -> np.ndarray:
    grid_x = np.full_like(x_m, source_index[0] + distance_m / dx_m)
    grid_y = source_index[1] + x_m / dx_m
    grid_z = source_index[2] + y_m / dx_m
    return map_coordinates(pressure, np.vstack((grid_x, grid_y, grid_z)), order=1, mode="constant", cval=np.nan)


def ordered_scan_spacing(x_m: np.ndarray, y_m: np.ndarray) -> float:
    """Infer the raster step without mistaking coordinate jitter for a grid step."""
    x_m = np.asarray(x_m, dtype=float)
    y_m = np.asarray(y_m, dtype=float)
    if x_m.shape != y_m.shape or x_m.size < 2:
        raise ValueError("transverse scan coordinates are invalid")
    adjacent_distance = np.hypot(np.diff(x_m), np.diff(y_m))
    usable = adjacent_distance[np.isfinite(adjacent_distance) & (adjacent_distance > 0)]
    if usable.size == 0:
        raise ValueError("transverse scan spacing is not identifiable")
    return float(np.median(usable))


def transverse_widths(x_m: np.ndarray, y_m: np.ndarray, pressure: np.ndarray) -> dict[str, float]:
    peak = int(np.nanargmax(pressure))
    px, py = x_m[peak], y_m[peak]
    spacing = ordered_scan_spacing(x_m, y_m)
    x_line = np.abs(y_m - py) <= 0.51 * spacing
    y_line = np.abs(x_m - px) <= 0.51 * spacing
    return {
        "minus6db_x_width_mm": continuous_threshold_width(x_m[x_line], pressure[x_line], MINUS_6DB_AMPLITUDE) * 1e3,
        "minus6db_y_width_mm": continuous_threshold_width(y_m[y_line], pressure[y_line], MINUS_6DB_AMPLITUDE) * 1e3,
        "peak_x_mm": px * 1e3,
        "peak_y_mm": py * 1e3,
    }


def frozen_measured_transverse_widths(summary: dict) -> dict[str, float]:
    """Return the transverse endpoints frozen with the measurement intake summary.

    The measurement archive is point-cloud data with anisotropic sampling.  Its
    width endpoints are therefore not re-derived here with a heuristic line
    selector; the accepted source is the audited measurement summary.
    """
    metrics = summary["transverse_qcw"]
    peak = metrics["peak_coordinate_native_mm"]
    return {
        "minus6db_x_width_mm": float(metrics["minus6db_x_width_mm"]),
        "minus6db_y_width_mm": float(metrics["minus6db_y_width_mm"]),
        "peak_x_mm": float(peak[0]),
        "peak_y_mm": float(peak[1]),
    }


def run(simulation_dir: Path, measurement_dir: Path, contract_path: Path) -> dict:
    stage = load_json(simulation_dir / "stage_result.json")
    if stage.get("status") != "completed":
        raise ValueError("simulation stage is not completed")
    summary = load_json(measurement_dir / "summary.json")
    contract = load_json(contract_path)
    with np.load(simulation_dir / "pressure_max_mpa.npz") as data:
        pressure_pa = np.asarray(data["pressure_max_mpa"], dtype=float) * 1e6
        dx_m = float(np.asarray(data["dx_m"]).item())
        target = np.asarray(data["target_index_ijk"], dtype=float)
    entry = load_json(Path(load_json(simulation_dir / "summary.json")["config"]["entry_plan_path"]))
    source = np.asarray(entry["source_center_index_ijk"], dtype=float)

    with np.load(measurement_dir / "qcw_axial_profile.npz") as data:
        axial_coordinates = np.asarray(data["coordinates_m"], dtype=float)
        axial_measured = np.asarray(data["pressure_amplitude_pa"], dtype=float)
    axial_distance = np.abs(axial_coordinates[:, 2])
    axial_simulated = simulation_line(pressure_pa, source, dx_m, axial_distance)
    scale = linear_scale(axial_simulated, float(axial_measured.max()))
    axial_scaled = axial_simulated * scale
    axial_metrics = normalized_metrics(axial_measured, axial_scaled)
    measured_peak_distance = float(abs(refined_peak_coordinate(axial_distance, axial_measured)) * 1e3)
    simulated_peak_distance = float(abs(refined_peak_coordinate(axial_distance, axial_scaled)) * 1e3)
    axial_metrics.update({
        "scale_factor": scale,
        "measured_peak_distance_mm": measured_peak_distance,
        "simulated_peak_distance_mm": simulated_peak_distance,
        "peak_position_difference_mm": abs(simulated_peak_distance - measured_peak_distance),
    })

    with np.load(measurement_dir / "qcw_transverse_map.npz") as data:
        transverse_coordinates = np.asarray(data["coordinates_m"], dtype=float)
        transverse_measured = np.asarray(data["pressure_amplitude_pa"], dtype=float)
    transverse_distance = abs(float(transverse_coordinates[0, 2]))
    transverse_simulated = simulation_transverse(
        pressure_pa, source, dx_m, transverse_distance, transverse_coordinates[:, 0], transverse_coordinates[:, 1]
    ) * scale
    common = np.isfinite(transverse_simulated)
    transverse_metrics_value = normalized_metrics(transverse_measured[common], transverse_simulated[common])
    measured_width = frozen_measured_transverse_widths(summary)
    simulated_width = transverse_widths(transverse_coordinates[common, 0], transverse_coordinates[common, 1], transverse_simulated[common])
    measured_peak = float(transverse_measured[common].max())
    simulated_peak = float(transverse_simulated[common].max())
    position_difference = float(np.hypot(measured_width["peak_x_mm"] - simulated_width["peak_x_mm"], measured_width["peak_y_mm"] - simulated_width["peak_y_mm"]))
    transverse_metrics_value.update({
        "common_points": int(common.sum()),
        "common_fraction": float(common.mean()),
        "peak_pressure_error_percent": 100.0 * (simulated_peak - measured_peak) / measured_peak,
        "peak_position_difference_mm": position_difference,
        "x_width_error_percent": 100.0 * (simulated_width["minus6db_x_width_mm"] - measured_width["minus6db_x_width_mm"]) / measured_width["minus6db_x_width_mm"],
        "y_width_error_percent": 100.0 * (simulated_width["minus6db_y_width_mm"] - measured_width["minus6db_y_width_mm"]) / measured_width["minus6db_y_width_mm"],
        "measured": measured_width,
        "simulated": simulated_width,
    })

    gates = contract["held_out_endpoints"]
    checks = {
        "axial_peak_position": axial_metrics["peak_position_difference_mm"] <= gates["axial_peak_position_difference_mm"]["maximum"],
        "axial_normalized_l2": axial_metrics["normalized_relative_l2_percent"] <= gates["axial_normalized_relative_l2_percent"]["maximum"],
        "transverse_peak_pressure": abs(transverse_metrics_value["peak_pressure_error_percent"]) <= gates["transverse_peak_pressure_error_percent"]["maximum_absolute"],
        "transverse_peak_position": transverse_metrics_value["peak_position_difference_mm"] <= gates["transverse_peak_position_difference_mm"]["maximum"],
        "transverse_correlation": transverse_metrics_value["normalized_correlation"] >= gates["transverse_normalized_correlation"]["minimum"],
        "transverse_normalized_l2": transverse_metrics_value["normalized_relative_l2_percent"] <= gates["transverse_normalized_relative_l2_percent"]["maximum"],
        "transverse_x_width": abs(transverse_metrics_value["x_width_error_percent"]) <= gates["transverse_minus6db_width_error_percent"]["maximum_absolute"],
        "transverse_y_width": abs(transverse_metrics_value["y_width_error_percent"]) <= gates["transverse_minus6db_width_error_percent"]["maximum_absolute"],
    }
    return {
        "schema_version": "1.0", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if all(checks.values()) else "observation_with_failed_preregistered_checks",
        "amplitude_fit": {"training_endpoint": "axial spatial peak", "scale_factor": scale},
        "axial_held_out": axial_metrics, "transverse_held_out": transverse_metrics_value,
        "checks": checks,
        "claim_boundary": "One homogeneous-water engineering validation observation; not Case079, skull, thermal or clinical evidence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulation-dir", type=Path, required=True)
    parser.add_argument("--measurement-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.simulation_dir, args.measurement_dir, args.contract)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
