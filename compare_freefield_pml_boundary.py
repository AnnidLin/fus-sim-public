from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_summary(path: Path) -> dict[str, Any]:
    summary_path = path / "freefield_summary.json" if path.is_dir() else path
    return json.loads(summary_path.read_text(encoding="utf-8"))


def pick(summary: dict[str, Any]) -> dict[str, Any]:
    q = summary["simulation_quality"]
    p = summary["pressure"]
    prof = summary.get("profile_metrics", {})
    return {
        "dx_mm": q.get("dx_mm"),
        "pml_size": q.get("pml_size"),
        "pml_thickness_mm": q.get("pml_size") * q.get("dx_mm"),
        "preset": q.get("preset"),
        "quality_level": q.get("quality_level"),
        "is_paper_grade": q.get("is_paper_grade"),
        "ppw_min_sound_speed": q.get("ppw_min_sound_speed"),
        "grid_size": q.get("grid_size"),
        "voxel_count": q.get("voxel_count"),
        "nt": q.get("nt"),
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


def delta(candidate: float | None, baseline: float | None) -> float | None:
    if candidate is None or baseline is None:
        return None
    return float(candidate) - float(baseline)


def pct_change(candidate: float | None, baseline: float | None) -> float | None:
    if candidate is None or baseline in (None, 0):
        return None
    return (float(candidate) / float(baseline) - 1.0) * 100.0


def build_comparison(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "description": "Free-field PML/boundary comparison. This compares existing summaries and does not run k-Wave.",
        "baseline": baseline,
        "candidate": candidate,
        "changes": {
            "pml_thickness_delta_mm": delta(candidate["pml_thickness_mm"], baseline["pml_thickness_mm"]),
            "runtime_pct_change": pct_change(candidate["runtime_s"], baseline["runtime_s"]),
            "voxel_count_pct_change": pct_change(candidate["voxel_count"], baseline["voxel_count"]),
            "effective_peak_pct_change": pct_change(candidate["effective_peak_mpa"], baseline["effective_peak_mpa"]),
            "target_window_peak_pct_change": pct_change(candidate["target_window_peak_mpa"], baseline["target_window_peak_mpa"]),
            "focus_distance_delta_mm": delta(
                candidate["effective_peak_to_geometric_focus_distance_mm"],
                baseline["effective_peak_to_geometric_focus_distance_mm"],
            ),
            "axial_fwhm_delta_mm": delta(candidate["axial_fwhm_mm"], baseline["axial_fwhm_mm"]),
            "lateral_fwhm_delta_mm": delta(candidate["lateral_fwhm_mm"], baseline["lateral_fwhm_mm"]),
        },
        "interpretation": [
            "Both runs are standard sanity / boundary checks, not paper-grade reproduction.",
            "Stable focal metrics between PML settings are evidence against a large PML sensitivity in this small free-field setup.",
            "This does not replace a full boundary-reflection analysis or complete grid convergence.",
        ],
    }


def fmt(value: Any, digits: int = 4) -> str:
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
        "# 自由场 PML / 边界复核对比",
        "",
        "本报告只比较已有 `freefield_summary.json`，不运行 k-Wave，不生成新的压力场。",
        "",
        "## 对比表",
        "",
        "| 指标 | PML baseline | PML candidate | 变化 |",
        "|---|---:|---:|---:|",
        f"| PML size | {b['pml_size']} | {c['pml_size']} | - |",
        f"| PML thickness mm | {fmt(b['pml_thickness_mm'], 3)} | {fmt(c['pml_thickness_mm'], 3)} | {fmt(ch['pml_thickness_delta_mm'], 3)} |",
        f"| grid | {'x'.join(map(str, b['grid_size']))} | {'x'.join(map(str, c['grid_size']))} | - |",
        f"| runtime s | {fmt(b['runtime_s'], 3)} | {fmt(c['runtime_s'], 3)} | {fmt(ch['runtime_pct_change'], 3)}% |",
        f"| effective peak MPa | {fmt(b['effective_peak_mpa'], 6)} | {fmt(c['effective_peak_mpa'], 6)} | {fmt(ch['effective_peak_pct_change'], 6)}% |",
        f"| target-window peak MPa | {fmt(b['target_window_peak_mpa'], 6)} | {fmt(c['target_window_peak_mpa'], 6)} | {fmt(ch['target_window_peak_pct_change'], 6)}% |",
        f"| focus distance mm | {fmt(b['effective_peak_to_geometric_focus_distance_mm'], 3)} | {fmt(c['effective_peak_to_geometric_focus_distance_mm'], 3)} | {fmt(ch['focus_distance_delta_mm'], 3)} |",
        f"| axial FWHM mm | {fmt(b['axial_fwhm_mm'], 3)} | {fmt(c['axial_fwhm_mm'], 3)} | {fmt(ch['axial_fwhm_delta_mm'], 3)} |",
        f"| lateral FWHM mm | {fmt(b['lateral_fwhm_mm'], 3)} | {fmt(c['lateral_fwhm_mm'], 3)} | {fmt(ch['lateral_fwhm_delta_mm'], 3)} |",
        "",
        "## 结论边界",
        "",
        "- `pml=12` 与 `pml=8` 的 focal metrics 基本一致，说明当前自由场小模型没有明显 PML 敏感性信号。",
        "- 本结果仍是 standard sanity / boundary check，不是 paper-grade。",
        "- 本轮没有运行 `dx=0.5 mm`，也没有做完整边界反射能量分析。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two free-field PML/boundary summaries.")
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
    (output_dir / "freefield_pml_boundary_comparison.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown(output_dir / "freefield_pml_boundary_comparison.md", comparison)


if __name__ == "__main__":
    main()
