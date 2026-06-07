from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required JSON file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8-sig")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def run_quality_dry_run(
    *,
    python_exe: Path,
    model_path: Path,
    entry_plan_path: Path,
    output_dir: Path,
    preset: str,
    sim_time_us: float,
    cycles: int,
    quick_lateral_mm: float,
    quick_post_target_mm: float,
    aperture_mm: float,
    radius_mm: float,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(python_exe),
        "simulate_kwave_3d_focus.py",
        "--model",
        str(model_path),
        "--entry-plan",
        str(entry_plan_path),
        "--output-dir",
        str(output_dir),
        "--preset",
        preset,
        "--dry-run-quality",
        "--sim-time-us",
        str(sim_time_us),
        "--cycles",
        str(cycles),
        "--quick-lateral-mm",
        str(quick_lateral_mm),
        "--quick-post-target-mm",
        str(quick_post_target_mm),
        "--aperture-mm",
        str(aperture_mm),
        "--radius-mm",
        str(radius_mm),
    ]
    stdout_path = output_dir / "dry_run_stdout.txt"
    stderr_path = output_dir / "dry_run_stderr.txt"
    with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open("w", encoding="utf-8") as stderr_handle:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            check=False,
            timeout=180,
        )
    summary_path = output_dir / "quality_dry_run_summary.json"
    status = {
        "command": command,
        "exit_code": result.returncode,
        "stdout_path": rel(stdout_path),
        "stderr_path": rel(stderr_path),
        "quality_dry_run_summary": rel(summary_path),
        "quality_dry_run_summary_exists": summary_path.exists(),
        "pressure_output_exists": (output_dir / "pressure_max_mpa.npz").exists(),
    }
    if result.returncode != 0 or not summary_path.exists():
        raise RuntimeError(f"CT quality dry-run failed: {json.dumps(status, ensure_ascii=False, indent=2)}")
    if (output_dir / "pressure_max_mpa.npz").exists():
        raise RuntimeError("Dry-run unexpectedly generated pressure_max_mpa.npz; stopping to avoid blind simulation.")
    return status


def build_runner_command(
    *,
    model_path: Path,
    entry_plan_path: Path,
    output_dir: Path,
    preset: str,
    sim_time_us: float,
    cycles: int,
    quick_lateral_mm: float,
    quick_post_target_mm: float,
    aperture_mm: float,
    radius_mm: float,
    checkpoint_sec: int,
    hard_stop_min: float,
) -> list[str]:
    return [
        str(PYTHON_EXE),
        "run_kwave_command.py",
        "--script",
        "simulate_kwave_3d_focus.py",
        "--output-dir",
        str(output_dir),
        "--preset",
        preset,
        "--model",
        str(model_path),
        "--entry-plan",
        str(entry_plan_path),
        "--sim-time-us",
        str(sim_time_us),
        "--cycles",
        str(cycles),
        "--quick-lateral-mm",
        str(quick_lateral_mm),
        "--quick-post-target-mm",
        str(quick_post_target_mm),
        "--aperture-mm",
        str(aperture_mm),
        "--radius-mm",
        str(radius_mm),
        "--execute",
        "--checkpoint-sec",
        str(checkpoint_sec),
        "--hard-stop-min",
        str(hard_stop_min),
    ]


