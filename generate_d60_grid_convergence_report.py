from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates

from generate_d60_freefield_closure_report import (
    continuous_half_peak_width_mm,
    orthonormal_lateral_axes,
)


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DX075 = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_dx0p75_resume_20260713/run"
DEFAULT_DX05 = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_dx0p5_fieldonly_20260713/run"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_grid_convergence_20260713"


def percent_change(coarse: float, fine: float) -> float:
    return 100.0 * abs(coarse - fine) / abs(fine)


def field_metrics(run_dir: Path) -> dict[str, object]:
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    runner = json.loads((run_dir / "runner_status.json").read_text(encoding="utf-8"))
    with np.load(run_dir / "pressure_max_mpa.npz") as data:
        field = np.asarray(data["pressure_max_mpa"], dtype=float)
        dx_mm = float(data["dx_m"]) * 1e3
        source = np.asarray(data["source_center_index_ijk"], dtype=float)
        target = np.asarray(data["target_index_ijk"], dtype=float)
        beam_axis = np.asarray(data["beam_axis"], dtype=float)
        source_mask = np.asarray(data["source_mask"])
        labels = np.asarray(data["labels"])
        waveform_recorded = "target_waveform" in data.files
        waveform_finite = bool(np.all(np.isfinite(data["target_waveform"]))) if waveform_recorded else None
        arrays_finite = all(
            np.all(np.isfinite(data[key]))
            for key in data.files
            if np.issubdtype(data[key].dtype, np.number)
        )

    pressure = summary["pressure"]
    peak = np.asarray(pressure["global_peak_index_ijk"], dtype=float)
    peak_mpa = float(pressure["global_peak_mpa"])
    unit_axis = beam_axis / np.linalg.norm(beam_axis)
    subvoxel_offsets = np.linspace(-2.0, 2.0, 801)
    subvoxel_values = map_coordinates(
        field,
        peak[:, None] + unit_axis[:, None] * subvoxel_offsets[None, :],
        order=3,
        mode="nearest",
    )
    subvoxel_offset = float(subvoxel_offsets[int(np.argmax(subvoxel_values))])
    refined_peak = peak + unit_axis * subvoxel_offset
    lateral_1, lateral_2 = orthonormal_lateral_axes(beam_axis)
    threshold = 0.5 * peak_mpa
    axial_width = continuous_half_peak_width_mm(field, peak, unit_axis, threshold, dx_mm)
    lateral_width_1 = continuous_half_peak_width_mm(field, peak, lateral_1, threshold, dx_mm)
    lateral_width_2 = continuous_half_peak_width_mm(field, peak, lateral_2, threshold, dx_mm)
    target_distance_mm = float(np.linalg.norm(target - source) * dx_mm)
    focus_axial_mm = float(pressure["global_peak_axial_from_source_mm"])
    focus_error_mm = abs(target_distance_mm - focus_axial_mm)
    peak_relative_to_source_mm = (peak - source) * dx_mm
    refined_peak_relative_to_source_mm = (refined_peak - source) * dx_mm
    refined_focus_axial_mm = float((refined_peak - source) @ unit_axis * dx_mm)
    refined_focus_error_mm = abs(target_distance_mm - refined_focus_axial_mm)
    boundary_distance_voxels = int(
        np.min(np.minimum(peak.astype(int), np.asarray(field.shape) - 1 - peak.astype(int)))
    )
    source_labels, source_counts = np.unique(labels[source_mask > 0], return_counts=True)
    return {
        "run_dir": str(run_dir.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "runner_status": runner["status"],
        "runtime_s": float(runner["execution"]["runtime_s"]),
        "grid_shape": list(field.shape),
        "dx_mm": dx_mm,
        "global_peak_mpa": peak_mpa,
        "target_pressure_mpa": float(pressure["target_pressure_mpa"]),
        "target_to_global_peak_ratio": float(pressure["target_to_global_peak_ratio"]),
        "target_distance_mm": target_distance_mm,
        "focus_axial_from_source_mm": focus_axial_mm,
        "focus_error_mm": focus_error_mm,
        "focus_error_percent": 100.0 * focus_error_mm / target_distance_mm,
        "peak_relative_to_source_mm": peak_relative_to_source_mm.tolist(),
        "subvoxel_peak_offset_voxels": subvoxel_offset,
        "subvoxel_peak_mpa": float(np.max(subvoxel_values)),
        "refined_peak_relative_to_source_mm": refined_peak_relative_to_source_mm.tolist(),
        "refined_focus_axial_from_source_mm": refined_focus_axial_mm,
        "refined_focus_error_mm": refined_focus_error_mm,
        "refined_focus_error_percent": 100.0 * refined_focus_error_mm / target_distance_mm,
        "global_peak_lateral_offset_mm": float(pressure["global_peak_lateral_offset_mm"]),
        "global_boundary_distance_voxels": boundary_distance_voxels,
        "minus6db_axial_width_mm": axial_width,
        "minus6db_lateral_width_1_mm": lateral_width_1,
        "minus6db_lateral_width_2_mm": lateral_width_2,
        "minus6db_lateral_equivalent_mm": float(np.sqrt(lateral_width_1 * lateral_width_2)),
        "source_label_counts": {
            str(int(label)): int(count) for label, count in zip(source_labels, source_counts)
        },
        "all_arrays_finite": bool(arrays_finite),
        "target_waveform_recorded": waveform_recorded,
        "target_waveform_finite": waveform_finite,
    }


def build_report(dx075_dir: Path, dx05_dir: Path) -> dict[str, object]:
    coarse = field_metrics(dx075_dir)
    fine = field_metrics(dx05_dir)
    peak_change = percent_change(float(coarse["global_peak_mpa"]), float(fine["global_peak_mpa"]))
    lateral_change = percent_change(
        float(coarse["minus6db_lateral_equivalent_mm"]),
        float(fine["minus6db_lateral_equivalent_mm"]),
    )
    axial_change = percent_change(
        float(coarse["minus6db_axial_width_mm"]),
        float(fine["minus6db_axial_width_mm"]),
    )
    focal_displacement = float(
        np.linalg.norm(
            np.asarray(coarse["refined_peak_relative_to_source_mm"])
            - np.asarray(fine["refined_peak_relative_to_source_mm"])
        )
    )
    checks = {
        "dx075_focus_error_pass": float(coarse["refined_focus_error_percent"]) <= 5.0,
        "dx05_focus_error_pass": float(fine["refined_focus_error_percent"]) <= 5.0,
        "global_peak_change_pass": peak_change <= 5.0,
        "lateral_width_change_pass": lateral_change <= 10.0,
        "focal_displacement_pass": focal_displacement <= 1.0,
        "target_to_global_pass": min(
            float(coarse["target_to_global_peak_ratio"]), float(fine["target_to_global_peak_ratio"])
        ) >= 0.9,
        "finite_fields_pass": bool(coarse["all_arrays_finite"] and fine["all_arrays_finite"]),
        "boundary_distance_pass": bool(
            coarse["global_boundary_distance_voxels"] >= 12
            and fine["global_boundary_distance_voxels"] >= 12
        ),
    }
    field_checks_pass = all(checks.values())
    waveform_complete = bool(coarse["target_waveform_recorded"] and fine["target_waveform_recorded"])
    if field_checks_pass and waveform_complete:
        status = "gate_b_dx075_dx05_pass"
    elif field_checks_pass:
        status = "field_metrics_pass_dx0p5_waveform_gap"
    else:
        status = "gate_b_dx075_dx05_failed"
    return {
        "status": status,
        "metric_semantics": {
            "percent_change_reference": "absolute change divided by dx0.5 value",
            "focal_displacement": "Euclidean displacement of the discrete global peak relative to the source center",
            "minus6db": "continuous half-amplitude width through the global peak using trilinear interpolation at 0.25 voxel spacing",
        },
        "dx0p75": coarse,
        "dx0p5": fine,
        "comparison": {
            "global_peak_change_percent": peak_change,
            "lateral_width_change_percent": lateral_change,
            "axial_width_change_percent": axial_change,
            "focal_displacement_mm": focal_displacement,
        },
        "acceptance": checks,
        "field_checks_pass": field_checks_pass,
        "waveform_complete": waveform_complete,
        "remaining_gaps": [
            gap
            for gap, present in (
                ("dx0.5 target waveform not recorded", fine["target_waveform_recorded"]),
                ("dx0.375 convergence not run", False),
                ("PML16 sensitivity not run", False),
                ("CFL0.1 sensitivity not run", False),
            )
            if not present
        ],
        "ct_pressure_authorized": False,
    }


def write_report(report: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "d60_grid_convergence_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    coarse = report["dx0p75"]
    fine = report["dx0p5"]
    comparison = report["comparison"]
    lines = [
        "# D60 dx0.75 vs dx0.5 Free-Field Comparison",
        "",
        f"- Status: `{report['status']}`",
        f"- Global peak: {coarse['global_peak_mpa']:.4f} vs {fine['global_peak_mpa']:.4f} MPa; change {comparison['global_peak_change_percent']:.3f}%",
        f"- Refined focus error: {coarse['refined_focus_error_percent']:.3f}% vs {fine['refined_focus_error_percent']:.3f}%",
        f"- Focal displacement: {comparison['focal_displacement_mm']:.3f} mm",
        f"- Lateral -6 dB equivalent width: {coarse['minus6db_lateral_equivalent_mm']:.3f} vs {fine['minus6db_lateral_equivalent_mm']:.3f} mm; change {comparison['lateral_width_change_percent']:.3f}%",
        f"- Axial -6 dB width: {coarse['minus6db_axial_width_mm']:.3f} vs {fine['minus6db_axial_width_mm']:.3f} mm; change {comparison['axial_width_change_percent']:.3f}%",
        f"- Field checks pass: {report['field_checks_pass']}",
        f"- Waveform complete: {report['waveform_complete']}",
        "",
        "CT pressure remains unauthorized. A failed absolute focal-error gate or missing dx0.5 waveform must not be described as Gate B closure.",
    ]
    (output_dir / "d60_grid_convergence_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dx0p75-dir", type=Path, default=DEFAULT_DX075)
    parser.add_argument("--dx0p5-dir", type=Path, default=DEFAULT_DX05)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report(args.dx0p75_dir.resolve(), args.dx0p5_dir.resolve())
    write_report(report, args.output_dir.resolve())
    print(json.dumps({"status": report["status"], "field_checks_pass": report["field_checks_pass"]}))


if __name__ == "__main__":
    main()
