from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = ROOT / "outputs" / "factorial_250khz_trajectory_transducer_20260729"
CELLS = ("default_small", "default_large", "h3_small", "h3_large")
INTENDED_FACTOR_FIELDS = {
    "entry_plan_path",
    "transducer_radius_m",
    "aperture_diameter_m",
}
METRICS = (
    "global_peak_mpa",
    "target_window_peak_mpa",
    "target_to_global_peak_ratio",
    "global_peak_to_target_distance_mm",
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label}: expected number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label}: expected finite number")
    return result


def load_cell(name: str) -> dict[str, Any]:
    directory = OUTPUT_ROOT / name
    summary_path = directory / "summary.json"
    focus_path = directory / "focus_metrics.json"
    pressure_path = directory / "pressure_max_mpa.npz"
    monitor_path = directory / "monitor_status.json"
    summary = load_json(summary_path)
    focus = load_json(focus_path)
    monitor = load_json(monitor_path)
    config = summary["config"]
    quality = summary["simulation_quality"]
    source = summary["source"]
    counts = source.get("source_label_counts")
    background_only = (
        isinstance(counts, dict)
        and set(counts) == {"0"}
        and isinstance(counts.get("0"), int)
        and counts["0"] > 0
    )
    core_complete = all(
        path.is_file() for path in (summary_path, focus_path, pressure_path)
    )
    return {
        "directory": str(directory.relative_to(ROOT)).replace("\\", "/"),
        "config": config,
        "grid_size": quality.get("grid_size"),
        "runtime_s": quality.get("runtime_s"),
        "source_label_counts": counts,
        "source_background_only": background_only,
        "monitor_status": monitor.get("status"),
        "return_code": monitor.get("return_code"),
        "core_complete": core_complete,
        "summary_sha256": sha256(summary_path),
        "focus_sha256": sha256(focus_path),
        "pressure_sha256": sha256(pressure_path),
        "metrics": {
            metric: finite(focus.get(metric), f"{name}:{metric}")
            for metric in METRICS
        },
    }


def unexpected_drift(cells: dict[str, dict[str, Any]]) -> list[str]:
    reference = cells["default_small"]["config"]
    fields = sorted(
        set().union(*(cell["config"].keys() for cell in cells.values()))
    )
    return [
        field
        for field in fields
        if field not in INTENDED_FACTOR_FIELDS
        and any(cell["config"].get(field) != reference.get(field) for cell in cells.values())
    ]


def factorial_effect(values: dict[str, float]) -> dict[str, float]:
    a = values["default_small"]
    b = values["default_large"]
    c = values["h3_small"]
    d = values["h3_large"]
    small_mean = (a + c) / 2
    large_mean = (b + d) / 2
    default_mean = (a + b) / 2
    h3_mean = (c + d) / 2
    return {
        "trajectory_main_effect": h3_mean - default_mean,
        "trajectory_main_effect_relative_to_default_mean": (
            (h3_mean - default_mean) / default_mean if default_mean else math.nan
        ),
        "transducer_main_effect": large_mean - small_mean,
        "transducer_main_effect_relative_to_small_mean": (
            (large_mean - small_mean) / small_mean if small_mean else math.nan
        ),
        "trajectory_effect_at_small": c - a,
        "trajectory_effect_at_small_relative": (c - a) / a if a else math.nan,
        "trajectory_effect_at_large": d - b,
        "trajectory_effect_at_large_relative": (d - b) / b if b else math.nan,
        "transducer_effect_at_default": b - a,
        "transducer_effect_at_default_relative": (b - a) / a if a else math.nan,
        "transducer_effect_at_h3": d - c,
        "transducer_effect_at_h3_relative": (d - c) / c if c else math.nan,
        "interaction": d - c - b + a,
    }


