from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from simulate_freefield_transducer import (
    FreefieldConfig,
    KWave3DConfig,
    PROJECT_ROOT,
    build_freefield_model,
    build_source_mask,
    medium_properties,
    quality_metadata,
)


def parse_float_list(value: str) -> list[float]:
    values: list[float] = []
    for part in value.split(","):
        stripped = part.strip()
        if not stripped:
            continue
        values.append(float(stripped))
    if not values:
        raise argparse.ArgumentTypeError("expected a comma-separated list, for example 1.0,0.75,0.5")
    return values


def risk_level(relative_work: float, memory_mb: float, ppw: float) -> str:
    if memory_mb > 1500 or relative_work > 20:
        return "very_high"
    if memory_mb > 750 or relative_work > 8:
        return "high"
    if memory_mb > 250 or relative_work > 3:
        return "medium"
    if ppw < 3.0:
        return "medium_ppw_limited"
    return "low"


def recommendation_note(row: dict[str, Any]) -> str:
    notes: list[str] = []
    if row["dx_mm"] == 1.0:
        notes.append("existing_standard_sanity_grid")
    if row["ppw_min_sound_speed"] < 3.0:
        notes.append("ppw_below_3")
    if row["risk_level"] in {"high", "very_high"}:
        notes.append("runtime_or_memory_risk")
    if row["dx_mm"] == 0.75:
        notes.append("preferred_next_finer_grid_candidate")
    if row["dx_mm"] <= 0.5:
        notes.append("risk_estimate_only_until_user_confirms")
    return ";".join(notes) if notes else "candidate"


def build_case(args: argparse.Namespace, dx_mm: float) -> dict[str, Any]:
    config = FreefieldConfig(
        aperture_mm=args.aperture_mm,
        radius_mm=args.radius_mm,
        frequency_khz=args.frequency_khz,
        source_pressure_mpa=args.source_pressure_mpa,
        medium=args.medium,
        dx_mm=dx_mm,
        cycles=args.cycles,
        sim_time_us=args.sim_time_us,
        cfl=args.cfl,
        pml_size=args.pml_size,
        preset=args.preset,
        source_margin_mm=args.source_margin_mm,
        post_focus_mm=args.post_focus_mm,
        lateral_margin_mm=args.lateral_margin_mm,
        nearfield_mm=args.nearfield_mm,
    )
    model, model_metadata = build_freefield_model(config)
    props = medium_properties(config.medium)
    _, source_metadata = build_source_mask(
        model,
        KWave3DConfig(
            frequency_hz=config.frequency_khz * 1e3,
            source_pressure_pa=config.source_pressure_mpa * 1e6,
            transducer_radius_m=config.radius_mm * 1e-3,
            aperture_diameter_m=config.aperture_mm * 1e-3,
            tone_burst_cycles=config.cycles,
            cfl=config.cfl,
            pml_size=config.pml_size,
            preset=config.preset,
            alpha_power=props["alpha_power"],
            nearfield_exclusion_m=config.nearfield_mm * 1e-3,
        ),
    )
    auto_time_s = (
        ((config.radius_mm + config.post_focus_mm) * 1e-3 / props["sound_speed_m_s"])
        + config.cycles / (config.frequency_khz * 1e3)
        + 8e-6
    )
    simulation_time_s = config.sim_time_us * 1e-6 if config.sim_time_us is not None else auto_time_s
    quality = quality_metadata(model, config, simulation_time_s)
    return {
        "config": asdict(config),
        "model": model_metadata,
        "source": source_metadata,
        "simulation_quality": quality,
    }


