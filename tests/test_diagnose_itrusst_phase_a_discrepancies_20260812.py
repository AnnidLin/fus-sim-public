import unittest
import json
from pathlib import Path

import numpy as np

from diagnose_itrusst_phase_a_discrepancies import (
    _fit_scale,
    _relative_l2,
    _shift_without_wrap,
)


class DiscrepancyDiagnosticTests(unittest.TestCase):
    def test_shift_without_wrap_does_not_reintroduce_wrapped_values(self):
        field = np.arange(9, dtype=float).reshape(3, 3)
        shifted = _shift_without_wrap(field, (0, 1))
        self.assertTrue(np.all(np.isnan(shifted[:, 0])))
        np.testing.assert_array_equal(shifted[:, 1:], field[:, :-1])

    def test_scale_fit_recovers_known_global_gain(self):
        reference = np.array([[1.0, 2.0], [3.0, 4.0]])
        candidate = reference * 1.25
        mask = np.ones(reference.shape, dtype=bool)
        scale = _fit_scale(reference, candidate, mask)
        self.assertTrue(np.isclose(scale, 0.8))
        self.assertLess(_relative_l2(reference, scale * candidate, mask), 1e-12)

    def test_frozen_contract_keeps_missing_numerical_gates_blocked(self):
        root = Path(__file__).resolve().parents[1]
        contract = json.loads(
            (root / "paper/PUB2_VERIFICATION_CONTRACT_20260812.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["status"], "prospective_project_contract")
        self.assertEqual(
            contract["claim_gates"]["paper_grade_numerical_verification"]["status"],
            "blocked",
        )
        self.assertEqual(
            contract["claim_gates"]["clinical_or_safety_claim"]["status"],
            "prohibited",
        )

    def test_saved_diagnostic_preserves_formal_metric_guardrail(self):
        root = Path(__file__).resolve().parents[1]
        report = json.loads(
            (
                root
                / "outputs/itrusst_phase_a_diagnostic_20260812/discrepancy_decomposition.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(report["claim_level"], "engineering_posthoc_diagnostic")
        self.assertEqual([case["benchmark"] for case in report["cases"]], ["BM1", "BM3", "BM4"])
        for case in report["cases"]:
            self.assertIn("must not replace", case["interpretation_guardrail"])


if __name__ == "__main__":
    unittest.main()
