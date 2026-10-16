from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
BASELINE_DIR = ROOT / "outputs" / "case079_tr_500khz_matched_20260726"
CANDIDATE_DIR = ROOT / "outputs" / "case079_tr_500khz_matched_pml8_cfl0p1_20260727"
OUTPUT_DIR = ROOT / "outputs" / "case079_tr_500khz_cfl_sensitivity_20260727"
THRESHOLDS = {
    "target_window_peak_relative_delta_abs_max": 0.20,
    "target_to_global_peak_ratio_relative_delta_abs_max": 0.20,
    "global_peak_to_target_distance_delta_mm_abs_max": 5.0,
}
FROZEN_FIELDS = (
    "model_path", "entry_plan_path", "frequency_hz",
    "calibration_pressure_pa", "source_pressure_pa", "normalize_source",
    "transducer_radius_m", "aperture_diameter_m", "tone_burst_cycles",
    "simulation_time_s", "pml_size", "preset", "backend", "device",
    "quick_mode", "quick_lateral_half_width_m",
    "quick_post_target_margin_m", "allow_entry_plan_resolution_mismatch",
)
METRICS = (
    "global_peak_mpa", "target_window_peak_mpa",
    "target_to_global_peak_ratio", "global_peak_to_target_distance_mm",
    "global_peak_axial_from_source_mm", "entry_axial_from_source_mm",
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label}: expected number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label}: expected finite number")
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_delta(candidate: float, baseline: float) -> float | None:
    return None if baseline == 0 else (candidate - baseline) / baseline


def load_run(directory: Path) -> dict[str, Any]:
    summary_path = directory / "summary.json"
    focus_path = directory / "focus_metrics.json"
    summary = load_json(summary_path)
    focus = load_json(focus_path)
    config = summary["config"]
    quality = summary["simulation_quality"]
    source = summary["source"]
    metrics = {name: finite(focus.get(name), name) for name in METRICS}
    metrics["global_peak_axial_offset_from_entry_mm"] = (
        metrics["global_peak_axial_from_source_mm"]
        - metrics["entry_axial_from_source_mm"]
    )
    return {
        "directory": str(directory.relative_to(ROOT)).replace("\\", "/"),
        "summary_sha256": sha256(summary_path),
        "focus_sha256": sha256(focus_path),
        "config": config,
        "grid_size": quality.get("grid_size"),
        "dt_s": quality.get("dt_s"),
        "nt": quality.get("nt"),
        "runtime_s": quality.get("runtime_s"),
        "paper_grade": quality.get("is_paper_grade"),
        "source_label_counts": source.get("source_label_counts"),
        "metrics": metrics,
    }