def choose_recommended(rows: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [row for row in rows if row["risk_level"] != "very_high"]
    preferred = [row for row in usable if abs(row["dx_mm"] - 0.75) < 1e-9]
    if preferred:
        return preferred[0]
    finer_than_one = [row for row in usable if row["dx_mm"] < 1.0]
    if finer_than_one:
        return sorted(finer_than_one, key=lambda r: (r["relative_work_estimate"], r["dx_mm"]))[0]
    return sorted(rows, key=lambda r: (r["relative_work_estimate"], r["dx_mm"]))[0]


def flatten_case(case: dict[str, Any], baseline_work: float | None = None) -> dict[str, Any]:
    quality = case["simulation_quality"]
    model = case["model"]
    source = case["source"]
    work = float(quality["voxel_count"]) * float(quality["nt"])
    relative_work = 1.0 if baseline_work is None or baseline_work <= 0 else work / baseline_work
    memory_mb = float(quality["memory_estimate"]["estimated_mb"])
    row = {
        "dx_mm": float(quality["dx_mm"]),
        "preset": quality["preset"],
        "quality_level": quality["quality_level"],
        "medium": model["medium"],
        "grid_size": "x".join(str(v) for v in quality["grid_size"]),
        "voxel_count": int(quality["voxel_count"]),
        "dt_ns": float(quality["dt_s"]) * 1e9,
        "nt": int(quality["nt"]),
        "simulation_time_us": float(quality["simulation_time_s"]) * 1e6,
        "ppw_min_sound_speed": float(quality["ppw_min_sound_speed"]),
        "pml_size": int(quality["pml_size"]),
        "pml_thickness_mm": float(quality["pml_size"]) * float(quality["dx_mm"]),
        "cfl": float(quality["cfl"]),
        "memory_estimate_mb": memory_mb,
        "work_estimate_voxel_steps": work,
        "relative_work_estimate": relative_work,
        "source_points": int(source["source_points"]),
        "geometric_focus_distance_mm": float(model["geometric_focus_distance_mm"]),
    }
    row["risk_level"] = risk_level(relative_work, memory_mb, row["ppw_min_sound_speed"])
    row["recommendation_note"] = recommendation_note(row)
    return row


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "dx_mm",
        "preset",
        "quality_level",
        "medium",
        "grid_size",
        "voxel_count",
        "dt_ns",
        "nt",
        "simulation_time_us",
        "ppw_min_sound_speed",
        "pml_size",
        "pml_thickness_mm",
        "cfl",
        "memory_estimate_mb",
        "work_estimate_voxel_steps",
        "relative_work_estimate",
        "source_points",
        "geometric_focus_distance_mm",
        "risk_level",
        "recommendation_note",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def powershell_command(args: argparse.Namespace, recommended: dict[str, Any]) -> str:
    output_dir = (
        PROJECT_ROOT
        / "outputs"
        / "freefield_grid_convergence_runs"
        / f"ap{args.aperture_mm:g}_r{args.radius_mm:g}_f{args.frequency_khz:g}_dx{recommended['dx_mm']:g}"
    )
    parts = [
        r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe",
        "run_kwave_command.py",
        "--script",
        "simulate_freefield_transducer.py",
        "--output-dir",
        str(output_dir),
        "--preset",
        args.preset,
        "--aperture-mm",
        f"{args.aperture_mm:g}",
        "--radius-mm",
        f"{args.radius_mm:g}",
        "--frequency-khz",
        f"{args.frequency_khz:g}",
        "--source-pressure-mpa",
        f"{args.source_pressure_mpa:g}",
        "--medium",
        args.medium,
        "--dx-mm",
        f"{recommended['dx_mm']:g}",
        "--execute",
        "--checkpoint-sec",
        "120",
        "--hard-stop-min",
        "30",
    ]
    return " ".join(parts)


def write_recommendation(path: Path, args: argparse.Namespace, recommended: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    lines = [
        "# 自由场网格收敛下一步建议",
        "",
        "本文件只来自 dry-run 质量估算，没有运行 k-Wave，也没有生成压力场。",
        "",
        "## 推荐候选",
        "",
        f"- dx: {recommended['dx_mm']:.3f} mm",
        f"- PPW: {recommended['ppw_min_sound_speed']:.3f}",
        f"- grid: {recommended['grid_size']}",
        f"- nt: {recommended['nt']}",
        f"- memory estimate: {recommended['memory_estimate_mb']:.3f} MB",
        f"- relative work estimate: {recommended['relative_work_estimate']:.2f}x",
        f"- risk level: {recommended['risk_level']}",
        "",
        "## 为什么不是直接跑全部",
        "",
        "- 当前目标是判断下一次 finer-grid sanity 应该选哪个点，不是批量执行收敛实验。",
        "- 后续最多先跑 1 个 finer-grid 候选；真实运行必须通过 `run_kwave_command.py --execute`。",
        "- `0.5 mm` 默认只作为风险估算点，除非用户明确确认并接受更高运行成本。",
        "",
        "## 推荐 runner 命令模板",
        "",
        "```powershell",
        powershell_command(args, recommended),
        "```",
        "",
        "## 所有候选概览",
        "",
        "| dx mm | PPW | grid | nt | memory MB | relative work | risk |",
        "|---:|---:|---|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['dx_mm']:.3f} | {row['ppw_min_sound_speed']:.3f} | {row['grid_size']} | "
            f"{row['nt']} | {row['memory_estimate_mb']:.3f} | {row['relative_work_estimate']:.2f} | {row['risk_level']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan free-field grid convergence dry-runs without running k-Wave.")
    parser.add_argument("--aperture-mm", type=float, default=25.0)
    parser.add_argument("--radius-mm", type=float, default=30.0)
    parser.add_argument("--frequency-khz", type=float, default=500.0)
    parser.add_argument("--source-pressure-mpa", type=float, default=1.0)
    parser.add_argument("--medium", choices=["water", "soft"], default="water")
    parser.add_argument("--dx-mm", type=parse_float_list, default=[1.0, 0.75, 0.5])
    parser.add_argument("--preset", choices=["smoke", "quick", "standard", "paper_grade"], default="standard")
    parser.add_argument("--cycles", type=int, default=6)
    parser.add_argument("--sim-time-us", type=float, default=None)
    parser.add_argument("--cfl", type=float, default=0.20)
    parser.add_argument("--pml-size", type=int, default=8)
    parser.add_argument("--source-margin-mm", type=float, default=10.0)
    parser.add_argument("--post-focus-mm", type=float, default=18.0)
    parser.add_argument("--lateral-margin-mm", type=float, default=12.0)
    parser.add_argument("--nearfield-mm", type=float, default=10.0)
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "outputs" / "freefield_grid_convergence_plan" / "ap25_r30_f500"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cases = [build_case(args, dx_mm) for dx_mm in args.dx_mm]
    baseline_case = max(cases, key=lambda case: case["simulation_quality"]["dx_mm"])
    baseline_work = float(baseline_case["simulation_quality"]["voxel_count"]) * float(baseline_case["simulation_quality"]["nt"])
    rows = [flatten_case(case, baseline_work) for case in cases]
    rows = sorted(rows, key=lambda row: row["dx_mm"], reverse=True)
    recommended = choose_recommended(rows)

    write_csv(output_dir / "grid_convergence_plan.csv", rows)
    plan = {
        "description": "Free-field grid convergence dry-run plan. This did not run k-Wave and did not generate pressure fields.",
        "dry_run_only": True,
        "baseline": {
            "transducer": "Gao baseline ap25/r30/f500/source=1 MPa unless overridden by CLI.",
            "source_pressure_definition": "source/excitation pressure, not free-field peak and not transcranial in-situ pressure.",
        },
        "inputs": {
            "aperture_mm": args.aperture_mm,
            "radius_mm": args.radius_mm,
            "frequency_khz": args.frequency_khz,
            "source_pressure_mpa": args.source_pressure_mpa,
            "medium": args.medium,
            "dx_mm": args.dx_mm,
            "preset": args.preset,
            "cycles": args.cycles,
            "cfl": args.cfl,
            "pml_size": args.pml_size,
        },
        "candidates": rows,
        "recommended_next_run": recommended,
        "recommended_runner_command": powershell_command(args, recommended),
        "guardrails": [
            "No k-Wave was run by this planning script.",
            "Run at most one finer-grid candidate next.",
            "Use run_kwave_command.py --execute for any real k-Wave run.",
            "Do not label the next run as paper-grade without grid comparison and PML/CFL review.",
        ],
    }
    (output_dir / "grid_convergence_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    write_recommendation(output_dir / "recommended_next_run.md", args, recommended, rows)
    (output_dir / "recommended_runner_command.ps1").write_text(
        "# 需要用户明确确认后再运行。本文件只是推荐命令模板。\n"
        "# This command uses run_kwave_command.py and explicitly includes --execute.\n"
        + powershell_command(args, recommended)
        + "\n",
        encoding="utf-8-sig",
    )


if __name__ == "__main__":
    main()
