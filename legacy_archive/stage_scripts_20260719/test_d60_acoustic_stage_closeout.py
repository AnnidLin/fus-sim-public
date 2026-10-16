import unittest
from pathlib import Path

from generate_d60_acoustic_stage_closeout import build_closeout


class D60AcousticStageCloseoutTests(unittest.TestCase):
    def test_claim_boundary_matches_retained_evidence(self) -> None:
        result = build_closeout(
            Path("outputs/freefield_aperture_calibration/d60_dx0p75_resume_20260713/run"),
            Path("outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pointwave_20260714/run"),
            Path("outputs/freefield_aperture_calibration/d60_r78p330_dx0p5_pointwave_20260714/run/interruption_record.json"),
        )
        self.assertEqual(result["status"], "dx0p75_source_calibration_closed_dx0p5_incomplete")
        self.assertTrue(all(result["acceptance"].values()))
        self.assertFalse(result["dx0p5"]["core_output_available"])
        self.assertFalse(result["dx0p5"]["supports_convergence_conclusion"])
        self.assertIn("paper-grade numerical convergence", result["claims"]["not_supported"])


if __name__ == "__main__":
    unittest.main()