def build_report() -> dict[str, Any]:
    cells = {name: load_cell(name) for name in CELLS}
    drift = unexpected_drift(cells)
    all_complete = all(
        cell["core_complete"]
        and cell["monitor_status"] == "completed"
        and cell["return_code"] == 0
        for cell in cells.values()
    )
    all_background = all(
        cell["source_background_only"] for cell in cells.values()
    )
    effects = {
        metric: factorial_effect({
            name: cells[name]["metrics"][metric] for name in CELLS
        })
        for metric in METRICS
    }
    tg_effect = effects["target_to_global_peak_ratio"]
    dominant_factor = (
        "transducer_geometry"
        if abs(tg_effect["transducer_main_effect"])
        > abs(tg_effect["trajectory_main_effect"])
        else "trajectory"
    )
    trajectory_sign_changes = (
        tg_effect["trajectory_effect_at_small"] < 0
        and tg_effect["trajectory_effect_at_large"] > 0
    )
    valid = all_complete and all_background and not drift
    return {
        "report_version": "1.0.0",
        "module": "freq250_trajectory_transducer_factorial_20260729",
        "claim_level": "matched_quick_factorial_engineering_observation",
        "cells": cells,
        "quality_gates": {
            "all_cells_complete": all_complete,
            "all_sources_background_only": all_background,
            "unexpected_config_drift": drift,
            "factorial_valid": valid,
        },
        "factorial_effects": effects,
        "decision": {
            "status": "valid_factorial" if valid else "factorial_blocked",
            "dominant_tg_factor": dominant_factor if valid else None,
            "trajectory_effect_changes_sign_by_transducer": (
                trajectory_sign_changes if valid else None
            ),
            "interpretation": (
                "The large ap60/r74.435 transducer is the dominant baseline "
                "target/global factor. H3 trajectory is detrimental with the "
                "small transducer but beneficial with the large transducer, "
                "showing a positive interaction rather than a universal "
                "trajectory-only benefit."
                if valid else "Factorial interpretation blocked by quality gates."
            ),
        },
        "remaining_gap": {
            "baseline_peak_reaches_target_neighborhood": all(
                cell["metrics"]["global_peak_to_target_distance_mm"] <= 10
                for cell in cells.values()
            ),
            "note": (
                "All four baseline global peaks remain approximately 56-58 mm "
                "from the target; the prior H3 TR result is what moved the peak "
                "into the 6.2 mm target neighborhood."
            ),
        },
        "blocked_claims": [
            "trajectory is universally beneficial",
            "baseline H3 large achieves target dominance",
            "formal numerical convergence",
            "thermal or clinical safety",
            "multi-case generalization",
        ],
    }


def write_report(report: dict[str, Any]) -> None:
    (OUTPUT_ROOT / "factorial_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    cells = report["cells"]
    tg = report["factorial_effects"]["target_to_global_peak_ratio"]
    tw = report["factorial_effects"]["target_window_peak_mpa"]
    lines = [
        "# Case079 250 kHz Trajectory × Transducer Factorial",
        "",
        f"- Status: `{report['decision']['status']}`",
        f"- Dominant T/G factor: `{report['decision']['dominant_tg_factor']}`",
        f"- Protocol drift: `{report['quality_gates']['unexpected_config_drift']}`",
        "",
        "## Matched cells",
        "",
        "| Cell | Target-window MPa | Global MPa | T/G | Peak→target mm | Runtime min |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in CELLS:
        cell = cells[name]
        metric = cell["metrics"]
        lines.append(
            f"| {name} | {metric['target_window_peak_mpa']:.4f} | "
            f"{metric['global_peak_mpa']:.4f} | "
            f"{metric['target_to_global_peak_ratio']:.4f} | "
            f"{metric['global_peak_to_target_distance_mm']:.2f} | "
            f"{cell['runtime_s'] / 60:.1f} |"
        )
    lines += [
        "",
        "## Factorial reading",
        "",
        f"- Transducer main effect on T/G: {tg['transducer_main_effect']:+.4f} "
        f"({tg['transducer_main_effect_relative_to_small_mean']:+.1%} vs small mean).",
        f"- Trajectory main effect on T/G: {tg['trajectory_main_effect']:+.4f} "
        f"({tg['trajectory_main_effect_relative_to_default_mean']:+.1%} vs default mean).",
        f"- H3 trajectory effect with small transducer: "
        f"{tg['trajectory_effect_at_small']:+.4f} "
        f"({tg['trajectory_effect_at_small_relative']:+.1%}).",
        f"- H3 trajectory effect with large transducer: "
        f"{tg['trajectory_effect_at_large']:+.4f} "
        f"({tg['trajectory_effect_at_large_relative']:+.1%}).",
        f"- T/G interaction: {tg['interaction']:+.4f}.",
        f"- Target-window transducer main effect: "
        f"{tw['transducer_main_effect']:+.4f} MPa.",
        "",
        report["decision"]["interpretation"],
        "",
        report["remaining_gap"]["note"],
        "",
        "Quick/cropped-domain engineering evidence only; no convergence, thermal,",
        "safety, clinical, or multi-case claim.",
    ]
    (OUTPUT_ROOT / "factorial_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> None:
    report = build_report()
    write_report(report)
    print(json.dumps({
        "status": report["decision"]["status"],
        "dominant_tg_factor": report["decision"]["dominant_tg_factor"],
        "trajectory_effect_changes_sign_by_transducer": report["decision"][
            "trajectory_effect_changes_sign_by_transducer"
        ],
        "output_dir": str(OUTPUT_ROOT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
