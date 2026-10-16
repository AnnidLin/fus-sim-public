from __future__ import annotations

import unittest

import numpy as np

from analyze_target_preserving_waveform_blend_20260722 import (
    affine_endpoint_corrected_ratio,
    blend_waveforms,
    select_candidate,
)


class TargetPreservingWaveformBlendTests(unittest.TestCase):
    def test_blend_reproduces_both_endpoints(self) -> None:
        control = np.array([[1.0, 2.0]])
        constrained = np.array([[3.0, 4.0]])
        np.testing.assert_array_equal(blend_waveforms(control, constrained, 0.0), control)
        np.testing.assert_array_equal(blend_waveforms(control, constrained, 1.0), constrained)

    def test_blend_midpoint_is_convex(self) -> None:
        control = np.array([[0.0, 2.0]])
        constrained = np.array([[2.0, 4.0]])
        np.testing.assert_array_equal(blend_waveforms(control, constrained, 0.25), np.array([[0.5, 2.5]]))

    def test_affine_correction_reproduces_observed_endpoint(self) -> None:
        self.assertAlmostEqual(affine_endpoint_corrected_ratio(0.2, 1.0, 0.2, 0.3), 0.3)
        self.assertAlmostEqual(affine_endpoint_corrected_ratio(1.0, 0.0, 0.2, 0.3), 1.0)

    def test_selection_uses_hotspot_objective_after_hard_gates(self) -> None:
        rows = [
            {"blend_fraction": 0.1, "passes_all_hard_gates": True, "corrected_original_hotspot_suppression": 0.2, "target_retention": 0.9},
            {"blend_fraction": 0.2, "passes_all_hard_gates": True, "corrected_original_hotspot_suppression": 0.3, "target_retention": 0.85},
            {"blend_fraction": 0.3, "passes_all_hard_gates": False, "corrected_original_hotspot_suppression": 0.5, "target_retention": 0.7},
        ]
        self.assertEqual(select_candidate(rows)["blend_fraction"], 0.2)

    def test_invalid_fraction_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            blend_waveforms(np.ones((1, 2)), np.ones((1, 2)), 1.1)


if __name__ == "__main__":
    unittest.main()
