import unittest
from pathlib import Path

from generate_d60_gate_b_focus_bias_audit import build_audit, load_json


class D60GateBFocusBiasAuditTest(unittest.TestCase):
    def test_canonical_geometry_and_memory_diagnosis(self) -> None:
        coarse = load_json(Path("outputs/freefield_aperture_calibration/d60_dx0p75_resume_20260713/run/summary.json"))
        fine = load_json(Path("outputs/freefield_aperture_calibration/d60_dx0p5_fieldonly_20260713/run/summary.json"))
        comparison = load_json(Path("outputs/freefield_aperture_calibration/d60_grid_convergence_20260713/d60_grid_convergence_report.json"))
        audit = build_audit(coarse, fine, comparison)

        self.assertEqual(audit["status"], "diagnosis_complete_no_pressure_run")
        self.assertEqual(audit["hypotheses"]["sphere_center_quantization"]["finding"], "excluded_as_primary_cause")
        self.assertAlmostEqual(audit["coarse_dx0p75"]["sphere_center_to_target_error_mm"], 0.0)
        self.assertAlmostEqual(audit["fine_dx0p5"]["sphere_center_to_target_error_mm"], 0.0)
        self.assertGreater(audit["sensor_memory"]["full_domain_float64_history_gib"], 100.0)
        self.assertFalse(audit["decision"]["ct_pressure_authorized"])
        self.assertGreater(audit["decision"]["single_corrected_radius_candidate_mm"], 78.0)
        self.assertLess(audit["decision"]["single_corrected_radius_candidate_mm"], 79.0)


if __name__ == "__main__":
    unittest.main()