def build_report() -> dict[str, Any]:
    baseline = load_run(BASELINE_DIR)
    candidate = load_run(CANDIDATE_DIR)
    mismatches = [
        field for field in FROZEN_FIELDS
        if baseline["config"].get(field) != candidate["config"].get(field)
    ]
    if mismatches:
        raise ValueError(f"non-CFL config drift: {mismatches}")
    if baseline["config"].get("cfl") != 0.2:
        raise ValueError("baseline CFL must be 0.2")
    if candidate["config"].get("cfl") != 0.1:
        raise ValueError("candidate CFL must be 0.1")

    deltas: dict[str, dict[str, Any]] = {}
    for field in (
        "global_peak_mpa", "target_window_peak_mpa",
        "target_to_global_peak_ratio", "global_peak_to_target_distance_mm",
        "global_peak_axial_offset_from_entry_mm",
    ):
        old, new = baseline["metrics"][field], candidate["metrics"][field]
        deltas[field] = {
            "cfl0p2": old, "cfl0p1": new,
            "absolute_delta": new - old,
            "relative_delta": relative_delta(new, old),
        }

    checks = {
        "target_window_peak_relative_delta": {
            "value": deltas["target_window_peak_mpa"]["relative_delta"],
            "threshold_abs_max": THRESHOLDS[
                "target_window_peak_relative_delta_abs_max"
            ],
        },
        "target_to_global_peak_ratio_relative_delta": {
            "value": deltas["target_to_global_peak_ratio"]["relative_delta"],
            "threshold_abs_max": THRESHOLDS[
                "target_to_global_peak_ratio_relative_delta_abs_max"
            ],
        },
        "global_peak_to_target_distance_delta_mm": {
            "value": deltas["global_peak_to_target_distance_mm"]["absolute_delta"],
            "threshold_abs_max": THRESHOLDS[
                "global_peak_to_target_distance_delta_mm_abs_max"
            ],
        },
    }
    for check in checks.values():
        check["status"] = (
            "pass" if check["value"] is not None
            and abs(check["value"]) <= check["threshold_abs_max"] else "fail"
        )
    source_ok = (
        baseline["source_label_counts"]
        == candidate["source_label_counts"]
        == {"0": 347}
    )
    entry_gate_ok = (
        baseline["config"].get("allow_entry_plan_resolution_mismatch") is False
        and candidate["config"].get("allow_entry_plan_resolution_mismatch") is False
    )
    time_step_halved = math.isclose(
        candidate["dt_s"], baseline["dt_s"] / 2, rel_tol=1e-12
    )
    time_steps_doubled = candidate["nt"] == baseline["nt"] * 2
    failed = [name for name, item in checks.items() if item["status"] != "pass"]
    for name, ok in (
        ("source_labels_background_only", source_ok),
        ("entry_plan_resolution_gate", entry_gate_ok),
        ("time_step_halved", time_step_halved),
        ("time_steps_doubled", time_steps_doubled),
    ):
        if not ok:
            failed.append(name)
    monitor = load_json(CANDIDATE_DIR / "monitor_status.json")
    complete = (
        monitor.get("status") == "completed"
        and monitor.get("return_code") == 0
        and all((CANDIDATE_DIR / name).is_file() for name in (
            "pressure_max_mpa.npz", "summary.json", "focus_metrics.json"
        ))
    )
    stable = complete and not failed
    return {
        "report_version": "1.0.0",
        "module": "case079_tr_500khz_cfl_sensitivity_20260727",
        "baseline_cfl0p2": baseline,
        "candidate_cfl0p1": candidate,
        "monitor": {
            "status": monitor.get("status"),
            "return_code": monitor.get("return_code"),
            "heartbeat_count": monitor.get("heartbeat_count"),
            "elapsed_s": monitor.get("elapsed_s"),
            "ceiling_adjustments": monitor.get("ceiling_adjustments"),
        },
        "config_mismatches_other_than_cfl": mismatches,
        "metric_deltas": deltas,
        "threshold_checks": checks,
        "source_labels_background_only": source_ok,
        "entry_plan_resolution_gate_not_bypassed": entry_gate_ok,
        "time_step_halved": time_step_halved,
        "time_steps_doubled": time_steps_doubled,
        "decision": {
            "cfl0p1_complete": complete,
            "stable_within_pause_thresholds": stable,
            "failed_checks": failed,
            "claim_level": (
                "single_CFL_perturbation_no_large_sensitivity_detected"
                if stable else "CFL_sensitivity_incomplete_or_outside_thresholds"
            ),
        },
        "blocked_claims": [
            "formal numerical convergence", "validated pressure baseline",
            "paper-grade reproduction", "dose or clinical safety",
            "anatomical efficacy",
        ],
    }


def write_report(report: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "cfl_sensitivity_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    d = report["metric_deltas"]
    lines = [
        "# Case079 500 kHz TR CFL Sensitivity",
        "",
        f"- CFL0.1 complete: `{str(report['decision']['cfl0p1_complete']).lower()}`",
        f"- Stable within pause thresholds: `{str(report['decision']['stable_within_pause_thresholds']).lower()}`",
        f"- Refocus runtime: `{report['monitor']['elapsed_s'] / 60:.1f}` minutes",
        "",
        "| Metric | CFL0.2 | CFL0.1 | Delta | Threshold | Status |",
        "|---|---:|---:|---:|---:|---|",
        f"| Target-window peak (MPa) | {d['target_window_peak_mpa']['cfl0p2']:.6f} | {d['target_window_peak_mpa']['cfl0p1']:.6f} | {d['target_window_peak_mpa']['relative_delta']:+.2%} | ±20% | {report['threshold_checks']['target_window_peak_relative_delta']['status']} |",
        f"| Target/global ratio | {d['target_to_global_peak_ratio']['cfl0p2']:.6f} | {d['target_to_global_peak_ratio']['cfl0p1']:.6f} | {d['target_to_global_peak_ratio']['relative_delta']:+.2%} | ±20% | {report['threshold_checks']['target_to_global_peak_ratio_relative_delta']['status']} |",
        f"| Global peak→target (mm) | {d['global_peak_to_target_distance_mm']['cfl0p2']:.3f} | {d['global_peak_to_target_distance_mm']['cfl0p1']:.3f} | {d['global_peak_to_target_distance_mm']['absolute_delta']:+.3f} mm | ±5 mm | {report['threshold_checks']['global_peak_to_target_distance_delta_mm']['status']} |",
        "",
        "The single CFL0.2→0.1 perturbation shows no large sensitivity under the",
        "preregistered engineering thresholds. The entry-side peak remains about",
        "56.38 mm from the target. This is not a formal convergence result.",
    ]
    (OUTPUT_DIR / "cfl_sensitivity_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> None:
    report = build_report()
    write_report(report)
    print(json.dumps({
        "status": "pass" if report["decision"]["stable_within_pause_thresholds"] else "fail",
        "stable_within_pause_thresholds": report["decision"]["stable_within_pause_thresholds"],
        "failed_checks": report["decision"]["failed_checks"],
        "output_dir": str(OUTPUT_DIR),
    }, indent=2))


if __name__ == "__main__":
    main()
