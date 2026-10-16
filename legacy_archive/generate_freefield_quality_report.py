from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_summary(directory: Path) -> dict[str, Any]:
    return load_json(directory / "freefield_summary.json")


def pick_run(label: str, directory: Path) -> dict[str, Any]:
    summary = load_summary(directory)
    q = summary["simulation_quality"]
    p = summary["pressure"]
    prof = summary.get("profile_metrics", {})
    return {
        "label": label,
        "path": str(directory),
        "preset": q.get("preset"),
        "quality_level": q.get("quality_level"),
        "is_paper_grade": q.get("is_paper_grade"),
        "dx_mm": q.get("dx_mm"),
        "ppw_min_sound_speed": q.get("ppw_min_sound_speed"),
        "pml_size": q.get("pml_size"),
        "pml_thickness_mm": q.get("pml_size") * q.get("dx_mm"),
        "grid_size": q.get("grid_size"),
        "nt": q.get("nt"),
        "runtime_s": q.get("runtime_s"),
        "memory_estimate_mb": q.get("memory_estimate", {}).get("estimated_mb"),
        "effective_peak_mpa": p.get("effective_peak_mpa"),
        "target_window_peak_mpa": p.get("target_window_peak_mpa"),
        "target_pressure_mpa": p.get("target_pressure_mpa"),
        "effective_peak_to_focus_distance_mm": p.get("effective_peak_to_target_distance_mm"),
        "target_to_effective_peak_ratio": p.get("target_to_effective_peak_ratio"),
        "axial_fwhm_mm": prof.get("axial_fwhm_mm"),
        "lateral_fwhm_mm": prof.get("lateral_fwhm_mm"),
    }


def fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    if isinstance(value, list):
        return "x".join(str(v) for v in value)
    return str(value)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    runs = [
        pick_run("dx1_pml8_standard", Path(args.dx1_dir)),
        pick_run("dx075_pml8_standard", Path(args.dx075_dir)),
        pick_run("dx075_pml12_standard", Path(args.pml12_dir)),
    ]
    grid_comp = load_json(Path(args.grid_comparison))
    pml_comp = load_json(Path(args.pml_comparison))
    return {
        "description": "Free-field calibration quality stage report. This only summarizes existing outputs and does not run k-Wave.",
        "transducer_baseline": {
            "name": "Gao baseline single-bowl transducer",
            "aperture_mm": 25,
            "radius_mm": 30,
            "frequency_khz": 500,
            "source_pressure_mpa": 1,
            "source_pressure_note": "1 MPa is source/excitation pressure, not free-field peak pressure and not transcranial in-situ pressure.",
        },
        "runs": runs,
        "grid_convergence_comparison": grid_comp,
        "pml_boundary_comparison": pml_comp,
        "stage_conclusion": {
            "can_enter_ct_standard_review": True,
            "do_not_run_dx05_now": True,
            "paper_grade": False,
            "summary": (
                "Free-field standard sanity, finer-grid sanity, and PML boundary sanity are internally consistent enough "
                "to stop adding single-case free-field runs and return to CT standard-review planning."
            ),
        },
        "remaining_gaps": [
            "No dx=0.5 mm run was executed.",
            "No full grid-convergence curve or boundary-reflection energy analysis was performed.",
            "No hydrophone/water-tank measurement data were used.",
            "Free-field pressure is not transcranial in-situ pressure.",
        ],
        "recommended_next_step": (
            "Return to 079 CT standard-review planning using calibrated free-field evidence and simulation_quality metadata; "
            "do not continue blind free-field single-case sweeps."
        ),
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    runs = report["runs"]
    grid_changes = report["grid_convergence_comparison"]["changes"]
    pml_changes = report["pml_boundary_comparison"]["changes"]
    lines = [
        "# 自由场校准质量阶段报告",
        "",
        "本报告只汇总已有自由场输出，不运行 k-Wave，不生成新的压力场。",
        "",
        "## 结论",
        "",
        "- 当前自由场阶段可以暂时收口，进入 079 CT standard-review 规划。",
        "- `dx=0.75 mm` finer-grid 与 `dx=1.0 mm` 的焦点位置差异可解释。",
        "- `pml=12` 与 `pml=8` 的 focal metrics 基本一致，当前小型自由场模型没有明显 PML 敏感性信号。",
        "- 当前仍不是 paper-grade：没有 `dx=0.5 mm`、没有完整网格收敛曲线、没有真实水听器测量。",
        "",
        "## 参数边界",
        "",
        "- 使用 Gao baseline：`aperture=25 mm`、`radius=30 mm`、`frequency=500 kHz`、`source pressure=1 MPa`。",
        "- `1 MPa` 是 source/excitation pressure，不是 free-field peak，也不是经颅 in-situ pressure。",
        "- 当前报告只说明单阵元 bowl source 在均匀水介质中的数值 sanity，不代表 CT 经颅结果。",
        "",
        "## 运行汇总",
        "",
        "| run | dx mm | PPW | PML | grid | runtime s | effective peak MPa | target-window peak MPa | focus distance mm | axial FWHM mm | lateral FWHM mm |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in runs:
        lines.append(
            f"| {row['label']} | {fmt(row['dx_mm'])} | {fmt(row['ppw_min_sound_speed'])} | {row['pml_size']} | "
            f"{fmt(row['grid_size'])} | {fmt(row['runtime_s'])} | {fmt(row['effective_peak_mpa'])} | "
            f"{fmt(row['target_window_peak_mpa'])} | {fmt(row['effective_peak_to_focus_distance_mm'])} | "
            f"{fmt(row['axial_fwhm_mm'])} | {fmt(row['lateral_fwhm_mm'])} |"
        )
    lines.extend(
        [
            "",
            "## 网格复核摘要",
            "",
            f"- `dx=0.75 mm` 相对 `dx=1.0 mm`：PPW ratio `{fmt(grid_changes['ppw_ratio'])}`。",
            f"- effective peak 变化 `{fmt(grid_changes['effective_peak_pct_change'])}%`。",
            f"- target-window peak 变化 `{fmt(grid_changes['target_window_peak_pct_change'])}%`。",
            f"- 焦点距离变化 `{fmt(grid_changes['focus_distance_delta_mm'])} mm`。",
            f"- runtime ratio `{fmt(grid_changes['runtime_ratio'])}`，说明 finer-grid 成本明显升高。",
            "",
            "## PML 复核摘要",
            "",
            f"- `pml=12` 相对 `pml=8`：PML 厚度增加 `{fmt(pml_changes['pml_thickness_delta_mm'])} mm`。",
            f"- effective peak 变化 `{fmt(pml_changes['effective_peak_pct_change'], 6)}%`。",
            f"- target-window peak 变化 `{fmt(pml_changes['target_window_peak_pct_change'], 6)}%`。",
            f"- 焦点距离变化 `{fmt(pml_changes['focus_distance_delta_mm'])} mm`。",
            "- focal metrics 基本一致，因此当前小型自由场模型没有明显 PML 敏感性信号。",
            "",
            "## 下一步建议",
            "",
            "- 停止继续追加自由场单 case。",
            "- 不直接跑 `dx=0.5 mm`。",
            "- 回到 079 CT 路线，生成带 free-field reference、preset、PPW/PML/CFL 和 runner 纪律的 CT standard-review 计划。",
            "",
            "## 剩余限制",
            "",
        ]
    )
    for item in report["remaining_gaps"]:
        lines.append(f"- {item}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a free-field calibration quality stage report from existing summaries.")
    parser.add_argument("--dx1-dir", default="outputs/freefield_standard_sanity/ap25_r30_f500_standard")
    parser.add_argument("--dx075-dir", default="outputs/freefield_grid_convergence_runs/ap25_r30_f500_dx0.75")
    parser.add_argument("--pml12-dir", default="outputs/freefield_pml_boundary_runs/ap25_r30_f500_dx0.75_pml12")
    parser.add_argument("--grid-comparison", default="outputs/freefield_grid_convergence_runs/freefield_grid_convergence_comparison.json")
    parser.add_argument("--pml-comparison", default="outputs/freefield_pml_boundary_runs/freefield_pml_boundary_comparison.json")
    parser.add_argument("--output-dir", default="outputs/freefield_quality_report")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(args)
    (output_dir / "freefield_quality_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown(output_dir / "freefield_quality_report.md", report)


if __name__ == "__main__":
    main()
