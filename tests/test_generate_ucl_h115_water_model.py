import unittest

import numpy as np

from generate_ucl_h115_water_model import build_geometry


class UclH115WaterModelTests(unittest.TestCase):
    def test_geometry_encodes_effective_radius_and_safe_margins(self) -> None:
        geometry = build_geometry(0.5e-3, 61.39e-3)
        source = geometry["source"]
        target = geometry["target"]
        distance_mm = np.linalg.norm(target - source) * 0.5
        self.assertAlmostEqual(distance_mm, 61.5, places=12)
        self.assertGreater(source[0], 16)
        self.assertGreater(geometry["shape"][0] - target[0], 50)
        self.assertTrue(np.array_equal(geometry["beam_axis"], [1, 0, 0]))

    def test_finer_grid_preserves_physical_domain_and_geometry(self) -> None:
        reference = build_geometry(0.5e-3, 61.39e-3)
        candidate = build_geometry(0.3e-3, 61.39e-3)
        self.assertEqual(candidate["shape"], (335, 268, 268))
        self.assertTrue(np.all(np.abs(candidate["physical_extent_m"] - reference["physical_extent_m"]) <= 0.3e-3))
        candidate_distance = np.linalg.norm(candidate["target"] - candidate["source"]) * 0.3e-3
        self.assertLessEqual(abs(candidate_distance - 61.39e-3), 0.15e-3)
        self.assertLessEqual(abs(candidate["source"][0] * 0.3e-3 - 10e-3), 0.15e-3)


if __name__ == "__main__":
    unittest.main()
