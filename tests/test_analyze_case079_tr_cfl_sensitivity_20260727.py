from __future__ import annotations

import unittest

from analyze_case079_tr_cfl_sensitivity_20260727 import build_report, relative_delta


class Case079TRCFLSensitivityTests(unittest.TestCase):
    def test_relative_delta(self) -> None:
        self.assertAlmostEqual(relative_delta(1.1, 1.0), 0.1)
        self.assertIsNone(relative_delta(1.0, 0.0))

    def test_only_cfl_changes_and_time_step_is_halved(self) -> None:
        report = build_report()
        self.assertEqual(report["config_mismatches_other_than_cfl"], [])
        self.assertTrue(report["time_step_halved"])
        self.assertTrue(report["time_steps_doubled"])
        self.assertTrue(report["decision"]["cfl0p1_complete"])

    def test_all_pause_thresholds_pass(self) -> None:
        report = build_report()
        self.assertTrue(report["decision"]["stable_within_pause_thresholds"])
        self.assertEqual(report["decision"]["failed_checks"], [])
        self.assertTrue(all(
            item["status"] == "pass"
            for item in report["threshold_checks"].values()
        ))


if __name__ == "__main__":
    unittest.main()
