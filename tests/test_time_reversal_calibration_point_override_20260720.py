from types import SimpleNamespace
import unittest

import numpy as np

from simulate_time_reversal_focus import TimeReversalConfig, calibration_point_metadata, run


def model_fixture():
    labels = np.zeros((125, 60, 50), dtype=np.uint8)
    labels[38, 39, 34] = 2
    return SimpleNamespace(
        sound_speed=np.zeros(labels.shape, dtype=np.float32),
        labels=labels,
        target_index_ijk=np.array([114, 36, 26]),
        crop_origin_ijk=np.array([37, 100, 79]),
    )


class CalibrationPointOverrideTests(unittest.TestCase):
    def test_default_calibration_point_is_model_target(self):
        local, metadata = calibration_point_metadata(model_fixture(), TimeReversalConfig())
        self.assertEqual(local.tolist(), [114, 36, 26])
        self.assertEqual(metadata["full_index_ijk"], [151, 136, 105])
        self.assertEqual(metadata["mode"], "model_target")
        self.assertTrue(metadata["independent_of_bowl_geometry"])

    def test_full_index_override_maps_to_hotspot_without_changing_bowl_target(self):
        config = TimeReversalConfig(calibration_point_override=(75, 139, 113))
        local, metadata = calibration_point_metadata(model_fixture(), config)
        self.assertEqual(local.tolist(), [38, 39, 34])
        self.assertEqual(metadata["material_label"], 2)
        self.assertEqual(metadata["bowl_geometry_target_local_ijk"], [114, 36, 26])
        self.assertEqual(metadata["mode"], "full_index_override_bowl_geometry_frozen")

    def test_override_is_rejected_for_refocus_before_execution(self):
        config = TimeReversalConfig(
            calibration_point_override=(75, 139, 113),
            stage="refocus",
        )
        with self.assertRaisesRegex(ValueError, "restricted to stage=calibrate"):
            run(config, None)
    def test_override_outside_quick_crop_is_rejected(self):
        config = TimeReversalConfig(calibration_point_override=(0, 0, 0))
        with self.assertRaisesRegex(ValueError, "outside cropped grid"):
            calibration_point_metadata(model_fixture(), config)


if __name__ == "__main__":
    unittest.main()