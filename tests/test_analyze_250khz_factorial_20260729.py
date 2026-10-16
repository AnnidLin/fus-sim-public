from __future__ import annotations

import unittest

from analyze_250khz_factorial_20260729 import build_report


class Factorial250kHzTests(unittest.TestCase):
    def test_all_cells_are_complete_and_protocol_matched(self) -> None:
        report = build_report()
        self.assertTrue(report["quality_gates"]["all_cells_complete"])
        self.assertTrue(report["quality_gates"]["all_sources_background_only"])
        self.assertEqual(report["quality_gates"]["unexpected_config_drift"], [])

    def test_large_transducer_is_the_dominant_tg_factor(self) -> None:
        report = build_report()
        effects = report["factorial_effects"]["target_to_global_peak_ratio"]
        self.assertGreater(effects["transducer_main_effect"], 0.3)
        self.assertGreater(
            abs(effects["transducer_main_effect"]),
            abs(effects["trajectory_main_effect"]),
        )

    def test_trajectory_effect_changes_sign_by_transducer(self) -> None:
        report = build_report()
        effects = report["factorial_effects"]["target_to_global_peak_ratio"]
        self.assertLess(effects["trajectory_effect_at_small"], 0)
        self.assertGreater(effects["trajectory_effect_at_large"], 0)
        self.assertGreater(effects["interaction"], 0)


if __name__ == "__main__":
    unittest.main()
