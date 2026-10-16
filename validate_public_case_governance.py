from __future__ import annotations

import argparse
import json
from pathlib import Path

from bbb_planning_contract import load_json
from bbb_public_case_input_contract import (
    DEFAULT_EXAMPLE,
    DEFAULT_SCHEMA,
    validate_contract,
)
from public_case_source_policy import (
    MIXED_MEDIUM,
    enforce_source_material_policy,
    load_label_counts,
)


def evaluate(
    contract_path: Path = DEFAULT_EXAMPLE,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, object]:
    contract = load_json(contract_path)
    schema = load_json(schema_path)
    validate_contract(contract, schema, verify_file_hashes=True)

    report_path = Path(__file__).resolve().parent / contract["trajectory_screening"]["dry_run_path"]
    counts = load_label_counts(report_path)
    quick_semantics = enforce_source_material_policy(
        counts,
        preset="quick",
        allow_mixed_medium_screening=True,
    )

    standard_rejected = False
    try:
        enforce_source_material_policy(
            counts,
            preset="standard",
            allow_mixed_medium_screening=True,
        )
    except ValueError:
        standard_rejected = True

    checks = {
        "contract_and_hashes_valid": True,
        "source_is_explicitly_mixed_medium": quick_semantics == MIXED_MEDIUM,
        "mixed_medium_quick_exception_explicit": True,
        "mixed_medium_standard_rejected": standard_rejected,
        "new_pressure_execution_blocked": (
            contract["provenance"]["contract_authorizes_new_pressure_execution"] is False
        ),
        "clinical_claim_blocked": contract["provenance"]["clinical_safety_claim"] is False,
    }
    return {
        "governance_version": "1.0.0",
        "contract_id": contract["contract_id"],
        "checks": checks,
        "governance_valid": all(checks.values()),
        "source_label_counts": counts,
        "claim_boundary": contract["provenance"]["claim_boundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate current public-case governance gates.")
    parser.add_argument("--contract", type=Path, default=DEFAULT_EXAMPLE)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = parser.parse_args()
    result = evaluate(args.contract, args.schema)
    print(json.dumps(result, indent=2))
    if not result["governance_valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
