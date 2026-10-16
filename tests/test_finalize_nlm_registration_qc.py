from __future__ import annotations

import unittest

from finalize_nlm_registration_qc import quantitative_checks


class FinalizeNlmRegistrationQCTests(unittest.TestCase):
    def test_small_dice_tradeoff_passes_when_nmi_and_composite_improve(self) -> None:
        report = {
            "metrics_before": {"nmi": 1.10, "dice": 0.86},
            "metrics_after": {"nmi": 1.15, "dice": 0.855},
            "checks": {"transform_plausible": True},
        }
        self.assertTrue(quantitative_checks(report)["quantitative_gate_pass"])

    def test_large_dice_drop_is_rejected(self) -> None:
        report = {
            "metrics_before": {"nmi": 1.10, "dice": 0.86},
            "metrics_after": {"nmi": 1.20, "dice": 0.75},
            "checks": {"transform_plausible": True},
        }
        self.assertFalse(quantitative_checks(report)["quantitative_gate_pass"])


if __name__ == "__main__":
    unittest.main()
