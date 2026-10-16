"""Regression tests for bounded H115 registration/aperture sensitivity."""
from __future__ import annotations

import unittest

import numpy as np

from analyze_ucl_h115_source_registration import disk_offsets, registration_sweep


class H115SourceRegistrationTests(unittest.TestCase):
    def test_disk_offsets_stay_inside_requested_aperture(self) -> None:
        offsets = disk_offsets(0.2)
        self.assertGreater(offsets.shape[0], 1)
        self.assertLessEqual(float(np.max(np.linalg.norm(offsets, axis=1))), 0.1e-3 + 1e-12)
        np.testing.assert_array_equal(disk_offsets(0.0), [[0.0, 0.0]])

    def test_positive_registration_offset_moves_peak_toward_shorter_measurement_coordinate(self) -> None:
        axis = np.arange(31, dtype=float)
        pressure = np.exp(-((axis[:, None, None] - 18.0) / 2.0) ** 2)
        measured_distance = np.arange(10, dtype=float) * 1e-3
        measured = np.exp(-((measured_distance - 6e-3) / 2e-3) ** 2)
        arms = registration_sweep(
            pressure, np.array([10.0, 0.0, 0.0]), 1e-3,
            measured_distance, measured, [0.0, 2.0],
        )
        self.assertGreater(arms[0]["peak_position_difference_mm"], arms[1]["peak_position_difference_mm"])


if __name__ == "__main__":
    unittest.main()
