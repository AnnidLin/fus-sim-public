"""Generate the H115 nominal/effective source and sensitivity paper figure."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from analyze_ucl_h115_source_registration import load_simulation
from analyze_ucl_h115_water_validation import simulation_line


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    return values / float(np.max(values))


def run(
    effective_dir: Path,
    nominal_dir: Path,
    measurement_dir: Path,
    effective_comparison_path: Path,
    sensitivity_path: Path,
    output_dir: Path,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    effective_comparison = json.loads(effective_comparison_path.read_text(encoding="utf-8"))
    nominal_comparison = json.loads((nominal_dir / "comparison.json").read_text(encoding="utf-8"))
    sensitivity = json.loads(sensitivity_path.read_text(encoding="utf-8"))
    with np.load(measurement_dir / "qcw_axial_profile.npz") as archive:
        coordinates = np.asarray(archive["coordinates_m"], dtype=float)
        measured = np.asarray(archive["pressure_amplitude_pa"], dtype=float)
    distance_m = np.abs(coordinates[:, 2])
    order = np.argsort(distance_m)
    profiles = {}
    for name, directory in (("Effective bowl", effective_dir), ("Nominal bowl", nominal_dir)):
        pressure, dx_m, source = load_simulation(directory)
        profiles[name] = simulation_line(pressure, source, dx_m, distance_m)

    fig, axes = plt.subplots(2, 2, figsize=(11.2, 8.4), constrained_layout=True)
    ax = axes[0, 0]
    ax.plot(distance_m[order] * 1e3, normalized(measured)[order], color="black", linewidth=2.2, label="UCL qCW")
    ax.plot(distance_m[order] * 1e3, normalized(profiles["Effective bowl"])[order], linewidth=1.9, label="Effective 61.39/50.40 mm")
    ax.plot(distance_m[order] * 1e3, normalized(profiles["Nominal bowl"])[order], linewidth=1.9, label="Nominal 64/64 mm")
    ax.set(xlabel="Distance from source plane (mm)", ylabel="Normalized pressure", title="a  Held-out axial profile")
    ax.legend(frameon=False, fontsize=8)

    ax = axes[0, 1]
    labels = ["Axial peak\nposition", "Axial\nnormalized L2", "Transverse\nnormalized L2", "Transverse\npeak position"]
    limits = np.array([1.0, 10.0, 10.0, 1.5])
    def ratios(comparison: dict) -> np.ndarray:
        return np.array([
            comparison["axial_held_out"]["peak_position_difference_mm"],
            comparison["axial_held_out"]["normalized_relative_l2_percent"],
            comparison["transverse_held_out"]["normalized_relative_l2_percent"],
            comparison["transverse_held_out"]["peak_position_difference_mm"],
        ]) / limits
    positions = np.arange(len(labels))
    width = 0.36
    ax.bar(positions - width / 2, ratios(effective_comparison), width, label="Effective")
    ax.bar(positions + width / 2, ratios(nominal_comparison), width, label="Nominal")
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1.1)
    ax.set_xticks(positions, labels)
    ax.set(ylabel="Observed value / frozen limit", title="b  Preregistered endpoint ratios")
    ax.set_yscale("log")
    ax.legend(frameon=False, fontsize=8)

    ax = axes[1, 0]
    arms = sensitivity["simulations"]["effective"]["registration"]
    offsets = np.array([arm["offset_mm"] for arm in arms])
    peak_error = np.array([arm["peak_position_difference_mm"] for arm in arms])
    axial_l2 = np.array([arm["normalized_relative_l2_percent"] for arm in arms])
    ax.plot(offsets, peak_error, marker="o", markersize=3, label="Peak-position error (mm)")
    ax.plot(offsets, axial_l2, marker="s", markersize=3, label="Axial normalized L2 (%)")
    ax.axhline(1.0, color="C0", linestyle="--", linewidth=1.0)
    ax.axhline(10.0, color="C1", linestyle="--", linewidth=1.0)
    ax.axvline(0.0, color="black", linewidth=0.8)
    ax.set(xlabel="Descriptive axial origin offset (mm)", ylabel="Error", title="c  Registration sensitivity (secondary)")
    ax.legend(frameon=False, fontsize=8)

    ax = axes[1, 1]
    aperture = sensitivity["simulations"]["effective"]["hydrophone_aperture"]
    diameters = np.array([arm["diameter_mm"] for arm in aperture])
    ax.plot(diameters, [arm["normalized_relative_l2_percent"] for arm in aperture], marker="o", label="Transverse L2 (%)")
    ax.plot(diameters, [abs(arm["x_width_error_percent"]) for arm in aperture], marker="s", label="|x width error| (%)")
    ax.plot(diameters, [abs(arm["y_width_error_percent"]) for arm in aperture], marker="^", label="|y width error| (%)")
    ax.axhline(10.0, color="black", linestyle="--", linewidth=1.0, label="Frozen limit")
    ax.set(xlabel="Circular averaging diameter (mm)", ylabel="Error (%)", title="d  Hydrophone-aperture sensitivity (secondary)")
    ax.legend(frameon=False, fontsize=8)

    png = output_dir / "figure_ucl_h115_source_registration.png"
    pdf = output_dir / "figure_ucl_h115_source_registration.pdf"
    fig.savefig(png, dpi=300)
    fig.savefig(pdf)
    plt.close(fig)
    manifest = {
        "schema_version": "1.0",
        "figure": "UCL H115 nominal-vs-effective source geometry, registration and aperture sensitivity",
        "inputs": [str(effective_comparison_path), str(nominal_dir / "comparison.json"), str(sensitivity_path)],
        "outputs": {
            "png": {"path": str(png), "sha256": sha256(png)},
            "pdf": {"path": str(pdf), "sha256": sha256(pdf)},
        },
        "claim_boundary": "Engineering sensitivity with a nonpassing primary external comparison; registration and aperture panels are secondary only.",
    }
    (output_dir / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--effective-dir", type=Path, required=True)
    parser.add_argument("--nominal-dir", type=Path, required=True)
    parser.add_argument("--measurement-dir", type=Path, required=True)
    parser.add_argument("--effective-comparison", type=Path, required=True)
    parser.add_argument("--sensitivity", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.effective_dir, args.nominal_dir, args.measurement_dir, args.effective_comparison, args.sensitivity, args.output_dir)
    print(json.dumps({"status": "completed", "png": result["outputs"]["png"]["path"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
