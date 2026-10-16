from __future__ import annotations

import unittest

from audit_matched_frequency_method_inventory_current import (
    build_current_inventory,
)


class CurrentMatchedFrequencyMethodInventoryTests(unittest.TestCase):
    def test_current_inventory_has_eight_matches(self) -> None:
        result = build_current_inventory()
        self.assertEqual(result["inventory_version"], "1.1.0")
        self.assertEqual(result["status_counts"]["present_match"], 8)
        self.assertEqual(result["status_counts"]["present_mismatch"], 0)
        self.assertEqual(result["status_counts"]["missing"], 0)
        self.assertEqual(result["missing_cells"], [])
        self.assertTrue(result["matched_matrix_complete"])
        self.assertFalse(result["new_pressure_execution_authorized"])

    def test_case079_500khz_cells_use_new_isolated_outputs(self) -> None:
        result = build_current_inventory()
        cells = {cell["cell_id"]: cell for cell in result["cells"]}
        baseline = cells["case079_500khz_baseline"]
        tr = cells["case079_500khz_tr"]
        self.assertEqual(baseline["status"], "present_match")
        self.assertEqual(tr["status"], "present_match")
        self.assertIn("500khz_matched_20260726", baseline["summary_path"])
        self.assertIn("500khz_matched_20260726", tr["summary_path"])
        self.assertEqual(
            baseline["source_material_semantics"],
            "background_only_external_source",
        )
        self.assertEqual(
            tr["source_material_semantics"],
            "background_only_external_source",
        )


if __name__ == "__main__":
    unittest.main()
