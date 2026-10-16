import unittest

from audit_a4b_preset_equivalence_20260719 import QUICK, STANDARD, compare, load


class A4bPresetEquivalenceTests(unittest.TestCase):
    def test_canonical_quick_and_standard_labels_are_numerically_identical(self) -> None:
        report = compare(load(QUICK), load(STANDARD))
        self.assertTrue(report["numerically_equivalent"])
        self.assertEqual(report["status"], "evidence_redundant_do_not_run")
        self.assertFalse(report["pressure_execution_authorized_by_equivalence_gate"])
        self.assertEqual(report["differences"], [])


if __name__ == "__main__":
    unittest.main()
