from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent


SUMMARY_FIELDS = [
    "case_id",
    "plan_status",
    "run_status",
    "run_dir",
    "reason",
    "target_pressure_mpa",
    "target_window_peak_mpa",
    "effective_peak_mpa",
    "effective_peak_to_target_distance_mm",
    "target_to_effective_peak_ratio",
    "global_peak_mpa",
    "source_label_counts",
    "source_points",
    "quick_crop_shape",
    "quick_voxel_count",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_dir_for_case(runs_root: Path, case_id: str) -> Path:
    return runs_root / f"{case_id}_smoke"


def read_source_label_counts(run_dir: Path, plan_case: dict[str, Any]) -> dict[str, int]:
    summary_path = run_dir / "summary.json"
    if summary_path.exists():
        summary = load_json(summary_path)
        source = summary.get("source", {})
        counts = source.get("source_label_counts")
        if isinstance(counts, dict):
            return {str(key): int(value) for key, value in counts.items()}
    counts = plan_case.get("source_label_counts", {})
    if isinstance(counts, dict):
        return {str(key): int(value) for key, value in counts.items()}
    return {}


def summarize_case(plan_case: dict[str, Any], runs_root: Path) -> dict[str, Any]:
    case_id = str(plan_case.get("case_id", "unknown_case"))
    run_dir = run_dir_for_case(runs_root, case_id)
    plan_status = str(plan_case.get("status", "unknown"))

    if plan_status != "ready":
        return {
            "case_id": case_id,
            "plan_status": plan_status,
            "run_status": "not_run_warning_case" if plan_status == "warning" else "not_run",
            "run_dir": str(run_dir),
            "reason": plan_case.get("reason", ""),
            "source_label_counts": plan_case.get("source_label_counts", {}),
            "source_points": plan_case.get("source_points", ""),
            "quick_crop_shape": plan_case.get("quick_crop_shape", ""),
            "quick_voxel_count": plan_case.get("quick_voxel_count", ""),
        }

    metrics_path = run_dir / "focus_metrics.json"
    pressure_path = run_dir / "pressure_max_mpa.npz"
    summary_path = run_dir / "summary.json"
    if not metrics_path.exists() or not pressure_path.exists() or not summary_path.exists():
        missing = [
            path.name
            for path in [metrics_path, pressure_path, summary_path]
            if not path.exists()
        ]
        return {
            "case_id": case_id,
            "plan_status": plan_status,
            "run_status": "missing_outputs",
            "run_dir": str(run_dir),
            "reason": f"missing: {','.join(missing)}",
            "source_label_counts": plan_case.get("source_label_counts", {}),
            "source_points": plan_case.get("source_points", ""),
            "quick_crop_shape": plan_case.get("quick_crop_shape", ""),
            "quick_voxel_count": plan_case.get("quick_voxel_count", ""),
        }

    metrics = load_json(metrics_path)
    return {
        "case_id": case_id,
        "plan_status": plan_status,
        "run_status": "kwave_ok",
        "run_dir": str(run_dir),
        "reason": "completed",
        "target_pressure_mpa": metrics.get("target_pressure_mpa"),
        "target_window_peak_mpa": metrics.get("target_window_peak_mpa"),
        "effective_peak_mpa": metrics.get("effective_peak_mpa"),
        "effective_peak_to_target_distance_mm": metrics.get("effective_peak_to_target_distance_mm"),
        "target_to_effective_peak_ratio": metrics.get("target_to_effective_peak_ratio"),
        "global_peak_mpa": metrics.get("global_peak_mpa"),
        "source_label_counts": read_source_label_counts(run_dir, plan_case),
        "source_points": plan_case.get("source_points", ""),
        "quick_crop_shape": plan_case.get("quick_crop_shape", ""),
        "quick_voxel_count": plan_case.get("quick_voxel_count", ""),
    }


def csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key)) for key in SUMMARY_FIELDS})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize per-case quick pressure smoke runs.")
    parser.add_argument(
        "--plan-summary",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "case_quick_pressure_plan" / "quick_pressure_plan_summary.json",
        help="Quick pressure plan summary generated by prepare_case_quick_pressure.py.",
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "case_quick_pressure_runs",
        help="Root directory containing CASE_ID_smoke outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan_summary = load_json(args.plan_summary)
    cases = plan_summary.get("cases", [])
    if not isinstance(cases, list):
        raise SystemExit(f"ERROR: plan summary does not contain a cases list: {args.plan_summary}")
    args.runs_root.mkdir(parents=True, exist_ok=True)
    rows = [summarize_case(case, args.runs_root) for case in cases]
    write_csv(args.runs_root / "quick_pressure_run_summary.csv", rows)
    summary = {
        "description": "Summary of quick pressure smoke runs connected to the multi-case pipeline.",
        "plan_summary": str(args.plan_summary),
        "runs_root": str(args.runs_root),
        "case_count": len(rows),
        "kwave_ok_count": sum(1 for row in rows if row.get("run_status") == "kwave_ok"),
        "not_run_count": sum(1 for row in rows if str(row.get("run_status", "")).startswith("not_run")),
        "missing_outputs_count": sum(1 for row in rows if row.get("run_status") == "missing_outputs"),
        "cases": rows,
    }
    (args.runs_root / "quick_pressure_run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    for row in rows:
        print(f"{row['run_status']}: {row['case_id']} ({row['reason']})")
    print(f"Wrote {args.runs_root / 'quick_pressure_run_summary.csv'}")


if __name__ == "__main__":
    main()
