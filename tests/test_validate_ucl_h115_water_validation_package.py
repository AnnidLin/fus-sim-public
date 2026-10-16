from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

import numpy as np

from validate_ucl_h115_water_validation_package import validate


class PackageValidatorTests(unittest.TestCase):
    def test_accepts_a_guarded_nonpassing_observation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "execution_status.json").write_text(json.dumps({"status": "completed", "result": {"stopped_reason": None}}))
            (root / "stage_result.json").write_text(json.dumps({"status": "completed", "return_code": 0}))
            (root / "summary.json").write_text("{}")
            (root / "focus_metrics.json").write_text("{}")
            (root / "comparison.json").write_text(json.dumps({"status": "observation_with_failed_preregistered_checks", "checks": {"axial_peak_position": False, "transverse_normalized_l2": False, "transverse_y_width": False}}))
            (root / "device_history.jsonl").write_text(json.dumps({"equivalent_cores": 6.4, "working_set_gib": 2.0, "system_free_memory_gib": 10.0}) + "\n")
            np.savez(root / "pressure_max_mpa.npz", pressure_max_mpa=np.array([1.0]))
            result = validate(root)
            self.assertEqual(result["status"], "passed_with_nonpassing_validation_observation")

    def test_grid_sensitivity_is_required_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "execution_status.json").write_text(json.dumps({"status": "completed", "result": {"stopped_reason": None}}))
            (root / "stage_result.json").write_text(json.dumps({"status": "completed", "return_code": 0}))
            (root / "summary.json").write_text("{}")
            (root / "focus_metrics.json").write_text("{}")
            (root / "comparison.json").write_text(json.dumps({"status": "observation_with_failed_preregistered_checks", "checks": {"axial_peak_position": False, "transverse_normalized_l2": False, "transverse_y_width": False}}))
            (root / "device_history.jsonl").write_text(json.dumps({"equivalent_cores": 6.0, "working_set_gib": 2.0, "system_free_memory_gib": 10.0}) + "\n")
            np.savez(root / "pressure_max_mpa.npz", pressure_max_mpa=np.array([1.0]))
            self.assertEqual(validate(root, require_grid_sensitivity=True)["status"], "failed")

    def test_completed_grid_check_is_json_serializable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "execution_status.json").write_text(json.dumps({"status": "completed", "result": {"stopped_reason": None}}))
            (root / "stage_result.json").write_text(json.dumps({"status": "completed", "return_code": 0}))
            (root / "summary.json").write_text("{}")
            (root / "focus_metrics.json").write_text("{}")
            (root / "comparison.json").write_text(json.dumps({"status": "observation_with_failed_preregistered_checks", "checks": {"axial_peak_position": False, "transverse_normalized_l2": False, "transverse_y_width": False}}))
            (root / "grid_sensitivity.json").write_text(json.dumps({"status": "completed_grid_sensitivity_observation", "nearfield_excluded_metrics": {"common_voxels": 10, "scaled_relative_l2_percent": 1.0}}))
            (root / "device_history.jsonl").write_text(json.dumps({"equivalent_cores": 6.0, "working_set_gib": 2.0, "system_free_memory_gib": 10.0}) + "\n")
            np.savez(root / "pressure_max_mpa.npz", pressure_max_mpa=np.array([1.0]))
            json.dumps(validate(root, require_grid_sensitivity=True))


if __name__ == "__main__":
    unittest.main()
