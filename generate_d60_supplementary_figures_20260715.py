from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import map_coordinates

OUTPUT_DIR = Path("outputs/d60_supplementary_figures_20260715")

BASELINE_RUN = Path("outputs/freefield_aperture_calibration/d60_dx0p75_resume_20260713/run")
CORRECTED_RUN = Path("outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pointwave_20260714/run")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_axis_profile(run_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    data = np.genfromtxt(run_dir / "axis_profile.csv", delimiter=",", skip_header=1)
    return data[:, 1].astype(float), data[:, 2].astype(float)


def load_field(run_dir: Path) -> tuple[np.ndarray, float, np.ndarray, np.ndarray]:
    with np.load(run_dir / "pressure_max_mpa.npz") as data:
        return (
            np.asarray(data["pressure_max_mpa"], dtype=float),
            float(data["dx_m"]) * 1e3,
            np.asarray(data["source_center_index_ijk"], dtype=float),
            np.asarray(data["target_index_ijk"], dtype=float),
        )


def axial_profile_from_field(run_dir: Path, start_mm: float, end_mm: float, n: int = 800) -> tuple[np.ndarray, np.ndarray]:
    field, dx_mm, source, target = load_field(run_dir)
    unit = (target - source) / np.linalg.norm(target - source)
    target_distance_mm = float(np.linalg.norm(target - source) * dx_mm)
    distance_mm = np.linspace(target_distance_mm + start_mm, target_distance_mm + end_mm, n)
    coordinates = source[:, None] + unit[:, None] * (distance_mm[None, :] / dx_mm)
    pressure_mpa = map_coordinates(field, coordinates, order=3, mode="nearest")
    return distance_mm, pressure_mpa


def draw_combined_axial_profile(baseline_dir: Path, corrected_dir: Path, output_path: Path) -> None:
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9})

    # Use field-derived axial profiles for consistent range
    b_dist, b_pres = axial_profile_from_field(baseline_dir, -35.0, 12.0)
    c_dist, c_pres = axial_profile_from_field(corrected_dir, -35.0, 12.0)

    fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    ax.plot(b_dist, b_pres, label="R74.435 mm baseline", color="#4c78a8", linewidth=2)
    ax.plot(c_dist, c_pres, label="R78.330 mm corrected", color="#e45756", linewidth=2)

    # Mark geometric target distance (~74 mm from source)
    ax.axvline(74.072, color="#222222", linestyle="--", linewidth=1, label="Geometric target")

    ax.set_xlim(52, 84)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Axial distance from source centre (mm)")
    ax.set_ylabel("Peak pressure (MPa)")
    ax.set_title("D60 free-field beam-axis pressure profiles (dx = 0.75 mm)", loc="left", fontweight="bold")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)

    fig.savefig(output_path, dpi=240)
    plt.close(fig)


def draw_focus_metrics_comparison(closeout: dict[str, Any], output_path: Path) -> None:
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9})

    baseline = closeout["baseline_r74p435_dx0p75"]
    corrected = closeout["corrected_r78p330_dx0p75"]

    labels = ["Focus error\n(%)", "Target/global\nratio x4", "Global peak\n(MPa)", "Lateral -6 dB\n(mm)"]
    baseline_values = [
        baseline["refined_focus_error_percent"],
        baseline["target_to_global_peak_ratio"] * 4,
        baseline["global_peak_mpa"],
        baseline["minus6db_lateral_equivalent_mm"],
    ]
    corrected_values = [
        corrected["refined_focus_error_percent"],
        corrected["target_to_global_peak_ratio"] * 4,
        corrected["global_peak_mpa"],
        corrected["minus6db_lateral_equivalent_mm"],
    ]

    fig, axes = plt.subplots(1, 4, figsize=(11, 3.2), constrained_layout=True)
    colors = ["#4c78a8", "#e45756"]
    for ax, label, b, c in zip(axes, labels, baseline_values, corrected_values):
        ax.bar([0, 1], [b, c], color=colors, width=0.6)
        ax.set_xticks([0, 1], ["R74.435", "R78.330"], rotation=45, ha="right")
        ax.set_ylabel(label)
        ax.set_title(label.split("\n")[0], loc="left", fontweight="bold")
        ax.spines[["top", "right"]].set_visible(False)
        if "Focus error" in label:
            ax.axhline(4.0, color="#222222", linestyle="--", linewidth=1)

    fig.suptitle("Prespecified D60 calibration metrics (dx = 0.75 mm)", fontsize=12, fontweight="bold")
    fig.savefig(output_path, dpi=240)
    plt.close(fig)


def draw_lateral_profiles(baseline_dir: Path, corrected_dir: Path, output_path: Path) -> None:
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9})

    def lateral_slice(run_dir: Path) -> tuple[np.ndarray, np.ndarray]:
        field, dx_mm, _, target = load_field(run_dir)
        target = target.astype(int)
        y = np.arange(field.shape[1]) * dx_mm - target[1] * dx_mm
        profile = field[target[0], :, target[2]]
        return y, profile

    b_y, b_prof = lateral_slice(baseline_dir)
    c_y, c_prof = lateral_slice(corrected_dir)

    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    ax.plot(b_y, b_prof, label="R74.435 mm baseline", color="#4c78a8", linewidth=2)
    ax.plot(c_y, c_prof, label="R78.330 mm corrected", color="#e45756", linewidth=2)
    ax.axvline(0, color="#222222", linestyle="--", linewidth=1, label="Geometric target")
    ax.set_xlim(-15, 15)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Lateral offset from target (mm)")
    ax.set_ylabel("Peak pressure (MPa)")
    ax.set_title("D60 free-field lateral pressure profiles at target plane (dx = 0.75 mm)", loc="left", fontweight="bold")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)

    fig.savefig(output_path, dpi=240)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    closeout = read_json(Path("outputs/acoustic_stage_closeout_20260714/d60_acoustic_stage_closeout.json"))

    axial_path = args.output_dir / "supplementary_figure_1_axial_profiles.png"
    metrics_path = args.output_dir / "supplementary_figure_2_metrics.png"
    lateral_path = args.output_dir / "supplementary_figure_3_lateral_profiles.png"

    draw_combined_axial_profile(BASELINE_RUN, CORRECTED_RUN, axial_path)
    draw_focus_metrics_comparison(closeout, metrics_path)
    draw_lateral_profiles(BASELINE_RUN, CORRECTED_RUN, lateral_path)

    manifest = {
        "status": "ok",
        "output_dir": str(args.output_dir),
        "figures": {
            "supplementary_figure_1_axial_profiles": str(axial_path.relative_to(args.output_dir)),
            "supplementary_figure_2_metrics": str(metrics_path.relative_to(args.output_dir)),
            "supplementary_figure_3_lateral_profiles": str(lateral_path.relative_to(args.output_dir)),
        },
        "source_data": [
            str(BASELINE_RUN / "pressure_max_mpa.npz"),
            str(CORRECTED_RUN / "pressure_max_mpa.npz"),
        ],
    }
    (args.output_dir / "supplementary_figures_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
