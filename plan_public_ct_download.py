from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent


READY_STATES = {"ready_nifti", "ready_dicom", "partial_ready_dicom"}


def load_sources(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing public CT sources file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    sources = data.get("sources")
    if not isinstance(sources, list):
        raise ValueError(f"Sources file does not contain a sources list: {path}")
    return data


def classify_action(source: dict[str, Any]) -> dict[str, Any]:
    readiness = str(source.get("pipeline_readiness", "unknown"))
    size_risk = str(source.get("expected_size_risk", "unknown"))
    if readiness in READY_STATES and size_risk in {"low", "medium"}:
        status = "candidate_for_manual_download"
        action = "Select one small case manually, then download into data/raw_ct/public/<case_id>/."
    elif readiness in READY_STATES:
        status = "manual_selection_required"
        action = "Do not bulk download; inspect collection and choose one small case first."
    elif readiness == "requires_format_support":
        status = "blocked_requires_format_support"
        action = "Implement format support before downloading."
    else:
        status = "blocked_requires_manual_format_review"
        action = "Confirm format, license, spacing metadata, and conversion path before downloading."
    return {"download_plan_status": status, "next_action": action}


def build_plan(data: dict[str, Any], download_root: Path, dry_run: bool) -> dict[str, Any]:
    planned_sources = []
    for source in data["sources"]:
        action = classify_action(source)
        source_id = str(source["source_id"])
        planned_sources.append(
            {
                **source,
                **action,
                "future_download_dir": str(download_root / source_id),
            }
        )
    recommended_first = [
        item
        for item in planned_sources
        if item["download_plan_status"] in {"candidate_for_manual_download", "manual_selection_required"}
        and item["format"].lower().startswith("dicom")
    ]
    return {
        "description": "Dry-run public CT download plan. No download commands are executed by this script.",
        "dry_run": bool(dry_run),
        "download_root": str(download_root),
        "no_download_performed": True,
        "supported_now": data.get("supported_now", []),
        "recommended_first_action": (
            "Choose one small DICOM/NIfTI case from a license-clear source, preferably TCIA after manual collection inspection."
            if recommended_first
            else "No ready DICOM/NIfTI candidate is currently selected; choose manually before downloading."
        ),
        "sources": planned_sources,
    }


def build_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Public CT Download Plan",
        "",
        "This is a dry-run plan. No files were downloaded and `data/raw_ct` was not modified.",
        "",
        f"- Future download root: `{plan['download_root']}`",
        f"- Recommended first action: {plan['recommended_first_action']}",
        "",
        "| Source | Format | Readiness | Size risk | Plan status | Next action |",
        "|---|---|---|---|---|---|",
    ]
    for item in plan["sources"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item["source_name"]),
                    str(item["format"]),
                    str(item["pipeline_readiness"]),
                    str(item["expected_size_risk"]),
                    str(item["download_plan_status"]),
                    str(item["next_action"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Do not bulk-download TCIA or Git LFS datasets.",
            "- Store future public data only under `data/raw_ct/public/<case_id>/`.",
            "- NRRD sources require a separate reader/conversion step before entering the current pipeline.",
            "- After any future download, rerun `inventory_ct_cases.py` and `validate_ct_case.py` before building models.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a dry-run download plan for public CT source candidates.")
    parser.add_argument(
        "--sources",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "public_ct_sources.json",
        help="Input public CT sources JSON from catalog_public_ct_sources.py.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "public_ct_download_plan",
        help="Output directory for download_plan.md/json.",
    )
    parser.add_argument(
        "--download-root",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw_ct" / "public",
        help="Future-only download root. This script does not create or write this directory.",
    )
    parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.dry_run:
        raise SystemExit("ERROR: Only dry-run mode is implemented. Omit --no-dry-run.")
    data = load_sources(args.sources)
    plan = build_plan(data, args.download_root, args.dry_run)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "download_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "download_plan.md").write_text(build_markdown(plan), encoding="utf-8")
    print(f"Wrote dry-run public CT download plan to {args.output_dir}")


if __name__ == "__main__":
    main()
