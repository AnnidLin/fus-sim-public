from __future__ import annotations

import json
from pathlib import Path

import audit_matched_frequency_method_inventory_20260726 as base


CURRENT_SUMMARY_PATHS = {
    ("case079", 500_000, "baseline"): (
        "outputs/case079_kwave_quick_500khz_matched_20260726/summary.json"
    ),
    ("case079", 500_000, "tr"): (
        "outputs/case079_tr_500khz_matched_20260726/summary.json"
    ),
}


def build_current_inventory(root: Path = base.ROOT) -> dict:
    original = dict(base.SUMMARY_PATHS)
    try:
        base.SUMMARY_PATHS.update(CURRENT_SUMMARY_PATHS)
        result = base.build_inventory(root)
    finally:
        base.SUMMARY_PATHS.clear()
        base.SUMMARY_PATHS.update(original)
    result["inventory_version"] = "1.1.0"
    result["recommended_next_action"] = (
        "Review matched frequency and method screening metrics while preserving "
        "waveform-protocol and quick-resolution limitations."
    )
    return result


def main() -> None:
    result = build_current_inventory()
    base.write_report(result, base.DEFAULT_OUTPUT)
    print(
        json.dumps(
            {
                "status": "pass",
                "inventory_version": result["inventory_version"],
                "present_match": result["status_counts"]["present_match"],
                "present_mismatch": result["status_counts"]["present_mismatch"],
                "missing": result["status_counts"]["missing"],
                "matched_matrix_complete": result["matched_matrix_complete"],
                "new_pressure_execution_authorized": result[
                    "new_pressure_execution_authorized"
                ],
                "output_dir": str(base.DEFAULT_OUTPUT),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
