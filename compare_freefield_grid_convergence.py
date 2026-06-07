from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent


def load_summary(path: Path) -> dict[str, Any]:
    summary_path = path / "freefield_summary.json" if path.is_dir() else path
    return json.loads(summary_path.read_text(encoding="utf-8"))


def pick(summary: dict[str, Any]) -> dict[str, Any]:
    q = summary["simulation_quality"]
    p = summary["pressure"]
    prof = summary.get("profile_metrics", {})
    return {
        "dx_mm": q.get("dx_mm"),
        "preset": q.get("preset"),
        "quality_level": q.get("quality_level"),
        "is_paper_grade": q.get("is_paper_grade"),
        "ppw_min_sound_speed": q.get("ppw_min_sound_speed"),
        "grid_size": q.get("grid_size"),
        "voxel_count": q.get("voxel_count"),
        "nt": q.get("nt"),
        "dt_ns": None if q.get("dt_s") is None else q["dt_s"] * 1e9,
        "runtime_s": q.get("runtime_s"),
        "memory_estimate_mb": q.get("memory_estimate", {}).get("estimated_mb"),
        "effective_peak_mpa": p.get("effective_peak_mpa"),
        "target_window_peak_mpa": p.get("target_window_peak_mpa"),
        "target_pressure_mpa": p.get("target_pressure_mpa"),
        "effective_peak_to_geometric_focus_distance_mm": p.get("effective_peak_to_target_distance_mm"),
        "target_to_effective_peak_ratio": p.get("target_to_effective_peak_ratio"),
        "axial_fwhm_mm": prof.get("axial_fwhm_mm"),
        "lateral_fwhm_mm": prof.get("lateral_fwhm_mm"),
        "effective_peak_relative_to_focus_mm": prof.get("effective_peak_relative_to_focus_mm"),
    }


def ratio(candidate: float | None, baseline: float | None) -> float | None:
    if candidate is None or baseline in (None, 0):
        return None
    return float(candidate) / float(baseline)


def pct_change(candidate: float | None, baseline: float | None) -> float | None:
    r = ratio(candidate, baseline)
    return None if r is None else (r - 1.0) * 100.0


def build_comparison(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "description": "Free-field grid convergence comparison. This compares existing summaries and does not run k-Wave.",
        "baseline": baseline,
        "candidate": candidate,
        "changes": {
            "ppw_ratio": ratio(candidate["ppw_min_sound_speed"], baseline["ppw_min_sound_speed"]),
            "runtime_ratio": ratio(candidate["runtime_s"], baseline["runtime_s"]),
            "voxel_count_ratio": ratio(candidate["voxel_count"], baseline["voxel_count"]),
            "effective_peak_pct_change": pct_change(candidate["effective_peak_mpa"], baseline["effective_peak_mpa"]),
            "target_window_peak_pct_change": pct_change(candidate["target_window_peak_mpa"], baseline["target_window_peak_mpa"]),
            "focus_distance_delta_mm": (
                None
                if candidate["effective_peak_to_geometric_focus_distance_mm"] is None
                or baseline["effective_peak_to_geometric_focus_distance_mm"] is None
                else candidate["effective_peak_to_geometric_focus_distance_mm"]
                - baseline["effective_peak_to_geometric_focus_distance_mm"]
            ),
            "axial_fwhm_delta_mm": (
                None
                if candidate["axial_fwhm_mm"] is None or baseline["axial_fwhm_mm"] is None
                else candidate["axial_fwhm_mm"] - baseline["axial_fwhm_mm"]
            ),
            "lateral_fwhm_delta_mm": (
                None
                if candidate["lateral_fwhm_mm"] is None or baseline["lateral_fwhm_mm"] is None
                else candidate["lateral_fwhm_mm"] - baseline["lateral_fwhm_mm"]
            ),
        },
        "interpretation": [
            "Both runs are standard sanity / grid-convergence checks, not paper-grade reproduction.",
            "Compare focal-region/effective peak and focus coordinate instead of treating source/global peak as calibration truth.",
            "If the finer grid changes focal metrics substantially, run at least one additional convergence point before using the result for stronger claims.",
        ],
    }


def fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def write_markdown(path: Path, comparison: dict[str, Any]) -> None:
    b = comparison["baseline"]
    c = comparison["candidate"]
    ch = comparison["changes"]
    lines = [
        "# 自由场网格收敛对比",
        "",
        "本报告只比较已有 `freefield_summary.json`，不运行 k-Wave，不生成新的压力场。",
        "",
        "## 对比表",
        "",
        "| 指标 | dx=1.0 mm baseline | dx=0.75 mm candidate | 变化 |",
        "|---|---:|---:|---:|",
        f"| PPW | {fmt(b['ppw_min_sound_speed'])} | {fmt(c['ppw_min_sound_speed'])} | ratio {fmt(ch['ppw_ratio'])} |",
        f"| grid | {'x'.join(map(str, b['grid_size']))} | {'x'.join(map(str, c['grid_size']))} | - |",
        f"| runtime s | {fmt(b['runtime_s'])} | {fmt(c['runtime_s'])} | ratio {fmt(ch['runtime_ratio'])} |",
        f"| effective peak MPa | {fmt(b['effective_peak_mpa'])} | {fmt(c['effective_peak_mpa'])} | {fmt(ch['effective_peak_pct_change'])}% |",
        f"| target-window peak MPa | {fmt(b['target_window_peak_mpa'])} | {fmt(c['target_window_peak_mpa'])} | {fmt(ch['target_window_peak_pct_change'])}% |",
        f"| focus distance mm | {fmt(b['effective_peak_to_geometric_focus_distance_mm'])} | {fmt(c['effective_peak_to_geometric_focus_distance_mm'])} | {fmt(ch['focus_distance_delta_mm'])} |",
        f"| axial FWHM mm | {fmt(b['axial_fwhm_mm'])} | {fmt(c['axial_fwhm_mm'])} | {fmt(ch['axial_fwhm_delta_mm'])} |",
        f"| lateral FWHM mm | {fmt(b['lateral_fwhm_mm'])} | {fmt(c['lateral_fwhm_mm'])} | {fmt(ch['lateral_fwhm_delta_mm'])} |",
        "",
        "## 结论边界",
        "",
        "- `dx=0.75 mm` 结果仍是 standard sanity / finer-grid check，不是 paper-grade。",
        "- 本轮没有运行 `dx=0.5 mm`，也没有完成完整网格收敛。",
        "- 后续若要支撑更强结论，需要至少增加一个 convergence 点，并补 PML/边界反射复核。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two free-field grid sanity summaries.")
    parser.add_argument("--baseline-dir", required=True)
    parser.add_argument("--candidate-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline = pick(load_summary(Path(args.baseline_dir)))
    candidate = pick(load_summary(Path(args.candidate_dir)))
    comparison = build_comparison(baseline, candidate)
    (output_dir / "freefield_grid_convergence_comparison.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown(output_dir / "freefield_grid_convergence_comparison.md", comparison)


if __name__ == "__main__":
    main()
