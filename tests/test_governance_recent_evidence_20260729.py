from __future__ import annotations

import unittest
from pathlib import Path

from governance_recent_evidence import (
    ITRUSST_RUN_SPECS,
    RECENT_ARTIFACT_SPECS,
    RECENT_RUN_SPECS,
)


ROOT = Path(__file__).resolve().parents[1]


class RecentGovernanceEvidenceTests(unittest.TestCase):
    def test_run_specs_are_unique(self) -> None:
        self.assertEqual(len({item["run_id"] for item in RECENT_RUN_SPECS}), len(RECENT_RUN_SPECS))
        self.assertEqual(len({item["output_dir"] for item in RECENT_RUN_SPECS}), len(RECENT_RUN_SPECS))

    def test_registered_runs_have_complete_core_outputs(self) -> None:
        self.assertEqual(len(RECENT_RUN_SPECS), 21)
        for item in RECENT_RUN_SPECS:
            directory = ROOT / item["output_dir"]
            with self.subTest(run_id=item["run_id"]):
                self.assertTrue((directory / "summary.json").is_file())
                self.assertTrue((directory / "focus_metrics.json").is_file())
                self.assertTrue((directory / "pressure_max_mpa.npz").is_file())

    def test_h115_water_runs_are_registered(self) -> None:
        run_ids = {item["run_id"] for item in RECENT_RUN_SPECS}
        self.assertTrue(
            {
                "ucl_h115_270khz_water_dx0p50_2026-08-18",
                "ucl_h115_270khz_water_dx0p30_2026-08-23",
                "ucl_h115_270khz_water_nominal64_dx0p50_2026-08-25",
            }.issubset(run_ids)
        )

    def test_registered_artifacts_exist_and_are_unique(self) -> None:
        self.assertEqual(len({item["artifact_id"] for item in RECENT_ARTIFACT_SPECS}), len(RECENT_ARTIFACT_SPECS))
        artifact_ids = {item["artifact_id"] for item in RECENT_ARTIFACT_SPECS}
        self.assertIn("brief.freq250_h3_large_matched_tr_20260730", artifact_ids)
        self.assertIn("report.freq250_h3_large_matched_tr_20260730", artifact_ids)
        self.assertIn("feedback.freq250_h3_large_matched_tr_20260730", artifact_ids)
        self.assertIn(
            "brief.freq250_h3_large_full_bowl_intermediate_20260730",
            artifact_ids,
        )
        self.assertIn(
            "report.freq250_h3_large_full_bowl_intermediate_20260730",
            artifact_ids,
        )
        self.assertIn(
            "feedback.freq250_h3_large_full_bowl_intermediate_20260730",
            artifact_ids,
        )
        for item in RECENT_ARTIFACT_SPECS:
            with self.subTest(artifact_id=item["artifact_id"]):
                self.assertTrue((ROOT / item["path"]).is_file())

    def test_itrusst_runs_have_harmonic_core_outputs(self) -> None:
        self.assertEqual(len(ITRUSST_RUN_SPECS), 3)
        self.assertEqual(
            len({item["run_id"] for item in ITRUSST_RUN_SPECS}),
            len(ITRUSST_RUN_SPECS),
        )
        for item in ITRUSST_RUN_SPECS:
            directory = ROOT / item["output_dir"]
            with self.subTest(run_id=item["run_id"]):
                self.assertTrue((directory / "summary.json").is_file())
                self.assertTrue((directory / "p_amp.npz").is_file())
                self.assertTrue((directory / "comparison.json").is_file())
                self.assertTrue((directory / "monitor_status.json").is_file())

    def test_pub1_bm4_and_phase_a_artifacts_are_registered(self) -> None:
        artifact_ids = {item["artifact_id"] for item in RECENT_ARTIFACT_SPECS}
        self.assertIn("report.pub1_itrusst_bm4_20260807", artifact_ids)
        self.assertIn("report.pub1_itrusst_phase_a_summary_20260807", artifact_ids)
        self.assertIn("figure.pub1_itrusst_phase_a_fields_20260807", artifact_ids)

    def test_pub2_pre_execution_artifacts_are_registered(self) -> None:
        artifact_ids = {item["artifact_id"] for item in RECENT_ARTIFACT_SPECS}
        self.assertTrue(
            {
                "brief.pub2_250khz_ct_sensitivity_20260807",
                "audit.pub2_250khz_reuse_20260807",
                "audit.pub2_dx0p75_model_equivalence_20260807",
                "report.pub2_entry_plan_resolution_family_20260807",
                "report.pub2_250khz_dry_run_matrix_20260807",
            }.issubset(artifact_ids)
        )

    def test_pub2_reference_completion_artifacts_are_registered(self) -> None:
        artifact_ids = {item["artifact_id"] for item in RECENT_ARTIFACT_SPECS}
        self.assertTrue(
            {
                "execution.pub2_reference_pair_20260810",
                "report.pub2_reference_analysis_20260810",
                "feedback.pub2_reference_20260810",
                "validation.pub2_reference_package_20260810",
            }.issubset(artifact_ids)
        )

    def test_pub2_pml16_baseline_artifacts_are_registered(self) -> None:
        run_ids = {item["run_id"] for item in RECENT_RUN_SPECS}
        artifact_ids = {item["artifact_id"] for item in RECENT_ARTIFACT_SPECS}
        self.assertIn("case079_pub2_250khz_pml16_baseline_2026-08-10", run_ids)
        self.assertTrue(
            {
                "execution.pub2_pml16_baseline_20260810",
                "report.pub2_pml16_baseline_20260810",
                "feedback.pub2_pml16_baseline_20260810",
                "validation.pub2_pml16_baseline_20260810",
            }.issubset(artifact_ids)
        )


if __name__ == "__main__":
    unittest.main()
