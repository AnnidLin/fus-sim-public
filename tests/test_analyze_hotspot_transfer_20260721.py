from __future__ import annotations

import unittest

import numpy as np

from analyze_hotspot_transfer_20260721 import (
    evaluate_candidates,
    normalized_weights,
    select_candidate,
)


class HotspotTransferAnalysisTests(unittest.TestCase):
    def test_normalization_matches_reference_max(self) -> None:
        weights = normalized_weights(np.array([1 + 1j, 0.2 - 0.1j]), 3.0)
        self.assertAlmostEqual(float(np.max(np.abs(weights))), 3.0)

    def test_candidates_are_finite_and_deterministic(self) -> None:
        target = np.array([1 + 0.2j, 0.4 - 0.3j, -0.2 + 0.8j, 0.9 + 0.1j])
        hotspot = np.array([0.3 + 0.8j, -0.5 + 0.2j, 0.6 - 0.1j, -0.1 + 0.4j])
        fractions = [0.0, 0.1, 1.0, 10.0]
        first = evaluate_candidates(target, hotspot, fractions, 0.0, 0.0)
        second = evaluate_candidates(target, hotspot, fractions, 0.0, 0.0)
        self.assertEqual([row["regularization_fraction"] for row in first], fractions)
        np.testing.assert_allclose(
            [row["target_retention"] for row in first],
            [row["target_retention"] for row in second],
        )
        self.assertTrue(all(row["finite"] for row in first))

    def test_selection_maximizes_target_then_suppression(self) -> None:
        rows = [
            {"passes_offline_gate": True, "target_retention": 0.90, "hotspot_suppression": 0.80},
            {"passes_offline_gate": True, "target_retention": 0.95, "hotspot_suppression": 0.31},
            {"passes_offline_gate": False, "target_retention": 1.00, "hotspot_suppression": 0.10},
        ]
        self.assertIs(select_candidate(rows), rows[1])

    def test_no_passing_candidate_returns_none(self) -> None:
        rows = [{"passes_offline_gate": False, "target_retention": 1.0, "hotspot_suppression": 0.0}]
        self.assertIsNone(select_candidate(rows))

    def test_rejects_shape_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "same 1D shape"):
            evaluate_candidates(np.ones(3), np.ones(4), [0.0], 0.85, 0.30)


if __name__ == "__main__":
    unittest.main()
