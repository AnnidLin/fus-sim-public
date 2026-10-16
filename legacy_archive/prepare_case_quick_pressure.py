from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from plan_ct_target_entry import load_model as load_entry_model
from plan_ct_target_entry import plan_left_x_entry
from simulate_kwave_3d_focus import KWave3DConfig, build_source_mask, load_model as load_kwave_model


PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")


PLAN_FIELDS = [
    "case_id",
    "status",
    "reason",
    "model_path",
    "entry_plan_path",
    "source_safety_path",
    "recommended_commands_path",
    "target_index_ijk",
    "entry_index_ijk",
    "source_center_index_ijk",
    "has_skull_crossing",
    "entry_label",
    "source_center_label",
    "source_label_counts",
    "source_points",
    "quick_crop_shape",
    "quick_voxel_count",
    "source_to_target_distance_mm",
    "skull_path_length_mm",
]


def load_batch_summary(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing batch summary: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError(f"Batch summary does not contain a cases list: {path}")
    return cases


def list_to_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, (list, tuple)):
        return ",".join(str(item) for item in value)
    return str(value)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=PLAN_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: list_to_string(row.get(key)) for key in PLAN_FIELDS})


def command_line(
    model_path: Path,
    entry_plan_path: Path,
    output_dir: Path,
    args: argparse.Namespace,
) -> str:
    parts = [
        str(PYTHON_EXE),
        "simulate_kwave_3d_focus.py",
        "--model",
        str(model_path),
        "--entry-plan",
        str(entry_plan_path),
        "--output-dir",
        str(output_dir),
        "--sim-time-us",
        f"{args.sim_time_us:g}",
        "--cycles",
        str(args.cycles),
        "--quick-lateral-mm",
        f"{args.quick_lateral_mm:g}",
        "--quick-post-target-mm",
        f"{args.quick_post_target_mm:g}",
        "--aperture-mm",
        f"{args.aperture_mm:g}",
        "--radius-mm",
        f"{args.radius_mm:g}",
    ]
    return " ".join(parts)


