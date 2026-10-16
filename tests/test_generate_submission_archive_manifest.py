import json
import unittest
from pathlib import Path

from generate_submission_archive_manifest import build_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = PROJECT_ROOT / "tests" / "fixtures" / "submission_archive_manifest"


class SubmissionArchiveManifestTests(unittest.TestCase):
    def test_manifest_is_sorted_and_blocks_unresolved_release(self) -> None:
        spec = {
            "trace_id": "TRACE-TEST",
            "base_manifest": "base_clean.json",
            "extra_files": ["code.py"],
            "prohibited_inclusions": ["data/raw_ct"],
            "project_license_status": "missing_author_decision",
            "source_revision_status": "working_tree",
            "release_version": "0.1.0-draft",
            "archive_doi": None,
            "excluded": [],
            "external_dependencies": [],
            "claim_boundary": "test",
        }
        manifest = build_manifest(FIXTURE_ROOT, spec)
        self.assertEqual([item["path"] for item in manifest["files"]], ["code.py", "paper/result.md"])
        self.assertFalse(manifest["archive_ready"])
        self.assertIn("project_license_unresolved", manifest["blockers"])
        self.assertIn("archive_doi_not_minted", manifest["blockers"])
        self.assertEqual(manifest["prohibited_matches"], [])

    def test_prohibited_raw_data_is_detected(self) -> None:
        spec = {
            "trace_id": "TRACE-TEST",
            "base_manifest": "base_restricted.json",
            "extra_files": [],
            "prohibited_inclusions": ["data/raw_ct"],
            "project_license_status": "resolved",
            "source_revision_status": "frozen",
            "release_version": "1.0.0",
            "archive_doi": "10.example/test",
            "excluded": [],
            "external_dependencies": [],
            "claim_boundary": "test",
        }
        manifest = build_manifest(FIXTURE_ROOT, spec)
        self.assertFalse(manifest["archive_ready"])
        self.assertEqual(manifest["prohibited_matches"], ["data/raw_ct/079.nii"])


if __name__ == "__main__":
    unittest.main()
