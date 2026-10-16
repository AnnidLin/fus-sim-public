from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from generate_d60_acoustic_stage_closeout import (
    BASELINE,
    CORRECTED,
    INTERRUPTION,
    OUTPUT,
    axial_profile,
    build_closeout,
    load_field,
)


def draw_figure(path: Path) -> None:
    closeout = build_closeout(BASELINE, CORRECTED, INTERRUPTION)
    baseline = closeout["baseline_r74p435_dx0p75"]
    corrected = closeout["corrected_r78p330_dx0p75"]
    baseline_field, dx_mm, _, target, _ = load_field(BASELINE)
    corrected_field, _, _, _, _ = load_field(CORRECTED)
    baseline_profile = axial_profile(BASELINE)
    corrected_profile = axial_profile(CORRECTED)
    z = int(target[2])
    x0, x1 = int(target[0] - 34), int(target[0] + 17)
    y0, y1 = int(target[1] - 17), int(target[1] + 18)
    extent = [
        (x0 - target[0]) * dx_mm,
        (x1 - target[0]) * dx_mm,
        (y0 - target[1]) * dx_mm,
        (y1 - target[1]) * dx_mm,
    ]
    vmax = max(float(np.max(baseline_field)), float(np.max(corrected_field)))
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9})
    fig, axes = plt.subplots(2, 2, figsize=(10, 7.2), constrained_layout=True)

    for ax, field, title in (
        (axes[0, 0], baseline_field, "a  R74.435 mm baseline"),
        (axes[0, 1], corrected_field, "b  R78.330 mm corrected"),
    ):
        image = ax.imshow(
            field[x0:x1, y0:y1, z].T,
            origin="lower",
            extent=extent,
            cmap="magma",
            vmin=0,
            vmax=vmax,
            aspect="auto",
        )
        ax.scatter([0], [0], marker="+", s=90, linewidths=1.5, color="cyan", label="Geometric target")
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xlabel("Axial-grid offset from target (mm)")
        ax.set_ylabel("Lateral-grid offset from target (mm)")
        ax.legend(frameon=False, loc="upper left", fontsize=8)
    fig.colorbar(image, ax=axes[0, :], label="Peak pressure (MPa)", shrink=0.92)

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
    values = [baseline["refined_focus_error_percent"], corrected["refined_focus_error_percent"]]
    ratios = [baseline["target_to_global_peak_ratio"], corrected["target_to_global_peak_ratio"]]
    bars = ax.bar(np.arange(2), values, width=0.56, color=["#4c78a8", "#e45756"])
    ax.axhline(4.0, color="#222222", linestyle="--", linewidth=1)
    ax.set_xticks(np.arange(2), ["R74.435", "R78.330"])
    ax.set_ylabel("Refined focus error (%)")
    ax.set_title("d  Prespecified calibration metrics", loc="left", fontweight="bold")
    for bar, value, ratio in zip(bars, values, ratios):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.12,
            f"{value:.2f}%\ntarget/global {ratio:.3f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    ax.text(1.48, 4.04, "4% gate", ha="right", va="bottom", fontsize=8, color="#333333")
    ax.set_ylim(0, 4.8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("D60 free-field source correction at dx = 0.75 mm", fontsize=13, fontweight="bold")
    fig.savefig(path, dpi=240)
    plt.close(fig)


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    draw_figure(OUTPUT / "d60_source_correction_figure.png")
