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


def parse_int_list(value: str) -> list[int]:
    values: list[int] = []
    for part in value.split(","):
        stripped = part.strip()
        if stripped:
            values.append(int(stripped))
    if not values:
        raise argparse.ArgumentTypeError("expected a comma-separated list, for example 8,12,16")
    return values


def pml_risk(row: dict[str, Any]) -> str:
    if row["pml_size"] < 8:
        return "high_pml_too_thin"
    if row["relative_work_estimate"] > 4:
        return "high_runtime_risk"
    if row["pml_thickness_mm"] < 6:
        return "medium_thin_physical_pml"
    if row["pml_size"] >= 12:
        return "low_candidate"
    return "medium_baseline"


def build_case(args: argparse.Namespace, pml_size: int) -> dict[str, Any]:
    config = FreefieldConfig(
        aperture_mm=args.aperture_mm,
        radius_mm=args.radius_mm,
        frequency_khz=args.frequency_khz,
        source_pressure_mpa=args.source_pressure_mpa,
        medium=args.medium,
        dx_mm=args.dx_mm,
        cycles=args.cycles,
        sim_time_us=args.sim_time_us,
        cfl=args.cfl,
        pml_size=pml_size,
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


def flatten_case(case: dict[str, Any], baseline_work: float) -> dict[str, Any]:
    quality = case["simulation_quality"]
    model = case["model"]
    source = case["source"]
    work = float(quality["voxel_count"]) * float(quality["nt"])
    row = {
        "pml_size": int(quality["pml_size"]),
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
        "pml_thickness_mm": float(quality["pml_size"]) * float(quality["dx_mm"]),
        "cfl": float(quality["cfl"]),
        "memory_estimate_mb": float(quality["memory_estimate"]["estimated_mb"]),
        "work_estimate_voxel_steps": work,
        "relative_work_estimate": 1.0 if baseline_work <= 0 else work / baseline_work,
        "source_points": int(source["source_points"]),
        "source_margin_mm": float(case["config"]["source_margin_mm"]),
        "post_focus_mm": float(case["config"]["post_focus_mm"]),
        "geometric_focus_distance_mm": float(model["geometric_focus_distance_mm"]),
    }
    row["risk_level"] = pml_risk(row)
    return row


def choose_recommended(rows: list[dict[str, Any]]) -> dict[str, Any]:
    preferred = [row for row in rows if row["pml_size"] == 12 and not row["risk_level"].startswith("high")]
    if preferred:
        return preferred[0]
    usable = [row for row in rows if not row["risk_level"].startswith("high")]
    if usable:
        return sorted(usable, key=lambda row: (abs(row["pml_size"] - 12), row["relative_work_estimate"]))[0]
    return sorted(rows, key=lambda row: row["relative_work_estimate"])[0]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "pml_size",
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
        "pml_thickness_mm",
        "cfl",
        "memory_estimate_mb",
        "work_estimate_voxel_steps",
        "relative_work_estimate",
        "source_points",
        "source_margin_mm",
        "post_focus_mm",
        "geometric_focus_distance_mm",
        "risk_level",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def runner_command(args: argparse.Namespace, recommended: dict[str, Any]) -> str:
    output_dir = (
        PROJECT_ROOT
        / "outputs"
        / "freefield_pml_boundary_runs"
        / f"ap{args.aperture_mm:g}_r{args.radius_mm:g}_f{args.frequency_khz:g}_dx{args.dx_mm:g}_pml{recommended['pml_size']}"
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
        f"{args.dx_mm:g}",
        "--pml-size",
        str(recommended["pml_size"]),
        "--execute",
        "--checkpoint-sec",
        "120",
        "--hard-stop-min",
        "30",
    ]
    return " ".join(parts)


def write_recommendation(path: Path, args: argparse.Namespace, recommended: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    lines = [
        "# 自由场 PML / 边界复核下一步建议",
        "",
        "本文件只来自 dry-run 质量估算，没有运行 k-Wave，也没有生成压力场。",
        "",
        "## 推荐候选",
        "",
        f"- dx: {recommended['dx_mm']:.3f} mm",
        f"- PML size: {recommended['pml_size']}",
        f"- PML thickness: {recommended['pml_thickness_mm']:.3f} mm",
        f"- grid: {recommended['grid_size']}",
        f"- nt: {recommended['nt']}",
        f"- relative work estimate: {recommended['relative_work_estimate']:.2f}x",
        f"- risk level: {recommended['risk_level']}",
        "",
        "## 执行边界",
        "",
        "- 当前目标是规划 PML/边界复核，不是直接证明边界反射已消除。",
        "- 后续最多先跑 1 个 PML 候选；真实运行必须通过 `run_kwave_command.py --execute`。",
        "- 不要把 PML dry-run 或单次 PML run 写成 paper-grade reproduction。",
        "",
        "## 推荐 runner 命令模板",
        "",
        "```powershell",
        runner_command(args, recommended),
        "```",
        "",
        "## 候选概览",
        "",
        "| PML size | thickness mm | grid | nt | relative work | risk |",
        "|---:|---:|---|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['pml_size']} | {row['pml_thickness_mm']:.3f} | {row['grid_size']} | "
            f"{row['nt']} | {row['relative_work_estimate']:.2f} | {row['risk_level']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan free-field PML/boundary dry-run review without running k-Wave.")
    parser.add_argument("--aperture-mm", type=float, default=25.0)
    parser.add_argument("--radius-mm", type=float, default=30.0)
    parser.add_argument("--frequency-khz", type=float, default=500.0)
    parser.add_argument("--source-pressure-mpa", type=float, default=1.0)
    parser.add_argument("--medium", choices=["water", "soft"], default="water")
    parser.add_argument("--dx-mm", type=float, default=0.75)
    parser.add_argument("--pml-size", type=parse_int_list, default=[8, 12, 16])
    parser.add_argument("--preset", choices=["smoke", "quick", "standard", "paper_grade"], default="standard")
    parser.add_argument("--cycles", type=int, default=6)
    parser.add_argument("--sim-time-us", type=float, default=None)
    parser.add_argument("--cfl", type=float, default=0.20)
    parser.add_argument("--source-margin-mm", type=float, default=10.0)
    parser.add_argument("--post-focus-mm", type=float, default=18.0)
    parser.add_argument("--lateral-margin-mm", type=float, default=12.0)
    parser.add_argument("--nearfield-mm", type=float, default=10.0)
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "outputs" / "freefield_pml_boundary_plan" / "ap25_r30_f500_dx075"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = [build_case(args, pml_size) for pml_size in args.pml_size]
    baseline_case = min(cases, key=lambda case: case["simulation_quality"]["pml_size"])
    baseline_work = float(baseline_case["simulation_quality"]["voxel_count"]) * float(baseline_case["simulation_quality"]["nt"])
    rows = [flatten_case(case, baseline_work) for case in cases]
    rows = sorted(rows, key=lambda row: row["pml_size"])
    recommended = choose_recommended(rows)

    write_csv(output_dir / "pml_boundary_plan.csv", rows)
    plan = {
        "description": "Free-field PML/boundary dry-run review plan. This did not run k-Wave and did not generate pressure fields.",
        "dry_run_only": True,
        "baseline": {
            "transducer": "Gao baseline ap25/r30/f500/source=1 MPa unless overridden by CLI.",
            "source_pressure_definition": "source/excitation pressure, not free-field peak and not transcranial in-situ pressure.",
            "grid_reference": "Uses dx=0.75 mm finer-grid sanity as the current free-field standard check.",
        },
        "inputs": {
            "aperture_mm": args.aperture_mm,
            "radius_mm": args.radius_mm,
            "frequency_khz": args.frequency_khz,
            "source_pressure_mpa": args.source_pressure_mpa,
            "medium": args.medium,
            "dx_mm": args.dx_mm,
            "pml_size": args.pml_size,
            "preset": args.preset,
            "cycles": args.cycles,
            "cfl": args.cfl,
        },
        "candidates": rows,
        "recommended_next_run": recommended,
        "recommended_runner_command": runner_command(args, recommended),
        "guardrails": [
            "No k-Wave was run by this planning script.",
            "Run at most one PML candidate next.",
            "Use run_kwave_command.py --execute for any real k-Wave run.",
            "Do not label a PML check as paper-grade without full grid convergence and boundary review evidence.",
        ],
    }
    (output_dir / "pml_boundary_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    write_recommendation(output_dir / "recommended_pml_next_run.md", args, recommended, rows)
    (output_dir / "recommended_runner_command.ps1").write_text(
        "# 需要用户明确确认后再运行。本文件只是推荐命令模板。\n"
        "# This command uses run_kwave_command.py and explicitly includes --execute.\n"
        + runner_command(args, recommended)
        + "\n",
        encoding="utf-8-sig",
    )


if __name__ == "__main__":
    main()
