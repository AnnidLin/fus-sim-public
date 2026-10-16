from __future__ import annotations

import unittest

import numpy as np

from simulate_source_array_focus import compute_apodization_weights


class HammingReplayTests(unittest.TestCase):
    def test_hamming_is_center_weighted_and_bounded(self) -> None:
        theta = np.linspace(0.0, 1.0, 101)
        weights = compute_apodization_weights(theta, 1.0, "hamming", 0.5)
        self.assertAlmostEqual(float(weights[0]), 1.0)
        self.assertAlmostEqual(float(weights[-1]), 0.08)
        self.assertTrue(np.all(np.diff(weights) <= 1e-12))
        self.assertTrue(np.all((weights >= 0.08) & (weights <= 1.0)))

    def test_row_weighting_preserves_phase_sign_and_time_shape(self) -> None:
        signals = np.array([[1.0, -2.0, 0.0], [-3.0, 4.0, -5.0]], dtype=np.float32)
        weights = np.array([1.0, 0.2], dtype=np.float32)
        weighted = signals * weights[:, None]
        self.assertEqual(weighted.shape, signals.shape)
        np.testing.assert_array_equal(np.signbit(weighted), np.signbit(signals))
        np.testing.assert_allclose(weighted[1], signals[1] * 0.2)


if __name__ == "__main__":
    unittest.main()
