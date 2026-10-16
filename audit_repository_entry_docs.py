"""Audit repository entry documents against current submission boundaries."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def build(root: Path) -> dict:
    readme = (root / "README.md").read_text(encoding="utf-8-sig")
    runbook = (root / "RUNBOOK.md").read_text(encoding="utf-8-sig")
    test_count = len(list((root / "tests").glob("test_*.py")))
    checks = {
        "readme_date_is_current": "Current Status (2026-08-29)" in readme,
        "readme_retains_submission_false": "`submission_ready=false`" in readme,
        "readme_reports_h115_6_of_8_and_0_of_8": all(token in readme for token in ("each pass 6/8", "passes 0/8", "nonpassing external comparison")),
        "readme_reports_recovered_cfl": "recovered baseline CFL0.1 comparison passes" in readme,
        "readme_has_no_stale_interrupted_cfl_status": "CFL0.1 baseline was interrupted" not in readme,
        "readme_blocks_solver_authorization": "No additional pressure solver is active or authorized" in readme,
        "readme_test_count_is_bounded_and_true": test_count > 100 and "more than 100 files" in readme,
        "readme_does_not_overstate_full_test_execution": "it is not a\nclaim that every test file ran" in readme,
        "readme_links_reviewer_guide": "paper/REVIEWER_REPRODUCTION_GUIDE_20260829.md" in readme,
        "runbook_is_not_authorization": "not authorization to launch a solver" in runbook,
        "runbook_marks_example_paths_as_historical_risk": "Example input paths may belong to older" in runbook,
        "runbook_requires_edd_and_device_gate": all(token in runbook for token in ("new Evidence Brief", "exact dry-run", "device gate", "none is currently\n> authorized")),
    }
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "trace_id": "TRACE-20260829-001",
        "status": "passed_entry_document_boundaries" if all(checks.values()) else "failed",
        "submission_ready": False,
        "test_file_count": test_count,
        "checks": checks,
        "failed_checks": [key for key, value in checks.items() if not value],
        "claim_boundary": "Entry-document currency prevents operational misuse; it does not validate simulation physics or authorize release.",
    }


def render(report: dict) -> str:
    lines = ["# Repository entry-document audit", "", f"Status: `{report['status']}`  ", f"Test files observed: `{report['test_file_count']}`", "", "## Checks", ""]
    lines += [f"- [{'x' if value else ' '}] `{key}`" for key, value in report["checks"].items()]
    lines += ["", report["claim_boundary"], ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.root.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "entry_document_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "entry_document_audit.md").write_text(render(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "failed": report["failed_checks"]}))
    return 0 if not report["failed_checks"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
