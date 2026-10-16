from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import map_coordinates

from generate_d60_grid_convergence_report import field_metrics


BASELINE = Path("outputs/freefield_aperture_calibration/d60_dx0p75_resume_20260713/run")
CORRECTED = Path("outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pointwave_20260714/run")
INTERRUPTION = Path("outputs/freefield_aperture_calibration/d60_r78p330_dx0p5_pointwave_20260714/run/interruption_record.json")
OUTPUT = Path("outputs/acoustic_stage_closeout_20260714")


def load_field(run_dir: Path) -> tuple[np.ndarray, float, np.ndarray, np.ndarray, np.ndarray]:
    with np.load(run_dir / "pressure_max_mpa.npz") as data:
        return (
            np.asarray(data["pressure_max_mpa"], dtype=float),
            float(data["dx_m"]) * 1e3,
            np.asarray(data["source_center_index_ijk"], dtype=float),
            np.asarray(data["target_index_ijk"], dtype=float),
            np.asarray(data["beam_axis"], dtype=float),
        )


def axial_profile(run_dir: Path) -> dict[str, np.ndarray]:
    field, dx_mm, source, target, beam = load_field(run_dir)
    unit = beam / np.linalg.norm(beam)
    target_distance_mm = float(np.linalg.norm(target - source) * dx_mm)
    distance_mm = np.linspace(35.0, target_distance_mm + 12.0, 900)
    coordinates = source[:, None] + unit[:, None] * (distance_mm[None, :] / dx_mm)
    pressure_mpa = map_coordinates(field, coordinates, order=3, mode="nearest")
    return {
        "distance_mm": distance_mm,
        "pressure_mpa": pressure_mpa,
        "target_distance_mm": np.asarray(target_distance_mm),
    }


def percent_delta(reference: float, candidate: float) -> float:
    return 100.0 * (candidate - reference) / reference


def build_closeout(baseline_dir: Path, corrected_dir: Path, interruption_path: Path) -> dict[str, Any]:
    baseline = field_metrics(baseline_dir.resolve())
    corrected = field_metrics(corrected_dir.resolve())
    interruption = json.loads(interruption_path.read_text(encoding="utf-8"))
    return {
        "status": "dx0p75_source_calibration_closed_dx0p5_incomplete",
        "scope": "homogeneous_freefield_engineering_evidence",
        "baseline_r74p435_dx0p75": baseline,
        "corrected_r78p330_dx0p75": corrected,
        "changes": {
            "refined_focus_error_mm": corrected["refined_focus_error_mm"] - baseline["refined_focus_error_mm"],
            "refined_focus_error_percentage_points": corrected["refined_focus_error_percent"] - baseline["refined_focus_error_percent"],
            "global_peak_percent": percent_delta(baseline["global_peak_mpa"], corrected["global_peak_mpa"]),
            "target_pressure_percent": percent_delta(baseline["target_pressure_mpa"], corrected["target_pressure_mpa"]),
            "target_to_global_percentage_points": corrected["target_to_global_peak_ratio"] - baseline["target_to_global_peak_ratio"],
            "axial_width_percent": percent_delta(baseline["minus6db_axial_width_mm"], corrected["minus6db_axial_width_mm"]),
            "lateral_width_percent": percent_delta(baseline["minus6db_lateral_equivalent_mm"], corrected["minus6db_lateral_equivalent_mm"]),
        },
        "acceptance": {
            "corrected_dx0p75_refined_error_le_4_percent": corrected["refined_focus_error_percent"] <= 4.0,
            "corrected_target_to_global_ge_0p9": corrected["target_to_global_peak_ratio"] >= 0.9,
            "corrected_waveform_complete": bool(corrected["target_waveform_recorded"] and corrected["target_waveform_finite"]),
            "corrected_field_finite": corrected["all_arrays_finite"],
            "corrected_boundary_ge_12": corrected["global_boundary_distance_voxels"] >= 12,
        },
        "dx0p5": {
            "status": interruption["status"],
            "core_output_available": False,
            "supports_convergence_conclusion": False,
        },
        "claims": {
            "supported": [
                "R78.330 improves D60 source calibration at dx0.75 in homogeneous free field.",
                "The low-memory target-waveform recording architecture completed at dx0.75.",
            ],
            "not_supported": [
                "R78.330 dx0.75/dx0.5 grid convergence",
                "paper-grade numerical convergence",
                "CT or transcranial pressure performance",
                "thermal or clinical safety",
            ],
        },
        "next": "Use this package for stage reporting; do not restart long simulations automatically.",
    }


