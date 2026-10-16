from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from bbb_planning_contract import DEFAULT_SCHEMA, ContractError, load_json, validate_contract


ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = ROOT / "planning_contracts" / "examples" / "bbb_cohort_manifest.json"


class CohortReadinessError(ValueError):
    pass


def _resolve_file(relative_path: str, project_root: Path) -> Path:
    path = (project_root / relative_path).resolve()
    try:
        path.relative_to(project_root.resolve())
    except ValueError as error:
        raise CohortReadinessError(f"path escapes project root: {relative_path}") from error
    if not path.is_file():
        raise CohortReadinessError(f"required file does not exist: {relative_path}")
    return path


def _artifact(case: dict[str, Any], name: str, project_root: Path) -> dict[str, Any]:
    artifacts = case.get("artifacts")
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get(name), str):
        raise CohortReadinessError(f"case {case.get('case_id', '<unknown>')}: missing artifacts.{name}")
    return load_json(_resolve_file(artifacts[name], project_root))


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("manifest_version") != "1.0.0":
        raise CohortReadinessError("manifest_version must be 1.0.0")
    if not isinstance(manifest.get("cohort_id"), str) or not manifest["cohort_id"].strip():
        raise CohortReadinessError("cohort_id must be a non-empty string")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise CohortReadinessError("cases must be a non-empty array")
    case_ids = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise CohortReadinessError(f"cases[{index}] must be an object")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise CohortReadinessError(f"cases[{index}].case_id must be a non-empty string")
        if not isinstance(case.get("plan_path"), str):
            raise CohortReadinessError(f"case {case_id}: plan_path must be a string")
        case_ids.append(case_id)
    duplicates = sorted(case_id for case_id, count in Counter(case_ids).items() if count > 1)
    if duplicates:
        raise CohortReadinessError(f"duplicate case_id values: {duplicates}")


def audit_case(
    case: dict[str, Any],
    schema: dict[str, Any],
    project_root: Path,
    verify_file_hashes: bool,
) -> dict[str, Any]:
    case_id = case["case_id"]
    plan = load_json(_resolve_file(case["plan_path"], project_root))
    try:
        validate_contract(plan, schema, verify_file_hashes=verify_file_hashes)
    except ContractError as error:
        raise CohortReadinessError(f"case {case_id}: invalid plan contract: {error}") from error
    if plan["patient_model"]["case_id"] != case_id:
        raise CohortReadinessError(f"case {case_id}: plan patient_model.case_id mismatch")

    report = _artifact(case, "plan_report", project_root)
    validation = _artifact(case, "report_validation", project_root)
    roi = _artifact(case, "roi_summary", project_root)
    roi_intake = _artifact(case, "registered_roi_intake", project_root)
    ranking = _artifact(case, "path_ranking", project_root)
    elements = _artifact(case, "element_plan", project_root)
    exposure = _artifact(case, "exposure_proxy", project_root)
    selected = report.get("path", {}).get("selected_existing_fullwave_trajectory")
    checks = {
        "report_case_matches": report.get("case_id") == case_id,
        "report_plan_matches": report.get("plan_id") == plan.get("plan_id"),
        "report_validation_passes": validation.get("status") == "pass"
        and validation.get("passed") == validation.get("total"),
        "roi_plan_matches": roi.get("plan_id") == plan.get("plan_id"),
        "roi_identity_matches": roi.get("roi_id") == plan["target_roi"]["roi_id"],
        "roi_intake_case_matches": roi_intake.get("case_id") == case_id,
        "roi_intake_identity_matches": roi_intake.get("roi_id") == plan["target_roi"]["roi_id"],
        "ranking_available": ranking.get("status") == "validated_ranking_available",
        "selected_path_matches_ranking": selected == ranking.get("lowest_validated_acoustic_cost_path"),
        "element_path_aligned": elements.get("trajectory") == selected,
        "element_checks_pass": bool(elements.get("checks")) and all(elements["checks"].values()),
        "no_clinical_claim": report.get("clinical_safety_claim") is False
        and exposure.get("clinical_safety_claim") is False,
        "report_runs_no_pressure": report.get("pressure_executed_by_report") is False,
    }
    prototype_ready = all(checks.values())
    anatomical_ready = roi_intake.get("status") == "registered_roi_intake_ready"
    hardware_ready = elements.get("hardware_geometry_required_for_device_export") is False
    exposure_blockers = list(exposure.get("blockers") or [])
    exposure_ready = exposure.get("status") != "blocked_for_bbb_dose_metrics" and not exposure_blockers
    blockers = []
    if not prototype_ready:
        blockers.append("prototype_artifact_consistency_failed")
    if not anatomical_ready:
        blockers.append("registered_anatomy_and_world_mapping_unavailable")
    if not hardware_ready:
        blockers.append("physical_device_geometry_unavailable")
    blockers.extend(exposure_blockers)
    return {
        "case_id": case_id,
        "plan_id": plan["plan_id"],
        "selected_trajectory": selected,
        "contract_valid": True,
        "file_hashes_verified": verify_file_hashes,
        "prototype_ready": prototype_ready,
        "anatomical_ready": anatomical_ready,
        "hardware_ready": hardware_ready,
        "exposure_ready": exposure_ready,
        "checks": checks,
        "blockers": sorted(set(blockers)),
        "claim_boundary": "research_simulation_readiness_not_clinical_readiness",
    }


