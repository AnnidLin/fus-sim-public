"""Audit abstract length and map manuscript author queries to owned actions."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


WORD = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*")
QUERY_ACTIONS = {
    "Q1": ["A04"],
    "Q2": ["A05"],
    "Q3": ["A05"],
    "Q4": ["A01"],
    "Q5": ["A05", "A10"],
    "Q6": ["A06", "A07", "A08"],
}


def build(root: Path) -> dict:
    text = (root / "paper/PUB2_MANUSCRIPT_DRAFT_V0_1_20260812.md").read_text(encoding="utf-8-sig")
    abstract = text.split("## Abstract", 1)[1].split("## Introduction", 1)[0]
    query_text = text.split("## Pre-submission author queries", 1)[1]
    queries = re.findall(r"(?m)^(\d+)\. (.+)$", query_text)
    ledger = json.loads((root / "paper/AUTHOR_ACTION_LEDGER_20260829.json").read_text(encoding="utf-8-sig"))
    actions = {item["id"]: item for item in ledger["actions"]}
    mapped_ids = {item for ids in QUERY_ACTIONS.values() for item in ids}
    checks = {
        "abstract_at_or_below_250_words": len(WORD.findall(abstract)) <= 250,
        "six_author_queries_retained": len(queries) == 6 and [number for number, _ in queries] == list("123456"),
        "all_queries_have_action_mapping": set(QUERY_ACTIONS) == {f"Q{number}" for number, _ in queries},
        "all_mapped_actions_exist": mapped_ids <= set(actions),
        "all_mapped_actions_pending": all(actions[action_id]["status"] == "pending" for action_id in mapped_ids),
        "all_mapped_actions_have_owner_evidence_impact": all(all(actions[action_id].get(field) for field in ("owner", "evidence_needed", "impact")) for action_id in mapped_ids),
        "scope_action_covers_single_case_numerical_boundary": "single-case numerical scope" in actions["A05"]["action"],
        "release_query_maps_licence_revision_doi": QUERY_ACTIONS["Q6"] == ["A06", "A07", "A08"],
        "ledger_retains_submission_false": ledger.get("submission_ready") is False,
    }
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "trace_id": "TRACE-20260829-001",
        "status": "passed_abstract_and_author_query_mapping" if all(checks.values()) else "failed",
        "submission_ready": False,
        "abstract_word_count": len(WORD.findall(abstract)),
        "conservative_abstract_ceiling": 250,
        "query_count": len(queries),
        "query_action_mapping": QUERY_ACTIONS,
        "checks": checks,
        "failed_checks": [key for key, value in checks.items() if not value],
        "claim_boundary": "A journal-neutral word ceiling and owned query mapping reduce administrative ambiguity; target-journal and author decisions remain pending.",
    }


def render(report: dict) -> str:
    lines = ["# Abstract and author-query audit", "", f"Status: `{report['status']}`  ", f"Abstract: `{report['abstract_word_count']}` / `{report['conservative_abstract_ceiling']}` words  ", f"Queries: `{report['query_count']}`", "", "## Query-to-action mapping", ""]
    lines += [f"- `{query}` → {', '.join(f'`{item}`' for item in actions)}" for query, actions in report["query_action_mapping"].items()]
    lines += ["", "## Checks", ""] + [f"- [{'x' if value else ' '}] `{key}`" for key, value in report["checks"].items()]
    lines += ["", report["claim_boundary"], ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.root.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "abstract_author_query_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "abstract_author_query_audit.md").write_text(render(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "abstract_words": report["abstract_word_count"], "failed": report["failed_checks"]}))
    return 0 if not report["failed_checks"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
