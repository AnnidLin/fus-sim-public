from __future__ import annotations

import unittest

import numpy as np

from prepare_target_preserving_blend_validation_20260722 import expected_blend


class PrepareTargetPreservingBlendTests(unittest.TestCase):
    def test_expected_blend_is_float32_and_exact(self) -> None:
        control = np.array([[1.0, 2.0]], dtype=np.float32)
        constrained = np.array([[3.0, 4.0]], dtype=np.float32)
        result = expected_blend(control, constrained, 0.4)
        self.assertEqual(result.dtype, np.float32)
        np.testing.assert_array_equal(result, np.array([[1.8, 2.8]], dtype=np.float32))

    def test_shape_mismatch_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            expected_blend(np.ones((1, 2)), np.ones((2, 2)), 0.4)


if __name__ == "__main__":
    unittest.main()
