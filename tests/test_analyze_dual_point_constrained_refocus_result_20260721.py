from __future__ import annotations

import unittest

from analyze_dual_point_constrained_refocus_result_20260721 import compare


def arm(target: float, skull: float, ratio: float, non_target: float = 2.0) -> dict:
    return {
        "target_window_peak_mpa": target,
        "global_peak_mpa": 2.0,
        "target_to_global_peak_ratio": ratio,
        "skull_peak_mpa": skull,
        "non_target_peak_mpa": non_target,
        "non_target_peak_index_ijk": [1, 1, 1],
        "non_target_peak_material_label": 2,
        "replay_max_abs_pa": 1_000_000.0,
        "source_points": 2979,
        "target_index_ijk": [114, 36, 26],
        "target_window_radius_grid_points": 3,
        "field_shape": [125, 60, 50],
    }


class ConstrainedRefocusResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.control = arm(2.0, 2.0, 0.90)

    def test_all_four_gates_pass_at_boundaries(self) -> None:
        result = compare(self.control, arm(1.6, 1.6, 0.85, non_target=2.0))
        self.assertEqual(result["status"], "four_gate_pass")
        self.assertTrue(all(result["gates"].values()))

    def test_each_pressure_gate_can_fail(self) -> None:
        variants = [
            arm(1.59, 1.5, 0.90, 1.9),
            arm(1.8, 1.61, 0.90, 1.9),
            arm(1.8, 1.5, 0.849, 1.9),
            arm(1.8, 1.5, 0.90, 2.01),
        ]
        for candidate in variants:
            with self.subTest(candidate=candidate):
                self.assertFalse(compare(self.control, candidate)["passed"])

    def test_mismatched_normalization_blocks_pass(self) -> None:
        candidate = arm(1.8, 1.5, 0.90, 1.9)
        candidate["replay_max_abs_pa"] = 999_999.0
        result = compare(self.control, candidate)
        self.assertFalse(result["passed"])
        self.assertFalse(result["input_checks"]["matched_replay_normalization"])


if __name__ == "__main__":
    unittest.main()
