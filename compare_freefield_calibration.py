from __future__ import annotations

import argparse
import json
from pathlib import Path

from simulate_kwave_3d_focus import PROJECT_ROOT


def read_summary(path: Path) -> dict[str, object]:
    summary_path = path / "freefield_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing freefield summary: {summary_path}")
    return json.loads(summary_path.read_text(encoding="utf-8"))


def value(summary: dict[str, object], *keys: str) -> object:
    current: object = summary
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def row(label: str, baseline: object, candidate: object) -> str:
    return f"| {label} | {baseline} | {candidate} |\n"


def build_comparison(baseline_dir: Path, candidate_dir: Path) -> dict[str, object]:
    baseline = read_summary(baseline_dir)
    candidate = read_summary(candidate_dir)
    metrics = [
        ("global_peak_mpa", ("pressure", "global_peak_mpa")),
        ("effective_peak_mpa", ("pressure", "effective_peak_mpa")),
        ("target_pressure_mpa", ("pressure", "target_pressure_mpa")),
        ("target_window_peak_mpa", ("pressure", "target_window_peak_mpa")),
        ("effective_peak_to_geometric_focus_distance_mm", ("pressure", "effective_peak_to_target_distance_mm")),
        ("axial_fwhm_mm", ("profile_metrics", "axial_fwhm_mm")),
        ("lateral_fwhm_mm", ("profile_metrics", "lateral_fwhm_mm")),
        ("runtime_s", ("runtime", "runtime_s")),
    ]
    comparison = {
        "description": "Free-field transducer calibration comparison.",
        "baseline_dir": str(baseline_dir),
        "candidate_dir": str(candidate_dir),
        "baseline_role": "Gao baseline ap25/r30/f500",
        "candidate_role": "current 079 tuned ap30/r35/f500",
        "boundary_note": "Free-field pressure is not transcranial target in-situ pressure.",
        "baseline_config": baseline.get("config", {}),
        "candidate_config": candidate.get("config", {}),
        "metrics": {},
    }
    for metric_id, path in metrics:
        comparison["metrics"][metric_id] = {
            "baseline": value(baseline, *path),
            "candidate": value(candidate, *path),
        }
    return comparison


def write_report(output_dir: Path, comparison: dict[str, object]) -> None:
    metrics = comparison["metrics"]
    text = "\n".join(
        [
            "# 自由场/水槽换能器校准对比报告",
            "",
            "## 结论边界",
            "",
            "- `ap25/r30/f500` 是 Gao2022 baseline 换能器几何。",
            "- `ap30/r35/f500` 是当前 079 quick tuned 参数，不是文献共识。",
            "- 这里报告的是均匀介质自由场结果，不能直接等同于经颅目标区 in situ pressure。",
            "- 本阶段是 quick free-field sanity check，不是论文级水听器实测复现。",
            "",
            "## 参数对比",
            "",
            "| 指标 | Gao baseline ap25/r30 | 当前 tuned ap30/r35 |",
            "|---|---:|---:|",
            row("global peak MPa", metrics["global_peak_mpa"]["baseline"], metrics["global_peak_mpa"]["candidate"]).strip(),
            row("effective peak MPa", metrics["effective_peak_mpa"]["baseline"], metrics["effective_peak_mpa"]["candidate"]).strip(),
            row("geometric focus pressure MPa", metrics["target_pressure_mpa"]["baseline"], metrics["target_pressure_mpa"]["candidate"]).strip(),
            row("focus-window peak MPa", metrics["target_window_peak_mpa"]["baseline"], metrics["target_window_peak_mpa"]["candidate"]).strip(),
            row("effective peak to geometric focus mm", metrics["effective_peak_to_geometric_focus_distance_mm"]["baseline"], metrics["effective_peak_to_geometric_focus_distance_mm"]["candidate"]).strip(),
            row("axial FWHM mm", metrics["axial_fwhm_mm"]["baseline"], metrics["axial_fwhm_mm"]["candidate"]).strip(),
            row("lateral FWHM mm", metrics["lateral_fwhm_mm"]["baseline"], metrics["lateral_fwhm_mm"]["candidate"]).strip(),
            row("runtime s", metrics["runtime_s"]["baseline"], metrics["runtime_s"]["candidate"]).strip(),
            "",
            "## 后续使用规则",
            "",
            "- 经颅仿真继续使用任何换能器参数前，应先引用本自由场校准输出。",
            "- 如果自由场有效焦点明显偏离几何焦点，优先检查 bowl source 朝向、相位/延迟定义和网格分辨率。",
            "- 若后续要写论文级结论，需要升级到 standard/paper preset，并补充 PPW/PML/CFL 和网格收敛报告。",
            "",
        ]
    )
    (output_dir / "freefield_calibration_report.md").write_text(text, encoding="utf-8-sig")
    (output_dir / "freefield_comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two free-field transducer calibration runs.")
    parser.add_argument("--baseline-dir", required=True)
    parser.add_argument("--candidate-dir", required=True)
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "outputs" / "freefield_calibration"))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_report(output_dir, build_comparison(Path(args.baseline_dir), Path(args.candidate_dir)))
