from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from audit_matched_frequency_method_inventory_20260726 import (
    CellSpec,
    audit_cell,
    build_inventory,
    compare_config,
    expected_config,
)


class MatchedFrequencyMethodInventoryTests(unittest.TestCase):
    def test_matching_config_has_no_mismatches(self) -> None:
        spec = CellSpec(
            "case079",
            500_000,
            "baseline",
            "summary.json",
            "model.npz",
            "entry.json",
        )
        self.assertEqual(compare_config(expected_config(spec), expected_config(spec)), [])

    def test_geometry_and_cycles_mismatches_are_detected(self) -> None:
        spec = CellSpec(
            "case079",
            500_000,
            "baseline",
            "summary.json",
            "model.npz",
            "entry.json",
        )
        actual = expected_config(spec)
        actual["aperture_diameter_m"] = 0.03
        actual["tone_burst_cycles"] = 2
        self.assertEqual(
            compare_config(actual, expected_config(spec)),
            ["aperture_diameter_m", "tone_burst_cycles"],
        )

    def test_audit_cell_reads_matching_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec = CellSpec(
                "case079",
                500_000,
                "baseline",
                "summary.json",
                "model.npz",
                "entry.json",
            )
            summary = {
                "config": expected_config(spec),
                "source": {"source_label_counts": {"0": 10}},
                "simulation_quality": {
                    "screening_only": True,
                    "is_paper_grade": False,
                    "runtime_s": 1.0,
                },
                "pressure": {
                    "global_peak_mpa": 2.0,
                    "target_window_peak_mpa": 1.0,
                    "target_to_global_peak_ratio": 0.5,
                },
            }
            (root / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            result = audit_cell(spec, root)
            self.assertEqual(result["status"], "present_match")
            self.assertEqual(
                result["source_material_semantics"],
                "background_only_external_source",
            )

    def test_current_inventory_has_six_matches_and_two_missing(self) -> None:
        result = build_inventory()
        self.assertEqual(result["status_counts"]["present_match"], 6)
        self.assertEqual(result["status_counts"]["present_mismatch"], 0)
        self.assertEqual(result["status_counts"]["missing"], 2)
        self.assertEqual(
            result["missing_cells"],
            ["case079_500khz_baseline", "case079_500khz_tr"],
        )
        self.assertFalse(result["matched_matrix_complete"])
        self.assertFalse(result["new_pressure_execution_authorized"])


if __name__ == "__main__":
    unittest.main()
