from __future__ import annotations

import unittest

import numpy as np

from design_dual_point_hotspot_constrained_tr_20260720 import extract_transfer_phasor
from prepare_dual_point_constrained_refocus_20260721 import normalize_max, realize_replay_phasors


class DualPointWaveformPreparationTests(unittest.TestCase):
    def test_hilbert_conversion_realizes_desired_phasors(self) -> None:
        frequency = 20.0
        dt = 0.001
        time = np.arange(2000) * dt
        replay = np.vstack([
            np.cos(2 * np.pi * frequency * time + 0.2),
            0.7 * np.cos(2 * np.pi * frequency * time - 0.8),
            1.2 * np.cos(2 * np.pi * frequency * time + 1.1),
        ])
        recorded = np.fliplr(replay)
        desired = np.array([1.0 + 0.2j, -0.3 + 0.9j, 0.4 - 0.7j]) * 1000
        modified_recorded, realized = realize_replay_phasors(recorded, desired, dt, frequency, chunk_rows=2)
        self.assertEqual(modified_recorded.shape, recorded.shape)
        relative = np.linalg.norm(realized - desired) / np.linalg.norm(desired)
        self.assertLess(relative, 1e-10)

    def test_stored_direction_reverses_to_realized_replay(self) -> None:
        frequency = 10.0
        dt = 0.001
        time = np.arange(1000) * dt
        recorded = np.fliplr(np.vstack([np.cos(2 * np.pi * frequency * time)]))
        desired = np.array([200 + 300j])
        modified_recorded, realized = realize_replay_phasors(recorded, desired, dt, frequency)
        replay_phasor = extract_transfer_phasor(np.fliplr(modified_recorded), dt, frequency)
        np.testing.assert_allclose(replay_phasor, realized, rtol=1e-6, atol=1e-3)

    def test_normalize_max_is_exact(self) -> None:
        value = normalize_max(np.array([1 + 1j, 2 - 0.5j]), 5.0)
        self.assertAlmostEqual(float(np.max(np.abs(value))), 5.0)

    def test_rejects_shape_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "incompatible"):
            realize_replay_phasors(np.ones((2, 10)), np.ones(3), 0.1, 1.0)


if __name__ == "__main__":
    unittest.main()
