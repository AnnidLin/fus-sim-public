"""Audit title, abstract and manuscript for unsupported positive claims."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


FORBIDDEN_POSITIVE_PHRASES = (
    "successful external validation",
    "successfully validated case079",
    "case079 was validated",
    "grid-converged",
    "numerically converged",
    "validated intracranial pressure",
    "clinically safe",
    "clinical efficacy was demonstrated",
    "ready for submission",
    "submission-ready",
)


def build(root: Path) -> dict:
    text = (root / "paper/PUB2_MANUSCRIPT_DRAFT_V0_1_20260812.md").read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    title = lines[0]
    abstract = text.split("## Abstract", 1)[1].split("## Introduction", 1)[0]
    lower = text.lower()
    hits = [phrase for phrase in FORBIDDEN_POSITIVE_PHRASES if phrase in lower]
    checks = {
        "title_retains_simulation_scope": title.lower().endswith("simulation workflow"),
        "abstract_reports_single_case_scope": "one frozen computational case" in abstract,
        "abstract_reports_h115_6_8_6_8_0_8": all(token in abstract for token in ("each passed 6/8", "passed 0/8", "remained nonpassing")),
        "abstract_blocks_convergence_accuracy_generalization_efficacy_safety": "do not establish numerical convergence, absolute-pressure accuracy, cross-subject generalization, efficacy or safety" in abstract,
        "abstract_uses_simulated_pressure_language": "simulated pressure magnitude" in abstract,
        "no_forbidden_positive_phrase": not hits,
        "methods_block_experimental_validation_claim": "does not claim experimental validation, formal numerical convergence or clinical performance" in text,
        "discussion_retains_nonpassing_external_comparison": "It remains a nonpassing external source-model comparison" in text,
        "discussion_blocks_case079_validation_transfer": "do not validate the present Case079 source, acoustic mapping or geometry" in text,
        "data_availability_does_not_imply_release": "it remains unreleased" in text,
    }
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "trace_id": "TRACE-20260829-001",
        "status": "passed_claim_scope" if all(checks.values()) else "failed",
        "submission_ready": False,
        "forbidden_positive_phrase_hits": hits,
        "checks": checks,
        "failed_checks": [key for key, value in checks.items() if not value],
        "claim_boundary": "Absence of overclaim language improves reporting discipline; it does not establish physical validity or publication readiness.",
    }


def render(report: dict) -> str:
    lines = ["# Manuscript claim-scope audit", "", f"Status: `{report['status']}`  ", f"Forbidden positive phrase hits: `{len(report['forbidden_positive_phrase_hits'])}`", "", "## Checks", ""]
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
    (args.output_dir / "claim_scope_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "claim_scope_audit.md").write_text(render(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "failed": report["failed_checks"], "hits": report["forbidden_positive_phrase_hits"]}))
    return 0 if not report["failed_checks"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
