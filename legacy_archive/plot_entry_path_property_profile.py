from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for key in (
            "sample_id",
            "distance_from_source_mm",
            "distance_from_entry_mm",
            "distance_to_target_mm",
            "i",
            "j",
            "k",
            "label",
            "hu",
            "sound_speed_m_s",
            "density_kg_m3",
            "alpha_db_mhz_cm",
        ):
            if key in row and row[key] not in ("", None):
                row[key] = float(row[key])
    return rows


def alpha_unit_for_model(summary: dict[str, Any], model: str) -> str:
    mapping = summary.get("model_mapping_profiles", {}).get(model, {})
    semantics = mapping.get("alpha_semantics")
    if isinstance(semantics, dict) and semantics.get("alpha_coeff_unit"):
        return str(semantics["alpha_coeff_unit"])
    return "dB/(MHz cm)"


def model_display_name(model: str) -> str:
    names = {
        "simple_hu300": "simple HU300",
        "prestus_marsac_mueller": "PRESTUS y=1",
        "no_dispersion": "no-disp y=1",
        "prestus_fit_alpha_power_2": "PRESTUS fit y=2",
    }
    return names.get(model, model)


def group_path_rows(rows: list[dict[str, Any]], path_name: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("path_name") != path_name:
            continue
        grouped[str(row["model"])].append(row)
    for model_rows in grouped.values():
        model_rows.sort(key=lambda item: float(item["distance_from_source_mm"]))
    return dict(grouped)


def first_model_rows(grouped: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    if "simple_hu300" in grouped:
        return grouped["simple_hu300"]
    return next(iter(grouped.values()))


def entry_distance_from_source(summary: dict[str, Any]) -> float | None:
    source = summary.get("source_center_index_ijk")
    entry = summary.get("entry_index_ijk")
    if not source or not entry:
        return None
    # Existing 079 profile uses 1 mm isotropic voxels after resampling.
    return sum((float(a) - float(b)) ** 2 for a, b in zip(source, entry)) ** 0.5


def add_entry_target_lines(ax: plt.Axes, entry_distance_mm: float | None, target_distance_mm: float | None) -> None:
    if entry_distance_mm is not None:
        ax.axvline(entry_distance_mm, color="#444444", linestyle="--", linewidth=0.9, alpha=0.7)
    if target_distance_mm is not None:
        ax.axvline(target_distance_mm, color="#111111", linestyle=":", linewidth=0.9, alpha=0.7)


def plot_material_profiles(grouped: dict[str, list[dict[str, Any]]], summary: dict[str, Any], output: Path) -> None:
    base_rows = first_model_rows(grouped)
    x_base = [float(row["distance_from_source_mm"]) for row in base_rows]
    target_distance = max(x_base) if x_base else None
    entry_distance = entry_distance_from_source(summary)

    fig, axes = plt.subplots(5, 1, figsize=(10, 13), sharex=True)
    fig.suptitle("079 candidate_006 entry path material profiles", fontsize=14)

    axes[0].plot(x_base, [row["hu"] for row in base_rows], color="#303030", linewidth=1.5)
    axes[0].set_ylabel("HU")
    axes[0].set_title("CT intensity along source-to-target path")

    axes[1].step(x_base, [row["label"] for row in base_rows], where="mid", color="#6c6c6c", linewidth=1.2)
    axes[1].set_ylabel("label")
    axes[1].set_yticks([0, 1, 2])

    for model, rows in grouped.items():
        x = [float(row["distance_from_source_mm"]) for row in rows]
        axes[2].plot(x, [row["sound_speed_m_s"] for row in rows], label=model_display_name(model), linewidth=1.2)
        axes[3].plot(x, [row["density_kg_m3"] for row in rows], label=model_display_name(model), linewidth=1.2)
        axes[4].plot(x, [row["alpha_db_mhz_cm"] for row in rows], label=model_display_name(model), linewidth=1.2)

    axes[2].set_ylabel("c (m/s)")
    axes[2].set_title("Sound speed")
    axes[3].set_ylabel("rho (kg/m3)")
    axes[3].set_title("Density")
    axes[4].set_ylabel("alpha coeff")
    axes[4].set_title("Alpha coefficient values; units differ by model, see split alpha plot")
    axes[4].set_xlabel("distance from source center (mm)")

    for ax in axes:
        add_entry_target_lines(ax, entry_distance, target_distance)
        ax.grid(True, alpha=0.25)

    axes[2].legend(loc="best", fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_alpha_split(grouped: dict[str, list[dict[str, Any]]], summary: dict[str, Any], output: Path) -> None:
    base_rows = first_model_rows(grouped)
    target_distance = max([float(row["distance_from_source_mm"]) for row in base_rows]) if base_rows else None
    entry_distance = entry_distance_from_source(summary)
    groups: dict[str, list[str]] = defaultdict(list)
    for model in grouped:
        groups[alpha_unit_for_model(summary, model)].append(model)

    fig, axes = plt.subplots(len(groups), 1, figsize=(10, max(4, 3.5 * len(groups))), sharex=True)
    axes = list(np.ravel(axes))
    fig.suptitle("Alpha coefficient split by unit semantics", fontsize=14)

    for ax, (unit, models) in zip(axes, groups.items()):
        for model in models:
            rows = grouped[model]
            x = [float(row["distance_from_source_mm"]) for row in rows]
            y = [float(row["alpha_db_mhz_cm"]) for row in rows]
            ax.plot(x, y, label=model_display_name(model), linewidth=1.3)
        add_entry_target_lines(ax, entry_distance, target_distance)
        ax.set_ylabel(unit)
        ax.grid(True, alpha=0.25)
        ax.legend(loc="best", fontsize=8)
    axes[-1].set_xlabel("distance from source center (mm)")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(output, dpi=180)
    plt.close(fig)


def build_interpretation(summary: dict[str, Any], output_paths: dict[str, str]) -> str:
    rows = [
        "# 079 candidate_006 路径属性可视化说明",
        "",
        "## 输出图",
        "",
        f"- 材料属性总览：`{output_paths['material_plot']}`",
        f"- alpha 语义分组：`{output_paths['alpha_plot']}`",
        "",
        "## 读图边界",
        "",
        "- 这些图只展示路径上的材料属性，不是声压传播结果。",
        "- 灰色虚线是 entry 附近位置，黑色点线是 target 端。",
        "- alpha 图按单位语义分组，避免把 `dB/(MHz cm)` 和 `dB/(MHz^2 cm)` 混为同一个物理量。",
        "- `prestus_fit_alpha_power_2` 的 alpha 数值更高，是 alpha_power=2 prefactor 重标定，不代表 500 kHz 下吸收直接翻倍。",
        "",
        "## 当前判断",
        "",
        "当前路径上的 PRESTUS route 仍显示低 HU 边缘颅骨被映射为接近水/软组织的声速和密度。该结果支持继续保持 pressure blocked，优先做单位交叉测试或模型审查。",
        "",
    ]
    return "\n".join(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot entry path property profiles from CSV/summary outputs.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--path-name", default="source_to_target")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    csv_path = input_dir / "entry_path_profile.csv"
    summary_path = input_dir / "entry_path_property_summary.json"
    rows = read_rows(csv_path)
    summary = read_json(summary_path)
    grouped = group_path_rows(rows, args.path_name)
    if not grouped:
        raise ValueError(f"No rows found for path_name={args.path_name!r}")

    material_plot = input_dir / "path_material_profiles.png"
    alpha_plot = input_dir / "path_alpha_by_semantics.png"
    plot_material_profiles(grouped, summary, material_plot)
    plot_alpha_split(grouped, summary, alpha_plot)

    plot_summary = {
        "scope": "entry path property visualization only; no k-Wave and no pressure simulation",
        "input_dir": str(input_dir),
        "path_name": args.path_name,
        "plots": {
            "material_profiles": str(material_plot),
            "alpha_by_semantics": str(alpha_plot),
        },
        "models": sorted(grouped),
        "pressure_simulation_allowed": False,
    }
    write_json(input_dir / "path_property_plot_summary.json", plot_summary)
    interpretation = build_interpretation(
        summary,
        {
            "material_plot": str(material_plot),
            "alpha_plot": str(alpha_plot),
        },
    )
    (input_dir / "path_property_plot_interpretation.md").write_text(
        interpretation + "\n",
        encoding="utf-8-sig",
    )
    print(f"Wrote plots to {input_dir}")


if __name__ == "__main__":
    main()
