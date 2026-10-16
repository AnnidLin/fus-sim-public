from __future__ import annotations

import unittest

from audit_nlm_public_case_readiness import evaluate


class AuditNlmPublicCaseReadinessTests(unittest.TestCase):
    def test_engineering_sandbox_does_not_require_expert_or_anatomical_roi(self) -> None:
        artifacts = {
            "intake": {
                "checks": {"ct_geometry_valid": True, "t2_geometry_valid": True},
                "subject_semantics": "postmortem",
            },
            "registration": {
                "quantitative_checks": {"quantitative_gate_pass": True},
                "codex_visual_review": "pass",
                "expert_human_visual_qc_pass": False,
            },
            "native_t2": {"checks": {"shape_matches_ct": True, "affine_matches_ct": True}},
            "affine_model": {"world_mapping": {"status": "available"}, "checks": {"a": True}},
            "proxy": {
                "proxy_coordinate_transfer_ready": True,
                "center_inside_mask": True,
                "registered_anatomical_roi_ready": False,
            },
            "entry": {
                "target_label": 1,
                "has_skull_crossing": True,
                "entry_label": 2,
                "source_center_label": 0,
            },
        }
        result = evaluate(artifacts)
        self.assertTrue(result["automated_public_data_pipeline_ready"])
        self.assertTrue(result["engineering_sandbox_input_ready"])
        self.assertFalse(result["expert_required_for_engineering_sandbox"])
        self.assertFalse(result["expert_human_registration_qc_ready"])
        self.assertFalse(result["registered_anatomical_roi_ready"])
        self.assertFalse(result["simulation_execution_ready"])
        self.assertNotIn("expert_human_registration_qc_missing", result["blockers"])
        self.assertIn(
            "expert_human_registration_qc_missing",
            result["gate_tracks"]["registered_anatomical_or_clinical"]["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
