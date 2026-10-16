from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "outputs" / "d60_supplementary_analysis_20260715"

def _pick_dx05_paths() -> dict[str, Path]:
    """Prefer the 2026-07-16 point-waveform dx0.5 run; fall back to the 2026-07-13 field-only run."""
    pointwave = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p5_pointwave_20260716/run"
    fieldonly = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_dx0p5_fieldonly_20260713/run"
    chosen = pointwave if (pointwave / "pressure_max_mpa.npz").exists() else fieldonly
    return {"npz": chosen / "pressure_max_mpa.npz", "summary": chosen / "summary.json"}


RUNS = {
    "baseline_dx0p75": {
        "npz": PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_dx0p75_resume_20260713/run/pressure_max_mpa.npz",
        "summary": PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_dx0p75_resume_20260713/run/summary.json",
        "label": "Baseline R74.435 dx0.75",
        "color": "#1f77b4",
    },
    "corrected_dx0p75": {
        "npz": PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pointwave_20260714/run/pressure_max_mpa.npz",
        "summary": PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pointwave_20260714/run/summary.json",
        "label": "Corrected R78.330 dx0.75",
        "color": "#ff7f0e",
    },
    "corrected_dx0p5": {
        **_pick_dx05_paths(),
        "label": "Corrected R78.330 dx0.5",
        "color": "#2ca02c",
    },
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_pressure(path: Path) -> np.ndarray:
    data = np.load(path)
    keys = list(data.keys())
    key = "p_max" if "p_max" in keys else keys[0]
    return np.asarray(data[key])


def focal_planes_figure(baseline: dict[str, Any], corrected: dict[str, Any], out_path: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(14, 9))
    fig.suptitle("Supplementary Figure 4: Focal-region pressure contours (baseline vs corrected, dx0.75)")

    for row, run in enumerate([baseline, corrected]):
        p = run["pressure"]
        peak = run["summary"]["pressure"]["global_peak_index_ijk"]
        dx_mm = run["summary"]["dx_m"] * 1000
        label = run["label"]

        # Coordinate vectors centered at peak voxel
        nx, ny, nz = p.shape
        x = (np.arange(nx) - peak[0]) * dx_mm
        y = (np.arange(ny) - peak[1]) * dx_mm
        z = (np.arange(nz) - peak[2]) * dx_mm

        planes = [
            ("xz (y=0)", p[:, peak[1], :], x, z),
            ("xy (z=0)", p[:, :, peak[2]], x, y),
            ("yz (x=0)", p[peak[0], :, :], y, z),
        ]

        for col, (title, slice_data, ax0, ax1) in enumerate(planes):
            ax = axes[row, col]
            vmax = run["summary"]["pressure"]["global_peak_mpa"]
            levels = np.linspace(0, vmax, 11)
            cf = ax.contourf(ax0, ax1, slice_data.T, levels=levels, cmap="viridis", vmin=0, vmax=vmax)
            ax.contour(ax0, ax1, slice_data.T, levels=[0.5 * vmax], colors="red", linewidths=1.0)
            ax.set_title(f"{label} --- {title}")
            ax.set_xlabel("mm")
            ax.set_ylabel("mm")
            ax.set_aspect("equal")
            plt.colorbar(cf, ax=ax, label="MPa")

    plt.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def focal_region_boundary_figure(baseline: dict[str, Any], corrected: dict[str, Any], out_path: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(14, 9))
    fig.suptitle("Supplementary Figure 5: -6 dB focal region boundaries (baseline vs corrected, dx0.75)")

    for row, run in enumerate([baseline, corrected]):
        p = run["pressure"]
        peak = run["summary"]["pressure"]["global_peak_index_ijk"]
        dx_mm = run["summary"]["dx_m"] * 1000
        label = run["label"]
        threshold = 0.5 * run["summary"]["pressure"]["global_peak_mpa"]

        x = (np.arange(p.shape[0]) - peak[0]) * dx_mm
        y = (np.arange(p.shape[1]) - peak[1]) * dx_mm
        z = (np.arange(p.shape[2]) - peak[2]) * dx_mm

        slices = [
            ("xz (y=0)", p[:, peak[1], :], x, z),
            ("xy (z=0)", p[:, :, peak[2]], x, y),
            ("yz (x=0)", p[peak[0], :, :], y, z),
        ]

        for col, (title, slice_data, ax0, ax1) in enumerate(slices):
            ax = axes[row, col]
            ax.contour(ax0, ax1, slice_data.T, levels=[threshold], colors=run["color"], linewidths=2.0)
            ax.axvline(0, color="white", linestyle="--", linewidth=0.8)
            ax.axhline(0, color="white", linestyle="--", linewidth=0.8)
            ax.set_title(f"{label} --- {title}")
            ax.set_xlabel("mm")
            ax.set_ylabel("mm")
            ax.set_aspect("equal")

    plt.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def cross_grid_axial_profile_figure(dx075: dict[str, Any], dx05: dict[str, Any], out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle("Supplementary Figure 6: Cross-grid axial peak-pressure profile (approximate beam-axis overlay)")

    for run in [dx075, dx05]:
        p = run["pressure"]
        summary = run["summary"]
        dx_m = summary["dx_m"]
        source_center = np.array(summary["source"]["source_center_index_ijk"])
        beam_axis = np.array(summary["source"]["beam_axis"])
        # Normalize beam axis to physical unit vector
        beam_axis_phys = beam_axis / np.linalg.norm(beam_axis) * dx_m

        # Create coordinate arrays
        coords = np.stack(np.indices(p.shape, dtype=float), axis=-1)  # (nx,ny,nz,3)
        # Vector from source center to each voxel
        rel = coords - source_center
        # Axial distance along beam axis (projection)
        axial_m = np.einsum("...i,i->...", rel, beam_axis / np.linalg.norm(beam_axis)) * dx_m

        # Restrict to beam-axis neighborhood to avoid off-axis maxima
        # Compute lateral distance from axis
        lateral_m = np.linalg.norm(rel * dx_m - np.expand_dims(axial_m, -1) * (beam_axis_phys / np.linalg.norm(beam_axis_phys)), axis=-1)
        mask = lateral_m <= 1.5e-3  # within 1.5 mm of axis

        # For each axial bin take max pressure
        axial_flat = axial_m[mask]
        pressure_flat = p[mask]
        bins = np.linspace(axial_flat.min(), axial_flat.max(), 200)
        bin_centers = 0.5 * (bins[:-1] + bins[1:])
        binned = []
        for i in range(len(bins) - 1):
            sel = (axial_flat >= bins[i]) & (axial_flat < bins[i + 1])
            binned.append(pressure_flat[sel].max() if sel.any() else np.nan)
        binned = np.array(binned)
        valid = ~np.isnan(binned)

        ax.plot(bin_centers[valid] * 1000, binned[valid], label=run["label"], color=run["color"])

    ax.set_xlabel("Axial distance from source centre (mm)")
    ax.set_ylabel("Peak pressure (MPa)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_title("dx0.75 corrected vs dx0.5 field-only; overlay is approximate because beam axes differ slightly")

    plt.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def focal_volume_table(runs: dict[str, Any], out_path: Path) -> None:
    rows = []
    for key, run in runs.items():
        p = run["pressure"]
        summary = run["summary"]
        dx_m = summary["dx_m"]
        global_peak = summary["pressure"]["global_peak_mpa"]
        threshold = 0.5 * global_peak
        voxel_volume_m3 = dx_m**3
        n_voxels = int(np.sum(p >= threshold))
        volume_mm3 = n_voxels * voxel_volume_m3 * 1e9
        volume_ml = volume_mm3 * 1e-3
        rows.append({
            "run": key,
            "label": run["label"],
            "global_peak_mpa": float(global_peak),
            "minus6db_threshold_mpa": float(threshold),
            "minus6db_voxel_count": n_voxels,
            "minus6db_volume_mm3": round(volume_mm3, 3),
            "minus6db_volume_ml": round(volume_ml, 6),
        })

    import csv
    fieldnames = ["run", "label", "global_peak_mpa", "minus6db_threshold_mpa", "minus6db_voxel_count", "minus6db_volume_mm3", "minus6db_volume_ml"]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    loaded = {}
    for key, spec in RUNS.items():
        loaded[key] = {
            "key": key,
            "label": spec["label"],
            "color": spec["color"],
            "pressure": load_pressure(spec["npz"]),
            "summary": read_json(spec["summary"]),
        }

    focal_planes_figure(loaded["baseline_dx0p75"], loaded["corrected_dx0p75"], OUT_DIR / "supplementary_figure_4_focal_plane_contours.png")
    focal_region_boundary_figure(loaded["baseline_dx0p75"], loaded["corrected_dx0p75"], OUT_DIR / "supplementary_figure_5_focal_region_boundaries.png")
    cross_grid_axial_profile_figure(loaded["corrected_dx0p75"], loaded["corrected_dx0p5"], OUT_DIR / "supplementary_figure_6_cross_grid_axial_profile.png")
    focal_volume_table(loaded, OUT_DIR / "supplementary_table_3_focal_volume.csv")

    manifest = {
        "output_dir": str(OUT_DIR.relative_to(PROJECT_ROOT)),
        "figures": [
            "supplementary_figure_4_focal_plane_contours.png",
            "supplementary_figure_5_focal_region_boundaries.png",
            "supplementary_figure_6_cross_grid_axial_profile.png",
        ],
        "tables": ["supplementary_table_3_focal_volume.csv"],
        "source_data": [str(spec["npz"].relative_to(PROJECT_ROOT)) for spec in RUNS.values()],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps({"status": "ok", "output_dir": str(OUT_DIR.relative_to(PROJECT_ROOT))}))


if __name__ == "__main__":
    main()
