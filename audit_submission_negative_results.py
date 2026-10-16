"""Audit retention of unfavourable endpoints and claim-limiting evidence."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def build(root: Path) -> dict:
    table = json.loads(read(root / "paper/tables/ucl_h115_validation_20260826/h115_validation_endpoints.json"))
    manuscript = read(root / "paper/PUB2_MANUSCRIPT_DRAFT_V0_1_20260812.md")
    risks = read(root / "paper/H115_REVIEWER_RISK_REGISTER_20260826.md")
    mapping = read(root / "paper/CT_HU_MAPPING_TARGET_QC_AUDIT_20260829.md")
    provenance = read(root / "paper/CASE079_PROVENANCE_COMPLIANCE_AUDIT_20260829.md")
    failed = [row for row in table["rows"] if row["status"] == "fail"]
    effective_failed = [row for row in failed if row["case"].startswith("Effective bowl")]
    nominal_failed = [row for row in failed if row["case"].startswith("Nominal")]
    checks = {
        "table_retains_24_endpoints": table.get("row_count") == 24 and len(table.get("rows", [])) == 24,
        "effective_grids_each_pass_6_of_8": all(table["counts"][case] == {"pass": 6, "fail": 2} for case in ("Effective bowl, dx0.50 mm", "Effective bowl, dx0.30 mm")),
        "nominal_geometry_retains_0_of_8": table["counts"].get("Nominal 64/64-mm bowl, dx0.50 mm") == {"pass": 0, "fail": 8},
        "effective_failures_are_axial_position_and_transverse_l2": {row["endpoint"] for row in effective_failed} == {"Axial peak-position error", "Transverse normalized L2"},
        "nominal_all_eight_failures_retained": len(nominal_failed) == 8,
        "manuscript_reports_both_effective_failure_values": all(value in manuscript for value in ("1.856 and 2.177 mm", "15.004% and 15.469%")),
        "manuscript_reports_nominal_worsening": all(value in manuscript for value in ("10.028 mm", "31.030%", "118.286%")),
        "manuscript_blocks_posthoc_registration": "applying it without independent uncertainty evidence would be post-hoc registration" in manuscript,
        "manuscript_blocks_formal_convergence": "rather than formal asymptotic convergence" in manuscript,
        "manuscript_retains_nonpassing_boundary": "It remains a nonpassing external source-model comparison and all unfavourable endpoints are retained." in manuscript,
        "reviewer_register_retains_all_eight_endpoint_gate": "Keep all eight H115 endpoints, including unfavourable ones" in risks,
        "mapping_qc_retains_unvalidated_boundaries": all(value in mapping for value in ("not validated segmentation", "engineering demonstration target only", "not presently backed")),
        "provenance_retains_private_author_confirmation": all(value in provenance for value in ("restricted-data agreement", "No explicit consent/waiver statement", "Do not add a statement that informed consent was obtained or waived")),
    }
    status = "passed_negative_results_and_limitations_retained" if all(checks.values()) else "failed"
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "trace_id": "TRACE-20260829-001",
        "status": status,
        "submission_ready": False,
        "h115_failed_endpoint_count": len(failed),
        "effective_failed_endpoint_count": len(effective_failed),
        "nominal_failed_endpoint_count": len(nominal_failed),
        "checks": checks,
        "failed_checks": [key for key, value in checks.items() if not value],
        "claim_boundary": "Retention of negative results reduces reporting bias; it does not make the nonpassing comparison successful validation.",
    }


def render(report: dict) -> str:
    lines = [
        "# Negative-results and limitations retention audit", "",
        f"Status: `{report['status']}`  ",
        f"Submission ready: `{str(report['submission_ready']).lower()}`  ",
        f"H115 failed rows retained: `{report['h115_failed_endpoint_count']}`", "",
        "## Checks", "",
    ]
    lines += [f"- [{'x' if value else ' '}] `{key}`" for key, value in report["checks"].items()]
    lines += ["", "## Interpretation", "", report["claim_boundary"], ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.root.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "negative_results_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "negative_results_audit.md").write_text(render(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "failed": report["failed_checks"]}))
    return 0 if not report["failed_checks"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