def summarize_reference_run(summary: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    pressure = summary.get("pressure", {})
    runtime = summary.get("runtime", {})
    source = summary.get("source", {})
    return {
        "target_pressure_mpa": metrics.get("target_pressure_mpa", pressure.get("target_pressure_mpa")),
        "target_window_peak_mpa": metrics.get("target_window_peak_mpa", pressure.get("target_window_peak_mpa")),
        "effective_peak_mpa": metrics.get("effective_peak_mpa", pressure.get("effective_peak_mpa")),
        "effective_peak_to_target_distance_mm": metrics.get(
            "effective_peak_to_target_distance_mm",
            pressure.get("effective_peak_to_target_distance_mm"),
        ),
        "target_to_effective_peak_ratio": metrics.get("target_to_effective_peak_ratio", pressure.get("target_to_effective_peak_ratio")),
        "runtime_s": runtime.get("runtime_s"),
        "source_label_counts": source.get("source_label_counts"),
        "historical_summary_has_simulation_quality": "simulation_quality" in summary,
    }


def build_plan_markdown(plan: dict[str, Any]) -> str:
    q = plan["quality_dry_run"]["simulation_quality"]
    ref = plan["reference_run"]["metrics"]
    runner = " ".join(plan["recommended_runner_command"])
    return f"""# 079 CT Standard-Review Plan

## 目标

把 079 当前最有效的经颅 quick 配置整理为一个可审阅的 standard-review 候选包。本文件只是执行前计划和 dry-run 质量记录，不包含新的 k-Wave 压力场。

## 为什么现在做

- 自由场质量阶段已经完成阶段性收口：`{plan['freefield_quality_report']}`。
- 079 的手工/复用候选已经证明明显优于 smoke baseline，但历史输出缺少统一 `simulation_quality` 字段。
- 下一步若要回到 CT，经项目规则必须先用 dry-run quality 明确 preset、PPW、PML、CFL、grid、runtime 风险和停止条件。

## 候选配置

- case: `{plan['case_id']}`
- model: `{plan['model_path']}`
- entry plan: `{plan['entry_plan_path']}`
- target index: `{plan['entry_plan']['target_index_ijk']}`
- entry offset mm: `{plan['entry_plan']['entry_offset_mm']}`
- source standoff mm: `{plan['entry_plan']['source_standoff_mm']}`
- aperture/radius: `{plan['candidate_config']['aperture_mm']} / {plan['candidate_config']['radius_mm']} mm`
- frequency: `{plan['candidate_config']['frequency_khz']} kHz`
- source pressure: `{plan['candidate_config']['source_pressure_mpa']} MPa`
- source pressure note: 这是 source/excitation pressure，不是 free-field peak pressure，也不是经颅 in-situ pressure。

## 历史参考结果

- target-window peak: `{ref['target_window_peak_mpa']}` MPa
- target pressure: `{ref['target_pressure_mpa']}` MPa
- effective peak: `{ref['effective_peak_mpa']}` MPa
- effective peak to target distance: `{ref['effective_peak_to_target_distance_mm']}` mm
- source label counts: `{ref['source_label_counts']}`
- historical summary has simulation_quality: `{ref['historical_summary_has_simulation_quality']}`

## Dry-Run 质量摘要

- preset: `{q['preset']}`
- quality level: `{q['quality_level']}`
- is paper grade: `{q['is_paper_grade']}`
- PPW at min sound speed: `{q['ppw_min_sound_speed']}`
- dx mm: `{q['dx_mm']}`
- PML size: `{q['pml_size']}`
- CFL: `{q['cfl']}`
- grid size: `{q['grid_size']}`
- nt / dt: `{q['nt']}` / `{q['dt_s']}`
- voxel count: `{q['voxel_count']}`
- memory estimate MB: `{q['memory_estimate']['estimated_mb']}`

## 推荐的下一步命令

这条命令尚未执行。若要真实运行，只建议最多执行这一条，并遵守 2 分钟检查点和 30 分钟硬停止。

```powershell
{runner}
```

## 本轮不做

- 不运行新的 CT k-Wave。
- 不跑 Visible Human。
- 不调 target/entry/aperture。
- 不把该计划写成论文级复现或医学安全结论。

## 停止条件

- dry-run 失败或缺少 `quality_dry_run_summary.json`。
- dry-run 意外生成 `pressure_max_mpa.npz`。
- 未来真实 run 超过硬停止时间仍无 `summary.json` 或 `pressure_max_mpa.npz`。
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a CT standard-review package without running k-Wave.")
    parser.add_argument("--case-id", default="079")
    parser.add_argument("--model", default="outputs/ct_acoustic_models_batch/079_bone300_dx1/acoustic_model_3d.npz")
    parser.add_argument("--entry-plan", default="outputs/case_refinement_plan/079/candidate_006/entry_plan.json")
    parser.add_argument("--reference-run", default="outputs/case_refinement_runs/079_candidate_006_offset_10_0")
    parser.add_argument("--freefield-report", default="outputs/freefield_quality_report/freefield_quality_summary.json")
    parser.add_argument("--output-dir", default="outputs/ct_standard_review_plan/079_candidate_006")
    parser.add_argument("--future-run-dir", default="outputs/ct_standard_review_runs/079_candidate_006_standard")
    parser.add_argument("--preset", choices=["quick", "standard", "paper_grade"], default="standard")
    parser.add_argument("--sim-time-us", type=float, default=55.0)
    parser.add_argument("--cycles", type=int, default=8)
    parser.add_argument("--quick-lateral-mm", type=float, default=17.0)
    parser.add_argument("--quick-post-target-mm", type=float, default=8.0)
    parser.add_argument("--aperture-mm", type=float, default=30.0)
    parser.add_argument("--radius-mm", type=float, default=35.0)
    parser.add_argument("--frequency-khz", type=float, default=500.0)
    parser.add_argument("--source-pressure-mpa", type=float, default=1.0)
    parser.add_argument("--checkpoint-sec", type=int, default=120)
    parser.add_argument("--hard-stop-min", type=float, default=30.0)
    parser.add_argument("--python-exe", default=str(PYTHON_EXE))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    model_path = Path(args.model)
    entry_plan_path = Path(args.entry_plan)
    reference_run = Path(args.reference_run)
    freefield_report_path = Path(args.freefield_report)
    future_run_dir = Path(args.future_run_dir)
    quality_dir = output_dir / "quality_dry_run"

    entry_plan = read_json(entry_plan_path)
    reference_summary = read_json(reference_run / "summary.json")
    reference_metrics = read_json(reference_run / "focus_metrics.json")
    freefield_report = read_json(freefield_report_path)

    dry_status = run_quality_dry_run(
        python_exe=Path(args.python_exe),
        model_path=model_path,
        entry_plan_path=entry_plan_path,
        output_dir=quality_dir,
        preset=args.preset,
        sim_time_us=args.sim_time_us,
        cycles=args.cycles,
        quick_lateral_mm=args.quick_lateral_mm,
        quick_post_target_mm=args.quick_post_target_mm,
        aperture_mm=args.aperture_mm,
        radius_mm=args.radius_mm,
    )
    dry_summary = read_json(quality_dir / "quality_dry_run_summary.json")

    runner_command = build_runner_command(
        model_path=model_path,
        entry_plan_path=entry_plan_path,
        output_dir=future_run_dir,
        preset=args.preset,
        sim_time_us=args.sim_time_us,
        cycles=args.cycles,
        quick_lateral_mm=args.quick_lateral_mm,
        quick_post_target_mm=args.quick_post_target_mm,
        aperture_mm=args.aperture_mm,
        radius_mm=args.radius_mm,
        checkpoint_sec=args.checkpoint_sec,
        hard_stop_min=args.hard_stop_min,
    )
    plan = {
        "description": "079 CT standard-review execution package. This is a dry-run and planning artifact; it does not run k-Wave.",
        "case_id": args.case_id,
        "created_by": Path(__file__).name,
        "evidence_brief": "outputs/evidence_briefs/ct_standard_review/evidence_brief.json",
        "model_path": rel(model_path),
        "entry_plan_path": rel(entry_plan_path),
        "reference_run_dir": rel(reference_run),
        "freefield_quality_report": rel(freefield_report_path),
        "future_run_dir": rel(future_run_dir),
        "candidate_config": {
            "frequency_khz": args.frequency_khz,
            "source_pressure_mpa": args.source_pressure_mpa,
            "source_pressure_definition": "source/excitation pressure; not free-field peak and not transcranial in-situ pressure",
            "aperture_mm": args.aperture_mm,
            "radius_mm": args.radius_mm,
            "cycles": args.cycles,
            "sim_time_us": args.sim_time_us,
            "quick_lateral_mm": args.quick_lateral_mm,
            "quick_post_target_mm": args.quick_post_target_mm,
            "preset": args.preset,
        },
        "entry_plan": entry_plan,
        "reference_run": {
            "metrics": summarize_reference_run(reference_summary, reference_metrics),
            "summary_path": rel(reference_run / "summary.json"),
            "focus_metrics_path": rel(reference_run / "focus_metrics.json"),
        },
        "freefield_quality_context": {
            "report_path": rel(freefield_report_path),
            "stage_conclusion": freefield_report.get("stage_conclusion") or freefield_report.get("conclusion"),
            "source_pressure_note": freefield_report.get("transducer_baseline", {}).get("source_pressure_note"),
        },
        "quality_dry_run": {
            "status": dry_status,
            "summary_path": rel(quality_dir / "quality_dry_run_summary.json"),
            "simulation_quality": dry_summary["simulation_quality"],
            "source": dry_summary["source"],
            "model": dry_summary["model"],
        },
        "recommended_runner_command": runner_command,
        "not_run_this_stage": [
            "No CT k-Wave solve was executed.",
            "No Visible Human or thermal model was executed.",
            "No existing pressure or thermal output directory was overwritten.",
        ],
        "stop_conditions_for_future_run": [
            "Runner dry-run fails or misses quality_dry_run_summary.json.",
            "Future run exceeds hard_stop_min without summary.json or pressure_max_mpa.npz.",
            "Future output shows source mask no longer background-only.",
        ],
        "interpretation_limits": [
            "This is standard-review planning, not paper-grade reproduction.",
            "target_020 is a CT geometric/engineering candidate, not a validated anatomical treatment target.",
            "ap30/r35 is current 079 tuned parameter, not literature consensus.",
        ],
    }

    write_json(output_dir / "ct_standard_review_plan.json", plan)
    write_markdown(output_dir / "ct_standard_review_plan.md", build_plan_markdown(plan))
    write_markdown(
        output_dir / "recommended_runner_command.ps1",
        "# 需要人工确认后再运行；本计划阶段不自动执行 k-Wave。\n"
        + " ".join(runner_command)
        + "\n",
    )

    print(json.dumps({"status": "planned_not_executed", "output_dir": rel(output_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
