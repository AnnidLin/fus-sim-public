from __future__ import annotations

import json
import unittest

from generate_h115_paper_bundle_manifest import EXPECTED, build
from validate_h115_submission_preflight import build as build_preflight
from validate_h115_reconstruction import canonical
from validate_h115_manuscript_consistency import ROOT, validate


class H115PaperTraceabilityTests(unittest.TestCase):
    def test_paper_bundle_has_all_fixed_scope_files(self) -> None:
        report = build()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["file_count"], len(EXPECTED))
        self.assertEqual(report["missing"], [])

    def test_manuscript_and_decision_brief_match_audited_values(self) -> None:
        report = validate(
            [
                ROOT / "paper/PUB2_MANUSCRIPT_DRAFT_V0_1_20260812.md",
                ROOT / "paper/PUB2_METHODS_RESULTS_EVIDENCE_20260812.md",
                ROOT / "paper/UCL_H115_PAPER_READINESS_20260823.md",
            ]
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["failed_checks"], [])

    def test_reconstruction_report_has_three_strict_matches(self) -> None:
        report = json.loads(
            (ROOT / "outputs/ucl_h115_recheck_20260826/reproducibility_recheck.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(len(report["checks"]), 3)
        self.assertTrue(all(item["exact_after_dropping_generated_at_utc"] for item in report["checks"]))
        self.assertEqual(len(report["derived_checks"]), 10)
        self.assertTrue(all(item["passed"] for item in report["derived_checks"]))

    def test_reconstruction_canonicalization_removes_only_timestamp(self) -> None:
        left = {"generated_at_utc": "a", "nested": [{"generated_at_utc": "b", "value": 1}]}
        right = {"generated_at_utc": "c", "nested": [{"generated_at_utc": "d", "value": 1}]}
        self.assertEqual(canonical(left), canonical(right))
        right["nested"][0]["value"] = 2
        self.assertNotEqual(canonical(left), canonical(right))

    def test_reviewer_risk_register_preserves_claim_boundaries(self) -> None:
        text = (ROOT / "paper/H115_REVIEWER_RISK_REGISTER_20260826.md").read_text(encoding="utf-8")
        self.assertEqual(sum(line.startswith(("| High |", "| Medium |", "| Low |")) for line in text.splitlines()), 10)
        lower = text.lower()
        for phrase in (
            "nonpassing external comparison",
            "formal convergence",
            "post-hoc coordinate correction",
            "not Case079 anatomy",
            "independent per-ring acoustic amplitude/phase",
        ):
            self.assertIn(phrase.lower(), lower)

    def test_submission_preflight_separates_technical_pass_from_author_blockers(self) -> None:
        report = build_preflight()
        self.assertEqual(report["technical_failed_count"], 0)
        self.assertEqual(report["status"], "technical_package_passed_author_inputs_pending")
        self.assertFalse(report["submission_ready"])
        self.assertEqual(len(report["author_blockers"]), 3)

    def test_chinese_deliverables_index_matches_current_state(self) -> None:
        text = (ROOT / "paper/H115_DELIVERABLES_INDEX_ZH_20260826.md").read_text(encoding="utf-8")
        for phrase in ("6/8", "0/8", "23/23", "364/364", "3/3", "10/10", "submission_ready=false"):
            self.assertIn(phrase, text)
        for boundary in ("不能宣称成功实验验证", "不能解释失配", "不授权更多求解器"):
            self.assertIn(boundary, text)


if __name__ == "__main__":
    unittest.main()
