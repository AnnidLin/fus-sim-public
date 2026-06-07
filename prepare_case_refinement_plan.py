from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Any

from scan_ct_entry_positions import generate_candidates, rank_geometry, write_csv as write_scan_csv
from select_ct_target_candidates import (
    build_target_candidates,
    parse_entry_probe_offsets,
    parse_float_list,
    write_csv as write_target_csv,
)


PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")


SUMMARY_FIELDS = [
    "case_id",
    "status",
    "reason",
    "model_path",
    "smoke_target_window_peak_mpa",
    "recommended_target_index_ijk",
    "recommended_entry_offset_y_mm",
    "recommended_entry_offset_z_mm",
    "best_entry_plan_path",
    "source_mask_label_counts",
    "quick_voxel_count",
    "recommended_commands_path",
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key)) for key in SUMMARY_FIELDS})


def plan_case_lookup(plan_summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases = plan_summary.get("cases", [])
    if not isinstance(cases, list):
        return {}
    return {str(case.get("case_id")): case for case in cases}


def command_line(model_path: Path, entry_plan_path: Path, output_dir: Path, args: argparse.Namespace) -> str:
    return " ".join(
        [
            str(PYTHON_EXE),
            "simulate_kwave_3d_focus.py",
            "--model",
            str(model_path),
            "--entry-plan",
            str(entry_plan_path),
            "--output-dir",
            str(output_dir),
            "--sim-time-us",
            f"{args.refine_sim_time_us:g}",
            "--cycles",
            str(args.refine_cycles),
            "--quick-lateral-mm",
            f"{args.quick_lateral_mm:g}",
            "--quick-post-target-mm",
            f"{args.quick_post_target_mm:g}",
            "--aperture-mm",
            f"{args.refine_aperture_mm:g}",
            "--radius-mm",
            f"{args.refine_radius_mm:g}",
        ]
    )


def write_commands(case_dir: Path, case_id: str, model_path: Path, entry_plan_path: Path, args: argparse.Namespace) -> Path:
    output_dir = PROJECT_ROOT / "outputs" / "case_refinement_runs" / f"{case_id}_best_candidate"
    command_path = case_dir / "recommended_refinement_commands.ps1"
    simulate_cmd = command_line(model_path, entry_plan_path, output_dir, args)
    analyze_cmd = f"{PYTHON_EXE} analyze_kwave_3d_focus.py --input-dir {output_dir}"
    command_path.write_text(
        "\n".join(
            [
                "# Generated refinement validation command.",
                "# This file is not executed by prepare_case_refinement_plan.py.",
                simulate_cmd,
                analyze_cmd,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return command_path


def should_refine(run_case: dict[str, Any], args: argparse.Namespace) -> tuple[bool, str]:
    if run_case.get("run_status") != "kwave_ok":
        return False, f"run_status_{run_case.get('run_status')}"
    value = run_case.get("target_window_peak_mpa")
    if value is None:
        return False, "missing_target_window_peak_mpa"
    if float(value) >= args.target_window_threshold_mpa:
        return False, f"target_window_peak_mpa_above_threshold_{args.target_window_threshold_mpa:g}"
    return True, "needs_refinement"


def process_case(run_case: dict[str, Any], plan_by_case: dict[str, dict[str, Any]], output_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    case_id = str(run_case.get("case_id", "unknown_case"))
    case_dir = output_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    do_refine, reason = should_refine(run_case, args)
    plan_case = plan_by_case.get(case_id)
    if not do_refine:
        return {
            "case_id": case_id,
            "status": "skipped",
            "reason": reason,
            "smoke_target_window_peak_mpa": run_case.get("target_window_peak_mpa"),
        }
    if plan_case is None:
        return {
            "case_id": case_id,
            "status": "skipped",
            "reason": "missing_case_in_quick_pressure_plan_summary",
            "smoke_target_window_peak_mpa": run_case.get("target_window_peak_mpa"),
        }

    model_path = Path(str(plan_case.get("model_path", "")))
    if not model_path.exists():
        return {
            "case_id": case_id,
            "status": "skipped",
            "reason": "missing_batch_model",
            "model_path": str(model_path),
            "smoke_target_window_peak_mpa": run_case.get("target_window_peak_mpa"),
        }

    try:
        labels, _dx_m, base_target, target_rows, rejected_target_rows = build_target_candidates(
            model_path=model_path,
            target_override=None,
            x_offsets_mm=args.target_x_offsets_mm,
            y_offsets_mm=args.target_y_offsets_mm,
            z_offsets_mm=args.target_z_offsets_mm,
            source_standoff_mm=args.source_standoff_mm,
            entry_probe_offsets_mm=args.entry_probe_offsets_mm,
            min_edge_margin_mm=args.min_edge_margin_mm,
            soft_radius_mm=args.soft_radius_mm,
            min_soft_fraction=args.min_soft_fraction,
        )
        write_target_csv(case_dir / "target_candidates.csv", target_rows)
        write_target_csv(case_dir / "rejected_target_candidates.csv", rejected_target_rows)
        if not target_rows:
            return {
                "case_id": case_id,
                "status": "skipped",
                "reason": "no_valid_target_candidates",
                "model_path": str(model_path),
                "smoke_target_window_peak_mpa": run_case.get("target_window_peak_mpa"),
            }

        best_target = target_rows[0]
        target_index = tuple(int(value) for value in best_target["target_index_ijk"])
        entry_rows, rejected_entry_rows = generate_candidates(
            model_path=model_path,
            output_dir=case_dir,
            target_override=target_index,
            source_standoff_mm=args.source_standoff_mm,
            y_offsets_mm=args.entry_y_offsets_mm,
            z_offsets_mm=args.entry_z_offsets_mm,
            auto_sim_time=True,
            fixed_sim_time_us=None,
        )
        ranked_entry_rows = rank_geometry(entry_rows)
        write_scan_csv(case_dir / "entry_candidates.csv", ranked_entry_rows)
        write_scan_csv(case_dir / "rejected_entry_candidates.csv", rejected_entry_rows)
        safe_rows = [
            row
            for row in ranked_entry_rows
            if int(row.get("source_center_label", -1)) == 0
            and int(row.get("source_mask_label_2_count", 1)) == 0
        ]
        if not safe_rows:
            return {
                "case_id": case_id,
                "status": "skipped",
                "reason": "no_entry_candidate_without_skull_source_overlap",
                "model_path": str(model_path),
                "smoke_target_window_peak_mpa": run_case.get("target_window_peak_mpa"),
                "recommended_target_index_ijk": best_target["target_index_ijk"],
            }

        best_entry = safe_rows[0]
        source_safety = {
            "case_id": case_id,
            "model_path": str(model_path),
            "base_target_index_ijk": base_target.astype(int).tolist(),
            "recommended_target": best_target,
            "recommended_entry": best_entry,
            "source_safety_ok": True,
            "source_center_label": best_entry.get("source_center_label"),
            "source_mask_label_counts": best_entry.get("source_mask_label_counts", {}),
            "note": "This is a geometry/safety refinement plan. k-Wave is not run by this script.",
        }
        source_safety_path = case_dir / "source_safety.json"
        source_safety_path.write_text(json.dumps(source_safety, ensure_ascii=False, indent=2), encoding="utf-8")
        best_entry_plan_path = case_dir / "best_entry_plan.json"
        shutil.copyfile(Path(str(best_entry["entry_plan"])), best_entry_plan_path)
        commands_path = write_commands(case_dir, case_id, model_path, best_entry_plan_path, args)

        return {
            "case_id": case_id,
            "status": "planned",
            "reason": "recommended_refinement_candidate_ready",
            "model_path": str(model_path),
            "smoke_target_window_peak_mpa": run_case.get("target_window_peak_mpa"),
            "recommended_target_index_ijk": best_target["target_index_ijk"],
            "recommended_entry_offset_y_mm": best_entry.get("entry_offset_y_mm"),
            "recommended_entry_offset_z_mm": best_entry.get("entry_offset_z_mm"),
            "best_entry_plan_path": str(best_entry_plan_path),
            "source_mask_label_counts": best_entry.get("source_mask_label_counts", {}),
            "quick_voxel_count": best_entry.get("voxel_count"),
            "recommended_commands_path": str(commands_path),
        }
    except Exception as exc:
        return {
            "case_id": case_id,
            "status": "failed",
            "reason": str(exc),
            "model_path": str(model_path),
            "smoke_target_window_peak_mpa": run_case.get("target_window_peak_mpa"),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare per-case target/entry refinement plans without running k-Wave.")
    parser.add_argument(
        "--run-summary",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "case_quick_pressure_runs" / "quick_pressure_run_summary.json",
        help="Smoke run summary generated by summarize_quick_pressure_runs.py.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "case_refinement_plan",
        help="Output directory for refinement plans.",
    )
    parser.add_argument("--target-window-threshold-mpa", type=float, default=0.1)
    parser.add_argument("--source-standoff-mm", type=float, default=16.0)
    parser.add_argument("--target-x-offsets-mm", type=parse_float_list, default=[-20.0, -10.0, 0.0, 10.0, 20.0])
    parser.add_argument("--target-y-offsets-mm", type=parse_float_list, default=[-20.0, -10.0, 0.0, 10.0, 20.0])
    parser.add_argument("--target-z-offsets-mm", type=parse_float_list, default=[-15.0, -5.0, 0.0, 5.0, 15.0])
    parser.add_argument("--entry-y-offsets-mm", type=parse_float_list, default=[-10.0, 0.0, 10.0])
    parser.add_argument("--entry-z-offsets-mm", type=parse_float_list, default=[-10.0, 0.0, 10.0])
    parser.add_argument(
        "--entry-probe-offsets-mm",
        type=parse_entry_probe_offsets,
        default=[
            (-10.0, -10.0),
            (-10.0, 0.0),
            (-10.0, 10.0),
            (0.0, -10.0),
            (0.0, 0.0),
            (0.0, 10.0),
            (10.0, -10.0),
            (10.0, 0.0),
            (10.0, 10.0),
        ],
        help="Semicolon-separated entry probe offsets, formatted as 'y,z;y,z'.",
    )
    parser.add_argument("--min-edge-margin-mm", type=float, default=20.0)
    parser.add_argument("--soft-radius-mm", type=float, default=3.0)
    parser.add_argument("--min-soft-fraction", type=float, default=0.65)
    parser.add_argument("--refine-sim-time-us", type=float, default=55.0)
    parser.add_argument("--refine-cycles", type=int, default=8)
    parser.add_argument("--refine-aperture-mm", type=float, default=30.0)
    parser.add_argument("--refine-radius-mm", type=float, default=35.0)
    parser.add_argument("--quick-lateral-mm", type=float, default=17.0)
    parser.add_argument("--quick-post-target-mm", type=float, default=8.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_summary = load_json(args.run_summary)
    plan_summary_path = Path(str(run_summary.get("plan_summary", "")))
    plan_summary = load_json(plan_summary_path)
    plan_by_case = plan_case_lookup(plan_summary)
    run_cases = run_summary.get("cases", [])
    if not isinstance(run_cases, list):
        raise SystemExit(f"ERROR: run summary does not contain a cases list: {args.run_summary}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = [process_case(case, plan_by_case, args.output_dir, args) for case in run_cases]
    write_summary_csv(args.output_dir / "refinement_plan_summary.csv", rows)
    summary = {
        "description": "Case-level target/entry refinement plans generated without running k-Wave.",
        "run_summary": str(args.run_summary),
        "quick_pressure_plan_summary": str(plan_summary_path),
        "output_dir": str(args.output_dir),
        "target_window_threshold_mpa": args.target_window_threshold_mpa,
        "case_count": len(rows),
        "planned_count": sum(1 for row in rows if row.get("status") == "planned"),
        "skipped_count": sum(1 for row in rows if row.get("status") == "skipped"),
        "failed_count": sum(1 for row in rows if row.get("status") == "failed"),
        "cases": rows,
    }
    (args.output_dir / "refinement_plan_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    for row in rows:
        print(f"{row['status'].upper()}: {row['case_id']} ({row['reason']})")
    print(f"Wrote {args.output_dir / 'refinement_plan_summary.csv'}")


if __name__ == "__main__":
    main()
