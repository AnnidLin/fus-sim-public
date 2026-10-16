"""Generate submission-oriented PUB.2 figures from accepted field artifacts.

This script performs no acoustic simulation. It reads frozen NPZ/JSON outputs,
uses physical coordinates relative to the target, and records source/output
hashes in a machine-readable manifest.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analyze_pub2_pml16_baseline_20260810 import common_views, load_field

ROOT = Path(__file__).resolve().parent
REFERENCE_ROOT = ROOT / "outputs" / "pub2_250khz_reference_pair_throttled_20260807"
PML16_BASELINE = ROOT / "outputs" / "pub2_250khz_pml16_baseline_20260810"
PML16_TR = ROOT / "outputs" / "pub2_250khz_pml16_tr_20260811" / "tr"
PML_REPORT = ROOT / "outputs" / "pub2_250khz_pml16_tr_analysis_20260812" / "paired_pml_analysis.json"
OUTPUT = ROOT / "paper" / "figures" / "pub2_20260812"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def load_plot_field(directory: Path) -> dict[str, Any]:
    path = directory / "pressure_max_mpa.npz"
    with np.load(path, allow_pickle=False) as archive:
        field = np.asarray(archive["pressure_max_mpa"], dtype=np.float64)
        target = np.asarray(archive["target_index_ijk"], dtype=np.int64)
        origin = np.asarray(archive["crop_origin_ijk"], dtype=np.int64)
        dx_mm = float(np.asarray(archive["dx_m"])) * 1e3
    metrics = load_json(directory / "focus_metrics.json")
    peak = np.asarray(metrics["global_peak_index_ijk"], dtype=np.int64)
    if field.ndim != 3 or not np.isfinite(field).all() or float(field.max()) <= 0:
        raise ValueError(f"{path}: invalid pressure field")
    return {
        "field": field,
        "target": target,
        "origin": origin,
        "dx_mm": dx_mm,
        "peak": peak,
        "metrics": metrics,
        "path": path,
    }


def target_relative_extent(shape: tuple[int, int], target_xy: np.ndarray, dx_mm: float) -> list[float]:
    """Return imshow extent for an x-y array, with the target at (0, 0)."""
    nx, ny = shape
    return [
        (-float(target_xy[0]) - 0.5) * dx_mm,
        (float(nx - 1 - target_xy[0]) + 0.5) * dx_mm,
        (-float(target_xy[1]) - 0.5) * dx_mm,
        (float(ny - 1 - target_xy[1]) + 0.5) * dx_mm,
    ]


def save_figure(fig: plt.Figure, stem: str) -> list[Path]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    paths = [OUTPUT / f"{stem}.png", OUTPUT / f"{stem}.svg"]
    fig.savefig(paths[0], dpi=400, bbox_inches="tight", facecolor="white")
    fig.savefig(paths[1], bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return paths


def plot_localization(baseline: dict[str, Any], tr: dict[str, Any]) -> list[Path]:
    vmax = max(float(baseline["field"].max()), float(tr["field"].max()))
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.15), constrained_layout=True, sharex=True, sharey=True)
    image = None
    for index, (ax, title, data) in enumerate(zip(axes, ("Baseline", "Time reversal"), (baseline, tr))):
        projection = np.max(data["field"], axis=2)
        extent = target_relative_extent(projection.shape, data["target"][:2], data["dx_mm"])
        image = ax.imshow(
            projection.T,
            origin="lower",
            extent=extent,
            cmap="magma",
            vmin=0,
            vmax=vmax,
            interpolation="nearest",
            aspect="equal",
        )
        peak_xy = (data["peak"][:2] - data["target"][:2]) * data["dx_mm"]
        ax.scatter(0, 0, marker="+", s=105, linewidths=1.8, color="#00E5FF", label="Target", zorder=3)
        ax.scatter(peak_xy[0], peak_xy[1], marker="x", s=65, linewidths=1.8, color="#7CFC00", label="Global peak", zorder=3)
        ax.set_title(title, fontsize=10, fontweight="bold")
        ax.set_xlabel("x relative to target (mm)")
        ax.text(0.02, 0.97, chr(ord("a") + index), transform=ax.transAxes, ha="left", va="top", color="white", fontweight="bold", fontsize=11)
    axes[0].set_ylabel("y relative to target (mm)")
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 1.08), ncol=2, frameon=False)
    colorbar = fig.colorbar(image, ax=axes, shrink=0.88, pad=0.025)
    colorbar.set_label("Temporal peak pressure magnitude (MPa)")
    return save_figure(fig, "figure2_baseline_vs_tr_localization")


def plot_endpoints(baseline: dict[str, Any], tr: dict[str, Any]) -> list[Path]:
    bm, tm = baseline["metrics"], tr["metrics"]
    colors = ["#4C78A8", "#E45756"]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.75), constrained_layout=True)
    panels = [
        ("Target/global\npeak ratio", [bm["target_to_global_peak_ratio"], tm["target_to_global_peak_ratio"]], "Ratio", (0, 1.1)),
        ("Peak-to-target\ndistance", [bm["global_peak_to_target_distance_mm"], tm["global_peak_to_target_distance_mm"]], "Distance (mm)", (0, 62)),
    ]
    for index, (title, values, ylabel, ylim) in enumerate(panels):
        axes[index].bar([0, 1], values, color=colors, width=0.62)
        axes[index].set_xticks([0, 1], ["Baseline", "TR"])
        axes[index].set_ylabel(ylabel)
        axes[index].set_ylim(*ylim)
        axes[index].set_title(title, fontsize=9.5, fontweight="bold")
        for x, value in enumerate(values):
            axes[index].text(x, value + (ylim[1] * 0.025), f"{value:.3g}", ha="center", va="bottom", fontsize=8)
    x = np.arange(2)
    width = 0.34
    target_values = [bm["target_pressure_mpa"], tm["target_pressure_mpa"]]
    peak_values = [bm["global_peak_mpa"], tm["global_peak_mpa"]]
    axes[2].bar(x - width / 2, target_values, width, label="At target", color="#72B7B2")
    axes[2].bar(x + width / 2, peak_values, width, label="Global peak", color="#F2CF5B")
    axes[2].set_xticks(x, ["Baseline", "TR"])
    axes[2].set_ylabel("Pressure magnitude (MPa)")
    axes[2].set_ylim(0, 4.4)
    axes[2].set_title("Simulated pressure", fontsize=9.5, fontweight="bold")
    axes[2].legend(frameon=False, fontsize=7.5, loc="upper right")
    for index, ax in enumerate(axes):
        ax.spines[["top", "right"]].set_visible(False)
        ax.text(0.01, 0.99, chr(ord("a") + index), transform=ax.transAxes, ha="left", va="top", fontweight="bold", fontsize=11)
    return save_figure(fig, "figure3_primary_endpoints")


def signed_max_abs_projection(difference: np.ndarray) -> np.ndarray:
    """Project along z while preserving the sign of the largest absolute difference."""
    index = np.argmax(np.abs(difference), axis=2)
    return np.take_along_axis(difference, index[..., None], axis=2)[..., 0]


def plot_pml_sensitivity() -> tuple[list[Path], dict[str, Any]]:
    pairs = [
        ("Baseline", REFERENCE_ROOT / "baseline", PML16_BASELINE),
        ("Time reversal", REFERENCE_ROOT / "tr", PML16_TR),
    ]
    report = load_json(PML_REPORT)["pml12_vs_pml16"]
    prepared: list[tuple[str, np.ndarray, np.ndarray, float]] = []
    for title, pml12_dir, pml16_dir in pairs:
        field12, field16 = load_field(pml12_dir / "pressure_max_mpa.npz"), load_field(pml16_dir / "pressure_max_mpa.npz")
        view12, view16, alignment = common_views(field12, field16)
        difference = view16.astype(np.float64) - view12.astype(np.float64)
        projection = signed_max_abs_projection(difference)
        target_common = field12["target"][:2] - np.asarray(alignment["reference_slices_start_ijk"][:2], dtype=np.int64)
        prepared.append((title, projection, target_common, field12["dx_m"] * 1e3))
    vmax = max(float(np.max(np.abs(item[1]))) for item in prepared)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), constrained_layout=True, sharex=True, sharey=True)
    image = None
    for index, (ax, (title, projection, target, dx_mm), key) in enumerate(zip(axes, prepared, ("baseline", "tr"))):
        extent = target_relative_extent(projection.shape, target, dx_mm)
        image = ax.imshow(projection.T, origin="lower", extent=extent, cmap="coolwarm", vmin=-vmax, vmax=vmax, interpolation="nearest", aspect="equal")
        ax.scatter(0, 0, marker="+", s=100, linewidths=1.8, color="black")
        metrics = report[key]["field_difference"]
        ax.set_title(f"{title}\nrel. L2={metrics['relative_l2']:.2e}; rel. L∞={metrics['relative_linf']:.2e}", fontsize=9.5, fontweight="bold")
        ax.set_xlabel("x relative to target (mm)")
        ax.text(0.02, 0.97, chr(ord("a") + index), transform=ax.transAxes, ha="left", va="top", fontweight="bold", fontsize=11)
    axes[0].set_ylabel("y relative to target (mm)")
    colorbar = fig.colorbar(image, ax=axes, shrink=0.88, pad=0.025)
    colorbar.set_label("PML16 − PML12 peak magnitude (MPa)")
    return save_figure(fig, "figure4_pml12_vs_pml16_difference"), {"shared_absolute_limit_mpa": vmax}


def main() -> int:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.linewidth": 0.8, "svg.fonttype": "none"})
    baseline = load_plot_field(REFERENCE_ROOT / "baseline")
    tr = load_plot_field(REFERENCE_ROOT / "tr")
    outputs: list[Path] = []
    outputs.extend(plot_localization(baseline, tr))
    outputs.extend(plot_endpoints(baseline, tr))
    pml_outputs, pml_rendering = plot_pml_sensitivity()
    outputs.extend(pml_outputs)
    sources = [
        baseline["path"], tr["path"],
        REFERENCE_ROOT / "baseline" / "focus_metrics.json",
        REFERENCE_ROOT / "tr" / "focus_metrics.json",
        PML16_BASELINE / "pressure_max_mpa.npz",
        PML16_TR / "pressure_max_mpa.npz",
        PML_REPORT,
    ]
    manifest = {
        "schema_version": "1.0",
        "status": "generated_from_accepted_artifacts",
        "pressure_definition": "max(abs(p_max), abs(p_min)) / 1e6 MPa at each voxel",
        "projection_definition": {
            "figure2": "maximum pressure magnitude along k/z; common baseline/TR scale",
            "figure4": "signed PML16-minus-PML12 difference selected at maximum absolute difference along k/z; common baseline/TR difference scale",
        },
        "coordinate_definition": "x and y in mm relative to the frozen target index; PML fields aligned with crop_origin_ijk before subtraction",
        "claim_boundary": "Single Case079 engineering evidence; PML perturbation only; not formal convergence, efficacy or safety evidence.",
        "pml_rendering": pml_rendering,
        "sources": {str(path.relative_to(ROOT)): sha256(path) for path in sources},
        "outputs": {str(path.relative_to(ROOT)): sha256(path) for path in outputs},
    }
    manifest_path = OUTPUT / "figure_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "completed", "output": str(OUTPUT), "figure_count": 3}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