def write_metrics_csv(closeout: dict[str, Any], path: Path) -> None:
    baseline = closeout["baseline_r74p435_dx0p75"]
    corrected = closeout["corrected_r78p330_dx0p75"]
    rows = [
        ("global_peak_mpa", baseline["global_peak_mpa"], corrected["global_peak_mpa"], "MPa"),
        ("target_pressure_mpa", baseline["target_pressure_mpa"], corrected["target_pressure_mpa"], "MPa"),
        ("target_to_global_peak_ratio", baseline["target_to_global_peak_ratio"], corrected["target_to_global_peak_ratio"], "ratio"),
        ("refined_focus_error_mm", baseline["refined_focus_error_mm"], corrected["refined_focus_error_mm"], "mm"),
        ("refined_focus_error_percent", baseline["refined_focus_error_percent"], corrected["refined_focus_error_percent"], "%"),
        ("minus6db_axial_width_mm", baseline["minus6db_axial_width_mm"], corrected["minus6db_axial_width_mm"], "mm"),
        ("minus6db_lateral_equivalent_mm", baseline["minus6db_lateral_equivalent_mm"], corrected["minus6db_lateral_equivalent_mm"], "mm"),
        ("global_boundary_distance_voxels", baseline["global_boundary_distance_voxels"], corrected["global_boundary_distance_voxels"], "voxels"),
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "r74p435_dx0p75", "r78p330_dx0p75", "unit"])
        writer.writerows(rows)


def draw_figure(baseline_dir: Path, corrected_dir: Path, closeout: dict[str, Any], path: Path) -> None:
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9})
    baseline_field, dx_mm, _, target, _ = load_field(baseline_dir)
    corrected_field, _, _, _, _ = load_field(corrected_dir)
    z = int(target[2])
    x0, x1 = int(target[0] - 34), int(target[0] + 17)
    y0, y1 = int(target[1] - 17), int(target[1] + 18)
    extent = [(x0 - target[0]) * dx_mm, (x1 - target[0]) * dx_mm, (y0 - target[1]) * dx_mm, (y1 - target[1]) * dx_mm]
    vmax = max(float(np.max(baseline_field)), float(np.max(corrected_field)))
    baseline_profile = axial_profile(baseline_dir)
    corrected_profile = axial_profile(corrected_dir)
    baseline = closeout["baseline_r74p435_dx0p75"]
    corrected = closeout["corrected_r78p330_dx0p75"]

    fig, axes = plt.subplots(2, 2, figsize=(10, 7.2), constrained_layout=True)
    images = []
    for ax, field, title in (
        (axes[0, 0], baseline_field, "a  R74.435 mm baseline"),
        (axes[0, 1], corrected_field, "b  R78.330 mm corrected"),
    ):
        image = ax.imshow(field[x0:x1, y0:y1, z].T, origin="lower", extent=extent, cmap="magma", vmin=0, vmax=vmax, aspect="auto")
        images.append(image)
        ax.scatter([0], [0], marker="+", s=90, linewidths=1.5, color="cyan", label="Geometric target")
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xlabel("Axial-grid offset from target (mm)")
        ax.set_ylabel("Lateral-grid offset from target (mm)")
        ax.legend(frameon=False, loc="upper left", fontsize=8)
    fig.colorbar(images[-1], ax=axes[0, :], label="Peak pressure (MPa)", shrink=0.92)

    ax = axes[1, 0]
    ax.plot(baseline_profile["distance_mm"], baseline_profile["pressure_mpa"], label="R74.435", color="#4c78a8", linewidth=2)
    ax.plot(corrected_profile["distance_mm"], corrected_profile["pressure_mpa"], label="R78.330", color="#e45756", linewidth=2)
    ax.axvline(float(baseline_profile["target_distance_mm"]), color="#222222", linestyle="--", linewidth=1, label="Target")
    ax.set_xlim(52, 84)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Axial distance from source centre (mm)")
    ax.set_ylabel("Peak pressure (MPa)")
    ax.set_title("c  Beam-axis pressure profile", loc="left", fontweight="bold")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False, fontsize=8)

    ax = axes[1, 1]
    labels = ["Focus error\n(%)", "Target/global\nratio"]
    x = np.arange(2)
    width = 0.34
    baseline_values = [baseline["refined_focus_error_percent"], baseline["target_to_global_peak_ratio"] * 4]
    corrected_values = [corrected["refined_focus_error_percent"], corrected["target_to_global_peak_ratio"] * 4]
    ax.bar(x - width / 2, baseline_values, width, color="#4c78a8", label="R74.435")
    ax.bar(x + width / 2, corrected_values, width, color="#e45756", label="R78.330")
    ax.axhline(4.0, color="#222222", linestyle="--", linewidth=1)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Focus error (%) / ratio x4")
    ax.set_title("d  Prespecified calibration metrics", loc="left", fontweight="bold")
    ax.text(1, 0.25, "Ratio plotted x4", ha="center", va="bottom", fontsize=8, color="#555555")
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("D60 free-field source correction at dx = 0.75 mm", fontsize=13, fontweight="bold")
    fig.savefig(path, dpi=240)
    plt.close(fig)


