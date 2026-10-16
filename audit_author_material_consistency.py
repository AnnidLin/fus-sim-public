"""Audit author forms and GO/NO-GO decisions against the action ledger."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def read(root: Path, path: str) -> str:
    return (root / path).read_text(encoding="utf-8-sig")


def build(root: Path) -> dict:
    decision = read(root, "paper/SUBMISSION_DECISION_SHEET_20260829.md")
    form = read(root, "paper/SUBMISSION_AUTHOR_METADATA_FORM_20260829.md")
    handoff = read(root, "paper/SUBMISSION_AUTHOR_HANDOFF_ZH_20260829.md")
    ledger = json.loads(read(root, "paper/AUTHOR_ACTION_LEDGER_20260829.json"))
    combined = "\n".join((decision, form, handoff))
    action_markers = {
        "A01": ("Target journal", "Article type"),
        "A02": ("ORCID", "CRediT"),
        "A03": ("Funding statement", "Competing-interests"),
        "A04": ("PhysioNet", "consent/waiver"),
        "A05": ("single-case numerical scope", "unvalidated-engineering"),
        "A06": ("Project licence",),
        "A07": ("Immutable source revision",),
        "A08": ("Archive DOI",),
        "A09": ("Development/test dependency lock", "Full non-solver test report"),
        "A10": ("line-numbered manuscript",),
    }
    covered = {action_id: all(marker.lower() in combined.lower() for marker in markers) for action_id, markers in action_markers.items()}
    checks = {
        "ledger_has_ten_pending_actions": len(ledger.get("actions", [])) == 10 and all(item["status"] == "pending" for item in ledger["actions"]),
        "all_ten_actions_covered_by_author_materials": all(covered.values()),
        "overall_decision_is_not_ready": "Overall state: **NOT READY TO SUBMIT**" in decision,
        "technical_go_is_reconstruction_only": "Technical reconstruction | GO" in decision,
        "bounded_draft_go_is_internal": "A computational-methods case-study draft can be circulated internally" in decision,
        "h115_physical_validation_no_go": "H115 physical validation | NO-GO" in decision,
        "case079_validation_no_go": "Case079 quantitative/anatomical validation | NO-GO" in decision,
        "public_release_no_go": "Public data/code release | NO-GO" in decision,
        "journal_submission_no_go": "Journal submission | NO-GO" in decision,
        "form_retains_submission_false": "Repository status: `submission_ready=false`" in form,
        "form_prohibits_private_records": all(token in form for token in ("passwords", "signed agreements", "private identifiers", "ethics documents")),
        "handoff_retains_no_solver_boundary": "不启动压力求解器" in handoff,
    }
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "trace_id": "TRACE-20260829-001",
        "status": "passed_author_material_consistency" if all(checks.values()) else "failed",
        "submission_ready": False,
        "action_coverage": covered,
        "checks": checks,
        "failed_checks": [key for key, value in checks.items() if not value],
        "claim_boundary": "Complete author-facing fields and consistent decisions do not replace private author evidence or authorize submission/release.",
    }


def render(report: dict) -> str:
    lines = ["# Author-material consistency audit", "", f"Status: `{report['status']}`", "", "## Action coverage", ""]
    lines += [f"- [{'x' if value else ' '}] `{key}`" for key, value in report["action_coverage"].items()]
    lines += ["", "## Decision checks", ""] + [f"- [{'x' if value else ' '}] `{key}`" for key, value in report["checks"].items()]
    lines += ["", report["claim_boundary"], ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.root.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "author_material_consistency.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "author_material_consistency.md").write_text(render(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "failed": report["failed_checks"], "coverage": report["action_coverage"]}))
    return 0 if not report["failed_checks"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
