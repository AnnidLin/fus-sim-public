import unittest

import numpy as np

from generate_pub2_paper_figures_20260812 import signed_max_abs_projection, target_relative_extent


class Pub2PaperFigureTests(unittest.TestCase):
    def test_target_relative_extent_centers_target(self):
        extent = target_relative_extent((5, 7), np.array([2, 3]), 0.75)
        self.assertEqual(extent, [-1.875, 1.875, -2.625, 2.625])

    def test_signed_max_abs_projection_preserves_sign(self):
        field = np.array([[[1.0, -3.0], [-4.0, 2.0]]])
        projection = signed_max_abs_projection(field)
        np.testing.assert_array_equal(projection, np.array([[-3.0, -4.0]]))


if __name__ == "__main__":
    unittest.main()
