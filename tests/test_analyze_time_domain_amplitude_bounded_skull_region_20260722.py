from __future__ import annotations

import unittest

import numpy as np

from analyze_time_domain_amplitude_bounded_skull_region_20260722 import (
    exact_mixture_peaks,
    select_margin_candidate,
    sentinel_peak_lower_bounds,
    simplex_coefficients,
    triangle_peak_upper_bounds,
)


class TimeDomainAmplitudeBoundedTests(unittest.TestCase):
    def test_simplex_grid_is_complete_and_normalized(self) -> None:
        coefficients = simplex_coefficients(0.25)
        self.assertEqual(coefficients.shape, (15, 3))
        np.testing.assert_allclose(np.sum(coefficients, axis=1), 1.0)
        self.assertTrue(np.all(coefficients >= 0.0))

    def test_triangle_bound_is_not_below_exact_peak(self) -> None:
        basis = np.array([[[1.0, -2.0, 0.5]], [[-1.5, 0.5, 1.0]], [[0.2, 0.1, -0.3]]])
        coefficients = np.array([[0.4, 0.4, 0.2], [0.1, 0.2, 0.7]])
        exact = exact_mixture_peaks(basis, coefficients, candidate_batch=1, sample_chunk=2)
        upper = triangle_peak_upper_bounds(coefficients, np.max(np.abs(basis), axis=(1, 2)))
        self.assertTrue(np.all(exact <= upper + 1e-12))

    def test_exact_peaks_match_direct_mixtures(self) -> None:
        rng = np.random.default_rng(17)
        basis = rng.normal(size=(3, 4, 7))
        coefficients = simplex_coefficients(0.5)
        expected = np.array([np.max(np.abs(np.tensordot(row, basis, axes=(0, 0)))) for row in coefficients])
        actual = exact_mixture_peaks(basis, coefficients, candidate_batch=2, sample_chunk=5)
        np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)

    def test_sentinel_bound_is_not_above_exact_peak(self) -> None:
        rng = np.random.default_rng(23)
        basis = rng.normal(size=(3, 4, 7))
        coefficients = simplex_coefficients(0.25)
        exact = exact_mixture_peaks(basis, coefficients)
        lower = sentinel_peak_lower_bounds(basis, coefficients, top_samples_per_basis=3)
        self.assertTrue(np.all(lower <= exact + 1e-12))

    def test_selection_uses_margin_then_worst_hotspot(self) -> None:
        rows = [
            {"passes_pressure_margin": True, "minimum_corrected_hotspot_suppression": 0.24, "target_retention": 0.95, "waveform_peak_vs_control": 1.1},
            {"passes_pressure_margin": True, "minimum_corrected_hotspot_suppression": 0.30, "target_retention": 0.89, "waveform_peak_vs_control": 1.2},
            {"passes_pressure_margin": False, "minimum_corrected_hotspot_suppression": 0.50, "target_retention": 0.70, "waveform_peak_vs_control": 1.0},
        ]
        self.assertIs(select_margin_candidate(rows), rows[1])


if __name__ == "__main__":
    unittest.main()
