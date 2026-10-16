"""Build a deterministic H115 technical-submission preflight report."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def build() -> dict:
    consistency = load("outputs/ucl_h115_source_registration_audit_20260825/manuscript_consistency.json")
    package = load("outputs/ucl_h115_source_registration_audit_20260825/package_validation.json")
    reconstruction = load("outputs/ucl_h115_recheck_20260826/reproducibility_recheck.json")
    bundle = load("paper/h115_paper_bundle_20260826/manifest.json")
    endpoints = load("paper/tables/ucl_h115_validation_20260826/h115_validation_endpoints.json")
    manuscript = (ROOT / "paper/PUB2_MANUSCRIPT_DRAFT_V0_1_20260812.md").read_text(encoding="utf-8")
    risks = (ROOT / "paper/H115_REVIEWER_RISK_REGISTER_20260826.md").read_text(encoding="utf-8")
    archive = load("paper/submission_archive_20260829/manifest.json")
    provenance = (ROOT / "paper/CASE079_PROVENANCE_COMPLIANCE_AUDIT_20260829.md").read_text(encoding="utf-8")
    mapping = (ROOT / "paper/CT_HU_MAPPING_TARGET_QC_AUDIT_20260829.md").read_text(encoding="utf-8")
    traceability = load("paper/submission_traceability_20260829/traceability_matrix.json")
    author_form = (ROOT / "paper/SUBMISSION_AUTHOR_METADATA_FORM_20260829.md").read_text(encoding="utf-8")
    reviewer_response = (ROOT / "paper/REVIEWER_RESPONSE_TEMPLATE_20260829.md").read_text(encoding="utf-8")
    decision_sheet = (ROOT / "paper/SUBMISSION_DECISION_SHEET_20260829.md").read_text(encoding="utf-8")
    handoff_zh = (ROOT / "paper/SUBMISSION_AUTHOR_HANDOFF_ZH_20260829.md").read_text(encoding="utf-8")
    submission_inventory = load("paper/submission_inventory_20260829/submission_inventory.json")
    reference_audit = load("paper/MANUSCRIPT_REFERENCE_AUDIT_20260829.json")
    journal_criteria = (ROOT / "paper/JOURNAL_SELECTION_CRITERIA_20260829.md").read_text(encoding="utf-8")
    environment_audit = load("paper/REPRODUCIBILITY_ENVIRONMENT_AUDIT_20260829.json")
    action_ledger = load("paper/AUTHOR_ACTION_LEDGER_20260829.json")
    dependency_licences = load("paper/dependency_licence_inventory_20260829/dependency_licence_inventory.json")
    with (ROOT / "outputs/evidence_briefs/submission_readiness_20260829/case079_claim_source_matrix.csv").open(encoding="utf-8") as handle:
        provenance_rows = list(csv.DictReader(handle))
    with (ROOT / "outputs/evidence_briefs/ct_hu_mapping_qc_20260829/claim_source_matrix.csv").open(encoding="utf-8") as handle:
        mapping_rows = list(csv.DictReader(handle))

    expected_counts = {
        "Effective bowl, dx0.50 mm": {"pass": 6, "fail": 2},
        "Effective bowl, dx0.30 mm": {"pass": 6, "fail": 2},
        "Nominal 64/64-mm bowl, dx0.50 mm": {"pass": 0, "fail": 8},
    }
    checks = {
        "manuscript_consistency_passed": consistency.get("status") == "passed",
        "integrated_package_passed": package.get("status") == "passed_with_nonpassing_external_validation",
        "fresh_reconstruction_passed": reconstruction.get("status") == "passed",
        "fresh_reconstruction_has_3_analysis_checks": len(reconstruction.get("checks", [])) == 3,
        "fresh_reconstruction_has_10_derived_checks": len(reconstruction.get("derived_checks", [])) == 10,
        "paper_bundle_manifest_passed": bundle.get("status") == "passed" and bundle.get("file_count") == bundle.get("expected_count"),
        "endpoint_counts_preserved": endpoints.get("counts") == expected_counts,
        "manuscript_retains_nonconvergence_boundary": "do not establish numerical convergence" in manuscript,
        "manuscript_retains_nonpassing_h115_boundary": "nonpassing external source-model comparison" in manuscript,
        "reviewer_register_has_13_risks": sum(
            line.startswith(("| High |", "| Medium |", "| Low |")) for line in risks.splitlines()
        ) == 13,
        "case079_provenance_matrix_has_9_claims": len(provenance_rows) == 9,
        "case079_dataset_doi_resolved": "10.13026/4nae-zg36" in provenance and "10.13026/4nae-zg36" in manuscript,
        "case079_raw_redistribution_blocked": "raw CT must be excluded" in provenance and "will not be redistributed" in manuscript,
        "mapping_matrix_has_14_claims": len(mapping_rows) == 14,
        "mapping_accuracy_boundary_retained": "not presently backed" in mapping and "not treated as a validated" in manuscript,
        "archive_candidate_has_no_missing_or_prohibited_files": not archive.get("missing") and not archive.get("prohibited_matches"),
        "archive_release_blockers_retained": set(archive.get("blockers", [])) == {
            "project_license_unresolved", "source_revision_not_frozen", "archive_doi_not_minted"
        },
        "figure_table_traceability_passed": traceability.get("status") == "passed"
        and len(traceability.get("items", [])) == 5
        and all(traceability.get("checks", {}).values()),
        "author_form_retains_release_and_scientific_gates": all(
            marker in author_form for marker in (
                "submission_ready=false", "[AUTHOR REQUIRED]", "nonpassing external comparison",
                "Raw Case079 CT excluded", "Project licence selected",
            )
        ),
        "reviewer_template_retains_failure_boundaries": all(
            marker in reviewer_response for marker in (
                "passed 6/8", "does not use “grid converged.”", "unvalidated engineering profile",
                "Reproducibility does not equal physical accuracy",
            )
        ),
        "decision_sheet_retains_submission_no_go": all(
            marker in decision_sheet for marker in (
                "**NOT READY TO SUBMIT**", "H115 physical validation | NO-GO",
                "Public data/code release | NO-GO", "No further k-Wave run is authorized",
            )
        ),
        "decision_sheet_preserves_author_actions": "Minimum author actions before submission" in decision_sheet,
        "chinese_handoff_retains_no_go_boundaries": all(
            marker in handoff_zh for marker in (
                "尚不能正式投稿", "136 个小型文件", "H115 已成功验证",
                "当前没有证据支持再启动一次 k-Wave 求解",
            )
        ),
        "submission_inventory_passed_but_not_ready": submission_inventory.get("status") == "passed_inventory_author_inputs_pending"
        and submission_inventory.get("submission_ready") is False
        and submission_inventory.get("target_journal") is None
        and all(submission_inventory.get("checks", {}).values()),
        "reference_audit_scopes_all_11_citations": reference_audit.get("status") == "passed_for_scoped_claims"
        and reference_audit.get("reference_count") == 11
        and len(reference_audit.get("entries", [])) == 11
        and all(reference_audit.get("checks", {}).values()),
        "journal_criteria_requires_author_candidates": all(
            marker in journal_criteria for marker in (
                "does not choose or rank a journal", "Provide 2–4 candidate journals",
                "requires public redistribution of the restricted raw CT",
            )
        ),
        "environment_audit_retains_test_runner_gap": environment_audit.get("status") == "passed_with_test_runner_gap"
        and environment_audit.get("checks", {}).get("all_11_documented_cli_interfaces_load") is True
        and environment_audit.get("checks", {}).get("pytest_available_in_kwave_runtime") is False,
        "author_action_ledger_has_10_open_items": action_ledger.get("status") == "open_author_and_release_actions"
        and action_ledger.get("submission_ready") is False
        and len(action_ledger.get("actions", [])) == 10
        and all(item.get("status") == "pending" for item in action_ledger.get("actions", [])),
        "dependency_licence_inventory_retains_project_blocker": dependency_licences.get("status") == "conditional_project_licence_missing"
        and dependency_licences.get("dependency_count") == 29
        and dependency_licences.get("project_licence_author_decision_required") is True
        and all(item.get("version_matches") for item in dependency_licences.get("dependencies", [])),
    }
    blockers = [
        "Author must privately confirm the registered PhysioNet access record and any journal-specific individual-consent/waiver wording.",
        "The exact binary acoustic mapping, threshold-only segmentation and engineering target remain unvalidated; stronger accuracy/anatomical claims require new independent evidence.",
        "Author must choose the project licence, freeze an immutable source revision and mint/report the archive DOI.",
    ]
    technical_passed = all(checks.values())
    return {
        "schema_version": "1.0",
        "status": "technical_package_passed_author_inputs_pending" if technical_passed else "technical_preflight_failed",
        "technical_checks": checks,
        "technical_check_count": len(checks),
        "technical_failed_count": sum(not value for value in checks.values()),
        "submission_ready": False,
        "author_blockers": blockers,
        "claim_boundary": "Nonpassing H115 external comparison; not successful validation, formal convergence, Case079 validation, or a clinical/safety conclusion.",
    }


def markdown(report: dict) -> str:
    lines = [
        "# H115 submission preflight",
        "",
        f'- status: `{report["status"]}`',
        f'- technical checks: `{report["technical_check_count"] - report["technical_failed_count"]}/{report["technical_check_count"]}`',
        f'- submission ready: `{str(report["submission_ready"]).lower()}`',
        "",
        "## Technical checks",
        "",
    ]
    lines.extend(f'- [{"x" if passed else " "}] `{name}`' for name, passed in report["technical_checks"].items())
    lines.extend(["", "## Author blockers", ""])
    lines.extend(f"- {blocker}" for blocker in report["author_blockers"])
    lines.extend(["", "## Claim boundary", "", report["claim_boundary"], ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "submission_preflight.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "submission_preflight.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "failed": report["technical_failed_count"]}))
    return 0 if report["technical_failed_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
