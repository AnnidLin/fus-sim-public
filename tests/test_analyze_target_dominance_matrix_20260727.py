from __future__ import annotations

import math
import unittest

from analyze_target_dominance_matrix_20260727 import (
    build_report,
    direction,
    finite_number,
    safe_fold,
)


class TargetDominanceDiagnosticTests(unittest.TestCase):
    def test_scalar_helpers(self) -> None:
        self.assertEqual(safe_fold(2.0, 0.5), 4.0)
        self.assertIsNone(safe_fold(1.0, 0.0))
        self.assertEqual(direction(0.1), "increase")
        self.assertEqual(direction(-0.1), "decrease")
        self.assertEqual(direction(0.0), "unchanged")
        self.assertEqual(finite_number(1, "value"), 1.0)
        with self.assertRaises(ValueError):
            finite_number(math.inf, "value")
        with self.assertRaises(ValueError):
            finite_number(True, "value")

    def test_current_matrix_has_eight_compatible_cells(self) -> None:
        report = build_report()
        self.assertEqual(report["aggregate"]["cell_count"], 8)
        self.assertTrue(report["aggregate"]["all_metric_semantics_v2"])
        self.assertEqual(len(report["method_pairs"]), 4)
        self.assertEqual(len(report["frequency_pairs"]), 4)

    def test_global_peaks_are_outside_target_windows(self) -> None:
        report = build_report()
        self.assertTrue(report["aggregate"]["all_global_peaks_outside_target_window"])
        self.assertTrue(
            all(not cell["global_peak_inside_target_window"] for cell in report["cells"])
        )
        lower, upper = report["aggregate"]["global_peak_to_target_distance_range_mm"]
        self.assertGreater(lower, 50.0)
        self.assertLess(upper, 80.0)

    def test_tr_ratio_direction_is_consistent(self) -> None:
        report = build_report()
        self.assertTrue(
            report["aggregate"]["all_four_tr_pairs_increase_target_global_ratio"]
        )
        self.assertTrue(
            all(
                pair["target_to_global_direction"] == "increase"
                for pair in report["method_pairs"]
            )
        )
        self.assertEqual(
            report["aggregate"]["highest_target_global_ratio_cell"]["cell_id"],
            "case079_500khz_tr",
        )

    def test_frequency_pattern_is_method_dependent(self) -> None:
        pattern = build_report()["aggregate"]["frequency_pattern"]
        self.assertTrue(pattern["500khz_ratio_lower_for_both_baselines"])
        self.assertTrue(pattern["500khz_ratio_higher_for_both_tr_runs"])


if __name__ == "__main__":
    unittest.main()
