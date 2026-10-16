import unittest

import numpy as np

from select_paper_gate_a_trajectories import (
    candidate_source_index,
    contiguous_segments,
    sampled_ray_indices,
)


class GateATrajectorySelectionTests(unittest.TestCase):
    def test_candidate_source_is_on_fixed_radius_within_half_voxel(self) -> None:
        target = np.array([100, 50, 50])
        source = candidate_source_index(target, (10.0, -5.0), 74.4353753, 0.75e-3)
        self.assertIsNotNone(source)
        distance_mm = np.linalg.norm(target - source) * 0.75
        self.assertLessEqual(abs(distance_mm - 74.4353753), 0.375)

    def test_sampled_ray_includes_endpoints(self) -> None:
        source = np.array([1, 1, 1])
        target = np.array([8, 4, 2])
        ray = sampled_ray_indices(source, target, (10, 10, 10))
        np.testing.assert_array_equal(ray[0], source)
        np.testing.assert_array_equal(ray[-1], target)

    def test_contiguous_segments(self) -> None:
        mask = np.array([False, True, True, False, True, False])
        self.assertEqual(contiguous_segments(mask), 2)
        self.assertEqual(contiguous_segments(np.zeros(4, dtype=bool)), 0)


if __name__ == "__main__":
    unittest.main()
