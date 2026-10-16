"""Regression tests for the H115 water validation analyzer."""
from __future__ import annotations

import unittest

import numpy as np

from analyze_ucl_h115_water_validation import frozen_measured_transverse_widths, transverse_widths


class FrozenMeasurementWidthTests(unittest.TestCase):
    def test_uses_frozen_summary_endpoints(self) -> None:
        summary = {
            "transverse_qcw": {
                "minus6db_x_width_mm": 8.2,
                "minus6db_y_width_mm": 8.0,
                "peak_coordinate_native_mm": [-0.016, 0.020, -39.998],
            }
        }
        self.assertEqual(
            frozen_measured_transverse_widths(summary),
            {
                "minus6db_x_width_mm": 8.2,
                "minus6db_y_width_mm": 8.0,
                "peak_x_mm": -0.016,
                "peak_y_mm": 0.020,
            },
        )

    def test_transverse_widths_ignore_substep_coordinate_jitter(self) -> None:
        axis = np.linspace(-6e-3, 6e-3, 9)
        grid_x, grid_y = np.meshgrid(axis, axis)
        # The UCL raster contains micron-scale x-coordinate jitter even though
        # its nominal scan step is 1.5 mm.  Width extraction must not treat
        # each jittered value as a distinct grid column.
        jitter = np.linspace(-8e-6, 8e-6, grid_x.size).reshape(grid_x.shape)
        sample_x = (grid_x + jitter).ravel()
        sample_y = grid_y.ravel()
        pressure = np.exp(-((grid_x / 3e-3) ** 2 + (grid_y / 3e-3) ** 2)).ravel()

        widths = transverse_widths(sample_x, sample_y, pressure)

        self.assertAlmostEqual(
            widths["minus6db_x_width_mm"],
            widths["minus6db_y_width_mm"],
            delta=0.05,
        )


if __name__ == "__main__":
    unittest.main()
