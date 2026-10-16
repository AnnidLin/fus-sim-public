"""Scan Visible Human target/entry candidates without running k-Wave."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from plan_ct_target_entry import PROJECT_ROOT, load_model, plan_left_x_entry, write_summary as write_entry_summary
from scan_ct_entry_positions import estimate_quick_crop, geometry_metrics, source_mask_safety, write_csv


DEFAULT_STANDOFFS_MM = [28.0, 32.0, 36.0, 40.0]
DEFAULT_OFFSETS_MM = [-10.0, 0.0, 10.0]
SOFT_TISSUE_SOUND_SPEED_M_S = 1540.0
AUTO_SIM_MARGIN_US = 8.0
AUTO_SIM_MIN_US = 45.0
AUTO_SIM_MAX_US = 65.0


def parse_float_list(value: str) -> list[float]:
    try:
        parsed = [float(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("list must be comma-separated numbers") from exc
    if not parsed:
        raise argparse.ArgumentTypeError("at least one number is required")
    return parsed


def parse_string_list(value: str) -> set[str]:
    return {part.strip() for part in value.split(",") if part.strip()}


def load_target_candidates(path: Path, skip_targets: set[str], top_targets: int) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing target candidates CSV: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    valid_rows = [row for row in rows if row.get("status") == "valid" and row.get("target_candidate_id") not in skip_targets]
    valid_rows.sort(key=lambda row: int(float(row.get("target_rank") or 10**9)))
    return valid_rows[:top_targets]


def parse_index_list(value: str) -> list[int]:
    parsed = json.loads(value)
    if not isinstance(parsed, list) or len(parsed) != 3:
        raise ValueError(f"target_index_ijk must be a JSON list with three items, got {value!r}")
    return [int(v) for v in parsed]


def estimate_sim_time_us(source_to_target_mm: float) -> dict[str, float | str]:
    arrival_time_us = source_to_target_mm * 1e-3 / SOFT_TISSUE_SOUND_SPEED_M_S * 1e6
    sim_time_us = min(AUTO_SIM_MAX_US, max(AUTO_SIM_MIN_US, arrival_time_us + AUTO_SIM_MARGIN_US))
    return {
        "arrival_time_us_estimate": float(arrival_time_us),
        "sim_time_us_estimate": float(sim_time_us),
        "sim_time_mode": "auto",
    }


def flatten_candidate(
    candidate_id: str,
    target_row: dict[str, Any],
    standoff_mm: float,
    entry_offset_y_mm: float,
    entry_offset_z_mm: float,
    candidate_dir: Path,
    plan: dict[str, Any],
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "candidate_id": candidate_id,
        "status": "valid",
        "target_candidate_id": target_row.get("target_candidate_id"),
        "target_rank": target_row.get("target_rank"),
        "target_index_ijk": plan.get("target_index_ijk"),
        "target_offset_x_mm": target_row.get("target_offset_x_mm"),
        "target_offset_y_mm": target_row.get("target_offset_y_mm"),
        "target_offset_z_mm": target_row.get("target_offset_z_mm"),
        "local_soft_tissue_fraction": target_row.get("local_soft_tissue_fraction"),
        "standoff_mm": float(standoff_mm),
        "entry_offset_y_mm": float(entry_offset_y_mm),
        "entry_offset_z_mm": float(entry_offset_z_mm),
        "candidate_dir": str(candidate_dir),
        "entry_plan": str(candidate_dir / "entry_plan.json"),
        "source_center_index_ijk": plan.get("source_center_index_ijk"),
        "entry_index_ijk": plan.get("entry_index_ijk"),
        "beam_axis": plan.get("beam_axis"),
        "source_center_label": plan.get("source_center_label"),
        "entry_label": plan.get("entry_label"),
        "target_label": plan.get("target_label"),
        "has_skull_crossing": plan.get("has_skull_crossing"),
        "source_to_target_distance_mm": plan.get("source_to_target_distance_mm"),
        "skull_path_length_mm": plan.get("skull_path_length_mm"),
    }
    row.update(estimate_sim_time_us(float(plan["source_to_target_distance_mm"])))
    row.update(estimate_quick_crop(plan, tuple(int(v) for v in plan["model_shape"]), True, None))
    row.update(geometry_metrics(plan))
    return row


def scan_candidates(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    model_path = Path(args.model)
    output_dir = Path(args.output_dir)
    labels, dx_m, _model_target = load_model(model_path)
    target_rows = load_target_candidates(Path(args.target_candidates), args.skip_targets, args.top_targets)
    valid_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []

    for target_row in target_rows:
        target_id = str(target_row["target_candidate_id"])
        target = np.asarray(parse_index_list(str(target_row["target_index_ijk"])), dtype=np.int32)
        for standoff_mm in args.standoff_mm:
            for y_offset_mm in args.y_offsets_mm:
                for z_offset_mm in args.z_offsets_mm:
                    candidate_id = f"{target_id}_s{standoff_mm:g}_y{y_offset_mm:g}_z{z_offset_mm:g}"
                    candidate_dir = output_dir / target_id / candidate_id
                    try:
                        plan = plan_left_x_entry(labels, dx_m, target, standoff_mm, (y_offset_mm, z_offset_mm))
                        if not plan["has_skull_crossing"]:
                            raise ValueError("candidate has no skull crossing")
                        if int(plan["source_center_label"]) != 0:
                            raise ValueError(f"source center label is {plan['source_center_label']}, expected 0")
                        if int(plan["entry_label"]) != 2:
                            raise ValueError(f"entry label is {plan['entry_label']}, expected 2")
                        candidate_dir.mkdir(parents=True, exist_ok=True)
                        write_entry_summary(candidate_dir, model_path, plan)
                        row = flatten_candidate(
                            candidate_id,
                            target_row,
                            standoff_mm,
                            y_offset_mm,
                            z_offset_mm,
                            candidate_dir,
                            plan,
                        )
                        row.update(source_mask_safety(model_path, candidate_dir / "entry_plan.json"))
                        valid_rows.append(row)
                    except Exception as exc:
                        rejected_rows.append(
                            {
                                "candidate_id": candidate_id,
                                "status": "rejected",
                                "target_candidate_id": target_id,
                                "target_index_ijk": target_row.get("target_index_ijk"),
                                "standoff_mm": standoff_mm,
                                "entry_offset_y_mm": y_offset_mm,
                                "entry_offset_z_mm": z_offset_mm,
                                "error": str(exc),
                            }
                        )
    return valid_rows, rejected_rows


def rank_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: (
            int(row.get("source_mask_label_2_count", 999)),
            int(row.get("source_mask_label_1_count", 999)),
            float(row.get("skull_path_length_mm", 1e9)),
            float(row.get("angle_from_left_x_deg", 1e9)),
            int(row.get("voxel_count", 10**12)),
            float(row.get("source_to_target_distance_mm", 1e9)),
        ),
    )
    for rank, row in enumerate(ranked, start=1):
        row["refinement_rank"] = rank
        row["recommended"] = rank == 1 and bool(row.get("source_mask_background_only"))
    return ranked


def write_outputs(args: argparse.Namespace, ranked_rows: list[dict[str, Any]], rejected_rows: list[dict[str, Any]]) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "refinement_candidates.csv", ranked_rows)
    write_csv(output_dir / "rejected_candidates.csv", rejected_rows)
    recommended = next((row for row in ranked_rows if row.get("recommended")), None)
    safe_count = sum(1 for row in ranked_rows if bool(row.get("source_mask_background_only")))
    summary = {
        "description": "Visible Human female multi-target source-safe refinement scan. This does not run k-Wave.",
        "model_path": str(args.model),
        "target_candidates_path": str(args.target_candidates),
        "skip_targets": sorted(args.skip_targets),
        "top_targets": args.top_targets,
        "standoff_candidates_mm": args.standoff_mm,
        "y_offsets_mm": args.y_offsets_mm,
        "z_offsets_mm": args.z_offsets_mm,
        "valid_candidate_count": len(ranked_rows),
        "rejected_candidate_count": len(rejected_rows),
        "background_only_candidate_count": safe_count,
        "recommended": recommended,
        "warning": None if recommended else "No background-only source mask candidate was found.",
        "baseline_notes": {
            "visible_human_female_head_1mm_t85_target_window_peak_mpa": 0.0035,
            "visible_human_female_head_1mm_t85_effective_peak_distance_mm": 97.7,
            "target_037_target_window_peak_mpa": 0.0029,
            "target_037_effective_peak_distance_mm": 77.1,
        },
    }
    (output_dir / "refinement_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")
    with (output_dir / "refinement_summary.txt").open("w", encoding="utf-8-sig") as handle:
        handle.write("Visible Human 多目标安全筛选摘要\n")
        handle.write(f"有效候选数: {len(ranked_rows)}\n")
        handle.write(f"被拒候选数: {len(rejected_rows)}\n")
        handle.write(f"纯背景 source mask 候选数: {safe_count}\n")
        if recommended:
            handle.write(f"推荐候选: {recommended['candidate_id']}\n")
            handle.write(f"entry_plan: {recommended['entry_plan']}\n")
            handle.write(f"sim_time_us_estimate: {recommended['sim_time_us_estimate']}\n")
            handle.write(f"source_label_counts: {recommended['source_mask_label_counts']}\n")
            handle.write(f"voxel_count: {recommended['voxel_count']}\n")
        else:
            handle.write("警告: 未找到纯背景 source mask 候选，不建议直接跑 k-Wave。\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Path to Visible Human acoustic_model_3d.npz.")
    parser.add_argument("--target-candidates", required=True, help="CSV produced by select_ct_target_candidates.py.")
    parser.add_argument("--output-dir", required=True, help="Directory for refinement scan outputs.")
    parser.add_argument("--skip-targets", type=parse_string_list, default={"target_037"}, help="Comma-separated target IDs to skip.")
    parser.add_argument("--top-targets", type=int, default=5, help="Number of ranked targets to scan after skipping.")
    parser.add_argument("--standoff-mm", type=parse_float_list, default=DEFAULT_STANDOFFS_MM, help="Comma-separated standoff values.")
    parser.add_argument("--y-offsets-mm", type=parse_float_list, default=DEFAULT_OFFSETS_MM, help="Comma-separated y entry offsets.")
    parser.add_argument("--z-offsets-mm", type=parse_float_list, default=DEFAULT_OFFSETS_MM, help="Comma-separated z entry offsets.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    valid_rows, rejected_rows = scan_candidates(args)
    ranked_rows = rank_candidates(valid_rows)
    write_outputs(args, ranked_rows, rejected_rows)
    if ranked_rows:
        best = ranked_rows[0]
        print(
            "recommended="
            f"{best['candidate_id']} safe={best.get('source_mask_background_only')} "
            f"entry_plan={best['entry_plan']} sim_time_us={float(best['sim_time_us_estimate']):.2f}"
        )
    else:
        print("No valid candidates were generated.")


if __name__ == "__main__":
    main()
