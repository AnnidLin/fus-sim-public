"""Validate the journal-neutral, non-solver reviewer reproduction path."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


COMMAND_SCRIPTS = (
    "validate_h115_paper_bundle_manifest.py",
    "validate_h115_manuscript_consistency.py",
    "validate_h115_submission_preflight.py",
    "validate_submission_status_consistency.py",
    "audit_submission_negative_results.py",
    "audit_manuscript_numeric_transcription.py",
    "audit_figure_table_captions.py",
)


def build(root: Path) -> dict:
    guide_path = root / "paper/REVIEWER_REPRODUCTION_GUIDE_20260829.md"
    guide = guide_path.read_text(encoding="utf-8-sig")
    manifest = json.loads((root / "paper/submission_archive_20260829/manifest.json").read_text(encoding="utf-8-sig"))
    archived = {item["path"] for item in manifest["files"]}
    checks = {
        "all_command_scripts_exist": all((root / script).is_file() for script in COMMAND_SCRIPTS),
        "all_command_scripts_are_archived": all(script in archived for script in COMMAND_SCRIPTS),
        "guide_has_both_external_dois": all(doi in guide for doi in ("10.5522/04/28025240.v2", "10.13026/4nae-zg36")),
        "guide_discloses_restricted_case079": all(token in guide for token in ("registered restricted-data", "raw CT", "reconstructable CT-derived volumes", "not included")),
        "guide_discloses_three_release_blockers": all(token in guide for token in ("project licence", "immutable revision", "DOI")),
        "guide_requires_scratch_outputs": guide.count("scratch/") >= 6,
        "guide_has_no_solver_execute_command": "--execute" not in guide,
        "guide_explicitly_blocks_pressure_solver": "does not execute `simulate_kwave_3d_focus.py`" in guide,
        "guide_retains_nonpassing_boundary": guide.count("nonpassing H115 external comparison") >= 1 or "H115 remains a nonpassing external comparison" in guide,
        "guide_retains_submission_false": "submission_ready=false" in guide,
        "archive_still_blocked": manifest.get("archive_ready") is False and manifest.get("status") == "blocked_local_candidate",
    }
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "trace_id": "TRACE-20260829-001",
        "status": "passed_non_solver_reviewer_path" if all(checks.values()) else "failed",
        "submission_ready": False,
        "command_script_count": len(COMMAND_SCRIPTS),
        "checks": checks,
        "failed_checks": [key for key, value in checks.items() if not value],
        "claim_boundary": "Executable-reader-path completeness does not reproduce excluded solver fields or establish physical validation.",
    }


def render(report: dict) -> str:
    lines = ["# Reviewer reproduction-path audit", "", f"Status: `{report['status']}`  ", f"Command scripts: `{report['command_script_count']}`", "", "## Checks", ""]
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
    (args.output_dir / "reviewer_reproduction_path.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "reviewer_reproduction_path.md").write_text(render(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "failed": report["failed_checks"]}))
    return 0 if not report["failed_checks"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
