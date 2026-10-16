#!/usr/bin/env python3
"""Validate the complete PUB.2 250 kHz reference evidence package.

This validator is independent of the live runner's stage validation.  It reads
the final baseline pressure, TR calibration signals, TR refocus pressure,
device histories, monitor snapshots, analysis and gap feedback.  It never runs
k-Wave and never authorizes follow-on pressure cells.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parent
DEFAULT_CHAIN_ROOT = (
    ROOT / "outputs" / "pub2_250khz_reference_pair_throttled_20260807"
)
DEFAULT_ANALYSIS = (
    ROOT
    / "outputs"
    / "pub2_250khz_reference_analysis_20260807"
    / "reference_pair_analysis.json"
)
DEFAULT_FEEDBACK = (
    ROOT
    / "outputs"
    / "evidence_briefs"
    / "pub2_250khz_ct_numerical_sensitivity_20260807"
    / "gap_feedback.json"
)
DEFAULT_OUTPUT_DIR = (
    ROOT / "outputs" / "pub2_250khz_reference_validation_20260807"
)
EXPECTED_STAGES = ("baseline", "tr_calibrate", "tr_refocus")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    values = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not values or not all(isinstance(item, dict) for item in values):
        raise ValueError(f"{path}: expected non-empty JSON-object lines")
    return values


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def resolved_chain_status_path(chain_root: Path) -> Path:
    recovered = chain_root / "reference_completion_status.json"
    return recovered if recovered.is_file() else chain_root / "chain_status.json"


def completed_device_history_path(
    chain_root: Path, chain: dict[str, Any], stage: str
) -> Path:
    if stage == "tr_refocus" and chain.get("recovery_attempt_id"):
        return chain_root / f"{chain['recovery_attempt_id']}_device_history.jsonl"
    return chain_root / f"{stage}_device_history.jsonl"


def completed_snapshot_path(
    chain_root: Path, chain: dict[str, Any], stage: str
) -> Path:
    if stage == "tr_refocus" and chain.get("recovery_attempt_id"):
        return chain_root / "monitor_snapshots" / str(chain["recovery_attempt_id"])
    return chain_root / "monitor_snapshots" / stage


def validate_core_array(path: Path, key: str) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as archive:
        present = key in archive
        if not present:
            return {
                "path": relative(path),
                "key": key,
                "present": False,
                "passed": False,
            }
        array = np.asarray(archive[key])
        finite = bool(
            np.issubdtype(array.dtype, np.number)
            and np.all(np.isfinite(array))
        )
        nonzero = bool(finite and np.any(np.abs(array) > 0))
        return {
            "path": relative(path),
            "key": key,
            "present": True,
            "shape": list(array.shape),
            "dtype": str(array.dtype),
            "finite": finite,
            "nonzero": nonzero,
            "minimum": float(np.min(array)) if finite else None,
            "maximum": float(np.max(array)) if finite else None,
            "passed": finite and nonzero,
        }


def validate_device_history(
    path: Path, *, maximum_working_set_gib: float = 12.0
) -> dict[str, Any]:
    records = read_jsonl(path)
    cores = [
        float(item["equivalent_cores"])
        for item in records
        if item.get("equivalent_cores") is not None
    ]
    max_cores = max(cores) if cores else None
    max_working_set = max(float(item["working_set_gib"]) for item in records)
    min_free = min(
        float(item["system_free_memory_gib"]) for item in records
    )
    recorded_breaches = [
        item for item in records if item.get("breach_reasons")
    ]
    checks = {
        "has_measured_cpu_samples": bool(cores),
        "maximum_equivalent_cores_at_or_below_6p5": (
            max_cores is not None and max_cores <= 6.5
        ),
        "maximum_working_set_within_stage_limit": (
            max_working_set <= maximum_working_set_gib
        ),
        "minimum_free_memory_at_or_above_4_gib": min_free >= 4.0,
        "no_recorded_breach": not recorded_breaches,
    }
    return {
        "path": relative(path),
        "sample_count": len(records),
        "maximum_equivalent_cores": max_cores,
        "maximum_working_set_gib": max_working_set,
        "authorized_working_set_limit_gib": maximum_working_set_gib,
        "minimum_system_free_memory_gib": min_free,
        "recorded_breach_count": len(recorded_breaches),
        "checks": checks,
        "passed": all(checks.values()),
    }


def validate_package(
    chain_root: Path,
    analysis_path: Path,
    feedback_path: Path,
) -> dict[str, Any]:
    chain_path = resolved_chain_status_path(chain_root)
    chain = load_json(chain_path)
    analysis = load_json(analysis_path)
    feedback = load_json(feedback_path)
    stage_map = {
        item.get("stage_id"): item for item in chain.get("stages", [])
    }

    core_arrays = {
        "baseline_pressure": validate_core_array(
            chain_root / "baseline" / "pressure_max_mpa.npz",
            "pressure_max_mpa",
        ),
        "tr_calibration_signals": validate_core_array(
            chain_root / "tr" / "element_signals.npz", "signals"
        ),
        "tr_refocus_pressure": validate_core_array(
            chain_root / "tr" / "pressure_max_mpa.npz",
            "pressure_max_mpa",
        ),
    }
    device = {
        stage: validate_device_history(
            completed_device_history_path(chain_root, chain, stage),
            maximum_working_set_gib=(
                16.0
                if stage == "tr_refocus" and chain.get("recovery_attempt_id")
                else 12.0
            ),
        )
        for stage in EXPECTED_STAGES
    }

    required_json = (
        chain_root / "baseline" / "summary.json",
        chain_root / "baseline" / "focus_metrics.json",
        chain_root / "tr" / "summary_calibrate.json",
        chain_root / "tr" / "summary.json",
        chain_root / "tr" / "focus_metrics.json",
    )
    json_checks: dict[str, bool] = {}
    for path in required_json:
        try:
            load_json(path)
            json_checks[relative(path)] = True
        except (OSError, ValueError, json.JSONDecodeError):
            json_checks[relative(path)] = False

    snapshots: dict[str, Any] = {}
    for stage in EXPECTED_STAGES:
        directory = completed_snapshot_path(chain_root, chain, stage)
        files = {
            name: (directory / name).is_file()
            for name in (
                "monitor_status.json",
                "monitor_history.jsonl",
                "monitor_attention.json",
                "monitored_stdout.txt",
                "monitored_stderr.txt",
            )
        }
        status_complete = False
        if files["monitor_status.json"]:
            status_complete = (
                load_json(directory / "monitor_status.json").get("status")
                == "completed"
            )
        snapshots[stage] = {
            "path": relative(directory),
            "files": files,
            "monitor_status_completed": status_complete,
            "passed": all(files.values()) and status_complete,
        }

    checks = {
        "chain_completed": chain.get("status") == "completed",
        "preflight_passed": chain.get("preflight", {}).get("status") == "passed",
        "exact_completed_stages": (
            set(stage_map) == set(EXPECTED_STAGES)
            and all(
                item.get("status") == "completed"
                for item in stage_map.values()
            )
        ),
        "pressure_scope_exact": (
            set(chain.get("pressure_scope", [])) == set(EXPECTED_STAGES)
        ),
        "no_follow_on_sensitivity_authorized": (
            chain.get("automatic_follow_on_sensitivity_cells_authorized") is False
        ),
        "core_arrays_passed": all(
            item["passed"] for item in core_arrays.values()
        ),
        "required_json_valid": all(json_checks.values()),
        "device_histories_passed": all(
            item["passed"] for item in device.values()
        ),
        "monitor_snapshots_passed": all(
            item["passed"] for item in snapshots.values()
        ),
        "analysis_passed": (
            analysis.get("status") == "passed"
            and analysis.get("decision", {}).get(
                "fresh_reference_pair_valid"
            )
            is True
            and analysis.get("decision", {}).get("historical_pair_promoted")
            is False
        ),
        "feedback_closes_reference_only": (
            feedback.get("pub2_reference_gate_complete") is True
            and feedback.get("pub2_numerical_sensitivity_complete") is False
            and feedback.get("paper_grade_convergence_claim_allowed") is False
            and feedback.get("clinical_safety_claim_allowed") is False
        ),
    }
    return {
        "schema_version": "1.0",
        "report_id": "pub2_250khz_reference_validation_20260807",
        "generated_at_utc": utc_now(),
        "status": "passed" if all(checks.values()) else "failed",
        "claim_level": "reference_package_integrity_validation",
        "checks": checks,
        "core_arrays": core_arrays,
        "required_json": json_checks,
        "device_histories": device,
        "monitor_snapshots": snapshots,
        "inputs": {
            "chain_status": relative(chain_path),
            "analysis": relative(analysis_path),
            "gap_feedback": relative(feedback_path),
        },
        "decision": {
            "reference_package_valid": all(checks.values()),
            "sensitivity_pressure_authorized": False,
        },
        "claim_boundary": (
            "Passing validates package integrity and device/resource records for "
            "the fresh single-case reference chain. It does not establish "
            "numerical convergence, efficacy, clinical safety or paper-grade "
            "validity and does not authorize a sensitivity pressure cell."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PUB.2 250 kHz reference-package validation",
        "",
        f"- Status: `{report['status']}`",
        "- Sensitivity pressure authorized: `false`",
        "",
        "## Checks",
        "",
        "| Check | Passed |",
        "|---|---:|",
    ]
    lines.extend(
        f"| {key} | {value} |" for key, value in report["checks"].items()
    )
    lines.extend(
        [
            "",
            "## Device histories",
            "",
            "| Stage | Samples | Max cores | Max WS GiB | Min free GiB | Passed |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for stage, item in report["device_histories"].items():
        lines.append(
            f"| {stage} | {item['sample_count']} | "
            f"{item['maximum_equivalent_cores']:.3f} | "
            f"{item['maximum_working_set_gib']:.3f} | "
            f"{item['minimum_system_free_memory_gib']:.3f} | "
            f"{item['passed']} |"
        )
    lines.extend(["", report["claim_boundary"], ""])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chain-root", type=Path, default=DEFAULT_CHAIN_ROOT)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--feedback", type=Path, default=DEFAULT_FEEDBACK)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = validate_package(
            args.chain_root, args.analysis, args.feedback
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "reference_package_validation.json"
    md_path = args.output_dir / "reference_package_validation.md"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "json": str(json_path)}))
    return 0 if report["status"] == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
