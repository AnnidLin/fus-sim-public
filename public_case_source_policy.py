from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping


BACKGROUND_ONLY = "background_only_external_source"
MIXED_MEDIUM = "mixed_medium_idealized_source"
SKULL_INVALID = "skull_overlapping_source_invalid"
UNCLASSIFIED = "unclassified_source_materials"


def normalize_label_counts(label_counts: Mapping[str | int, int] | None) -> dict[int, int]:
    if not label_counts:
        return {}
    return {
        int(label): int(count)
        for label, count in label_counts.items()
        if int(count) > 0
    }


def classify_source_materials(label_counts: Mapping[str | int, int] | None) -> str:
    counts = normalize_label_counts(label_counts)
    if not counts:
        return UNCLASSIFIED
    if any(label not in {0, 1, 2} for label in counts) or counts.get(2, 0) > 0:
        return SKULL_INVALID
    if counts.get(1, 0) > 0:
        return MIXED_MEDIUM
    return BACKGROUND_ONLY


def enforce_source_material_policy(
    label_counts: Mapping[str | int, int] | None,
    *,
    preset: str,
    allow_mixed_medium_screening: bool = False,
) -> str:
    semantics = classify_source_materials(label_counts)
    if semantics == UNCLASSIFIED:
        raise ValueError("Source material policy violation: material labels are unavailable.")
    if semantics == SKULL_INVALID:
        raise ValueError("Source material policy violation: source overlaps skull or unsupported labels.")
    if semantics == MIXED_MEDIUM:
        if not allow_mixed_medium_screening:
            raise ValueError(
                "Source material policy violation: soft-tissue source points require "
                "an explicit mixed-medium screening exception."
            )
        if preset != "quick":
            raise ValueError(
                "Mixed-medium idealized sources are permitted only for quick engineering screening."
            )
    return semantics


def load_label_counts(path: Path) -> dict[str, int]:
    report = json.loads(path.read_text(encoding="utf-8"))
    source = report.get("source", {})
    counts = source.get("source_label_counts") or source.get("label_composition")
    if not isinstance(counts, dict):
        raise ValueError(f"{path}: source label counts are missing")
    return {str(label): int(count) for label, count in counts.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate public-case source material semantics.")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--preset",
        choices=["smoke", "quick", "standard", "paper_grade"],
        default="quick",
    )
    parser.add_argument("--allow-mixed-medium-screening", action="store_true")
    args = parser.parse_args()

    counts = load_label_counts(args.report)
    semantics = enforce_source_material_policy(
        counts,
        preset=args.preset,
        allow_mixed_medium_screening=args.allow_mixed_medium_screening,
    )
    print(json.dumps({
        "status": "pass",
        "source_material_semantics": semantics,
        "source_label_counts": counts,
        "preset": args.preset,
        "mixed_medium_screening_explicitly_allowed": args.allow_mixed_medium_screening,
        "new_pressure_execution_authorized": False,
        "claim_boundary": "source_material_preflight_only",
    }, indent=2))


if __name__ == "__main__":
    main()
