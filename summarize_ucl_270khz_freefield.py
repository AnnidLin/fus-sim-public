"""Create a bounded, calibrated summary of the UCL H115 270 kHz free field.

Only the quasi-continuous-wave scans (datasets 3 and 4) are converted to
pressure.  The conversion follows the paper's carrier-frequency sensitivity
method and reads the HDF5 waveform matrix in small point chunks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np


MINUS_6DB_AMPLITUDE = 10.0 ** (-6.0 / 20.0)
EXPECTED_INPUT_SHA256 = "0275af014151ca972c0c7799af2735e345554c460f797f217bd8ceb4f3dfa0ad"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def integer_cycle_slice(sample_count: int, sample_period_s: float, frequency_hz: float) -> slice:
    available_cycles = sample_count * sample_period_s * frequency_hz
    cycles = max(1, int(np.floor(available_cycles)))
    kept_samples = min(sample_count, int(round(cycles / (frequency_hz * sample_period_s))))
    start = (sample_count - kept_samples) // 2
    return slice(start, start + kept_samples)


def carrier_projector(sample_count: int, sample_period_s: float, frequency_hz: float) -> np.ndarray:
    time_s = np.arange(sample_count, dtype=np.float64) * sample_period_s
    phase = 2.0 * np.pi * frequency_hz * time_s
    design = np.column_stack((np.sin(phase), np.cos(phase), np.ones(sample_count)))
    return np.linalg.pinv(design)


def fit_carrier(waveforms_v: np.ndarray, projector: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return peak voltage amplitude, phase and DC offset for rows of waveforms."""
    coefficients = np.asarray(waveforms_v, dtype=np.float64) @ projector.T
    sin_coefficient = coefficients[:, 0]
    cos_coefficient = coefficients[:, 1]
    amplitude_v = np.hypot(sin_coefficient, cos_coefficient)
    phase_rad = np.arctan2(cos_coefficient, sin_coefficient)
    return amplitude_v, phase_rad, coefficients[:, 2]


def interpolate_calibration(response: np.ndarray, frequency_hz: float) -> dict[str, float]:
    table = np.asarray(response, dtype=np.float64)
    if table.ndim == 3:
        table = table[0]
    if table.shape[0] != 5:
        raise ValueError(f"expected frequencyResponse [5,N], got {table.shape}")
    frequencies = table[0]
    if not frequencies[0] <= frequency_hz <= frequencies[-1]:
        raise ValueError("carrier frequency lies outside the hydrophone calibration")
    unwrapped_phase = np.unwrap(table[3])
    return {
        "frequency_hz": float(frequency_hz),
        "sensitivity_v_per_pa": float(np.interp(frequency_hz, frequencies, table[1])),
        "amplitude_uncertainty_percent": float(np.interp(frequency_hz, frequencies, table[2])),
        "phase_rad": float(np.interp(frequency_hz, frequencies, unwrapped_phase)),
        "phase_uncertainty_percent": float(np.interp(frequency_hz, frequencies, table[4])),
    }


