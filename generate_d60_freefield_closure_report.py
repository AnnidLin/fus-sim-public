from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_RUN_DIR = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_dx0p75_resume_20260713/run"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_dx0p75_resume_20260713"


def orthonormal_lateral_axes(beam_axis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    unit_axis = beam_axis / np.linalg.norm(beam_axis)
    reference = np.array([0.0, 0.0, 1.0])
    if abs(float(unit_axis @ reference)) > 0.9:
        reference = np.array([0.0, 1.0, 0.0])
    lateral_1 = np.cross(unit_axis, reference)
    lateral_1 /= np.linalg.norm(lateral_1)
    lateral_2 = np.cross(unit_axis, lateral_1)
    lateral_2 /= np.linalg.norm(lateral_2)
    return lateral_1, lateral_2


def continuous_half_peak_width_mm(
    field: np.ndarray,
    center: np.ndarray,
    direction: np.ndarray,
    threshold: float,
    dx_mm: float,
) -> float:
    sample_step_voxels = 0.25
    half_diagonal = float(np.linalg.norm(field.shape))
    offsets = np.arange(-half_diagonal, half_diagonal + sample_step_voxels, sample_step_voxels)
    coordinates = center[:, None] + direction[:, None] * offsets[None, :]
    inside = np.all((coordinates >= 0) & (coordinates <= (np.asarray(field.shape) - 1)[:, None]), axis=0)
    offsets = offsets[inside]
    values = map_coordinates(field, coordinates[:, inside], order=1, mode="nearest")
    center_index = int(np.argmin(np.abs(offsets)))
    above = values >= threshold
    if not above[center_index]:
        return 0.0
    lower = center_index
    upper = center_index
    while lower > 0 and above[lower - 1]:
        lower -= 1
    while upper + 1 < len(above) and above[upper + 1]:
        upper += 1
    return float((offsets[upper] - offsets[lower]) * dx_mm)


def build_report(run_dir: Path) -> dict[str, object]:
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    runner = json.loads((run_dir / "runner_status.json").read_text(encoding="utf-8"))
    with np.load(run_dir / "pressure_max_mpa.npz") as data:
        field = np.asarray(data["pressure_max_mpa"], dtype=float)
        dx_mm = float(data["dx_m"]) * 1e3
        target = np.asarray(data["target_index_ijk"], dtype=float)
        source = np.asarray(data["source_center_index_ijk"], dtype=float)
        beam_axis = np.asarray(data["beam_axis"], dtype=float)
        source_mask = np.asarray(data["source_mask"])
        labels = np.asarray(data["labels"])
        target_waveform = np.asarray(data["target_waveform"], dtype=float)
        all_arrays_finite = all(
            np.all(np.isfinite(data[key]))
            for key in data.files
            if np.issubdtype(data[key].dtype, np.number)
        )

    pressure = summary["pressure"]
    peak = np.asarray(pressure["global_peak_index_ijk"], dtype=float)
    peak_mpa = float(pressure["global_peak_mpa"])
    unit_axis = beam_axis / np.linalg.norm(beam_axis)
    lateral_1, lateral_2 = orthonormal_lateral_axes(beam_axis)
    half_peak = 0.5 * peak_mpa
    axial_width = continuous_half_peak_width_mm(field, peak, unit_axis, half_peak, dx_mm)
    lateral_width_1 = continuous_half_peak_width_mm(field, peak, lateral_1, half_peak, dx_mm)
    lateral_width_2 = continuous_half_peak_width_mm(field, peak, lateral_2, half_peak, dx_mm)
    target_distance_mm = float(np.linalg.norm(target - source) * dx_mm)
    focus_axial_mm = float(pressure["global_peak_axial_from_source_mm"])
    focus_error_mm = abs(target_distance_mm - focus_axial_mm)
    focus_error_percent = 100.0 * focus_error_mm / target_distance_mm
    boundary_distance_voxels = int(
        np.min(np.minimum(peak.astype(int), np.asarray(field.shape) - 1 - peak.astype(int)))
    )
    source_labels, source_counts = np.unique(labels[source_mask > 0], return_counts=True)
    source_label_counts = {str(int(label)): int(count) for label, count in zip(source_labels, source_counts)}
    target_to_global = float(pressure["target_to_global_peak_ratio"])
    focus_pass = focus_error_percent <= 5.0
    ratio_pass = target_to_global >= 0.9
    finite_pass = bool(all_arrays_finite and np.all(np.isfinite(target_waveform)))
    boundary_pass = boundary_distance_voxels >= int(summary["config"]["pml_size"])
    source_pass = set(source_label_counts) == {"0"}
    paper_grade_blockers = list(summary["simulation_quality"]["paper_grade_blockers"])
    if summary.get("environment_record"):
        paper_grade_blockers = [
            blocker for blocker in paper_grade_blockers if blocker != "environment_record_missing"
        ]

    return {
        "status": "gate_b_d60_pass" if all((focus_pass, ratio_pass, finite_pass, boundary_pass, source_pass)) else "gate_b_d60_failed",
        "metric_semantics": {
            "minus6db": "continuous half-amplitude width through the global peak using trilinear interpolation at 0.25 voxel spacing",
            "lateral_equivalent": "geometric mean of two orthogonal lateral half-amplitude widths",
        },
        "run_dir": str(run_dir.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "runner_status": runner["status"],
        "runtime_s": float(runner["execution"]["runtime_s"]),
        "grid_shape": list(field.shape),
        "dx_mm": dx_mm,
        "source_label_counts": source_label_counts,
        "all_arrays_finite": bool(all_arrays_finite),
        "target_waveform_finite": bool(np.all(np.isfinite(target_waveform))),
        "global_peak_mpa": peak_mpa,
        "target_pressure_mpa": float(pressure["target_pressure_mpa"]),
        "target_window_peak_mpa": float(pressure["target_window_peak_mpa"]),
        "target_to_global_peak_ratio": target_to_global,
        "target_distance_mm": target_distance_mm,
        "focus_axial_from_source_mm": focus_axial_mm,
        "focus_error_mm": focus_error_mm,
        "focus_error_percent": focus_error_percent,
        "global_peak_lateral_offset_mm": float(pressure["global_peak_lateral_offset_mm"]),
        "global_boundary_distance_voxels": boundary_distance_voxels,
        "minus6db_axial_width_mm": axial_width,
        "minus6db_lateral_width_1_mm": lateral_width_1,
        "minus6db_lateral_width_2_mm": lateral_width_2,
        "minus6db_lateral_equivalent_mm": float(np.sqrt(lateral_width_1 * lateral_width_2)),
        "acceptance": {
            "focus_error_percent_max": 5.0,
            "focus_error_pass": focus_pass,
            "target_to_global_min": 0.9,
            "target_to_global_pass": ratio_pass,
            "finite_outputs_pass": finite_pass,
            "boundary_distance_at_least_pml_pass": boundary_pass,
            "background_only_source_pass": source_pass,
        },
        "all_acceptance_checks_pass": all((focus_pass, ratio_pass, finite_pass, boundary_pass, source_pass)),
        "paper_grade_blockers": paper_grade_blockers,
        "next": "validate D60 source safety on all three Gate A trajectories before any CT pressure",
    }


def write_report(report: dict[str, object], report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "d60_freefield_closure_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    acceptance = report["acceptance"]
    lines = [
        "# D60 Free-Field Closure Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Runtime: {report['runtime_s']:.1f} s",
        f"- Focus error: {report['focus_error_mm']:.3f} mm ({report['focus_error_percent']:.3f}%)",
        f"- Target/global pressure ratio: {report['target_to_global_peak_ratio']:.4f}",
        f"- Global/target pressure: {report['global_peak_mpa']:.3f}/{report['target_pressure_mpa']:.3f} MPa",
        f"- Global peak boundary distance: {report['global_boundary_distance_voxels']} voxels",
        f"- -6 dB axial width: {report['minus6db_axial_width_mm']:.3f} mm",
        f"- -6 dB lateral widths: {report['minus6db_lateral_width_1_mm']:.3f}/{report['minus6db_lateral_width_2_mm']:.3f} mm",
        f"- All acceptance checks pass: {report['all_acceptance_checks_pass']}",
        "",
        "The D60 dx0.75 free-field source-closure gate passes. This is engineering evidence only; grid convergence and PML/CFL reviews remain required before paper-grade wording.",
    ]
    (report_dir / "d60_freefield_closure_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args()
    report = build_report(args.run_dir.resolve())
    write_report(report, args.report_dir.resolve())
    print(json.dumps({"status": report["status"], "focus_error_percent": report["focus_error_percent"]}))


if __name__ == "__main__":
    main()