def audit_cohort(
    manifest: dict[str, Any],
    schema: dict[str, Any],
    project_root: Path = ROOT,
    verify_file_hashes: bool = False,
) -> dict[str, Any]:
    validate_manifest(manifest)
    cases = [audit_case(case, schema, project_root, verify_file_hashes) for case in manifest["cases"]]
    prototype_count = sum(case["prototype_ready"] for case in cases)
    registered_count = sum(case["anatomical_ready"] for case in cases)
    multi_case_ready = len(cases) >= 2 and prototype_count == len(cases) and registered_count == len(cases)
    blocker_counts = Counter(blocker for case in cases for blocker in case["blockers"])
    return {
        "status": "multi_case_registered_cohort_ready" if multi_case_ready else "cohort_onboarding_incomplete",
        "manifest_version": manifest["manifest_version"],
        "cohort_id": manifest["cohort_id"],
        "case_count": len(cases),
        "prototype_ready_count": prototype_count,
        "registered_anatomy_ready_count": registered_count,
        "multi_case_registered_analysis_ready": multi_case_ready,
        "cases": cases,
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "pressure_executed": False,
        "clinical_safety_claim": False,
        "claim_boundary": "cohort_input_and_evidence_readiness_only",
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cohort_readiness.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    fields = [
        "case_id", "plan_id", "selected_trajectory", "prototype_ready",
        "anatomical_ready", "hardware_ready", "exposure_ready", "blockers",
    ]
    with (output_dir / "case_readiness.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for case in result["cases"]:
            row = {key: case[key] for key in fields[:-1]}
            row["blockers"] = ";".join(case["blockers"])
            writer.writerow(row)
    lines = [
        f"# BBB Cohort Readiness: {result['cohort_id']}", "",
        f"- Status: `{result['status']}`", f"- Cases: {result['case_count']}",
        f"- Pure-simulation prototypes ready: {result['prototype_ready_count']}/{result['case_count']}",
        f"- Registered anatomy ready: {result['registered_anatomy_ready_count']}/{result['case_count']}",
        f"- Multi-case registered analysis ready: `{str(result['multi_case_registered_analysis_ready']).lower()}`",
        "- Claim boundary: cohort input and evidence readiness only; not clinical readiness.", "",
        "## Cases", "", "| Case | Prototype | Anatomy | Hardware | Exposure | Selected trajectory |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for case in result["cases"]:
        lines.append(
            f"| {case['case_id']} | {case['prototype_ready']} | {case['anatomical_ready']} | "
            f"{case['hardware_ready']} | {case['exposure_ready']} | {case['selected_trajectory']} |"
        )
    lines.extend(["", "## Blocking evidence", ""])
    lines.extend(f"- `{blocker}`: {count} case(s)" for blocker, count in result["blocker_counts"].items())
    (output_dir / "cohort_readiness.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit BBB multi-case onboarding and evidence readiness.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-files", action="store_true")
    args = parser.parse_args()
    result = audit_cohort(load_json(args.manifest), load_json(args.schema), verify_file_hashes=args.verify_files)
    if args.output_dir:
        write_outputs(result, args.output_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
