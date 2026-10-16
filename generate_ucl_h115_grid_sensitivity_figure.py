"""Generate the paper figure for H115 measurement and grid sensitivity."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from analyze_ucl_h115_grid_sensitivity import load_field, sample_candidate_on_reference
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


def failed_gate_ratios(comparison: dict) -> list[float]:
    transverse = comparison["transverse_held_out"]
    return [
        float(comparison["axial_held_out"]["peak_position_difference_mm"]) / 1.0,
        float(transverse["normalized_relative_l2_percent"]) / 10.0,
    ]


def run(
    reference_dir: Path,
    candidate_dir: Path,
    measurement_dir: Path,
    output_dir: Path,
    reference_comparison_path: Path | None = None,
    candidate_comparison_path: Path | None = None,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    reference = load_field(reference_dir)
    candidate = load_field(candidate_dir)
    reference_comparison_path = reference_comparison_path or reference_dir / "comparison.json"
    candidate_comparison_path = candidate_comparison_path or candidate_dir / "comparison.json"
    reference_comparison = json.loads(reference_comparison_path.read_text(encoding="utf-8"))
    candidate_comparison = json.loads(candidate_comparison_path.read_text(encoding="utf-8"))
    grid = json.loads((candidate_dir / "grid_sensitivity.json").read_text(encoding="utf-8"))

    with np.load(measurement_dir / "qcw_axial_profile.npz") as archive:
        measured_coordinates = np.asarray(archive["coordinates_m"], dtype=float)
        measured_pressure = np.asarray(archive["pressure_amplitude_pa"], dtype=float)
    measured_distance_mm = np.abs(measured_coordinates[:, 2]) * 1e3
    reference_at_measurement = simulation_line(
        np.asarray(reference["pressure"]) * 1e6,
        np.asarray(reference["source"]),
        float(reference["dx_m"]),
        np.abs(measured_coordinates[:, 2]),
    )
    candidate_at_measurement = simulation_line(
        np.asarray(candidate["pressure"]) * 1e6,
        np.asarray(candidate["source"]),
        float(candidate["dx_m"]),
        np.abs(measured_coordinates[:, 2]),
    )

    mapped, valid = sample_candidate_on_reference(reference, candidate)
    scale = grid["nearfield_excluded_metrics"]["candidate_to_reference_least_squares_scale"]
    reference_pressure = np.asarray(reference["pressure"])
    difference = (mapped * scale - reference_pressure) / float(np.max(reference_pressure)) * 100.0
    z = int(np.asarray(reference["source"])[2])
    difference_slice = difference[:, :, z].T
    valid_slice = valid[:, :, z].T
    difference_slice[~valid_slice] = np.nan
    x_mm = (np.arange(reference_pressure.shape[0]) - reference["source"][0]) * float(reference["dx_m"]) * 1e3
    y_mm = (np.arange(reference_pressure.shape[1]) - reference["source"][1]) * float(reference["dx_m"]) * 1e3
    difference_slice[:, x_mm < float(reference["nearfield_m"]) * 1e3] = np.nan

    labels = ["Axial peak\nposition", "Transverse\nnormalized L2"]
    reference_ratios = failed_gate_ratios(reference_comparison)
    candidate_ratios = failed_gate_ratios(candidate_comparison)

    fig, axes = plt.subplots(2, 2, figsize=(11.2, 8.2), constrained_layout=True)
    ax = axes[0, 0]
    order = np.argsort(measured_distance_mm)
    ax.plot(measured_distance_mm[order], normalized(measured_pressure)[order], color="black", linewidth=2.0, label="UCL qCW measurement")
    ax.plot(measured_distance_mm[order], normalized(reference_at_measurement)[order], linewidth=1.8, label="dx 0.50 mm")
    ax.plot(measured_distance_mm[order], normalized(candidate_at_measurement)[order], linewidth=1.8, label="dx 0.30 mm")
    ax.set(xlabel="Distance from source plane (mm)", ylabel="Normalized pressure", title="a  Held-out axial profile")
    ax.legend(frameon=False, fontsize=8)

    ax = axes[0, 1]
    positions = np.arange(len(labels))
    width = 0.36
    ax.bar(positions - width / 2, reference_ratios, width, label="dx 0.50 mm")
    ax.bar(positions + width / 2, candidate_ratios, width, label="dx 0.30 mm")
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1.2, label="Acceptance limit")
    ax.set_xticks(positions, labels)
    ax.set(ylabel="Observed value / acceptance limit", title="b  Failed preregistered endpoints")
    ax.legend(frameon=False, fontsize=8)

    ax = axes[1, 0]
    limit = float(np.nanpercentile(np.abs(difference_slice), 99.5))
    image = ax.imshow(difference_slice, origin="lower", extent=[x_mm[0], x_mm[-1], y_mm[0], y_mm[-1]], cmap="coolwarm", vmin=-limit, vmax=limit, aspect="auto")
    ax.set(xlabel="Axial distance from source centre (mm)", ylabel="Lateral distance (mm)", title="c  Scaled dx0.30 − dx0.50 field")
    ax.set_xlim(float(reference["nearfield_m"]) * 1e3, x_mm[-1])
    fig.colorbar(image, ax=ax, label="Difference (% of dx0.50 peak)")

    ax = axes[1, 1]
    metrics = grid["nearfield_excluded_metrics"]
    ax.axis("off")
    lines = [
        "Physical-coordinate grid comparison",
        f"Common voxels: {metrics['common_voxels']:,}",
        f"Correlation: {metrics['normalized_correlation']:.6f}",
        f"Scaled relative L2: {metrics['scaled_relative_l2_percent']:.3f}%",
        f"Scaled relative L∞: {metrics['scaled_relative_linf_percent_of_reference_peak']:.3f}%",
        f"Peak magnitude change: {metrics['peak_magnitude_change_percent']:+.4f}%",
        f"Discrete axial peak shift: {grid['axial_peak']['candidate_minus_reference_mm']:+.3f} mm",
        "",
        "Interpretation:",
        "Refinement preserves the simulated field",
        "but does not repair experimental mismatch.",
        "Two grids do not establish formal convergence.",
    ]
    ax.text(0.02, 0.98, "\n".join(lines), va="top", ha="left", fontsize=10.2, linespacing=1.35)
    ax.set_title("d  Numerical-sensitivity summary", loc="left")

    png = output_dir / "figure_ucl_h115_grid_sensitivity.png"
    pdf = output_dir / "figure_ucl_h115_grid_sensitivity.pdf"
    fig.savefig(png, dpi=300)
    fig.savefig(pdf)
    plt.close(fig)
    manifest = {
        "schema_version": "1.0",
        "figure": "UCL H115 dx0.50-to-dx0.30 grid sensitivity and held-out measurement comparison",
        "inputs": [str(reference_comparison_path), str(candidate_comparison_path), str(candidate_dir / "grid_sensitivity.json")],
        "outputs": {"png": {"path": str(png), "sha256": sha256(png)}, "pdf": {"path": str(pdf), "sha256": sha256(pdf)}},
        "claim_boundary": "Two-grid homogeneous-water sensitivity and nonpassing external comparison; not formal convergence or successful source validation.",
    }
    (output_dir / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--measurement-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reference-comparison", type=Path)
    parser.add_argument("--candidate-comparison", type=Path)
    args = parser.parse_args()
    manifest = run(
        args.reference_dir, args.candidate_dir, args.measurement_dir, args.output_dir,
        reference_comparison_path=args.reference_comparison,
        candidate_comparison_path=args.candidate_comparison,
    )
    print(json.dumps({"status": "completed", "output": manifest["outputs"]["png"]["path"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