def threshold_region(x: np.ndarray, amplitude: np.ndarray, fraction: float) -> dict[str, float | str | None]:
    x = np.asarray(x, dtype=np.float64)
    amplitude = np.asarray(amplitude, dtype=np.float64)
    order = np.argsort(x)
    x = x[order]
    amplitude = amplitude[order]
    peak_index = int(np.argmax(amplitude))
    threshold = float(amplitude[peak_index] * fraction)

    left = peak_index
    while left > 0 and amplitude[left] >= threshold:
        left -= 1
    right = peak_index
    while right < amplitude.size - 1 and amplitude[right] >= threshold:
        right += 1
    left_censored = left == 0 and amplitude[left] >= threshold
    right_censored = right == amplitude.size - 1 and amplitude[right] >= threshold
    left_crossing = None if left_censored else float(
        np.interp(threshold, [amplitude[left], amplitude[left + 1]], [x[left], x[left + 1]])
    )
    right_crossing = None if right_censored else float(
        np.interp(threshold, [amplitude[right], amplitude[right - 1]], [x[right], x[right - 1]])
    )
    if left_crossing is not None and right_crossing is not None:
        width = abs(right_crossing - left_crossing)
        lower_bound = width
        status = "complete"
    elif left_crossing is None and right_crossing is not None:
        width = None
        lower_bound = abs(right_crossing - x[0])
        status = "left_censored"
    elif left_crossing is not None and right_crossing is None:
        width = None
        lower_bound = abs(x[-1] - left_crossing)
        status = "right_censored"
    else:
        width = None
        lower_bound = abs(x[-1] - x[0])
        status = "both_censored"
    return {
        "status": status,
        "width": None if width is None else float(width),
        "lower_bound": float(lower_bound),
        "left_crossing": left_crossing,
        "right_crossing": right_crossing,
        "left_endpoint_fraction_of_peak": float(amplitude[0] / amplitude[peak_index]),
        "right_endpoint_fraction_of_peak": float(amplitude[-1] / amplitude[peak_index]),
    }


def continuous_threshold_width(x: np.ndarray, amplitude: np.ndarray, fraction: float) -> float:
    result = threshold_region(x, amplitude, fraction)
    return float("nan") if result["width"] is None else float(result["width"])


