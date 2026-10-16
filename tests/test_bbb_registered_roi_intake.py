from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from bbb_planning_contract import DEFAULT_EXAMPLE, DEFAULT_SCHEMA, load_json
from bbb_registered_roi_intake import RegisteredROIIntakeError, audit_registered_roi, write_report


class BBBRegisteredROIIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(DEFAULT_SCHEMA)
        cls.example = load_json(DEFAULT_EXAMPLE)

    def registered_fixture(self, root: Path) -> tuple[dict, dict]:
        plan = copy.deepcopy(self.example)
        patient = plan["patient_model"]
        patient["shape_ijk"] = [8, 8, 8]
        patient["spacing_m_ijk"] = [0.001, 0.001, 0.001]
        patient["crop_origin_ijk"] = [1, 1, 1]
        affine = np.diag([1.0, 1.0, 1.0, 1.0])
        patient["world_mapping"] = {
            "status": "available",
            "reason": "test fixture patient grid",
            "affine_ijk_to_world_mm": affine.tolist(),
        }
        roi = plan["target_roi"]
        roi.update({
            "roi_id": "registered_test_roi",
            "roi_kind": "binary_mask",
            "anatomical_status": "registered_anatomical",
            "center_full_ijk": [3, 3, 3],
            "center_local_ijk": [2, 2, 2],
            "voxel_count": 2,
            "generation": {"method": "loaded_mask", "radius_m": None, "mask_path": "roi_mask.npz"},
        })
        transducer = plan["transducer_plan"]
        transducer["target_full_ijk"] = [3, 3, 3]
        transducer["source_center_full_ijk"] = [1, 1, 1]
        transducer["entry_full_ijk"] = [2, 2, 2]

        mask = np.zeros((8, 8, 8), dtype=np.uint8)
        mask[3, 3, 3] = 1
        mask[3, 3, 4] = 1
        mask_path = root / "roi_mask.npz"
        np.savez_compressed(mask_path, roi_mask=mask)
        digest = hashlib.sha256(mask_path.read_bytes()).hexdigest()
        sidecar = {
            "registration_version": "1.0.0",
            "case_id": "079",
            "roi_id": "registered_test_roi",
            "roi_mask_path": "roi_mask.npz",
            "roi_mask_sha256": digest,
            "mask_affine_ijk_to_world_mm": affine.tolist(),
            "registration_method": "native_patient_grid",
            "interpolation": "nearest_neighbor",
            "source_image_id": "test_mri",
            "transform": {"status": "identity", "path": None, "sha256": None},
        }
        return plan, sidecar

    def test_case079_synthetic_contract_remains_blocked(self) -> None:
        result = audit_registered_roi(copy.deepcopy(self.example), self.schema)
        self.assertEqual(result["status"], "registered_roi_intake_blocked")
        self.assertFalse(result["registration_ready"])
        self.assertIn("roi_contract_is_not_registered_anatomy", result["blockers"])
        self.assertIn("authoritative_patient_affine_unavailable", result["blockers"])

    def test_registered_npz_with_sidecar_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, sidecar = self.registered_fixture(root)
            result = audit_registered_roi(plan, self.schema, project_root=root, sidecar=sidecar)
            self.assertEqual(result["status"], "registered_roi_intake_ready")
            self.assertTrue(result["center_inside_mask"])
            self.assertEqual(result["roi_summary"]["voxel_count"], 2)
            self.assertFalse(result["pressure_executed"])

    def test_mask_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, sidecar = self.registered_fixture(root)
            sidecar["roi_mask_sha256"] = "0" * 64
            with self.assertRaisesRegex(RegisteredROIIntakeError, "SHA256 mismatch"):
                audit_registered_roi(plan, self.schema, project_root=root, sidecar=sidecar)

    def test_affine_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, sidecar = self.registered_fixture(root)
            sidecar["mask_affine_ijk_to_world_mm"][0][3] = 2.0
            with self.assertRaisesRegex(RegisteredROIIntakeError, "affine does not match"):
                audit_registered_roi(plan, self.schema, project_root=root, sidecar=sidecar)

    def test_center_outside_mask_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, sidecar = self.registered_fixture(root)
            plan["target_roi"]["center_full_ijk"] = [4, 4, 4]
            plan["target_roi"]["center_local_ijk"] = [3, 3, 3]
            plan["transducer_plan"]["target_full_ijk"] = [4, 4, 4]
            with self.assertRaisesRegex(RegisteredROIIntakeError, "outside the registered mask"):
                audit_registered_roi(plan, self.schema, project_root=root, sidecar=sidecar)

    def test_report_output_is_deterministic(self) -> None:
        result = audit_registered_roi(copy.deepcopy(self.example), self.schema)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            write_report(result, output)
            first = (output / "registered_roi_intake.json").read_bytes()
            write_report(result, output)
            self.assertEqual(first, (output / "registered_roi_intake.json").read_bytes())
            parsed = json.loads(first)
            self.assertFalse(parsed["clinical_safety_claim"])


if __name__ == "__main__":
    unittest.main()
