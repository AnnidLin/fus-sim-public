from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from bbb_roi import ROIError, load_roi_mask, pressure_coverage_metrics, sphere_mask, summarize_roi


class BBBROITests(unittest.TestCase):
    def test_case079_sphere_uses_actual_spacing(self) -> None:
        spacing = (0.000750000006519258,) * 3
        mask = sphere_mask((267, 267, 267), (151, 136, 105), spacing, 0.003)
        summary = summarize_roi(mask, spacing)
        self.assertEqual(summary["voxel_count"], 251)
        self.assertEqual(summary["centroid_ijk"], [151.0, 136.0, 105.0])

    def test_sphere_rejects_out_of_bounds_center(self) -> None:
        with self.assertRaisesRegex(ROIError, "outside"):
            sphere_mask((5, 5, 5), (5, 2, 2), (1.0, 1.0, 1.0), 1.0)

    def test_binary_validator_rejects_empty_and_nonbinary(self) -> None:
        with self.assertRaisesRegex(ROIError, "empty"):
            summarize_roi(np.zeros((3, 3, 3)), (1.0, 1.0, 1.0))
        bad = np.zeros((3, 3, 3))
        bad[1, 1, 1] = 2
        with self.assertRaisesRegex(ROIError, "binary"):
            summarize_roi(bad, (1.0, 1.0, 1.0))

    def test_npz_loading_and_shape_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "roi.npz"
            mask = np.zeros((3, 4, 5), dtype=np.uint8)
            mask[1, 2, 3] = 1
            np.savez_compressed(path, roi_mask=mask)
            loaded = load_roi_mask(path, (3, 4, 5))
            self.assertEqual(int(loaded.mask.sum()), 1)
            with self.assertRaisesRegex(ROIError, "shape mismatch"):
                load_roi_mask(path, (3, 4, 6))

    def test_nifti_requires_authoritative_affine(self) -> None:
        with self.assertRaisesRegex(ROIError, "authoritative expected affine"):
            load_roi_mask(Path("unread.nii.gz"), (3, 3, 3), None)

    def test_pressure_metrics_match_hand_computable_values(self) -> None:
        pressure = np.arange(27, dtype=float).reshape(3, 3, 3)
        roi = np.zeros_like(pressure, dtype=bool)
        roi[1, 1, 1] = True
        roi[1, 1, 2] = True
        labels = np.ones_like(pressure, dtype=np.uint8)
        labels[0, 0, 0] = 2
        result = pressure_coverage_metrics(pressure, roi, threshold_pa=14.0, labels=labels)
        self.assertEqual(result["roi_peak_pressure_pa"], 14.0)
        self.assertEqual(result["roi_mean_pressure_pa"], 13.5)
        self.assertEqual(result["roi_coverage_fraction"], 0.5)
        self.assertEqual(result["global_peak_pressure_pa"], 26.0)
        self.assertEqual(result["global_peak_ijk"], [2, 2, 2])
        self.assertEqual(result["skull_peak_pressure_pa"], 0.0)
        self.assertEqual(result["non_target_brain_peak_pressure_pa"], 26.0)


if __name__ == "__main__":
    unittest.main()
