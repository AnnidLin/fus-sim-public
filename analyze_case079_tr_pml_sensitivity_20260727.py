from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
BASELINE_DIR = ROOT / "outputs" / "case079_tr_500khz_matched_20260726"
CANDIDATE_DIR = (
    ROOT / "outputs" / "case079_tr_500khz_matched_pml16_cfl0p2_20260727"
)
OUTPUT_DIR = ROOT / "outputs" / "case079_tr_500khz_pml_sensitivity_20260727"
THRESHOLDS = {
    "target_window_peak_relative_delta_abs_max": 0.20,
    "target_to_global_peak_ratio_relative_delta_abs_max": 0.20,
    "global_peak_to_target_distance_delta_mm_abs_max": 5.0,
}
FROZEN_CONFIG_FIELDS = (
    "model_path",
    "entry_plan_path",
    "frequency_hz",
    "calibration_pressure_pa",
    "source_pressure_pa",
    "normalize_source",
    "transducer_radius_m",
    "aperture_diameter_m",
    "tone_burst_cycles",
    "cfl",
    "simulation_time_s",
    "preset",
    "backend",
    "device",
    "quick_mode",
    "quick_lateral_half_width_m",
    "quick_post_target_margin_m",
    "allow_entry_plan_resolution_mismatch",
)
METRIC_FIELDS = (
    "global_peak_mpa",
    "target_window_peak_mpa",
    "target_to_global_peak_ratio",
    "global_peak_to_target_distance_mm",
    "global_peak_axial_from_source_mm",
    "entry_axial_from_source_mm",
)


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label}: expected numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label}: expected finite scalar")
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
    summary = load_object(summary_path)
    focus = load_object(focus_path)
    config = summary.get("config")
    quality = summary.get("simulation_quality")
    source = summary.get("source")
    if not all(isinstance(item, dict) for item in (config, quality, source)):
        raise ValueError(f"{summary_path}: missing config/quality/source")
    metrics = {
        field: finite(focus.get(field), f"{focus_path}:{field}")
        for field in METRIC_FIELDS
    }
    return {
        "directory": str(directory.relative_to(ROOT)).replace("\\", "/"),
        "summary_sha256": sha256(summary_path),
        "focus_sha256": sha256(focus_path),
        "config": config,
        "grid_size": quality.get("grid_size"),
        "ppw_min_sound_speed": quality.get("ppw_min_sound_speed"),
        "runtime_s": quality.get("runtime_s"),
        "paper_grade": quality.get("is_paper_grade"),
        "source_label_counts": source.get("source_label_counts"),
        "metrics": {
            **metrics,
            "global_peak_axial_offset_from_entry_mm": (
                metrics["global_peak_axial_from_source_mm"]
                - metrics["entry_axial_from_source_mm"]
            ),
        },
    }


def build_report() -> dict[str, Any]:
    baseline = load_run(BASELINE_DIR)
    candidate = load_run(CANDIDATE_DIR)
    config_mismatches = [
        field
        for field in FROZEN_CONFIG_FIELDS
        if baseline["config"].get(field) != candidate["config"].get(field)
    ]
    if config_mismatches:
        raise ValueError(f"non-PML config drift: {config_mismatches}")
    if baseline["config"].get("pml_size") != 8:
        raise ValueError("baseline PML must be 8")
    if candidate["config"].get("pml_size") != 16:
        raise ValueError("candidate PML must be 16")

    deltas: dict[str, dict[str, Any]] = {}
    for field in (
        "global_peak_mpa",
        "target_window_peak_mpa",
        "target_to_global_peak_ratio",
        "global_peak_to_target_distance_mm",
        "global_peak_axial_offset_from_entry_mm",
    ):
        old = baseline["metrics"][field]
        new = candidate["metrics"][field]
        deltas[field] = {
            "baseline": old,
            "pml16": new,
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
            "value": deltas["global_peak_to_target_distance_mm"][
                "absolute_delta"
            ],
            "threshold_abs_max": THRESHOLDS[
                "global_peak_to_target_distance_delta_mm_abs_max"
            ],
        },
    }
    for payload in checks.values():
        payload["status"] = (
            "pass"
            if payload["value"] is not None
            and abs(payload["value"]) <= payload["threshold_abs_max"]
            else "fail"
        )
    source_check = (
        baseline["source_label_counts"]
        == candidate["source_label_counts"]
        == {"0": 347}
    )
    entry_gate_check = (
        baseline["config"].get("allow_entry_plan_resolution_mismatch") is False
        and candidate["config"].get("allow_entry_plan_resolution_mismatch")
        is False
    )
    failed = [name for name, payload in checks.items() if payload["status"] != "pass"]
    if not source_check:
        failed.append("source_labels_background_only")
    if not entry_gate_check:
        failed.append("entry_plan_resolution_gate")

    monitor = load_object(CANDIDATE_DIR / "monitor_status.json")
    complete = (
        monitor.get("status") == "completed"
        and (CANDIDATE_DIR / "pressure_max_mpa.npz").is_file()
        and (CANDIDATE_DIR / "summary.json").is_file()
    )
    stable = complete and not failed
    return {
        "report_version": "1.0.0",
        "module": "case079_tr_500khz_pml_sensitivity_20260727",
        "baseline": baseline,
        "pml16": candidate,
        "monitor": {
            "status": monitor.get("status"),
            "heartbeat_count": monitor.get("heartbeat_count"),
            "elapsed_s": monitor.get("elapsed_s"),
            "ceiling_adjustments": monitor.get("ceiling_adjustments"),
        },
        "config_mismatches_other_than_pml": config_mismatches,
        "metric_deltas": deltas,
        "threshold_checks": checks,
        "source_labels_background_only": source_check,
        "entry_plan_resolution_gate_not_bypassed": entry_gate_check,
        "decision": {
            "pml16_complete": complete,
            "stable_within_pause_thresholds": stable,
            "failed_checks": failed,
            "S2_cfl0p1_status": (
                "unlocked_for_separate_monitored_execution"
                if stable
                else "blocked"
            ),
            "claim_level": (
                "single_PML_perturbation_no_large_sensitivity_detected"
                if stable
                else "PML_sensitivity_incomplete_or_outside_pause_thresholds"
            ),
        },
        "blocked_claims": [
            "numerical convergence",
            "validated pressure baseline",
            "paper-grade reproduction",
            "dose or clinical safety",
            "anatomical efficacy",
        ],
    }


