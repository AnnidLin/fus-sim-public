"""Generate a journal-neutral, machine-readable submission inventory."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


WORD = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def section(text: str, start: str, end: str | None) -> str:
    tail = text.split(start, 1)[1]
    return tail.split(end, 1)[0] if end else tail


def build(root: Path) -> dict:
    manuscript_path = root / "paper/PUB2_MANUSCRIPT_DRAFT_V0_1_20260812.md"
    text = manuscript_path.read_text(encoding="utf-8-sig")
    headings = re.findall(r"(?m)^## (.+)$", text)
    abstract = section(text, "## Abstract", "## Introduction")
    references = section(text, "## References", "## Pre-submission author queries")
    reference_numbers = [int(value) for value in re.findall(r"(?m)^(\d+)\. ", references)]
    author_queries = re.findall(r"(?m)^\d+\. .+$", section(text, "## Pre-submission author queries", None))
    figure_legends = re.findall(r"(?m)^\*\*Figure \d+", text)
    supplementary_figures = re.findall(r"(?m)^\*\*Supplementary Figure \d+", text)
    supplementary_tables = re.findall(r"(?m)^\*\*Supplementary Table \d+", text)
    asset_groups = [
        "paper/figures/pub2_20260812/figure_manifest.json",
        "paper/figures/ucl_h115_grid_sensitivity_corrected_20260825/figure_manifest.json",
        "paper/figures/ucl_h115_source_registration_20260825/figure_manifest.json",
        "paper/tables/ucl_h115_validation_20260826/h115_validation_endpoints.json",
        "paper/tables/ucl_h115_validation_20260826/h115_methods_parameters.json",
    ]
    archive = json.loads((root / "paper/submission_archive_20260829/manifest.json").read_text(encoding="utf-8-sig"))
    bundle = json.loads((root / "paper/h115_paper_bundle_20260826/manifest.json").read_text(encoding="utf-8-sig"))
    checks = {
        "required_sections_present": all(name in headings for name in ("Abstract", "Introduction", "Methods", "Results", "Discussion", "Data and code availability", "Figure legends", "References", "Pre-submission author queries")),
        "references_are_1_to_11": reference_numbers == list(range(1, 12)),
        "three_main_figure_legends": len(figure_legends) == 3,
        "two_supplementary_figure_legends": len(supplementary_figures) == 2,
        "two_supplementary_table_legends": len(supplementary_tables) == 2,
        "five_asset_groups_present": all((root / path).is_file() for path in asset_groups),
        "paper_bundle_passed": bundle.get("status") == "passed" and bundle.get("file_count") == 31,
        "archive_has_136_files_and_is_blocked": archive.get("file_count") == 136 and archive.get("archive_ready") is False,
        "claim_boundary_present": "do not establish numerical convergence, absolute-pressure accuracy, cross-subject generalization, efficacy or safety" in text,
        "author_queries_retained": len(author_queries) == 6,
    }
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed_inventory_author_inputs_pending" if all(checks.values()) else "failed",
        "submission_ready": False,
        "target_journal": None,
        "journal_limits_evaluated": False,
        "manuscript": {
            "path": str(manuscript_path.relative_to(root)).replace("\\", "/"),
            "sha256": sha256(manuscript_path),
            "bytes": manuscript_path.stat().st_size,
            "approximate_word_count_including_references": len(WORD.findall(text)),
            "abstract_word_count": len(WORD.findall(abstract)),
            "level_2_sections": headings,
            "reference_count": len(reference_numbers),
            "main_figure_legend_count": len(figure_legends),
            "supplementary_figure_legend_count": len(supplementary_figures),
            "supplementary_table_legend_count": len(supplementary_tables),
            "pre_submission_author_query_count": len(author_queries),
        },
        "asset_groups": asset_groups,
        "paper_bundle_file_count": bundle.get("file_count"),
        "archive_file_count": archive.get("file_count"),
        "checks": checks,
        "author_pending": [
            "target journal and article type",
            "journal word/figure/table/supplement limits",
            "authors, affiliations, ORCIDs and CRediT roles",
            "funding, competing interests and acknowledgements",
            "private PhysioNet access and journal-specific consent/waiver wording",
            "project licence, immutable revision and archive DOI",
        ],
        "claim_boundary": "Inventory completeness is not submission authorization, physical validation or formal convergence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.root.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "submission_inventory.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    m = report["manuscript"]
    lines = [
        "# Journal-neutral submission inventory", "",
        f"- status: `{report['status']}`",
        f"- submission ready: `{str(report['submission_ready']).lower()}`",
        f"- approximate manuscript words including references: `{m['approximate_word_count_including_references']}`",
        f"- abstract words: `{m['abstract_word_count']}`",
        f"- references: `{m['reference_count']}`",
        f"- figure legends: `{m['main_figure_legend_count']} main + {m['supplementary_figure_legend_count']} supplementary`",
        f"- supplementary table legends: `{m['supplementary_table_legend_count']}`",
        f"- paper bundle files: `{report['paper_bundle_file_count']}`",
        f"- archive files: `{report['archive_file_count']}`", "",
        "Target journal is unresolved, so journal-specific limits have not been evaluated.", "",
        "## Author-pending fields", "",
    ]
    lines += [f"- {item}" for item in report["author_pending"]]
    lines += ["", "## Checks", ""] + [f"- [{'x' if value else ' '}] `{key}`" for key, value in report["checks"].items()] + ["", report["claim_boundary"], ""]
    (args.output_dir / "submission_inventory.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": report["status"], "failed": [key for key, value in report["checks"].items() if not value]}))
    return 0 if report["status"].startswith("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
