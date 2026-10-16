#!/usr/bin/env python3
"""Generate post-execution PUB.2 reference-chain gap feedback.

The generator is intentionally fail-closed: it requires a completed three-stage
chain and a passed independent reference-pair analysis.  It does not authorize
any numerical-sensitivity pressure cell.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
DEFAULT_BRIEF = (
    ROOT
    / "outputs"
    / "evidence_briefs"
    / "pub2_250khz_ct_numerical_sensitivity_20260807"
    / "evidence_brief.json"
)
DEFAULT_OUTPUT_DIR = DEFAULT_BRIEF.parent
EXPECTED_STAGES = ("baseline", "tr_calibrate", "tr_refocus")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{number}: expected JSON object")
        records.append(value)
    if not records:
        raise ValueError(f"{path}: no device samples")
    return records


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def resolved_chain_status_path(chain_root: Path) -> Path:
    recovered = chain_root / "reference_completion_status.json"
    return recovered if recovered.is_file() else chain_root / "chain_status.json"


def device_history_path(chain_root: Path, chain: dict[str, Any], stage: str) -> Path:
    if stage == "tr_refocus" and chain.get("recovery_attempt_id"):
        return chain_root / f"{chain['recovery_attempt_id']}_device_history.jsonl"
    return chain_root / f"{stage}_device_history.jsonl"


def summarize_device_history(path: Path) -> dict[str, Any]:
    records = read_jsonl(path)
    cores = [
        float(item["equivalent_cores"])
        for item in records
        if item.get("equivalent_cores") is not None
    ]
    working_sets = [float(item["working_set_gib"]) for item in records]
    free_memory = [float(item["system_free_memory_gib"]) for item in records]
    breaches = [
        {
            "at_utc": item.get("at_utc"),
            "reasons": list(item.get("breach_reasons", [])),
        }
        for item in records
        if item.get("breach_reasons")
    ]
    return {
        "path": relative(path),
        "sample_count": len(records),
        "maximum_equivalent_cores": max(cores) if cores else None,
        "mean_equivalent_cores": (
            sum(cores) / len(cores) if cores else None
        ),
        "maximum_working_set_gib": max(working_sets),
        "minimum_system_free_memory_gib": min(free_memory),
        "breach_events": breaches,
        "passed": not breaches,
    }


def build_feedback(
    chain_root: Path,
    analysis_path: Path,
    brief_path: Path,
) -> dict[str, Any]:
    chain_path = resolved_chain_status_path(chain_root)
    chain = load_json(chain_path)
    analysis = load_json(analysis_path)
    brief = load_json(brief_path)
    stages = {item.get("stage_id"): item for item in chain.get("stages", [])}
    chain_checks = {
        "chain_completed": chain.get("status") == "completed",
        "exact_three_stages": set(stages) == set(EXPECTED_STAGES),
        "all_stage_outputs_passed": (
            set(stages) == set(EXPECTED_STAGES)
            and all(
                item.get("status") == "completed"
                and item.get("output_validation", {}).get("status") == "passed"
                for item in stages.values()
            )
        ),
        "preflight_passed": chain.get("preflight", {}).get("status") == "passed",
        "analysis_passed": analysis.get("status") == "passed",
        "analysis_validates_fresh_pair": (
            analysis.get("decision", {}).get("fresh_reference_pair_valid") is True
        ),
        "analysis_does_not_promote_history": (
            analysis.get("decision", {}).get("historical_pair_promoted") is False
        ),
        "no_sensitivity_pressure_authorized": (
            chain.get("automatic_follow_on_sensitivity_cells_authorized") is False
            and analysis.get("decision", {}).get(
                "automatic_sensitivity_pressure_authorized"
            )
            is False
        ),
        "brief_identity_matches": (
            brief.get("brief_id")
            == "pub2_250khz_ct_numerical_sensitivity_20260807"
        ),
    }
    failed = [key for key, value in chain_checks.items() if not value]
    if failed:
        raise ValueError(f"post-execution feedback gates failed: {failed}")

    resources: dict[str, Any] = {}
    for stage in EXPECTED_STAGES:
        history = device_history_path(chain_root, chain, stage)
        resources[stage] = summarize_device_history(history)
    if not all(item["passed"] for item in resources.values()):
        raise ValueError("one or more device histories contain breach events")

    methods = analysis["same_method_historical_reproducibility"]
    contrast = analysis["fresh_method_contrast"]["metrics"]
    return {
        "schema_version": "1.0",
        "brief_id": "pub2_250khz_ct_numerical_sensitivity_20260807",
        "feedback_id": "pub2_250khz_reference_pair_feedback_20260807",
        "generated_at_utc": utc_now(),
        "status": "reference_pair_complete_sensitivity_pressure_still_blocked",
        "claim_level": "engineering_reference_method_evidence",
        "completed": [
            "historical_reuse_inventory_completed",
            "fresh_model_physical_array_equivalence_passed",
            "explicit_alpha_semantics_recorded",
            "three_resolution_coordinate_family_passed",
            "twelve_matched_dry_runs_passed",
            "fresh_dx0p75_baseline_completed",
            "fresh_dx0p75_tr_calibration_completed",
            "fresh_dx0p75_tr_refocus_completed",
            "independent_pressure_field_validation_passed",
            "same_method_historical_reproducibility_measured",
            "matched_fresh_baseline_tr_contrast_measured",
            "device_watchdog_histories_preserved",
        ],
        "verification": {
            "checks": chain_checks,
            "chain_status": relative(chain_path),
            "analysis": relative(analysis_path),
            "evidence_brief": relative(brief_path),
        },
        "execution_performed": {
            "pressure_simulation": True,
            "pressure_stages": list(EXPECTED_STAGES),
            "sensitivity_pressure_cells": [],
            "automatic_follow_on_execution": False,
        },
        "device_guard": {
            "policy": {
                "thread_environment_limit": 6,
                "priority": "BelowNormal",
                "maximum_sustained_equivalent_cores": 6.5,
                "maximum_process_tree_working_set_gib_by_stage": {
                    "baseline": 12.0,
                    "tr_calibrate": 12.0,
                    "tr_refocus": (
                        16.0 if chain.get("recovery_attempt_id") else 12.0
                    ),
                },
                "minimum_system_free_memory_gib": 4.0,
            },
            "stages": resources,
            "all_stages_passed": True,
        },
        "same_method_historical_reproducibility": {
            method: {
                "configuration_matched": item["configuration"]["matched"],
                "field_reproducibility_class": item[
                    "field_reproducibility"
                ]["reproducibility_class"],
                "relative_l2": item["field_reproducibility"].get("relative_l2"),
                "relative_linf": item["field_reproducibility"].get(
                    "relative_linf"
                ),
                "metadata_arrays_all_equal": item[
                    "field_reproducibility"
                ].get("metadata_arrays_all_equal"),
                "historical_reuse_status": "context_only_not_promoted",
            }
            for method, item in methods.items()
        },
        "fresh_method_contrast": contrast,
        "known_gaps": [
            {
                "gap": (
                    "The historical comparison pair did not record explicit "
                    "alpha semantics."
                ),
                "handling": (
                    "It remains context-only even if same-method pressure fields "
                    "are numerically close or exact."
                ),
            },
            {
                "gap": (
                    "The fresh evidence is one Case079 trajectory and one "
                    "dx0.75/PML12/CFL0.2/domain reference configuration."
                ),
                "handling": (
                    "Do not claim numerical convergence, population "
                    "generalization or paper-grade validity."
                ),
            },
            {
                "gap": (
                    "Baseline tone-burst and normalized TR replay use different "
                    "drive mechanisms."
                ),
                "handling": (
                    "Use cross-method spatial ratios and localization metrics; "
                    "do not interpret absolute MPa as a direct efficacy ratio."
                ),
            },
        ],
        "blockers": [
            "No sensitivity pressure cell has been executed.",
            "Any next cell requires a post-reference review and a new explicit amendment.",
        ],
        "next_safe_action": (
            "Review the fresh reference contrast and reproduction diagnostics. "
            "If the reference is accepted, amend the Evidence Brief to authorize "
            "exactly one single-variable sensitivity pressure cell, rerun its "
            "dry-run/resource gate, and preserve the same device watchdog."
        ),
        "pub2_reference_gate_complete": True,
        "pub2_numerical_sensitivity_complete": False,
        "clinical_safety_claim_allowed": False,
        "paper_grade_convergence_claim_allowed": False,
    }


def render_markdown(feedback: dict[str, Any]) -> str:
    lines = [
        "# PUB.2 250 kHz reference-chain gap feedback",
        "",
        f"- Status: `{feedback['status']}`",
        f"- Claim level: `{feedback['claim_level']}`",
        "- PUB.2 reference gate complete: `true`",
        "- PUB.2 numerical sensitivity complete: `false`",
        "",
        "## Device guard",
        "",
        "| Stage | Samples | Max cores | Mean cores | Max WS GiB | Min free GiB | Breaches |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for stage, item in feedback["device_guard"]["stages"].items():
        lines.append(
            f"| {stage} | {item['sample_count']} | "
            f"{item['maximum_equivalent_cores']:.3f} | "
            f"{item['mean_equivalent_cores']:.3f} | "
            f"{item['maximum_working_set_gib']:.3f} | "
            f"{item['minimum_system_free_memory_gib']:.3f} | "
            f"{len(item['breach_events'])} |"
        )
    lines.extend(
        [
            "",
            "## Same-method historical reproducibility",
            "",
            "| Method | Field class | rel L2 | rel Linf | Historical status |",
            "|---|---|---:|---:|---|",
        ]
    )
    for method, item in feedback[
        "same_method_historical_reproducibility"
    ].items():
        lines.append(
            f"| {method} | {item['field_reproducibility_class']} | "
            f"{item['relative_l2']} | {item['relative_linf']} | "
            f"{item['historical_reuse_status']} |"
        )
    lines.extend(
        [
            "",
            "## Remaining blockers",
            "",
            *[f"- {item}" for item in feedback["blockers"]],
            "",
            "## Next safe action",
            "",
            feedback["next_safe_action"],
            "",
            "No clinical-safety, efficacy, population-generalization or "
            "paper-grade convergence claim is authorized.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chain-root", type=Path, default=DEFAULT_CHAIN_ROOT)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--brief", type=Path, default=DEFAULT_BRIEF)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        feedback = build_feedback(
            args.chain_root, args.analysis, args.brief
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "gap_feedback.json"
    md_path = args.output_dir / "gap_feedback.md"
    json_path.write_text(
        json.dumps(feedback, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(feedback), encoding="utf-8")
    print(json.dumps({"status": feedback["status"], "json": str(json_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
