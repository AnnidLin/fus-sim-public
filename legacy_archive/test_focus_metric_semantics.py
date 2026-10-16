from __future__ import annotations

import unittest

import numpy as np

from simulate_kwave_3d_focus import compute_focus_metrics


class FocusMetricSemanticsTest(unittest.TestCase):
    def test_preserves_legacy_and_adds_beam_axis_metrics(self) -> None:
        pressure = np.zeros((12, 9, 5), dtype=np.float32)
        source_mask = np.zeros_like(pressure, dtype=bool)
        source_mask[1:4, 3:6, 2] = True
        source_center = np.array([1, 5, 2], dtype=np.int32)
        target = np.array([10, 2, 2], dtype=np.int32)
        pressure[5, 4, 2] = 9.0
        pressure[8, 3, 2] = 7.0
        pressure[10, 2, 2] = 5.0

        metrics = compute_focus_metrics(
            pressure,
            source_mask,
            target,
            dx_m=1e-3,
            nearfield_exclusion_m=4e-3,
            source_center_index_ijk=source_center,
            entry_index_ijk=np.array([4, 4, 2], dtype=np.int32),
        )

        self.assertEqual(metrics["effective_peak_index_ijk"], [8, 3, 2])
        self.assertEqual(metrics["beam_axis_effective_peak_index_ijk"], [5, 4, 2])
        self.assertEqual(metrics["metric_semantics_version"], "2.0.0")
        self.assertEqual(metrics["legacy_effective_peak_semantics"], "global_x_cut_after_source_mask_front")
        self.assertAlmostEqual(metrics["beam_axis_effective_peak_axial_from_source_mm"], 4.1109609, places=5)
        self.assertGreater(metrics["beam_axis_effective_peak_lateral_offset_mm"], 0.0)
        self.assertEqual(metrics["post_entry_peak_index_ijk"], [5, 4, 2])
        self.assertEqual(metrics["post_entry_semantics"], "axial_projection_at_or_beyond_entry_index")

    def test_omits_beam_axis_metrics_without_source_center(self) -> None:
        pressure = np.zeros((5, 5, 5), dtype=np.float32)
        pressure[4, 2, 2] = 1.0
        source_mask = np.zeros_like(pressure, dtype=bool)
        source_mask[0, 2, 2] = True
        metrics = compute_focus_metrics(pressure, source_mask, np.array([4, 2, 2]), 1e-3, 1e-3)
        self.assertEqual(metrics["metric_semantics_version"], "1.0.0_legacy_only")
        self.assertNotIn("beam_axis_effective_peak_index_ijk", metrics)


if __name__ == "__main__":
    unittest.main()
