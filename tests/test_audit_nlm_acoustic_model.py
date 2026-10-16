from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from audit_nlm_acoustic_model import audit


class AuditNlmAcousticModelTests(unittest.TestCase):
    def test_float32_spacing_passes_but_world_mapping_remains_blocked(self) -> None:
        with TemporaryDirectory(dir=".") as directory:
            root = Path(directory)
            model, summary = root / "model.npz", root / "summary.json"
            labels = np.asarray([[[0, 1, 2]]], dtype=np.uint8)
            fields = np.ones(labels.shape, dtype=np.float32)
            np.savez_compressed(model, labels=labels, hu=fields, sound_speed=fields, density=fields,
                                alpha_coeff=fields, dx_m=np.asarray(0.00075, dtype=np.float32))
            summary.write_text(json.dumps({"grid_shape": [1, 1, 3], "mapping_profile": {
                "profile_id": "simple_hu300", "review_status": "baseline_compatible"}}), encoding="utf-8")
            result = audit(model.resolve(), summary.resolve())
            self.assertTrue(result["checks"]["dx_is_0p75_mm"])
            self.assertTrue(result["acoustic_model_candidate_ready"])
            self.assertEqual(result["world_mapping"]["status"], "unavailable")
            self.assertFalse(result["registered_anatomical_roi_ready"])


if __name__ == "__main__":
    unittest.main()
