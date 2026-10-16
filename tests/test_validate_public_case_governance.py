from __future__ import annotations

import unittest

from validate_public_case_governance import evaluate


class PublicCaseGovernanceTests(unittest.TestCase):
    def test_current_public_case_governance_is_closed(self) -> None:
        result = evaluate()
        self.assertTrue(result["governance_valid"])
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(
            result["claim_boundary"],
            "mixed_medium_public_postmortem_quick_screening_input_only",
        )


if __name__ == "__main__":
    unittest.main()
