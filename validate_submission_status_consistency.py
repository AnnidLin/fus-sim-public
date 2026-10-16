"""Validate current submission status across canonical paper-facing artifacts."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(root: Path) -> dict:
    archive = read_json(root / "paper/submission_archive_20260829/manifest.json")
    preflight = read_json(root / "paper/h115_submission_preflight_20260826/submission_preflight.json")
    consistency = read_json(root / "outputs/ucl_h115_source_registration_audit_20260825/manuscript_consistency.json")
    bundle = read_json(root / "paper/h115_paper_bundle_20260826/manifest.json")
    canonical = [
        "paper/PUB2_MANUSCRIPT_DRAFT_V0_1_20260812.md",
        "paper/PUB2_REPORTING_CHECKLIST_20260812.md",
        "paper/SUBMISSION_ARCHIVE_READINESS_20260829.md",
        "paper/SUBMISSION_AUTHOR_METADATA_FORM_20260829.md",
    ]
    texts = {name: (root / name).read_text(encoding="utf-8-sig") for name in canonical}
    checks = {
        "archive_has_136_files": archive.get("file_count") == 136,
        "archive_has_no_missing_files": not archive.get("missing"),
        "archive_has_no_prohibited_matches": not archive.get("prohibited_matches"),
        "archive_not_release_ready": archive.get("archive_ready") is False,
        "archive_retains_three_blockers": set(archive.get("blockers", [])) == {"project_license_unresolved", "source_revision_not_frozen", "archive_doi_not_minted"},
        "preflight_has_zero_technical_failures": preflight.get("technical_failed_count") == 0,
        "preflight_not_submission_ready": preflight.get("submission_ready") is False,
        "manuscript_consistency_passed": consistency.get("status") == "passed" and not consistency.get("failed_checks"),
        "paper_bundle_passed_31_files": bundle.get("status") == "passed" and bundle.get("file_count") == 31 and not bundle.get("missing"),
        "canonical_docs_report_136_files": all("136" in text for text in texts.values()),
        "canonical_docs_have_no_stale_counts": all(token not in text for text in texts.values() for token in ("70 compact files", "75 files", "77 files", "78 files", "81 files", "85 files", "88 files", "92 files", "97 files", "97-file", "101 files", "101-file", "113 files", "113-file", "134 files", "134-file")),
        "decision_sheet_is_no_go": "**NOT READY TO SUBMIT**" in (root / "paper/SUBMISSION_DECISION_SHEET_20260829.md").read_text(encoding="utf-8-sig"),
    }
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "failed_checks": [key for key, value in checks.items() if not value],
        "claim_boundary": "Cross-document status consistency only; not physical validation or submission authorization.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.root.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "status_consistency.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["# Submission status consistency", "", f"Status: `{report['status']}`", ""]
    lines += [f"- [{'x' if value else ' '}] `{key}`" for key, value in report["checks"].items()]
    lines += ["", report["claim_boundary"], ""]
    (args.output_dir / "status_consistency.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": report["status"], "failed": report["failed_checks"]}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
