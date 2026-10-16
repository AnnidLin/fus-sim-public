from __future__ import annotations

import unittest

import numpy as np

import generate_entry_plan_resolution_family as family


class EntryPlanResolutionFamilyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference = {
            "dx_m": 0.001,
            "target_index_ijk": [18, 10, 10],
            "source_center_index_ijk": [2, 10, 10],
            "source_to_target_distance_mm": 16.0,
            "entry_direction": "fixed_reference",
            "entry_offset_mm": [0.0, 0.0],
        }

    def test_same_resolution_plan_passes_and_crosses_skull(self) -> None:
        labels = np.ones((22, 22, 22), dtype=np.uint8)
        labels[:6] = 0
        labels[8:12] = 2
        plan, diagnostics = family.transform_plan(
            self.reference,
            labels,
            0.001,
            np.array([18, 10, 10], dtype=np.int32),
        )
        self.assertTrue(diagnostics["passed"])
        self.assertEqual(plan["source_center_index_ijk"], [2, 10, 10])
        self.assertEqual(plan["entry_index_ijk"], [8, 10, 10])
        self.assertEqual(plan["skull_exit_index_ijk"], [11, 10, 10])
        self.assertFalse(plan["pressure_execution_authorized"])

    def test_half_millimeter_mapping_preserves_physical_ray(self) -> None:
        labels = np.ones((44, 44, 44), dtype=np.uint8)
        labels[:12] = 0
        labels[16:24] = 2
        plan, diagnostics = family.transform_plan(
            self.reference,
            labels,
            0.0005,
            np.array([36, 20, 20], dtype=np.int32),
        )
        self.assertTrue(diagnostics["passed"])
        self.assertEqual(plan["source_center_index_ijk"], [4, 20, 20])
        self.assertEqual(plan["target_index_ijk"], [36, 20, 20])
        self.assertAlmostEqual(plan["source_to_target_distance_mm"], 16.0)

    def test_model_target_mismatch_fails_gate(self) -> None:
        labels = np.ones((22, 22, 22), dtype=np.uint8)
        labels[:6] = 0
        labels[8:12] = 2
        _, diagnostics = family.transform_plan(
            self.reference,
            labels,
            0.001,
            np.array([17, 10, 10], dtype=np.int32),
        )
        self.assertFalse(diagnostics["passed"])
        self.assertFalse(
            diagnostics["checks"]["model_target_matches_mapped_reference"]
        )

    def test_missing_skull_crossing_is_rejected(self) -> None:
        labels = np.ones((22, 22, 22), dtype=np.uint8)
        labels[:6] = 0
        with self.assertRaisesRegex(ValueError, "does not cross skull"):
            family.transform_plan(
                self.reference,
                labels,
                0.001,
                np.array([18, 10, 10], dtype=np.int32),
            )


if __name__ == "__main__":
    unittest.main()
