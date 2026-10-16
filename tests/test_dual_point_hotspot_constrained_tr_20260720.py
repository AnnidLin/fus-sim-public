from __future__ import annotations

import unittest

import numpy as np

from design_dual_point_hotspot_constrained_tr_20260720 import (
    extract_transfer_phasor,
    null_projected_weights,
    predicted_response,
)


class DualPointConstrainedTRTests(unittest.TestCase):
    def test_unregularized_projection_nulls_hotspot(self) -> None:
        target = np.array([1 + 1j, 2 - 0.5j, -0.2 + 0.7j])
        hotspot = np.array([0.3 - 0.2j, -1 + 0.4j, 0.8 + 0.1j])
        weights = null_projected_weights(target, hotspot)
        self.assertLess(abs(predicted_response(hotspot, weights)), 1e-12)
        self.assertGreater(abs(predicted_response(target, weights)), 0.1)

    def test_regularization_trades_null_depth_for_target_retention(self) -> None:
        target = np.array([1 + 0j, 0.5 + 1j, -0.3 + 0.2j])
        hotspot = np.array([0.2 + 0.7j, -0.4 + 0.1j, 0.9 - 0.2j])
        exact = null_projected_weights(target, hotspot, 0.0)
        regularized = null_projected_weights(target, hotspot, 0.2)
        self.assertGreaterEqual(abs(predicted_response(hotspot, regularized)), abs(predicted_response(hotspot, exact)))
        self.assertEqual(exact.shape, target.shape)

    def test_phasor_extracts_known_frequency(self) -> None:
        frequency = 10.0
        dt = 0.001
        time = np.arange(1000) * dt
        signals = np.vstack([np.cos(2 * np.pi * frequency * time), np.sin(2 * np.pi * frequency * time)])
        phasor = extract_transfer_phasor(signals, dt, frequency)
        self.assertEqual(phasor.shape, (2,))
        self.assertGreater(abs(phasor[0]), 400)
        self.assertGreater(abs(phasor[1]), 400)

    def test_rejects_shape_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            null_projected_weights(np.ones(3), np.ones(4))


if __name__ == "__main__":
    unittest.main()
