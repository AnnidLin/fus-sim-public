from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
MODULE = "p3a_pml16_sensitivity_analysis"
OUT_DIR = PROJECT_ROOT / "outputs" / MODULE / "079_candidate_006_dx0p75"
OUT_JSON = OUT_DIR / "p3a_pml16_sensitivity_report.json"
OUT_MD = OUT_DIR / "p3a_pml16_sensitivity_report.md"
BRIEF_DIR = PROJECT_ROOT / "outputs" / "evidence_briefs" / "p3a_pml16_boundary_sensitivity"

BASELINE_DIR = PROJECT_ROOT / "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard"
P3A_DIR = PROJECT_ROOT / "outputs/corrected_pressure_sensitivity/079_candidate_006_dx0p75_pml16_cfl0p2_standard"


METRIC_KEYS = [
    "target_pressure_mpa",
    "target_window_peak_mpa",
    "global_peak_mpa",
    "global_peak_to_target_distance_mm",
    "target_to_global_peak_ratio",
    "effective_peak_mpa",
    "effective_peak_to_target_distance_mm",
    "target_to_effective_peak_ratio",
]

THRESHOLDS = {
    "target_window_peak_relative_delta_abs_max": 0.20,
    "target_to_global_peak_ratio_relative_delta_abs_max": 0.20,
    "global_peak_to_target_distance_delta_mm_abs_max": 5.0,
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def nested(data: dict[str, Any] | None, keys: list[str], default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def relative_delta(new: float, old: float) -> float | None:
    if old == 0:
        return None
    return (new - old) / old


def metric_delta(key: str, baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    old = float(baseline[key])
    new = float(candidate[key])
    return {
        "baseline": old,
        "p3a": new,
        "absolute_delta": new - old,
        "relative_delta": relative_delta(new, old),
    }


def build_report() -> dict[str, Any]:
    baseline_runner = read_json(BASELINE_DIR / "runner_status.json")
    baseline_summary = read_json(BASELINE_DIR / "summary.json")
    baseline_focus = read_json(BASELINE_DIR / "focus_metrics.json")
    p3a_runner = read_json(P3A_DIR / "runner_status.json")
    p3a_summary = read_json(P3A_DIR / "summary.json")
    p3a_focus = read_json(P3A_DIR / "focus_metrics.json")

    deltas = {key: metric_delta(key, baseline_focus, p3a_focus) for key in METRIC_KEYS}
    threshold_checks = {
        "target_window_peak_relative_delta": {
            "status": "pass"
            if abs(float(deltas["target_window_peak_mpa"]["relative_delta"])) <= THRESHOLDS[
                "target_window_peak_relative_delta_abs_max"
            ]
            else "fail",
            "value": deltas["target_window_peak_mpa"]["relative_delta"],
            "threshold_abs_max": THRESHOLDS["target_window_peak_relative_delta_abs_max"],
        },
        "target_to_global_peak_ratio_relative_delta": {
            "status": "pass"
            if abs(float(deltas["target_to_global_peak_ratio"]["relative_delta"])) <= THRESHOLDS[
                "target_to_global_peak_ratio_relative_delta_abs_max"
            ]
            else "fail",
            "value": deltas["target_to_global_peak_ratio"]["relative_delta"],
            "threshold_abs_max": THRESHOLDS["target_to_global_peak_ratio_relative_delta_abs_max"],
        },
        "global_peak_to_target_distance_delta_mm": {
            "status": "pass"
            if abs(float(deltas["global_peak_to_target_distance_mm"]["absolute_delta"])) <= THRESHOLDS[
                "global_peak_to_target_distance_delta_mm_abs_max"
            ]
            else "fail",
            "value": deltas["global_peak_to_target_distance_mm"]["absolute_delta"],
            "threshold_abs_max": THRESHOLDS["global_peak_to_target_distance_delta_mm_abs_max"],
        },
        "source_labels_background_only": {
            "status": "pass" if nested(p3a_summary, ["source", "source_label_counts"]) == {"0": 1292} else "fail",
            "value": nested(p3a_summary, ["source", "source_label_counts"]),
            "expected": {"0": 1292},
        },
        "entry_plan_resolution_gate_not_bypassed": {
            "status": "pass"
            if nested(p3a_summary, ["config", "allow_entry_plan_resolution_mismatch"]) is False
            else "fail",
            "value": nested(p3a_summary, ["config", "allow_entry_plan_resolution_mismatch"]),
            "expected": False,
        },
    }
    failed_checks = [name for name, payload in threshold_checks.items() if payload["status"] != "pass"]
    stable_for_p3b = not failed_checks

    return {
        "report_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": MODULE,
        "case_id": "079",
        "candidate_id": "candidate_006",
        "baseline": {
            "run_id": "079_candidate_006_simple_hu300_dx075_pml12_cfl02_corrected_standard_2026-06-18",
            "output_dir": rel(BASELINE_DIR),
            "runner_status": nested(baseline_runner, ["status"]),
            "runtime_s": nested(baseline_runner, ["execution", "runtime_s"]),
            "pml_size": nested(baseline_summary, ["config", "pml_size"]),
            "cfl": nested(baseline_summary, ["config", "cfl"]),
            "grid_size": nested(baseline_summary, ["simulation_quality", "grid_size"]),
            "nt": nested(baseline_summary, ["runtime", "nt"]),
        },
        "p3a": {
            "run_id": "079_candidate_006_simple_hu300_dx075_pml16_cfl02_standard_2026-06-18",
            "output_dir": rel(P3A_DIR),
            "runner_status": nested(p3a_runner, ["status"]),
            "runtime_s": nested(p3a_runner, ["execution", "runtime_s"]),
            "pml_size": nested(p3a_summary, ["config", "pml_size"]),
            "cfl": nested(p3a_summary, ["config", "cfl"]),
            "grid_size": nested(p3a_summary, ["simulation_quality", "grid_size"]),
            "nt": nested(p3a_summary, ["runtime", "nt"]),
            "tuning_note": nested(p3a_summary, ["tuning_note"]),
        },
        "metric_deltas": deltas,
        "threshold_checks": threshold_checks,
        "decision": {
            "p3a_stable_within_thresholds": stable_for_p3b,
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
            "recommended_next_packet": (
                "P3b_cfl0p1_timestep_sensitivity_authorization" if stable_for_p3b else "pause_for_p3a_boundary_analysis"
            ),
            "claim_level": "pml_boundary_sensitivity_observation_not_convergence",
        },
        "blocked_claims": [
            "validated pressure baseline",
            "paper-grade reproduction",
            "medical or safety conclusion",
            "tuned focus baseline",
            "numerical convergence claim",
            "thermal result",
        ],
    }


def build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# P3a PML16 Sensitivity Report",
        "",
        f"- generated at: `{report['generated_at']}`",
        f"- decision: p3a stable within thresholds `{report['decision']['p3a_stable_within_thresholds']}`",
        f"- recommended next packet: `{report['decision']['recommended_next_packet']}`",
        f"- claim level: `{report['decision']['claim_level']}`",
        "",
        "## Runs",
        "",
        f"- baseline: `{report['baseline']['output_dir']}`, PML `{report['baseline']['pml_size']}`, runtime `{report['baseline']['runtime_s']}`",
        f"- P3a: `{report['p3a']['output_dir']}`, PML `{report['p3a']['pml_size']}`, runtime `{report['p3a']['runtime_s']}`",
        "",
        "## Metric Deltas",
        "",
        "| Metric | Baseline | P3a | Absolute Delta | Relative Delta |",
        "|---|---:|---:|---:|---:|",
    ]
    for key, payload in report["metric_deltas"].items():
        lines.append(
            f"| `{key}` | `{payload['baseline']}` | `{payload['p3a']}` | "
            f"`{payload['absolute_delta']}` | `{payload['relative_delta']}` |"
        )
    lines.extend(["", "## Threshold Checks", ""])
    for key, payload in report["threshold_checks"].items():
        lines.append(f"- `{key}`: `{payload['status']}` value `{payload['value']}`")
    lines.extend(["", "## Blocked Claims", ""])
    lines.extend(f"- {item}" for item in report["blocked_claims"])
    lines.append("")
    return "\n".join(lines)


def write_gap_feedback(report: dict[str, Any]) -> None:
    validation_path = OUT_DIR / "p3a_pml16_sensitivity_report_validation.json"
    validation = read_json(validation_path) if validation_path.exists() else None
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    feedback = {
        "module": "p3a_pml16_boundary_sensitivity",
        "feedback_type": "post_execution_gap_feedback",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "actual_execution": [
            "executed exactly one P3a PML16 boundary sensitivity run",
            "generated P3a comparison report against corrected P2 baseline",
            "did not run P3b",
            "did not run thermal",
        ],
        "outputs": {
            "report_json": rel(OUT_JSON),
            "report_md": rel(OUT_MD),
            "p3a_output_dir": report["p3a"]["output_dir"],
        },
        "decision": report["decision"],
        "validation": {
            "status": "passed" if nested(validation, ["report_valid"], False) is True else "pending",
            "report_valid": nested(validation, ["report_valid"]),
            "failed_check_count": nested(validation, ["failed_check_count"]),
        },
        "blocked_claims": report["blocked_claims"],
        "recommended_next_step": report["decision"]["recommended_next_packet"],
    }
    (BRIEF_DIR / "gap_feedback.json").write_text(json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8")
    (BRIEF_DIR / "gap_feedback.md").write_text(
        "\n".join(
            [
                "# Gap Feedback: P3a PML16 Boundary Sensitivity",
                "",
                "## Actual Execution",
                "",
                "- Executed exactly one P3a PML16 boundary sensitivity run.",
                "- Generated P3a comparison report against corrected P2 baseline.",
                "- Did not run P3b.",
                "- Did not run thermal.",
                "",
                "## Decision",
                "",
                f"- stable within thresholds: `{report['decision']['p3a_stable_within_thresholds']}`",
                f"- failed check count: `{report['decision']['failed_check_count']}`",
                f"- recommended next packet: `{report['decision']['recommended_next_packet']}`",
                "",
                "## Validation",
                "",
                f"- report valid: `{nested(validation, ['report_valid'])}`",
                f"- failed check count: `{nested(validation, ['failed_check_count'])}`",
                "",
                "## Outputs",
                "",
                f"- `{rel(OUT_JSON)}`",
                f"- `{rel(OUT_MD)}`",
                f"- `{report['p3a']['output_dir']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(build_markdown(report), encoding="utf-8")
    write_gap_feedback(report)
    print(f"Wrote {rel(OUT_JSON)}")
    print(f"Wrote {rel(OUT_MD)}")


if __name__ == "__main__":
    main()
