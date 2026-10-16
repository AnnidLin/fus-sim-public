"""Generate a bounded pre-close snapshot for TRACE-20260829-001."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


START = datetime.fromisoformat("2026-08-29T00:02:00+08:00")
TARGET_HOURS = 10.0


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(root: Path, as_of: datetime) -> dict:
    spec = read_json(root / "paper/submission_archive_spec_20260829.json")
    bundle = read_json(root / "paper/h115_paper_bundle_20260826/manifest.json")
    preflight = read_json(root / "paper/h115_submission_preflight_20260826/submission_preflight.json")
    consistency = read_json(root / "outputs/ucl_h115_source_registration_audit_20260825/manuscript_consistency.json")
    ledger = read_json(root / "outputs/run_ledger_validation.json")
    registry = read_json(root / "outputs/evidence_registry/evidence_registry_validation.json")
    reproducibility = read_json(root / "outputs/reproducibility_manifest/case_079_reproducibility_manifest_validation.json")
    author_actions = read_json(root / "paper/AUTHOR_ACTION_LEDGER_20260829.json")
    evidence = read_json(root / "outputs/evidence_briefs/submission_readiness_20260829/evidence_brief.json")
    base = read_json(root / spec["base_manifest"])
    expected_files = len({item["path"] for item in base["files"]} | set(spec["extra_files"]))
    elapsed = max(0.0, (as_of - START).total_seconds() / 3600.0)
    checks = {
        "paper_bundle_passed": bundle.get("status") == "passed" and not bundle.get("missing"),
        "technical_preflight_passed": preflight.get("technical_failed_count") == 0,
        "submission_remains_not_ready": preflight.get("submission_ready") is False,
        "manuscript_consistency_passed": consistency.get("status") == "passed" and not consistency.get("failed_checks"),
        "run_ledger_valid": ledger.get("ledger_valid") is True,
        "evidence_registry_valid": registry.get("registry_valid") is True,
        "reproducibility_manifest_valid": reproducibility.get("manifest_valid") is True,
        "archive_candidate_has_136_files": expected_files == 136,
        "author_actions_remain_explicit": len([a for a in author_actions["actions"] if a["status"] == "pending"]) == 10,
        "evidence_brief_remains_open": evidence.get("status") == "in_progress_non_solver",
    }
    work_window_reached = elapsed >= TARGET_HOURS
    return {
        "schema_version": "1.0",
        "trace_id": "TRACE-20260829-001",
        "as_of": as_of.isoformat(),
        "window_start": START.isoformat(),
        "target_hours": TARGET_HOURS,
        "elapsed_hours": round(elapsed, 3),
        "work_window_reached": work_window_reached,
        "closure_complete": False,
        "status": "preclose_passed_pending_time_and_author_actions" if all(checks.values()) and not work_window_reached else "review_required",
        "submission_ready": False,
        "solver_authorized": False,
        "h115_external_comparison": "nonpassing",
        "archive": {
            "expected_file_count": expected_files,
            "ready": False,
            "blockers": ["project_license_unresolved", "source_revision_not_frozen", "archive_doi_not_minted"],
        },
        "pending_author_action_count": 10,
        "checks": checks,
        "failed_checks": [key for key, value in checks.items() if not value],
        "retained_gaps": [
            "Independent H115 per-ring complex drive or measured complex field/hologram is unavailable.",
            "Case079 mapping, segmentation, registration and engineering target lack independent validation.",
            "Private PhysioNet access and journal-specific consent/waiver wording require author confirmation.",
            "Project licence, immutable source revision and archive DOI require author action.",
            "A pinned test runner/development lock and retained full non-solver test report are pending.",
            "Target journal, authorship and declarations are unresolved.",
        ],
        "claim_boundary": "This is a technical pre-close snapshot, not physical validation, submission authorization, convergence evidence, or a clinical/safety conclusion.",
    }


def render(report: dict) -> str:
    lines = [
        "# Submission pre-close snapshot", "",
        f"Trace: `{report['trace_id']}`  ",
        f"Status: `{report['status']}`  ",
        f"Elapsed window: `{report['elapsed_hours']}` / `{report['target_hours']}` hours  ",
        f"Work window reached: `{str(report['work_window_reached']).lower()}`  ",
        f"Closure complete: `{str(report['closure_complete']).lower()}`  ",
        f"Submission ready: `{str(report['submission_ready']).lower()}`  ",
        f"Solver authorized: `{str(report['solver_authorized']).lower()}`", "",
        "## Technical checks", "",
    ]
    lines += [f"- [{'x' if value else ' '}] `{key}`" for key, value in report["checks"].items()]
    lines += ["", "## Retained gaps", ""] + [f"- {item}" for item in report["retained_gaps"]]
    lines += ["", "## Boundary", "", report["claim_boundary"], ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--as-of", required=True, help="ISO-8601 timestamp with offset")
    args = parser.parse_args()
    report = build(args.root.resolve(), datetime.fromisoformat(args.as_of))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "closure_snapshot.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "closure_snapshot.md").write_text(render(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "elapsed_hours": report["elapsed_hours"], "failed": report["failed_checks"]}))
    return 0 if not report["failed_checks"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
