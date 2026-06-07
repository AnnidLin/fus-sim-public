"""Summarize Visible Human quick-smoke pressure runs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_run(case_id: str, run_dir: Path) -> dict[str, Any]:
    summary = load_json(run_dir / "summary.json")
    metrics = load_json(run_dir / "focus_metrics.json")
    if not summary or not metrics:
        return {
            "case_id": case_id,
            "status": "missing_outputs",
            "run_dir": str(run_dir),
        }
    source = summary.get("source", {})
    runtime = summary.get("runtime", {})
    entry = summary.get("entry_plan", {})
    source_counts = source.get("source_label_counts", {})
    return {
        "case_id": case_id,
        "status": "kwave_ok",
        "run_dir": str(run_dir),
        "model_path": summary.get("config", {}).get("model_path"),
        "entry_plan_path": summary.get("config", {}).get("entry_plan_path"),
        "source_label_counts": json.dumps(source_counts, ensure_ascii=False),
        "source_mask_background_only": set(source_counts.keys()) == {"0"},
        "source_points": source.get("source_points"),
        "source_standoff_mm": entry.get("source_standoff_mm"),
        "entry_offset_mm": json.dumps(entry.get("entry_offset_mm"), ensure_ascii=False),
        "source_to_target_distance_mm": entry.get("source_to_target_distance_mm"),
        "skull_path_length_mm": entry.get("skull_path_length_mm"),
        "dt_s": runtime.get("dt_s"),
        "nt": runtime.get("nt"),
        "runtime_s": runtime.get("runtime_s"),
        "global_peak_mpa": metrics.get("global_peak_mpa"),
        "target_pressure_mpa": metrics.get("target_pressure_mpa"),
        "target_window_peak_mpa": metrics.get("target_window_peak_mpa"),
        "effective_peak_mpa": metrics.get("effective_peak_mpa"),
        "effective_peak_to_target_distance_mm": metrics.get("effective_peak_to_target_distance_mm"),
        "target_to_effective_peak_ratio": metrics.get("target_to_effective_peak_ratio"),
        "tuning_note": summary.get("tuning_note"),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", default="outputs/visible_human_quick_smoke_runs")
    parser.add_argument(
        "--case-run",
        action="append",
        default=[],
        help="Case/run mapping formatted as case_id=relative_or_absolute_run_dir.",
    )
    args = parser.parse_args()

    runs_root = Path(args.runs_root)
    mappings = args.case_run or [
        "visible_human_female_head_1mm=visible_human_female_head_1mm_best_safe",
    ]
    rows: list[dict[str, Any]] = []
    for mapping in mappings:
        case_id, run_value = mapping.split("=", 1)
        run_path = Path(run_value)
        if not run_path.is_absolute():
            run_path = runs_root / run_path
        rows.append(summarize_run(case_id, run_path))

    runs_root.mkdir(parents=True, exist_ok=True)
    write_csv(runs_root / "visible_human_smoke_summary.csv", rows)
    (runs_root / "visible_human_smoke_summary.json").write_text(
        json.dumps(
            {
                "description": "Visible Human quick-smoke run summary.",
                "run_count": len(rows),
                "kwave_ok_count": sum(1 for row in rows if row.get("status") == "kwave_ok"),
                "rows": rows,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8-sig",
    )
    print(f"Wrote {len(rows)} Visible Human smoke summary row(s) to {runs_root}")


if __name__ == "__main__":
    main()