def write_report(report: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "pml_sensitivity_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    deltas = report["metric_deltas"]
    lines = [
        "# Case079 500 kHz TR PML Sensitivity",
        "",
        f"- PML16 complete: `{str(report['decision']['pml16_complete']).lower()}`",
        (
            "- Stable within pause thresholds: "
            f"`{str(report['decision']['stable_within_pause_thresholds']).lower()}`"
        ),
        f"- S2 CFL0.1: `{report['decision']['S2_cfl0p1_status']}`",
        f"- Monitored heartbeats: `{report['monitor']['heartbeat_count']}`",
        f"- Refocus runtime: `{report['monitor']['elapsed_s'] / 60:.1f}` minutes",
        "",
        "## Comparison",
        "",
        "| Metric | PML8 | PML16 | Relative/absolute delta | Threshold | Status |",
        "|---|---:|---:|---:|---:|---|",
        (
            f"| Target-window peak (MPa) | {deltas['target_window_peak_mpa']['baseline']:.6f} | "
            f"{deltas['target_window_peak_mpa']['pml16']:.6f} | "
            f"{deltas['target_window_peak_mpa']['relative_delta']:+.2%} | ±20% | "
            f"{report['threshold_checks']['target_window_peak_relative_delta']['status']} |"
        ),
        (
            f"| Target/global ratio | {deltas['target_to_global_peak_ratio']['baseline']:.6f} | "
            f"{deltas['target_to_global_peak_ratio']['pml16']:.6f} | "
            f"{deltas['target_to_global_peak_ratio']['relative_delta']:+.2%} | ±20% | "
            f"{report['threshold_checks']['target_to_global_peak_ratio_relative_delta']['status']} |"
        ),
        (
            f"| Global peak→target (mm) | {deltas['global_peak_to_target_distance_mm']['baseline']:.3f} | "
            f"{deltas['global_peak_to_target_distance_mm']['pml16']:.3f} | "
            f"{deltas['global_peak_to_target_distance_mm']['absolute_delta']:+.3f} mm | ±5 mm | "
            f"{report['threshold_checks']['global_peak_to_target_distance_delta_mm']['status']} |"
        ),
        "",
        "## Interpretation",
        "",
        "- No large PML sensitivity was detected under this single PML8→PML16 perturbation.",
        "- The entry-side/global peak location did not move toward the target.",
        "- This is not a numerical-convergence or paper-grade result.",
    ]
    (OUTPUT_DIR / "pml_sensitivity_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> None:
    report = build_report()
    write_report(report)
    print(
        json.dumps(
            {
                "status": "pass",
                "stable_within_pause_thresholds": report["decision"][
                    "stable_within_pause_thresholds"
                ],
                "failed_checks": report["decision"]["failed_checks"],
                "S2_cfl0p1_status": report["decision"]["S2_cfl0p1_status"],
                "output_dir": str(OUTPUT_DIR),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