def write_recommended_commands(
    case_dir: Path,
    case_id: str,
    model_path: Path,
    entry_plan_path: Path,
    args: argparse.Namespace,
) -> Path:
    runs_dir = PROJECT_ROOT / "outputs" / "case_quick_pressure_runs" / f"{case_id}_smoke"
    command_path = case_dir / "recommended_commands.ps1"
    simulate_cmd = command_line(model_path, entry_plan_path, runs_dir, args)
    analyze_cmd = f"{PYTHON_EXE} analyze_kwave_3d_focus.py --input-dir {runs_dir}"
    command_path.write_text(
        "\n".join(
            [
                "# Generated quick pressure smoke commands.",
                "# These commands are not run by prepare_case_quick_pressure.py.",
                simulate_cmd,
                analyze_cmd,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return command_path


def source_label_count(source_metadata: dict[str, Any], label: int) -> int:
    counts = source_metadata.get("source_label_counts", {})
    if not isinstance(counts, dict):
        return 0
    return int(counts.get(str(label), 0))


def build_case_plan(case: dict[str, Any], output_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    case_id = str(case.get("case_id", "unknown_case"))
    case_dir = output_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    if case.get("status") != "built":
        return {
            "case_id": case_id,
            "status": "skipped",
            "reason": f"batch_status_{case.get('status')}",
        }

    model_path = Path(str(case.get("output_dir", ""))) / "acoustic_model_3d.npz"
    if not model_path.exists():
        return {
            "case_id": case_id,
            "status": "skipped",
            "reason": "missing_acoustic_model_3d_npz",
            "model_path": str(model_path),
        }

    try:
        labels, dx_m, target = load_entry_model(model_path)
        plan = plan_left_x_entry(
            labels=labels,
            dx_m=dx_m,
            target=target,
            source_standoff_mm=args.source_standoff_mm,
            entry_offset_mm=(args.entry_offset_y_mm, args.entry_offset_z_mm),
        )
        entry_plan_path = case_dir / "entry_plan.json"
        entry_plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

        config = KWave3DConfig(
            model_path=model_path,
            entry_plan_path=entry_plan_path,
            quick_mode=True,
            quick_lateral_half_width_m=args.quick_lateral_mm * 1e-3,
            quick_post_target_margin_m=args.quick_post_target_mm * 1e-3,
            aperture_diameter_m=args.aperture_mm * 1e-3,
            transducer_radius_m=args.radius_mm * 1e-3,
            tone_burst_cycles=args.cycles,
            simulation_time_s=args.sim_time_us * 1e-6,
        )
        loaded = load_kwave_model(config)
        _source_mask, source_metadata = build_source_mask(loaded, config)
        source_label_counts = source_metadata.get("source_label_counts", {})
        label1 = source_label_count(source_metadata, 1)
        label2 = source_label_count(source_metadata, 2)
        warnings: list[str] = []
        if not bool(plan.get("has_skull_crossing")):
            warnings.append("no_skull_crossing_on_left_x_ray")
        if int(plan.get("source_center_label", -1)) != 0:
            warnings.append("source_center_not_background")
        if int(plan.get("entry_label", -1)) != 2:
            warnings.append("entry_label_not_skull")
        if label1 > 0:
            warnings.append("source_mask_overlaps_soft_tissue")
        if label2 > 0:
            warnings.append("source_mask_overlaps_skull")

        safety = {
            "case_id": case_id,
            "status": "warning" if warnings else "ready",
            "warnings": warnings,
            "model_path": str(model_path),
            "entry_plan_path": str(entry_plan_path),
            "quick_parameters": {
                "source_standoff_mm": args.source_standoff_mm,
                "entry_offset_mm": [args.entry_offset_y_mm, args.entry_offset_z_mm],
                "aperture_mm": args.aperture_mm,
                "radius_mm": args.radius_mm,
                "cycles": args.cycles,
                "sim_time_us": args.sim_time_us,
                "quick_lateral_mm": args.quick_lateral_mm,
                "quick_post_target_mm": args.quick_post_target_mm,
            },
            "entry_plan": plan,
            "source_metadata": source_metadata,
            "quick_crop_shape": [int(value) for value in loaded.sound_speed.shape],
            "quick_voxel_count": int(np.prod(loaded.sound_speed.shape)),
            "crop_origin_ijk": loaded.crop_origin_ijk.astype(int).tolist(),
            "source_model_shape": [int(value) for value in loaded.source_model_shape],
        }
        source_safety_path = case_dir / "source_safety.json"
        source_safety_path.write_text(json.dumps(safety, ensure_ascii=False, indent=2), encoding="utf-8")
        commands_path = write_recommended_commands(case_dir, case_id, model_path, entry_plan_path, args)

        return {
            "case_id": case_id,
            "status": safety["status"],
            "reason": ";".join(warnings) if warnings else "ready",
            "model_path": str(model_path),
            "entry_plan_path": str(entry_plan_path),
            "source_safety_path": str(source_safety_path),
            "recommended_commands_path": str(commands_path),
            "target_index_ijk": plan["target_index_ijk"],
            "entry_index_ijk": plan["entry_index_ijk"],
            "source_center_index_ijk": plan["source_center_index_ijk"],
            "has_skull_crossing": bool(plan["has_skull_crossing"]),
            "entry_label": int(plan["entry_label"]),
            "source_center_label": int(plan["source_center_label"]),
            "source_label_counts": source_label_counts,
            "source_points": int(source_metadata.get("source_points", 0)),
            "quick_crop_shape": safety["quick_crop_shape"],
            "quick_voxel_count": safety["quick_voxel_count"],
            "source_to_target_distance_mm": float(plan["source_to_target_distance_mm"]),
            "skull_path_length_mm": float(plan["skull_path_length_mm"]),
        }
    except Exception as exc:
        failure = {
            "case_id": case_id,
            "status": "skipped",
            "reason": str(exc),
            "model_path": str(model_path),
        }
        (case_dir / "source_safety.json").write_text(json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8")
        return failure


def write_summary(output_dir: Path, rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    summary = {
        "description": "Reusable quick-pressure preparation package for batch CT acoustic models.",
        "batch_summary": str(args.batch_summary),
        "output_dir": str(output_dir),
        "case_count": len(rows),
        "ready_count": sum(1 for row in rows if row.get("status") == "ready"),
        "warning_count": sum(1 for row in rows if row.get("status") == "warning"),
        "skipped_count": sum(1 for row in rows if row.get("status") == "skipped"),
        "quick_defaults": {
            "source_standoff_mm": args.source_standoff_mm,
            "entry_offset_mm": [args.entry_offset_y_mm, args.entry_offset_z_mm],
            "aperture_mm": args.aperture_mm,
            "radius_mm": args.radius_mm,
            "cycles": args.cycles,
            "sim_time_us": args.sim_time_us,
            "quick_lateral_mm": args.quick_lateral_mm,
            "quick_post_target_mm": args.quick_post_target_mm,
        },
        "cases": rows,
    }
    (output_dir / "quick_pressure_plan_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare reusable quick-pressure entry/safety packages from batch CT acoustic models.")
    parser.add_argument(
        "--batch-summary",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "ct_acoustic_models_batch" / "batch_summary.json",
        help="Batch model summary generated by batch_build_ct_models.py.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "case_quick_pressure_plan",
        help="Output directory for quick pressure preparation files.",
    )
    parser.add_argument("--source-standoff-mm", type=float, default=16.0)
    parser.add_argument("--entry-offset-y-mm", type=float, default=0.0)
    parser.add_argument("--entry-offset-z-mm", type=float, default=0.0)
    parser.add_argument("--aperture-mm", type=float, default=25.0)
    parser.add_argument("--radius-mm", type=float, default=30.0)
    parser.add_argument("--cycles", type=int, default=6)
    parser.add_argument("--sim-time-us", type=float, default=45.0)
    parser.add_argument("--quick-lateral-mm", type=float, default=17.0)
    parser.add_argument("--quick-post-target-mm", type=float, default=8.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_cases = load_batch_summary(args.batch_summary)
    rows = [build_case_plan(case, output_dir, args) for case in batch_cases]
    write_csv(output_dir / "quick_pressure_plan.csv", rows)
    write_summary(output_dir, rows, args)
    for row in rows:
        print(f"{str(row.get('status')).upper()}: {row.get('case_id')} ({row.get('reason')})")
    print(f"Wrote quick pressure plan to {output_dir / 'quick_pressure_plan.csv'}")


if __name__ == "__main__":
    main()
