from __future__ import annotations

import unittest

from analyze_case079_tr_pml_sensitivity_20260727 import (
    build_report,
    relative_delta,
)


class Case079TRPMLSensitivityTests(unittest.TestCase):
    def test_relative_delta(self) -> None:
        self.assertAlmostEqual(relative_delta(1.1, 1.0), 0.1)
        self.assertIsNone(relative_delta(1.0, 0.0))

    def test_only_pml_changes_and_outputs_are_complete(self) -> None:
        report = build_report()
        self.assertEqual(report["config_mismatches_other_than_pml"], [])
        self.assertTrue(report["decision"]["pml16_complete"])
        self.assertEqual(report["monitor"]["status"], "completed")
        self.assertGreaterEqual(report["monitor"]["heartbeat_count"], 30)

    def test_all_pause_thresholds_pass(self) -> None:
        report = build_report()
        self.assertTrue(report["decision"]["stable_within_pause_thresholds"])
        self.assertEqual(report["decision"]["failed_checks"], [])
        self.assertTrue(
            all(
                payload["status"] == "pass"
                for payload in report["threshold_checks"].values()
            )
        )
        self.assertEqual(
            report["decision"]["S2_cfl0p1_status"],
            "unlocked_for_separate_monitored_execution",
        )


if __name__ == "__main__":
    unittest.main()
