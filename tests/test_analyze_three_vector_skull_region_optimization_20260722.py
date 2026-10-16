from __future__ import annotations

import unittest

import numpy as np

from analyze_three_vector_skull_region_optimization_20260722 import (
    affine_two_endpoint_correction,
    minimum_norm_response_weights,
    select_candidate,
)


class ThreeVectorSkullRegionTests(unittest.TestCase):
    def test_minimum_norm_solution_satisfies_complex_constraints(self) -> None:
        matrix = np.array([[1 + 0j, 0.5 + 0.2j, 0.1j], [0.2 - 0.1j, 1 + 0j, 0.3], [0.4, 0.2j, 1 - 0.1j]])
        baseline = np.array([1 + 0.2j, 0.5 - 0.1j, -0.3 + 0.4j])
        desired = np.array([1.2 + 0.1j, 0.2 - 0.3j, -0.1 + 0.2j])
        result = minimum_norm_response_weights(matrix, baseline, desired)
        np.testing.assert_allclose(matrix @ result, desired, rtol=1e-9, atol=1e-9)

    def test_affine_correction_reproduces_both_anchors(self) -> None:
        self.assertAlmostEqual(affine_two_endpoint_correction(1.0, 0.2, 0.3), 1.0)
        self.assertAlmostEqual(affine_two_endpoint_correction(0.2, 0.2, 0.3), 0.3)

    def test_selection_maximizes_worst_hotspot_after_gates(self) -> None:
        rows = [
            {"passes_all_hard_gates": True, "minimum_corrected_hotspot_suppression": 0.25, "target_retention": 0.95},
            {"passes_all_hard_gates": True, "minimum_corrected_hotspot_suppression": 0.30, "target_retention": 0.86},
            {"passes_all_hard_gates": False, "minimum_corrected_hotspot_suppression": 0.50, "target_retention": 0.70},
        ]
        self.assertIs(select_candidate(rows), rows[1])


if __name__ == "__main__":
    unittest.main()