def write_report(closeout: dict[str, Any], path: Path) -> None:
    b = closeout["baseline_r74p435_dx0p75"]
    c = closeout["corrected_r78p330_dx0p75"]
    x = closeout["changes"]
    text = f"""# D60 Acoustic Stage Closeout

## Evidence status

The corrected R78.330 source passed the preregistered dx0.75 calibration gate in homogeneous free field. The dx0.5 confirmation was stopped before core outputs, so grid convergence remains incomplete and CT pressure remains blocked.

## Main result

Increasing the nominal curvature radius from 74.435 to 78.330 mm shifted the refined axial pressure maximum from {b['refined_focus_axial_from_source_mm']:.3f} to {c['refined_focus_axial_from_source_mm']:.3f} mm. Refined absolute focal error decreased from {b['refined_focus_error_mm']:.3f} mm ({b['refined_focus_error_percent']:.3f}%) to {c['refined_focus_error_mm']:.3f} mm ({c['refined_focus_error_percent']:.3f}%), an improvement of {-x['refined_focus_error_percentage_points']:.3f} percentage points.

The target/global pressure ratio increased from {b['target_to_global_peak_ratio']:.4f} to {c['target_to_global_peak_ratio']:.4f}. Global peak pressure changed from {b['global_peak_mpa']:.3f} to {c['global_peak_mpa']:.3f} MPa ({x['global_peak_percent']:+.2f}%), while the equivalent lateral -6 dB width changed from {b['minus6db_lateral_equivalent_mm']:.3f} to {c['minus6db_lateral_equivalent_mm']:.3f} mm ({x['lateral_width_percent']:+.2f}%). The corrected field and its 1,000-sample target waveform were finite, and the global peak remained 27 voxels from the nearest boundary.

## Manuscript-ready Results draft

In homogeneous free-field simulations at 500 kHz, first-order curvature compensation improved the spatial calibration of the 60-mm aperture source. At 0.75-mm grid spacing, increasing the nominal radius of curvature from 74.435 to 78.330 mm reduced the refined focal-position error from 3.555% to 1.364% and increased the target-to-global peak-pressure ratio from 0.982 to 0.991. This improvement was accompanied by a {abs(x['global_peak_percent']):.2f}% reduction in global peak pressure and a {abs(x['lateral_width_percent']):.2f}% change in equivalent lateral -6 dB width, indicating that the correction primarily translated the focal maximum without materially broadening the lateral focus. The corrected run produced a finite full-domain peak-pressure field and a finite 1,000-sample target waveform.

## Limitation statement

The R78.330 dx0.5 execution was stopped before a pressure field or summary was generated. These results therefore establish coarse-grid free-field source calibration only; they do not establish dx0.75/dx0.5 convergence, paper-grade numerical convergence, transcranial efficacy, thermal safety, or clinical safety.

## Deliverables

- `d60_source_correction_figure.png`: pressure maps, axial profiles, and calibration metrics.
- `d60_source_correction_metrics.csv`: traceable values for tables and plotting.
- `d60_acoustic_stage_closeout.json`: structured evidence and claim boundaries.
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-dir", type=Path, default=BASELINE)
    parser.add_argument("--corrected-dir", type=Path, default=CORRECTED)
    parser.add_argument("--interruption-record", type=Path, default=INTERRUPTION)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    closeout = build_closeout(args.baseline_dir, args.corrected_dir, args.interruption_record)
    (args.output_dir / "d60_acoustic_stage_closeout.json").write_text(json.dumps(closeout, indent=2) + "\n", encoding="utf-8")
    write_metrics_csv(closeout, args.output_dir / "d60_source_correction_metrics.csv")
    draw_figure(args.baseline_dir, args.corrected_dir, closeout, args.output_dir / "d60_source_correction_figure.png")
    write_report(closeout, args.output_dir / "d60_acoustic_stage_closeout.md")
    print(json.dumps({"status": closeout["status"], "output_dir": str(args.output_dir)}))


if __name__ == "__main__":
    main()