def refined_peak_coordinate(x: np.ndarray, amplitude: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    amplitude = np.asarray(amplitude, dtype=np.float64)
    order = np.argsort(x)
    x = x[order]
    amplitude = amplitude[order]
    peak_index = int(np.argmax(amplitude))
    if peak_index in (0, amplitude.size - 1):
        return float(x[peak_index])
    coefficients = np.polyfit(x[peak_index - 1 : peak_index + 2], amplitude[peak_index - 1 : peak_index + 2], 2)
    if coefficients[0] >= 0:
        return float(x[peak_index])
    vertex = -coefficients[1] / (2.0 * coefficients[0])
    if x[peak_index - 1] <= vertex <= x[peak_index + 1]:
        return float(vertex)
    return float(x[peak_index])


def read_qcw_scan(
    scan: h5py.Group,
    frequency_hz: float,
    sensitivity_v_per_pa: float,
    sensitivity_phase_rad: float,
    chunk_points: int,
) -> dict[str, np.ndarray | float | int]:
    waveforms = scan["waveformData"]
    coordinates_m = np.asarray(scan["scanCoordinates"][0], dtype=np.float64).T
    sample_period_s = float(np.asarray(scan["waveformSamplePeriod"][()]).reshape(-1)[0])
    full_samples = int(waveforms.shape[1])
    cycle_slice = integer_cycle_slice(full_samples, sample_period_s, frequency_hz)
    kept_samples = cycle_slice.stop - cycle_slice.start
    projector = carrier_projector(kept_samples, sample_period_s, frequency_hz)
    total_points = int(waveforms.shape[2])
    amplitude_v = np.empty(total_points, dtype=np.float64)
    pressure_phase_rad = np.empty(total_points, dtype=np.float64)
    dc_offset_v = np.empty(total_points, dtype=np.float64)

    for start in range(0, total_points, chunk_points):
        stop = min(total_points, start + chunk_points)
        chunk = np.asarray(waveforms[0, cycle_slice, start:stop], dtype=np.float64).T
        chunk_amplitude, chunk_phase, chunk_dc = fit_carrier(chunk, projector)
        amplitude_v[start:stop] = chunk_amplitude
        pressure_phase_rad[start:stop] = np.angle(np.exp(1j * (chunk_phase - sensitivity_phase_rad)))
        dc_offset_v[start:stop] = chunk_dc

    return {
        "coordinates_m": coordinates_m,
        "pressure_amplitude_pa": amplitude_v / sensitivity_v_per_pa,
        "pressure_phase_rad": pressure_phase_rad,
        "carrier_amplitude_v": amplitude_v,
        "dc_offset_v": dc_offset_v,
        "sample_period_s": sample_period_s,
        "full_samples": full_samples,
        "kept_samples": kept_samples,
        "kept_cycles": kept_samples * sample_period_s * frequency_hz,
    }


def transverse_metrics(scan: dict[str, np.ndarray | float | int], spacing_m: tuple[float, float]) -> dict[str, object]:
    coordinates = np.asarray(scan["coordinates_m"])
    pressure = np.asarray(scan["pressure_amplitude_pa"])
    peak_index = int(np.argmax(pressure))
    peak_coordinate = coordinates[peak_index]
    dx, dy = spacing_m
    x_line_mask = np.abs(coordinates[:, 1] - peak_coordinate[1]) <= 0.51 * dy
    y_line_mask = np.abs(coordinates[:, 0] - peak_coordinate[0]) <= 0.51 * dx
    threshold = pressure[peak_index] * MINUS_6DB_AMPLITUDE
    return {
        "peak_index": peak_index,
        "peak_pressure_pa": float(pressure[peak_index]),
        "peak_pressure_mpa": float(pressure[peak_index] / 1e6),
        "peak_coordinate_native_m": peak_coordinate.tolist(),
        "peak_coordinate_native_mm": (peak_coordinate * 1e3).tolist(),
        "minus6db_x_width_mm": float(continuous_threshold_width(coordinates[x_line_mask, 0], pressure[x_line_mask], MINUS_6DB_AMPLITUDE) * 1e3),
        "minus6db_y_width_mm": float(continuous_threshold_width(coordinates[y_line_mask, 1], pressure[y_line_mask], MINUS_6DB_AMPLITUDE) * 1e3),
        "minus6db_area_mm2": float(np.count_nonzero(pressure >= threshold) * dx * dy * 1e6),
        "peak_distance_from_scan_edge_mm": float(
            min(
                peak_coordinate[0] - coordinates[:, 0].min(),
                coordinates[:, 0].max() - peak_coordinate[0],
                peak_coordinate[1] - coordinates[:, 1].min(),
                coordinates[:, 1].max() - peak_coordinate[1],
            )
            * 1e3
        ),
    }


def axial_metrics(scan: dict[str, np.ndarray | float | int]) -> dict[str, object]:
    coordinates = np.asarray(scan["coordinates_m"])
    pressure = np.asarray(scan["pressure_amplitude_pa"])
    z = coordinates[:, 2]
    peak_index = int(np.argmax(pressure))
    refined_z = refined_peak_coordinate(z, pressure)
    minus6db = threshold_region(z, pressure, MINUS_6DB_AMPLITUDE)
    return {
        "peak_index": peak_index,
        "peak_pressure_pa": float(pressure[peak_index]),
        "peak_pressure_mpa": float(pressure[peak_index] / 1e6),
        "peak_coordinate_native_m": coordinates[peak_index].tolist(),
        "peak_coordinate_native_mm": (coordinates[peak_index] * 1e3).tolist(),
        "refined_peak_z_native_mm": float(refined_z * 1e3),
        "refined_peak_distance_from_transducer_mm": float(abs(refined_z) * 1e3),
        "minus6db_axial_width_mm": None if minus6db["width"] is None else float(minus6db["width"] * 1e3),
        "minus6db_axial_width_status": minus6db["status"],
        "minus6db_axial_width_lower_bound_mm": float(minus6db["lower_bound"] * 1e3),
        "minus6db_endpoint_fractions_of_peak": {
            "far_native_z_min": minus6db["left_endpoint_fraction_of_peak"],
            "near_native_z_max": minus6db["right_endpoint_fraction_of_peak"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--chunk-points", type=int, default=64)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with h5py.File(args.input, "r") as h5:
        frequency_hz = float(np.asarray(h5["data/dataset3/drivingConditions/drivingFrequency"][()]).reshape(-1)[0])
        calibration = interpolate_calibration(h5["sensor/sensorProperties/frequencyResponse"][()], frequency_hz)
        transverse = read_qcw_scan(
            h5["data/dataset3/scanData"], frequency_hz,
            calibration["sensitivity_v_per_pa"], calibration["phase_rad"], args.chunk_points,
        )
        axial = read_qcw_scan(
            h5["data/dataset4/scanData"], frequency_hz,
            calibration["sensitivity_v_per_pa"], calibration["phase_rad"], args.chunk_points,
        )
        spacing = tuple(float(value) for value in np.asarray(h5["data/dataset3/scanData/scanPointSpacing"][()]).reshape(-1))

    transverse_summary = transverse_metrics(transverse, spacing)
    axial_summary = axial_metrics(axial)
    plane_z = float(np.asarray(transverse["coordinates_m"])[0, 2])
    axial_coordinates = np.asarray(axial["coordinates_m"])
    axial_pressure = np.asarray(axial["pressure_amplitude_pa"])
    order = np.argsort(axial_coordinates[:, 2])
    axial_at_plane = float(np.interp(plane_z, axial_coordinates[order, 2], axial_pressure[order]))
    cross_scan_difference = 100.0 * (transverse_summary["peak_pressure_pa"] - axial_at_plane) / axial_at_plane

    input_sha256 = sha256_file(args.input)
    if input_sha256 != EXPECTED_INPUT_SHA256:
        raise ValueError(f"input SHA-256 drift: {input_sha256}")
    for label, scan in (("transverse", transverse), ("axial", axial)):
        pressure = np.asarray(scan["pressure_amplitude_pa"])
        if not np.isfinite(pressure).all() or np.any(pressure < 0):
            raise ValueError(f"{label} pressure amplitude failed finite/non-negative validation")

    report = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "scope": "UCL H115 270 kHz qCW free-field measurement summary; no solver run",
        "input": {
            "path": str(args.input),
            "size_bytes": args.input.stat().st_size,
            "sha256": input_sha256,
            "sha256_matches_intake": True,
            "doi": "10.5522/04/28025240.v2",
            "license": "CC BY 4.0",
        },
        "method": {
            "paper_doi": "10.1088/1361-6560/ada19d",
            "measurement_datasets": ["dataset3 transverse qCW", "dataset4 axial qCW"],
            "pressure_definition": "least-squares peak amplitude of the 270 kHz carrier divided by the interpolated complex hydrophone sensitivity magnitude",
            "phase_definition": "fitted voltage carrier phase minus interpolated hydrophone sensitivity phase",
            "window": "centred integer-cycle crop; no taper needed for carrier least-squares fit",
            "chunk_points": args.chunk_points,
            "excluded": "PW datasets 1 and 2 are not converted by this tool because reproducing their broadband Tukey/band-pass deconvolution requires a separately frozen filter contract",
        },
        "coordinate_convention": {
            "native_units": "m",
            "native_z_sign": "measurement locations are negative z; reported distance from transducer is abs(z)",
            "origin": "centre of transducer face, set by time of flight",
        },
        "calibration": {
            **calibration,
            "schema_rows": ["frequency_Hz", "sensitivity_V_per_Pa", "amplitude_uncertainty_percent", "phase_rad", "phase_uncertainty_percent"],
            "uncertainty_interpretation": "the 9% calibration amplitude uncertainty is reported alone; other acquisition/model uncertainties are not available and are not combined",
        },
        "transverse_qcw": {
            **transverse_summary,
            "scan_plane_z_native_mm": plane_z * 1e3,
            "sample_period_s": transverse["sample_period_s"],
            "full_samples": transverse["full_samples"],
            "kept_samples": transverse["kept_samples"],
            "kept_cycles": transverse["kept_cycles"],
        },
        "axial_qcw": {
            **axial_summary,
            "sample_period_s": axial["sample_period_s"],
            "full_samples": axial["full_samples"],
            "kept_samples": axial["kept_samples"],
            "kept_cycles": axial["kept_cycles"],
        },
        "cross_scan_check": {
            "axial_profile_pressure_at_transverse_plane_pa": axial_at_plane,
            "transverse_peak_minus_axial_interpolation_percent": cross_scan_difference,
            "interpretation": "independent scans were acquired on consecutive days; this is a consistency observation, not an acceptance gate",
        },
        "artifact_checks": {
            "input_integrity": "pass",
            "all_pressure_amplitudes_finite_and_nonnegative": "pass",
            "transverse_peak_interior": "pass" if transverse_summary["peak_distance_from_scan_edge_mm"] > max(spacing) * 1e3 else "fail",
            "axial_minus6db_width": axial_summary["minus6db_axial_width_status"],
        },
        "claim_boundary": "engineering measurement evidence only; it does not validate the current Case079 source, skull model, thermal safety, or clinical performance",
    }

    np.savez_compressed(
        args.output_dir / "qcw_transverse_map.npz",
        coordinates_m=np.asarray(transverse["coordinates_m"]),
        pressure_amplitude_pa=np.asarray(transverse["pressure_amplitude_pa"]),
        pressure_phase_rad=np.asarray(transverse["pressure_phase_rad"]),
        normalized_amplitude=np.asarray(transverse["pressure_amplitude_pa"]) / transverse_summary["peak_pressure_pa"],
    )
    np.savez_compressed(
        args.output_dir / "qcw_axial_profile.npz",
        coordinates_m=np.asarray(axial["coordinates_m"]),
        pressure_amplitude_pa=np.asarray(axial["pressure_amplitude_pa"]),
        pressure_phase_rad=np.asarray(axial["pressure_phase_rad"]),
        normalized_amplitude=np.asarray(axial["pressure_amplitude_pa"]) / axial_summary["peak_pressure_pa"],
    )
    (args.output_dir / "summary.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    axial_width_text = (
        f'{axial_summary["minus6db_axial_width_mm"]:.3f} mm'
        if axial_summary["minus6db_axial_width_mm"] is not None
        else f'censored; > {axial_summary["minus6db_axial_width_lower_bound_mm"]:.3f} mm within the measured domain'
    )
    report_md = f"""# UCL H115 270 kHz qCW free-field summary

- Calibrated axial peak: **{axial_summary['peak_pressure_mpa']:.4f} MPa** at **{axial_summary['refined_peak_distance_from_transducer_mm']:.3f} mm** from the transducer face.
- Transverse-plane peak at {abs(plane_z) * 1e3:.3f} mm: **{transverse_summary['peak_pressure_mpa']:.4f} MPa**, located at x={transverse_summary['peak_coordinate_native_mm'][0]:.3f} mm, y={transverse_summary['peak_coordinate_native_mm'][1]:.3f} mm.
- Transverse -6 dB widths at the hologram plane: x={transverse_summary['minus6db_x_width_mm']:.3f} mm, y={transverse_summary['minus6db_y_width_mm']:.3f} mm. These are not focal widths.
- Axial -6 dB width: **{axial_width_text}**; the far endpoint remains above threshold.
- Independent transverse-vs-axial pressure agreement at the scan plane: **{cross_scan_difference:+.4f}%** (descriptive, not preregistered acceptance evidence).
- Hydrophone sensitivity at 270 kHz: {calibration['sensitivity_v_per_pa']:.4e} V/Pa with {calibration['amplitude_uncertainty_percent']:.1f}% stated amplitude uncertainty.

This is engineering free-field measurement evidence. PW broadband pressure, Case079 source matching, skull propagation, thermal safety and clinical claims remain outside scope.
"""
    (args.output_dir / "report.md").write_text(report_md, encoding="utf-8")
    print(json.dumps({"status": "completed", "output": str(args.output_dir / "summary.json")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
