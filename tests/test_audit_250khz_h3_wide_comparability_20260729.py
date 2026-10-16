from __future__ import annotations

import unittest

from audit_250khz_h3_wide_comparability_20260729 import build_audit


class H3WideComparabilityAuditTests(unittest.TestCase):
    def test_h3_default_comparison_is_not_single_variable(self) -> None:
        audit = build_audit()
        baseline = audit["comparisons"]["h3_vs_default_baseline"]
        self.assertFalse(baseline["single_variable_comparison"])
        self.assertIn("tone_burst_cycles", baseline["confounded_config_fields"])
        self.assertIn("pml_size", baseline["confounded_config_fields"])

    def test_nlm_wide_comparison_is_not_domain_only(self) -> None:
        audit = build_audit()
        wide = audit["comparisons"]["nlm_wide_vs_quick_tr"]
        self.assertFalse(wide["single_variable_comparison"])
        self.assertIn("tone_burst_cycles", wide["confounded_config_fields"])
        self.assertIn(
            "allow_entry_plan_resolution_mismatch",
            wide["confounded_config_fields"],
        )
        self.assertFalse(wide["source_background_only"])

    def test_claims_are_downgraded_but_observations_preserved(self) -> None:
        audit = build_audit()
        self.assertEqual(audit["decision"]["status"], "comparability_blocked")
        self.assertTrue(audit["decision"]["raw_outputs_complete"])
        self.assertFalse(audit["decision"]["geometry_causal_claim_supported"])
        self.assertFalse(audit["decision"]["wide_domain_only_claim_supported"])


if __name__ == "__main__":
    unittest.main()
