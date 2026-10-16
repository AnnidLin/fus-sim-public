#!/usr/bin/env python3
"""Generate the ITRUSST Phase-A official/candidate/difference figure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analyze_itrusst_benchmark import load_array, sha256_file, validate_amplitude
from generate_itrusst_phase_a_summary import DEFAULT_CASES, load_json


ROOT = Path(__file__).resolve().parent
DEFAULT_REFERENCES = {
    benchmark: ROOT
    / "outputs"
    / "itrusst_benchmark_pub1_20260803"
    / "official_reference_subset"
    / "KWAVE"
    / f"PH1-{benchmark}-SC1_KWAVE.mat"
    for benchmark in ("BM1", "BM3", "BM4")
}


def build_panel_data(
    benchmark: str,
    reference_path: Path,
    candidate_path: Path,
    comparison_path: Path,
) -> dict[str, Any]:
    reference = validate_amplitude(load_array(reference_path), "reference")
    candidate = validate_amplitude(load_array(candidate_path), "candidate")
    if reference.shape != candidate.shape:
        raise ValueError(
            f"{benchmark}: shape mismatch {reference.shape} != {candidate.shape}"
        )
    if reference.shape != (141, 241):
        raise ValueError(f"{benchmark}: expected 141x241 field")
    scale = float(np.max(reference))
    difference_percent = 100.0 * (candidate - reference) / scale
    comparison = load_json(comparison_path)
    if comparison.get("benchmark") != benchmark:
        raise ValueError(f"{benchmark}: comparison metadata drift")
    return {
        "benchmark": benchmark,
        "reference": reference,
        "candidate": candidate,
        "difference_percent": difference_percent,
        "pressure_scale_pa": scale,
        "difference_abs_max_percent": float(
            np.max(np.abs(difference_percent))
        ),
        "metrics": comparison["metrics"],
        "hashes": {
            "reference": sha256_file(reference_path),
            "candidate": sha256_file(candidate_path),
            "comparison": sha256_file(comparison_path),
        },
        "paths": {
            "reference": str(reference_path.resolve()),
            "candidate": str(candidate_path.resolve()),
            "comparison": str(comparison_path.resolve()),
        },
    }


def render_figure(
    panels: list[dict[str, Any]],
    output_png: Path,
    output_svg: Path,
) -> None:
    if [panel["benchmark"] for panel in panels] != ["BM1", "BM3", "BM4"]:
        raise ValueError("panels must be ordered BM1, BM3, BM4")
    figure, axes = plt.subplots(3, 3, figsize=(11.4, 10.2), constrained_layout=True)
    extent = (0.0, 120.0, -35.0, 35.0)
    column_titles = ("Official k-Wave", "fus-sim candidate", "Difference / ref. peak (%)")
    for column, title in enumerate(column_titles):
        axes[0, column].set_title(title, fontsize=11)
    for row, panel in enumerate(panels):
        scale_kpa = panel["pressure_scale_pa"] / 1000.0
        reference_kpa = panel["reference"] / 1000.0
        candidate_kpa = panel["candidate"] / 1000.0
        difference = panel["difference_percent"]
        difference_limit = max(1.0, panel["difference_abs_max_percent"])
        pressure_images = []
        pressure_images.append(
            axes[row, 0].imshow(
                reference_kpa,
                origin="lower",
                extent=extent,
                aspect="auto",
                cmap="viridis",
                vmin=0,
                vmax=scale_kpa,
            )
        )
        pressure_images.append(
            axes[row, 1].imshow(
                candidate_kpa,
                origin="lower",
                extent=extent,
                aspect="auto",
                cmap="viridis",
                vmin=0,
                vmax=scale_kpa,
            )
        )
        difference_image = axes[row, 2].imshow(
            difference,
            origin="lower",
            extent=extent,
            aspect="auto",
            cmap="coolwarm",
            vmin=-difference_limit,
            vmax=difference_limit,
        )
        metrics = panel["metrics"]
        axes[row, 0].set_ylabel(
            f"{panel['benchmark']}\nLateral (mm)",
            fontsize=10,
        )
        axes[row, 1].text(
            0.02,
            0.98,
            (
                f"L2 {metrics['relative_l2_percent']:.2f}%\n"
                f"peak Δ {metrics['peak_difference_percent']:.2f}%\n"
                f"focus Δ {metrics['focal_position_difference_mm']:.2f} mm"
            ),
            transform=axes[row, 1].transAxes,
            va="top",
            ha="left",
            fontsize=8.5,
            color="white",
            bbox={"facecolor": "black", "alpha": 0.55, "pad": 3},
        )
        figure.colorbar(
            pressure_images[-1],
            ax=axes[row, :2],
            shrink=0.78,
            label="Pressure amplitude (kPa)",
        )
        figure.colorbar(
            difference_image,
            ax=axes[row, 2],
            shrink=0.78,
            label="Relative difference (%)",
        )
    for axis in axes[-1, :]:
        axis.set_xlabel("Axial position (mm)")
    for axis in axes.flat:
        axis.set_xlim(0, 120)
        axis.set_ylim(-35, 35)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_png, dpi=220)
    figure.savefig(output_svg)
    plt.close(figure)


def metadata_for_panels(panels: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "figure_id": "itrusst_phase_a_official_candidate_difference",
        "panel_order": [panel["benchmark"] for panel in panels],
        "comparison_grid": {
            "shape_lateral_axial": [141, 241],
            "dx_mm": 0.5,
            "extent_axial_lateral_mm": [120, 70],
        },
        "normalization": (
            "Pressure panels share the official peak scale within each row; "
            "difference is 100*(candidate-reference)/official_peak."
        ),
        "cases": [
            {
                key: panel[key]
                for key in (
                    "benchmark",
                    "pressure_scale_pa",
                    "difference_abs_max_percent",
                    "metrics",
                    "hashes",
                    "paths",
                )
            }
            for panel in panels
        ],
        "claim_boundary": (
            "Engineering benchmark visualization only; not paper-grade "
            "convergence, whole-skull, experimental, clinical, or safety evidence."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for benchmark in ("bm1", "bm3", "bm4"):
        upper = benchmark.upper()
        parser.add_argument(
            f"--{benchmark}",
            type=Path,
            default=DEFAULT_CASES[upper],
        )
        parser.add_argument(
            f"--{benchmark}-reference",
            type=Path,
            default=DEFAULT_REFERENCES[upper],
        )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    panels = []
    for benchmark in ("BM1", "BM3", "BM4"):
        case_dir = getattr(args, benchmark.lower()).resolve()
        reference = getattr(args, f"{benchmark.lower()}_reference").resolve()
        panels.append(
            build_panel_data(
                benchmark,
                reference,
                case_dir / "p_amp.npz",
                case_dir / "comparison.json",
            )
        )
    output_dir = args.output_dir.resolve()
    output_png = output_dir / "itrusst_phase_a_fields.png"
    output_svg = output_dir / "itrusst_phase_a_fields.svg"
    render_figure(panels, output_png, output_svg)
    metadata = metadata_for_panels(panels)
    metadata_path = output_dir / "itrusst_phase_a_fields.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "completed",
                "png": str(output_png),
                "svg": str(output_svg),
                "metadata": str(metadata_path),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
