import json, unittest
from pathlib import Path
import analyze_pub2_cfl0p1_baseline_20260812 as analysis

ROOT=Path(__file__).resolve().parents[1]
class Pub2CflAndUclIntakeTests(unittest.TestCase):
    def test_saved_cfl_analysis_passes_all_frozen_checks(self):
        report=analysis.build()
        self.assertEqual(report["status"],"passed")
        self.assertTrue(all(report["checks"].values()))
        self.assertFalse(report["decision"]["formal_convergence_established"])
        self.assertFalse(report["decision"]["tr_time_step_sensitivity_established"])
    def test_ucl_intake_integrity_and_claim_boundary(self):
        m=json.loads((ROOT/"outputs/ucl_270khz_freefield_intake_20260812/intake_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(m["integrity_status"],"passed")
        self.assertEqual(m["license"],"CC BY 4.0")
        self.assertEqual(m["schema_counts"],{"groups":29,"datasets":157})
        self.assertIn("no source calibration",m["claim_boundary"])
if __name__=="__main__": unittest.main()
