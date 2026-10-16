from __future__ import annotations

import unittest

import numpy as np

from analyze_target_hard_constrained_hotspot_20260722 import (
    conservative_hotspot_ratio,
    select_candidate,
    solver_normalized_response_ratio,
)


class TargetHardConstrainedHotspotTests(unittest.TestCase):
    def test_solver_normalization_penalizes_larger_time_peak(self) -> None:
        frequency = 10.0
        dt = 0.001
        time = np.arange(1000) * dt
        control = np.vstack([np.cos(2 * np.pi * frequency * time), np.cos(2 * np.pi * frequency * time)])
        candidate = control.copy()
        candidate[0, 0] = 2.0
        transfer = np.array([1.0 + 0j, 1.0 + 0j])
        ratio = solver_normalized_response_ratio(transfer, candidate, control, dt, frequency)
        self.assertLess(ratio, 0.6)

    def test_solver_ratio_is_invariant_to_global_candidate_scale(self) -> None:
        frequency = 10.0
        dt = 0.001
        time = np.arange(1000) * dt
        control = np.vstack([np.cos(2 * np.pi * frequency * time)])
        transfer = np.array([1.0 + 0j])
        first = solver_normalized_response_ratio(transfer, control * 2.0, control, dt, frequency)
        second = solver_normalized_response_ratio(transfer, control * 7.0, control, dt, frequency)
        self.assertAlmostEqual(first, second)

    def test_conservative_hotspot_correction_never_reduces_ratio(self) -> None:
        corrected, factor = conservative_hotspot_ratio(0.2, 0.3, 0.2)
        self.assertAlmostEqual(corrected, 0.3)
        self.assertAlmostEqual(factor, 1.5)
        corrected2, factor2 = conservative_hotspot_ratio(0.2, 0.1, 0.2)
        self.assertEqual(corrected2, 0.2)
        self.assertEqual(factor2, 1.0)

    def test_selection_respects_hard_gate_then_hotspot_objective(self) -> None:
        rows = [
            {"regularization_fraction": 1.0, "passes_all_hard_gates": False, "conservative_hotspot_suppression": 0.9, "target_retention": 0.4},
            {"regularization_fraction": 3.0, "passes_all_hard_gates": True, "conservative_hotspot_suppression": 0.3, "target_retention": 0.9},
            {"regularization_fraction": 10.0, "passes_all_hard_gates": True, "conservative_hotspot_suppression": 0.2, "target_retention": 0.98},
        ]
        self.assertEqual(select_candidate(rows)["regularization_fraction"], 3.0)


if __name__ == "__main__":
    unittest.main()
