from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def metric_delta(candidate: float | None, baseline: float | None) -> float | None:
    if candidate is None or baseline is None:
        return None
    return float(candidate) - float(baseline)


def get_pressure_summary(run_dir: Path) -> dict[str, Any]:
    summary = load_json(run_dir / "summary.json")
    focus_metrics_path = run_dir / "focus_metrics.json"
    focus_metrics = load_json(focus_metrics_path) if focus_metrics_path.exists() else summary.get("pressure", {})
    return {
        "run_dir": str(run_dir),
        "summary": summary,
        "pressure": focus_metrics,
        "source": summary.get("source", {}),
        "runtime": summary.get("runtime", {}),
        "config": summary.get("config", {}),
        "tuning_note": summary.get("tuning_note", ""),
    }


def compact(run: dict[str, Any]) -> dict[str, Any]:
    pressure = run["pressure"]
    source = run["source"]
    runtime = run["runtime"]
    return {
        "run_dir": run["run_dir"],
        "target_pressure_mpa": pressure.get("target_pressure_mpa"),
        "target_window_peak_mpa": pressure.get("target_window_peak_mpa"),
        "effective_peak_mpa": pressure.get("effective_peak_mpa"),
        "effective_peak_to_target_distance_mm": pressure.get("effective_peak_to_target_distance_mm"),
        "target_to_effective_peak_ratio": pressure.get("target_to_effective_peak_ratio"),
        "source_label_counts": source.get("source_label_counts", {}),
        "source_points": source.get("source_points"),
        "runtime_s": runtime.get("runtime_s"),
        "nt": runtime.get("nt"),
        "tuning_note": run["tuning_note"],
    }


def build_comparison(baseline_dir: Path, candidate_dir: Path) -> dict[str, Any]:
    baseline = get_pressure_summary(baseline_dir)
    candidate = get_pressure_summary(candidate_dir)
    baseline_c = compact(baseline)
    candidate_c = compact(candidate)
    deltas = {
        key + "_delta": metric_delta(candidate_c.get(key), baseline_c.get(key))
        for key in [
            "target_pressure_mpa",
            "target_window_peak_mpa",
            "effective_peak_mpa",
            "effective_peak_to_target_distance_mm",
            "target_to_effective_peak_ratio",
            "runtime_s",
        ]
    }
    candidate_source_counts = candidate_c.get("source_label_counts") or {}
    source_safe = not candidate_source_counts.get("1") and not candidate_source_counts.get("2")
    return {
        "description": "Pressure-run comparison between baseline and candidate CT skull threshold models.",
        "baseline": baseline_c,
        "candidate": candidate_c,
        "deltas_candidate_minus_baseline": deltas,
        "candidate_source_mask_background_only": bool(source_safe),
        "candidate_target_window_peak_improved": bool(
            (candidate_c.get("target_window_peak_mpa") or 0) > (baseline_c.get("target_window_peak_mpa") or 0)
        ),
        "candidate_effective_peak_distance_improved": bool(
            (candidate_c.get("effective_peak_to_target_distance_mm") or float("inf"))
            < (baseline_c.get("effective_peak_to_target_distance_mm") or float("inf"))
        ),
        "interpretation": interpretation(baseline_c, candidate_c, bool(source_safe)),
    }


def interpretation(baseline: dict[str, Any], candidate: dict[str, Any], source_safe: bool) -> str:
    if not source_safe:
        return "Candidate source mask is not background-only; do not treat it as a better model."
    peak_delta = metric_delta(candidate.get("target_window_peak_mpa"), baseline.get("target_window_peak_mpa"))
    distance_delta = metric_delta(candidate.get("effective_peak_to_target_distance_mm"), baseline.get("effective_peak_to_target_distance_mm"))
    if peak_delta is not None and distance_delta is not None and peak_delta > 0 and distance_delta < 0:
        return "Candidate improves target-window pressure and effective peak distance in this quick comparison."
    if peak_delta is not None and peak_delta > 0:
        return "Candidate increases target-window pressure, but focus distance should still be checked."
    if distance_delta is not None and distance_delta < 0:
        return "Candidate improves effective peak distance, but target-window pressure should still be checked."
    return "Candidate does not clearly improve the current 300 HU baseline; avoid blind threshold tuning."


def write_markdown(path: Path, comparison: dict[str, Any]) -> None:
    baseline = comparison["baseline"]
    candidate = comparison["candidate"]
    deltas = comparison["deltas_candidate_minus_baseline"]
    lines = [
        "# Pressure Comparison: 300 HU Baseline vs 250 HU Candidate",
        "",
        "## Summary",
        "",
        f"- Interpretation: {comparison['interpretation']}",
        f"- Candidate source background-only: `{comparison['candidate_source_mask_background_only']}`",
        "",
        "## Metrics",
        "",
        "| Metric | 300 HU baseline | 250 HU candidate | Candidate - baseline |",
        "|---|---:|---:|---:|",
    ]
    for key, label in [
        ("target_pressure_mpa", "Target pressure (MPa)"),
        ("target_window_peak_mpa", "Target-window peak (MPa)"),
        ("effective_peak_mpa", "Effective peak (MPa)"),
        ("effective_peak_to_target_distance_mm", "Effective peak distance (mm)"),
        ("target_to_effective_peak_ratio", "Target/effective ratio"),
        ("runtime_s", "Runtime (s)"),
    ]:
        delta = deltas.get(key + "_delta")
        lines.append(
            f"| {label} | {fmt(baseline.get(key))} | {fmt(candidate.get(key))} | {fmt(delta)} |"
        )
    lines.extend(
        [
            "",
            "## Source Safety",
            "",
            f"- Baseline source label counts: `{baseline.get('source_label_counts')}`",
            f"- Candidate source label counts: `{candidate.get('source_label_counts')}`",
            "",
            "## Notes",
            "",
            f"- Baseline tuning note: {baseline.get('tuning_note')}",
            f"- Candidate tuning note: {candidate.get('tuning_note')}",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return f"{float(value):.6g}"
    return str(value)


def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    comparison = build_comparison(Path(args.baseline_dir), Path(args.candidate_dir))
    (output_dir / "comparison_summary.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(output_dir / "comparison_summary.md", comparison)
    print(f"comparison={output_dir / 'comparison_summary.md'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two 3D pressure simulation output directories.")
    parser.add_argument("--baseline-dir", required=True)
    parser.add_argument("--candidate-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
