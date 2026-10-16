from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from bbb_cohort_readiness import (
    DEFAULT_MANIFEST,
    CohortReadinessError,
    audit_cohort,
    validate_manifest,
    write_outputs,
)
from bbb_planning_contract import DEFAULT_SCHEMA, load_json


class BBBCohortReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(DEFAULT_SCHEMA)
        cls.manifest = load_json(DEFAULT_MANIFEST)

    def changed(self) -> dict:
        return copy.deepcopy(self.manifest)

    def test_case079_passes_prototype_but_not_registered_cohort_gate(self) -> None:
        result = audit_cohort(self.changed(), self.schema, verify_file_hashes=True)
        self.assertEqual(result["status"], "cohort_onboarding_incomplete")
        self.assertEqual(result["prototype_ready_count"], 1)
        self.assertEqual(result["registered_anatomy_ready_count"], 0)
        self.assertFalse(result["multi_case_registered_analysis_ready"])
        self.assertIn("registered_anatomy_and_world_mapping_unavailable", result["blocker_counts"])
        self.assertFalse(result["pressure_executed"])
        self.assertFalse(result["clinical_safety_claim"])

    def test_duplicate_case_id_is_rejected(self) -> None:
        manifest = self.changed()
        manifest["cases"].append(copy.deepcopy(manifest["cases"][0]))
        with self.assertRaisesRegex(CohortReadinessError, "duplicate case_id"):
            validate_manifest(manifest)

    def test_case_id_mismatch_is_rejected(self) -> None:
        manifest = self.changed()
        manifest["cases"][0]["case_id"] = "different"
        with self.assertRaisesRegex(CohortReadinessError, "case_id mismatch"):
            audit_cohort(manifest, self.schema)

    def test_path_escape_is_rejected(self) -> None:
        manifest = self.changed()
        manifest["cases"][0]["plan_path"] = "../outside.json"
        with self.assertRaisesRegex(CohortReadinessError, "escapes project root"):
            audit_cohort(manifest, self.schema)

    def test_outputs_are_deterministic_and_complete(self) -> None:
        result = audit_cohort(self.changed(), self.schema)
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            write_outputs(result, output_dir)
            first = (output_dir / "cohort_readiness.json").read_bytes()
            write_outputs(result, output_dir)
            self.assertEqual(first, (output_dir / "cohort_readiness.json").read_bytes())
            self.assertTrue((output_dir / "case_readiness.csv").is_file())
            self.assertTrue((output_dir / "cohort_readiness.md").is_file())


if __name__ == "__main__":
    unittest.main()
