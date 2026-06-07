from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
SMOKE_BASELINE_TARGET_WINDOW_MPA = 0.013300606049597263
HAND_TUNED_TARGET_WINDOW_MPA = 2.254160165786743


FIELDS = [
    "case_id",
    "candidate_id",
    "run_status",
    "run_dir",
    "target_index_ijk",
    "entry_offset_mm",
    "source_label_counts",
    "target_pressure_mpa",
    "target_window_peak_mpa",
    "effective_peak_mpa",
    "effective_peak_to_target_distance_mm",
    "target_to_effective_peak_ratio",
    "global_peak_mpa",
    "improvement_vs_smoke_x",
    "fraction_of_hand_tuned_best",
    "runtime_s",
    "reason",
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


def summarize_run(
    case_id: str,
    candidate_id: str,
    run_dir: Path,
    entry_plan_path: Path,
    smoke_baseline_mpa: float,
    hand_tuned_mpa: float,
) -> dict[str, Any]:
    metrics_path = run_dir / "focus_metrics.json"
    summary_path = run_dir / "summary.json"
    pressure_path = run_dir / "pressure_max_mpa.npz"
    missing = [path.name for path in [metrics_path, summary_path, pressure_path] if not path.exists()]
    if missing:
        return {
            "case_id": case_id,
            "candidate_id": candidate_id,
            "run_status": "missing_outputs",
            "run_dir": str(run_dir),
            "reason": f"missing: {','.join(missing)}",
        }

    metrics = load_json(metrics_path)
    summary = load_json(summary_path)
    entry_plan = load_json(entry_plan_path) if entry_plan_path.exists() else {}
    target_window = float(metrics.get("target_window_peak_mpa", 0.0))
    smoke_ratio = target_window / smoke_baseline_mpa if smoke_baseline_mpa > 0 else None
    hand_fraction = target_window / hand_tuned_mpa if hand_tuned_mpa > 0 else None
    return {
        "case_id": case_id,
        "candidate_id": candidate_id,
        "run_status": "kwave_ok",
        "run_dir": str(run_dir),
        "target_index_ijk": metrics.get("target_window_peak_index_ijk") and entry_plan.get("target_index_ijk"),
        "entry_offset_mm": entry_plan.get("entry_offset_mm"),
        "source_label_counts": summary.get("source", {}).get("source_label_counts", {}),
        "target_pressure_mpa": metrics.get("target_pressure_mpa"),
        "target_window_peak_mpa": metrics.get("target_window_peak_mpa"),
        "effective_peak_mpa": metrics.get("effective_peak_mpa"),
        "effective_peak_to_target_distance_mm": metrics.get("effective_peak_to_target_distance_mm"),
        "target_to_effective_peak_ratio": metrics.get("target_to_effective_peak_ratio"),
        "global_peak_mpa": metrics.get("global_peak_mpa"),
        "improvement_vs_smoke_x": smoke_ratio,
        "fraction_of_hand_tuned_best": hand_fraction,
        "runtime_s": summary.get("runtime", {}).get("runtime_s"),
        "reason": "completed",
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in FIELDS})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize candidate refinement k-Wave runs.")
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "case_refinement_runs",
        help="Root folder for refinement run outputs.",
    )
    parser.add_argument("--case-id", default="079")
    parser.add_argument("--candidate-id", default="candidate_006")
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "case_refinement_runs" / "079_candidate_006_offset_10_0",
    )
    parser.add_argument(
        "--entry-plan",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "case_refinement_plan" / "079" / "candidate_006" / "entry_plan.json",
    )
    parser.add_argument("--smoke-baseline-target-window-mpa", type=float, default=SMOKE_BASELINE_TARGET_WINDOW_MPA)
    parser.add_argument("--hand-tuned-target-window-mpa", type=float, default=HAND_TUNED_TARGET_WINDOW_MPA)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.runs_root.mkdir(parents=True, exist_ok=True)
    row = summarize_run(
        case_id=args.case_id,
        candidate_id=args.candidate_id,
        run_dir=args.run_dir,
        entry_plan_path=args.entry_plan,
        smoke_baseline_mpa=args.smoke_baseline_target_window_mpa,
        hand_tuned_mpa=args.hand_tuned_target_window_mpa,
    )
    rows = [row]
    write_csv(args.runs_root / "refinement_run_summary.csv", rows)
    summary = {
        "description": "Summary of case refinement validation runs.",
        "runs_root": str(args.runs_root),
        "smoke_baseline_target_window_mpa": args.smoke_baseline_target_window_mpa,
        "hand_tuned_target_window_mpa": args.hand_tuned_target_window_mpa,
        "kwave_ok_count": sum(1 for item in rows if item.get("run_status") == "kwave_ok"),
        "cases": rows,
    }
    (args.runs_root / "refinement_run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{row['run_status']}: {row['case_id']} {row['candidate_id']} ({row['reason']})")
    print(f"Wrote {args.runs_root / 'refinement_run_summary.csv'}")


if __name__ == "__main__":
    main()
