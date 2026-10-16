from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path

import numpy as np

from plan_ct_target_entry import (
    PROJECT_ROOT,
    load_model,
    plan_left_x_entry,
    save_layout_images,
    write_summary as write_entry_summary,
)
from simulate_kwave_3d_focus import KWave3DConfig, build_source_mask, load_model as load_kwave_model


DEFAULT_OFFSETS_MM = [-20.0, -10.0, 0.0, 10.0, 20.0]
FAST_LATERAL_MM = 17.0
FAST_POST_TARGET_MM = 8.0
DEFAULT_MAX_VOXELS = 160_000
DEFAULT_FAST_RUNS = 3
SOFT_TISSUE_SOUND_SPEED_M_S = 1540.0
AUTO_SIM_MARGIN_US = 8.0
AUTO_SIM_MIN_US = 45.0
AUTO_SIM_MAX_US = 65.0
BASELINE_TARGET_WINDOW_PEAK_MPA = 0.501
BASELINE_EFFECTIVE_DISTANCE_MM = 52.0


def parse_float_list(value: str) -> list[float]:
    try:
        return [float(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("offset list must be comma-separated numbers") from exc


def parse_index(value: str) -> tuple[int, int, int]:
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("index must be formatted as i,j,k")
    return tuple(parts)


def flatten_plan(candidate_id: str, candidate_dir: Path, plan: dict[str, object], status: str, error: str = "") -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "status": status,
        "error": error,
        "candidate_dir": str(candidate_dir),
        "entry_plan": str(candidate_dir / "entry_plan.json"),
        "entry_offset_y_mm": plan.get("entry_offset_mm", [None, None])[0],
        "entry_offset_z_mm": plan.get("entry_offset_mm", [None, None])[1],
        "target_index_ijk": plan.get("target_index_ijk"),
        "entry_index_ijk": plan.get("entry_index_ijk"),
        "source_center_index_ijk": plan.get("source_center_index_ijk"),
        "beam_axis": plan.get("beam_axis"),
        "source_center_label": plan.get("source_center_label"),
        "entry_label": plan.get("entry_label"),
        "target_label": plan.get("target_label"),
        "has_skull_crossing": plan.get("has_skull_crossing"),
        "source_to_target_distance_mm": plan.get("source_to_target_distance_mm"),
        "skull_path_length_mm": plan.get("skull_path_length_mm"),
    }


def estimate_sim_time_us(plan: dict[str, object], auto_sim_time: bool, fixed_sim_time_us: float | None) -> dict[str, object]:
    arrival_time_us = float(plan["source_to_target_distance_mm"]) * 1e-3 / SOFT_TISSUE_SOUND_SPEED_M_S * 1e6
    if fixed_sim_time_us is not None:
        sim_time_us = float(fixed_sim_time_us)
        mode = "fixed"
    elif auto_sim_time:
        sim_time_us = min(AUTO_SIM_MAX_US, max(AUTO_SIM_MIN_US, arrival_time_us + AUTO_SIM_MARGIN_US))
        mode = "auto"
    else:
        sim_time_us = AUTO_SIM_MIN_US
        mode = "minimum"
    return {
        "arrival_time_us_estimate": arrival_time_us,
        "sim_time_us_estimate": sim_time_us,
        "sim_time_mode": mode,
    }


def estimate_quick_crop(
    plan: dict[str, object],
    model_shape: tuple[int, int, int],
    auto_sim_time: bool,
    fixed_sim_time_us: float | None,
) -> dict[str, object]:
    target = np.array(plan["target_index_ijk"], dtype=int)
    source = np.array(plan["source_center_index_ijk"], dtype=int)
    dx_m = float(plan["dx_m"])
    sim_time = estimate_sim_time_us(plan, auto_sim_time, fixed_sim_time_us)
    pml_size = 8
    lateral_half_width = max(8, int(round(FAST_LATERAL_MM * 1e-3 / dx_m)))
    post_target_margin = max(4, int(round(FAST_POST_TARGET_MM * 1e-3 / dx_m)))
    anchor_min = np.minimum(target, source)
    anchor_max = np.maximum(target, source)
    x0 = max(0, int(anchor_min[0]) - pml_size - 4)
    x1 = min(model_shape[0], int(anchor_max[0]) + post_target_margin)
    y0 = max(0, int(anchor_min[1]) - lateral_half_width)
    y1 = min(model_shape[1], int(anchor_max[1]) + lateral_half_width + 1)
    z0 = max(0, int(anchor_min[2]) - lateral_half_width)
    z1 = min(model_shape[2], int(anchor_max[2]) + lateral_half_width + 1)
    crop_shape = [int(x1 - x0), int(y1 - y0), int(z1 - z0)]
    voxel_count = int(np.prod(crop_shape))
    nt_estimate = int(np.ceil(float(sim_time["sim_time_us_estimate"]) * 1e-6 / (0.20 * dx_m / 2800.0)))
    return {
        **sim_time,
        "crop_origin_ijk": [int(x0), int(y0), int(z0)],
        "crop_shape": crop_shape,
        "voxel_count": voxel_count,
        "nt_estimate": nt_estimate,
        "work_estimate": int(voxel_count * nt_estimate),
    }


def geometry_metrics(plan: dict[str, object]) -> dict[str, object]:
    beam = np.array(plan["beam_axis"], dtype=float)
    beam_norm = float(np.linalg.norm(beam))
    cos_angle = float(beam[0] / beam_norm) if beam_norm > 0 else 0.0
    cos_angle = max(-1.0, min(1.0, cos_angle))
    angle_deg = float(np.degrees(np.arccos(cos_angle)))
    return {
        "angle_from_left_x_deg": angle_deg,
        "source_is_background": int(plan["source_center_label"]) == 0,
        "entry_is_skull": int(plan["entry_label"]) == 2,
    }


def add_estimates(
    row: dict[str, object],
    plan: dict[str, object],
    auto_sim_time: bool,
    fixed_sim_time_us: float | None,
) -> dict[str, object]:
    estimated = dict(row)
    estimated.update(estimate_quick_crop(plan, tuple(int(v) for v in plan["model_shape"]), auto_sim_time, fixed_sim_time_us))
    estimated.update(geometry_metrics(plan))
    estimated["geometry_score"] = (
        float(estimated["voxel_count"]) / 100_000.0
        + 0.20 * float(estimated["skull_path_length_mm"])
        + 0.05 * float(estimated["angle_from_left_x_deg"])
    )
    return estimated


def source_mask_safety(model_path: Path, entry_plan_path: Path) -> dict[str, object]:
    config = KWave3DConfig(
        model_path=model_path,
        entry_plan_path=entry_plan_path,
        quick_mode=True,
        quick_lateral_half_width_m=FAST_LATERAL_MM * 1e-3,
        quick_post_target_margin_m=FAST_POST_TARGET_MM * 1e-3,
    )
    loaded = load_kwave_model(config)
    _source_mask, metadata = build_source_mask(loaded, config)
    counts = metadata.get("source_label_counts", {})
    if not isinstance(counts, dict):
        counts = {}
    label0 = int(counts.get("0", 0))
    label1 = int(counts.get("1", 0))
    label2 = int(counts.get("2", 0))
    source_points = int(metadata["source_points"])
    unsafe_points = label1 + label2
    return {
        "source_mask_label_counts": counts,
        "source_mask_label_0_count": label0,
        "source_mask_label_1_count": label1,
        "source_mask_label_2_count": label2,
        "source_mask_unsafe_points": unsafe_points,
        "source_mask_unsafe_fraction": float(unsafe_points / source_points) if source_points else 1.0,
        "source_mask_background_only": unsafe_points == 0,
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def generate_candidates(
    model_path: Path,
    output_dir: Path,
    target_override: tuple[int, int, int] | None,
    source_standoff_mm: float,
    y_offsets_mm: list[float],
    z_offsets_mm: list[float],
    auto_sim_time: bool,
    fixed_sim_time_us: float | None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    labels, dx_m, model_target = load_model(model_path)
    target = np.array(target_override if target_override is not None else model_target, dtype=np.int32)
    valid_rows: list[dict[str, object]] = []
    rejected_rows: list[dict[str, object]] = []
    valid_index = 0

    for y_offset in y_offsets_mm:
        for z_offset in z_offsets_mm:
            candidate_id = f"candidate_{valid_index:03d}"
            try:
                plan = plan_left_x_entry(labels, dx_m, target, source_standoff_mm, (y_offset, z_offset))
                if not plan["has_skull_crossing"]:
                    raise ValueError("candidate has no skull crossing")
                if int(plan["source_center_label"]) != 0:
                    raise ValueError(f"source center label is {plan['source_center_label']}, expected 0")
                if int(plan["entry_label"]) != 2:
                    raise ValueError(f"entry label is {plan['entry_label']}, expected 2")

                candidate_dir = output_dir / candidate_id
                candidate_dir.mkdir(parents=True, exist_ok=True)
                save_layout_images(candidate_dir, labels, plan)
                write_entry_summary(candidate_dir, model_path, plan)
                row = add_estimates(
                    flatten_plan(candidate_id, candidate_dir, plan, "valid"),
                    plan,
                    auto_sim_time,
                    fixed_sim_time_us,
                )
                row.update(source_mask_safety(model_path, candidate_dir / "entry_plan.json"))
                valid_rows.append(row)
                valid_index += 1
            except Exception as exc:
                rejected_rows.append(
                    {
                        "entry_offset_y_mm": y_offset,
                        "entry_offset_z_mm": z_offset,
                        "status": "rejected",
                        "error": str(exc),
                    }
                )

    return valid_rows, rejected_rows


def rank_geometry(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    ranked = sorted(
        rows,
        key=lambda row: (
            int(row.get("source_mask_label_2_count", 0)),
            int(row.get("source_mask_label_1_count", 0)),
            float(row["voxel_count"]),
            float(row["skull_path_length_mm"]),
            float(row["angle_from_left_x_deg"]),
        ),
    )
    for rank, row in enumerate(ranked, start=1):
        row["geometry_rank"] = rank
        row["recommended_geometry_top3"] = rank <= 3
    return ranked


def read_metrics(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Missing focus metrics: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_fast_candidate(
    python_exe: Path,
    model_path: Path,
    candidate_row: dict[str, object],
    timeout_s: int,
) -> dict[str, object]:
    candidate_dir = Path(str(candidate_row["candidate_dir"]))
    output_dir = candidate_dir / "kwave_fast"
    command = [
        str(python_exe),
        "simulate_kwave_3d_focus.py",
        "--model",
        str(model_path),
        "--entry-plan",
        str(candidate_dir / "entry_plan.json"),
        "--output-dir",
        str(output_dir),
        "--sim-time-us",
        str(candidate_row["sim_time_us_estimate"]),
        "--quick-lateral-mm",
        str(FAST_LATERAL_MM),
        "--quick-post-target-mm",
        str(FAST_POST_TARGET_MM),
    ]
    result = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True, timeout=timeout_s)
    row = dict(candidate_row)
    row["kwave_output_dir"] = str(output_dir)
    row["sim_time_us_used"] = candidate_row["sim_time_us_estimate"]
    row["returncode"] = int(result.returncode)
    row["stdout_tail"] = result.stdout[-500:]
    row["stderr_tail"] = result.stderr[-1000:]
    if result.returncode != 0:
        row["status"] = "kwave_failed"
        row["rank_score"] = ""
        return row

    metrics = read_metrics(output_dir / "focus_metrics.json")
    summary_path = output_dir / "summary.json"
    runtime_s = ""
    source_label_counts = ""
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        runtime_s = summary.get("runtime", {}).get("runtime_s", "")
        source_label_counts = summary.get("source", {}).get("source_label_counts", "")

    row.update(
        {
            "status": "kwave_ok",
            "global_peak_mpa": metrics.get("global_peak_mpa"),
            "effective_peak_mpa": metrics.get("effective_peak_mpa"),
            "effective_peak_to_target_distance_mm": metrics.get("effective_peak_to_target_distance_mm"),
            "target_pressure_mpa": metrics.get("target_pressure_mpa"),
            "target_window_peak_mpa": metrics.get("target_window_peak_mpa"),
            "target_to_effective_peak_ratio": metrics.get("target_to_effective_peak_ratio"),
            "runtime_s": runtime_s,
            "source_label_counts": source_label_counts,
        }
    )
    row["beats_baseline"] = bool(
        float(row["target_window_peak_mpa"]) > BASELINE_TARGET_WINDOW_PEAK_MPA
        or float(row["effective_peak_to_target_distance_mm"]) < BASELINE_EFFECTIVE_DISTANCE_MM
    )
    row["rank_score"] = float(row["target_window_peak_mpa"]) - 0.01 * float(row["effective_peak_to_target_distance_mm"])
    return row


def load_existing_fast_result(candidate_row: dict[str, object]) -> dict[str, object] | None:
    candidate_dir = Path(str(candidate_row["candidate_dir"]))
    output_dir = candidate_dir / "kwave_fast"
    metrics_path = output_dir / "focus_metrics.json"
    summary_path = output_dir / "summary.json"
    if not metrics_path.exists() or not summary_path.exists():
        return None

    metrics = read_metrics(metrics_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    row = dict(candidate_row)
    sim_time_s = summary.get("config", {}).get("simulation_time_s")
    row.update(
        {
            "status": "kwave_reused",
            "kwave_output_dir": str(output_dir),
            "sim_time_us_used": float(sim_time_s) * 1e6 if sim_time_s is not None else candidate_row["sim_time_us_estimate"],
            "returncode": "",
            "stdout_tail": "",
            "stderr_tail": "",
            "global_peak_mpa": metrics.get("global_peak_mpa"),
            "effective_peak_mpa": metrics.get("effective_peak_mpa"),
            "effective_peak_to_target_distance_mm": metrics.get("effective_peak_to_target_distance_mm"),
            "target_pressure_mpa": metrics.get("target_pressure_mpa"),
            "target_window_peak_mpa": metrics.get("target_window_peak_mpa"),
            "target_to_effective_peak_ratio": metrics.get("target_to_effective_peak_ratio"),
            "runtime_s": summary.get("runtime", {}).get("runtime_s", ""),
            "source_label_counts": summary.get("source", {}).get("source_label_counts", ""),
        }
    )
    row["beats_baseline"] = bool(
        float(row["target_window_peak_mpa"]) > BASELINE_TARGET_WINDOW_PEAK_MPA
        or float(row["effective_peak_to_target_distance_mm"]) < BASELINE_EFFECTIVE_DISTANCE_MM
    )
    row["rank_score"] = float(row["target_window_peak_mpa"]) - 0.01 * float(row["effective_peak_to_target_distance_mm"])
    return row


def run_fast_scan(
    python_exe: Path,
    model_path: Path,
    valid_rows: list[dict[str, object]],
    max_fast_runs: int | None,
    run_all_fast: bool,
    max_voxels: int,
    timeout_s: int,
    top_ranked: int,
    skip_existing: bool,
    force_rerun: bool,
) -> list[dict[str, object]]:
    considered_rows = valid_rows if run_all_fast else valid_rows[:top_ranked]
    eligible_rows = [row for row in considered_rows if int(row.get("voxel_count", 0)) <= max_voxels]
    skipped_rows = []
    for row in considered_rows:
        if int(row.get("voxel_count", 0)) > max_voxels:
            skipped = dict(row)
            skipped.update(
                {
                    "status": "skipped_max_voxels",
                    "error": f"voxel_count {row['voxel_count']} exceeds --max-voxels {max_voxels}",
                    "rank_score": "",
                }
            )
            skipped_rows.append(skipped)

    selected = eligible_rows
    if max_fast_runs is not None:
        selected = selected[:max_fast_runs]
    results: list[dict[str, object]] = []
    for index, row in enumerate(selected, start=1):
        if skip_existing and not force_rerun:
            reused = load_existing_fast_result(row)
            if reused is not None:
                print(f"[{index}/{len(selected)}] reuse k-Wave {row['candidate_id']} from {reused['kwave_output_dir']}")
                results.append(reused)
                continue
        print(
            f"[{index}/{len(selected)}] fast k-Wave {row['candidate_id']} "
            f"offset=({row['entry_offset_y_mm']},{row['entry_offset_z_mm']}) "
            f"crop={row['crop_shape']} voxels={row['voxel_count']} "
            f"sim_time_us={float(row['sim_time_us_estimate']):.2f} nt~{row['nt_estimate']}"
        )
        try:
            results.append(run_fast_candidate(python_exe, model_path, row, timeout_s))
        except Exception as exc:
            failed = dict(row)
            failed.update({"status": "kwave_exception", "error": str(exc), "rank_score": ""})
            results.append(failed)
    return results + skipped_rows


def sort_ranked(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    ok_statuses = {"kwave_ok", "kwave_reused"}
    ok_rows = [row for row in rows if row.get("status") in ok_statuses]
    failed_rows = [row for row in rows if row.get("status") not in ok_statuses]
    ok_rows.sort(
        key=lambda row: (
            -float(row.get("target_window_peak_mpa", 0.0)),
            float(row.get("effective_peak_to_target_distance_mm", 1e9)),
            -float(row.get("target_to_effective_peak_ratio", 0.0)),
        )
    )
    for rank, row in enumerate(ok_rows, start=1):
        row["rank"] = rank
        row["recommended_top3"] = rank <= 3
    for row in failed_rows:
        row["rank"] = ""
        row["recommended_top3"] = False
    return ok_rows + failed_rows


def write_summary(
    output_dir: Path,
    model_path: Path,
    valid_rows: list[dict[str, object]],
    rejected_rows: list[dict[str, object]],
    ranked_rows: list[dict[str, object]] | None,
) -> None:
    best = None
    if ranked_rows:
        ok_rows = [row for row in ranked_rows if row.get("status") in {"kwave_ok", "kwave_reused"}]
        best = ok_rows[0] if ok_rows else None
    summary = {
        "model_path": str(model_path),
        "valid_candidate_count": len(valid_rows),
        "rejected_candidate_count": len(rejected_rows),
        "ran_fast_count": 0 if ranked_rows is None else sum(1 for row in ranked_rows if row.get("status") == "kwave_ok"),
        "reused_fast_count": 0 if ranked_rows is None else sum(1 for row in ranked_rows if row.get("status") == "kwave_reused"),
        "skipped_fast_count": 0 if ranked_rows is None else sum(1 for row in ranked_rows if str(row.get("status", "")).startswith("skipped")),
        "sim_time_policy": {
            "auto_margin_us": AUTO_SIM_MARGIN_US,
            "auto_min_us": AUTO_SIM_MIN_US,
            "auto_max_us": AUTO_SIM_MAX_US,
            "sound_speed_m_s": SOFT_TISSUE_SOUND_SPEED_M_S,
        },
        "voxel_count_range": [
            min((int(row["voxel_count"]) for row in valid_rows), default=0),
            max((int(row["voxel_count"]) for row in valid_rows), default=0),
        ],
        "recommended_geometry_top3": [
            {
                "candidate_id": row["candidate_id"],
                "entry_offset_y_mm": row["entry_offset_y_mm"],
                "entry_offset_z_mm": row["entry_offset_z_mm"],
                "crop_shape": row["crop_shape"],
                "voxel_count": row["voxel_count"],
                "arrival_time_us_estimate": row["arrival_time_us_estimate"],
                "sim_time_us_estimate": row["sim_time_us_estimate"],
                "skull_path_length_mm": row["skull_path_length_mm"],
                "angle_from_left_x_deg": row["angle_from_left_x_deg"],
                "source_mask_label_counts": row.get("source_mask_label_counts", {}),
                "source_mask_background_only": row.get("source_mask_background_only", False),
            }
            for row in valid_rows[:3]
        ],
        "baseline": {
            "target_window_peak_mpa": BASELINE_TARGET_WINDOW_PEAK_MPA,
            "effective_peak_to_target_distance_mm": BASELINE_EFFECTIVE_DISTANCE_MM,
        },
        "best_candidate": best,
    }
    (output_dir / "scan_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    model_path = Path(args.model)
    output_dir.mkdir(parents=True, exist_ok=True)
    valid_rows, rejected_rows = generate_candidates(
        model_path=model_path,
        output_dir=output_dir,
        target_override=args.target_index,
        source_standoff_mm=args.source_standoff_mm,
        y_offsets_mm=args.y_offsets_mm,
        z_offsets_mm=args.z_offsets_mm,
        auto_sim_time=args.auto_sim_time,
        fixed_sim_time_us=args.fixed_sim_time_us,
    )
    ranked_candidates = rank_geometry(valid_rows)
    write_csv(output_dir / "candidates.csv", valid_rows)
    write_csv(output_dir / "ranked_candidates.csv", ranked_candidates)
    write_csv(output_dir / "rejected_candidates.csv", rejected_rows)

    ranked_rows = None
    if args.run_fast:
        ranked_rows = sort_ranked(
            run_fast_scan(
                python_exe=Path(args.python_exe),
                model_path=model_path,
                valid_rows=ranked_candidates,
                max_fast_runs=args.max_fast_runs,
                run_all_fast=args.run_all_fast,
                max_voxels=args.max_voxels,
                timeout_s=args.fast_timeout_s,
                top_ranked=args.top_ranked,
                skip_existing=args.skip_existing,
                force_rerun=args.force_rerun,
            )
        )
        write_csv(output_dir / "ranked_results.csv", ranked_rows)
    write_summary(output_dir, model_path, ranked_candidates, rejected_rows, ranked_rows)
    print(
        f"valid_candidates={len(valid_rows)} rejected_candidates={len(rejected_rows)} "
        f"recommended_first={ranked_candidates[0]['candidate_id'] if ranked_candidates else 'none'} "
        f"output_dir={output_dir}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and optionally run a left-side CT tFUS entry-position scan.")
    parser.add_argument(
        "--model",
        default=str(PROJECT_ROOT / "outputs" / "ct_acoustic_model_3d" / "acoustic_model_3d.npz"),
        help="Path to a CT-derived acoustic model .npz file.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs" / "ct_entry_scan_079"),
        help="Output directory for scan candidates and results.",
    )
    parser.add_argument("--target-index", type=parse_index, default=None, help="Optional target index formatted as i,j,k.")
    parser.add_argument("--source-standoff-mm", type=float, default=8.0, help="Source-center standoff from skull entry in millimeters.")
    parser.add_argument("--y-offsets-mm", type=parse_float_list, default=DEFAULT_OFFSETS_MM, help="Comma-separated y offsets in millimeters.")
    parser.add_argument("--z-offsets-mm", type=parse_float_list, default=DEFAULT_OFFSETS_MM, help="Comma-separated z offsets in millimeters.")
    parser.add_argument("--run-fast", action="store_true", help="Run fast k-Wave smoke simulations for valid candidates.")
    parser.add_argument("--max-fast-runs", type=int, default=None, help="Optional cap on fast simulations; defaults to 3 when --run-fast is used.")
    parser.add_argument("--top-ranked", type=int, default=DEFAULT_FAST_RUNS, help="Only consider the top N geometry-ranked candidates when --run-fast is used.")
    parser.add_argument("--run-all-fast", action="store_true", help="Run all eligible fast simulations; use only when long runtimes are acceptable.")
    parser.add_argument("--max-voxels", type=int, default=DEFAULT_MAX_VOXELS, help="Skip fast simulations whose estimated quick crop exceeds this voxel count.")
    parser.add_argument("--skip-existing", action=argparse.BooleanOptionalAction, default=True, help="Reuse existing kwave_fast outputs instead of rerunning them.")
    parser.add_argument("--force-rerun", action="store_true", help="Force rerunning candidates even when existing kwave_fast outputs are present.")
    parser.add_argument("--auto-sim-time", action=argparse.BooleanOptionalAction, default=True, help="Estimate simulation time from source-target distance.")
    parser.add_argument("--fixed-sim-time-us", type=float, default=None, help="Override automatic per-candidate simulation time.")
    parser.add_argument("--fast-timeout-s", type=int, default=900, help="Per-candidate fast simulation timeout in seconds.")
    parser.add_argument(
        "--python-exe",
        default=str(PROJECT_ROOT.parent / "python-envs" / "kwave312" / "Scripts" / "python.exe"),
        help="Python executable used to launch simulate_kwave_3d_focus.py.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
