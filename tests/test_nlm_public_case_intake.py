from __future__ import annotations

import unittest

import numpy as np

from nlm_public_case_intake import PublicCaseIntakeError, build_affine_ras, slice_normal


class NlmPublicCaseIntakeTests(unittest.TestCase):
    def test_axial_lps_affine_is_converted_to_ras(self) -> None:
        affine = build_affine_ras(
            [1, 0, 0, 0, 1, 0],
            [0.5, 0.4],
            [-100, -120, -20],
            1.0,
        )
        np.testing.assert_allclose(
            affine,
            [
                [-0.4, 0.0, 0.0, 100.0],
                [0.0, -0.5, 0.0, 120.0],
                [0.0, 0.0, 1.0, -20.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
        )

    def test_oblique_slice_normal_is_unit_length(self) -> None:
        normal = slice_normal([0.997903, -0.043587, -0.047856, 0.043668, 0.999046, 0.000637])
        self.assertAlmostEqual(float(np.linalg.norm(normal)), 1.0, places=7)
        self.assertGreater(normal[2], 0.99)

    def test_degenerate_orientation_is_rejected(self) -> None:
        with self.assertRaises(PublicCaseIntakeError):
            slice_normal([1, 0, 0, 1, 0, 0])


if __name__ == "__main__":
    unittest.main()
