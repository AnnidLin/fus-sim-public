from __future__ import annotations

import unittest

import numpy as np

from analyze_ucl_h115_grid_sensitivity import sample_candidate_on_reference


class PhysicalAlignmentTests(unittest.TestCase):
    def test_linear_field_is_preserved_across_spacing(self) -> None:
        reference_shape = (5, 5, 5)
        candidate_shape = (9, 9, 9)
        reference_source = np.array([2.0, 2.0, 2.0])
        candidate_source = np.array([4.0, 4.0, 4.0])
        candidate_grid = np.indices(candidate_shape, dtype=float)
        candidate_pressure = 1.0 + 0.1 * (candidate_grid[0] - candidate_source[0]) + 0.2 * (candidate_grid[1] - candidate_source[1])
        reference_grid = np.indices(reference_shape, dtype=float)
        reference_pressure = 1.0 + 0.2 * (reference_grid[0] - reference_source[0]) + 0.4 * (reference_grid[1] - reference_source[1])
        reference = {"pressure": reference_pressure, "dx_m": 1.0, "source": reference_source}
        candidate = {"pressure": candidate_pressure, "dx_m": 0.5, "source": candidate_source}
        mapped, valid = sample_candidate_on_reference(reference, candidate)
        self.assertTrue(valid.all())
        np.testing.assert_allclose(mapped, reference_pressure, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
