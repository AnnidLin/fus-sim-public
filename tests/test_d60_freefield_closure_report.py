import unittest

import numpy as np

from generate_d60_freefield_closure_report import (
    continuous_half_peak_width_mm,
    orthonormal_lateral_axes,
)


class D60ClosureMetricTests(unittest.TestCase):
    def test_lateral_axes_are_orthonormal(self) -> None:
        axis = np.array([4.0, -1.0, 0.5])
        lateral_1, lateral_2 = orthonormal_lateral_axes(axis)
        unit_axis = axis / np.linalg.norm(axis)
        self.assertAlmostEqual(float(unit_axis @ lateral_1), 0.0, places=12)
        self.assertAlmostEqual(float(unit_axis @ lateral_2), 0.0, places=12)
        self.assertAlmostEqual(float(lateral_1 @ lateral_2), 0.0, places=12)

    def test_half_peak_width_on_binary_bar(self) -> None:
        field = np.zeros((21, 21, 21), dtype=float)
        field[7:14, 10, 10] = 1.0
        width = continuous_half_peak_width_mm(
            field,
            np.array([10.0, 10.0, 10.0]),
            np.array([1.0, 0.0, 0.0]),
            threshold=0.5,
            dx_mm=1.0,
        )
        self.assertGreaterEqual(width, 6.0)
        self.assertLessEqual(width, 7.0)


if __name__ == "__main__":
    unittest.main()
