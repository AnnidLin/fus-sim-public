import unittest
from pathlib import Path

from generate_d60_r78p330_confirmation_report import build_report


class D60R78ConfirmationReportTests(unittest.TestCase):
    def test_canonical_confirmation_passes_and_only_authorizes_dx0p5(self) -> None:
        report = build_report(
            Path("outputs/freefield_aperture_calibration/d60_dx0p75_resume_20260713/run"),
            Path("outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pointwave_20260714/run"),
        )
        self.assertEqual(report["status"], "r78p330_dx0p75_confirmation_pass")
        self.assertTrue(report["passed"])
        self.assertTrue(report["dx0p5_confirmation_authorized"])
        self.assertFalse(report["ct_pressure_authorized"])
        self.assertLess(report["corrected_r78p330"]["refined_focus_error_percent"], 4.0)


if __name__ == "__main__":
    unittest.main()
