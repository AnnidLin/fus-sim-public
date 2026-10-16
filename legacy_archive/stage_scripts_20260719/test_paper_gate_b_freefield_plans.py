import unittest

import numpy as np

from generate_paper_gate_b_freefield_plans import RADIUS_MM, make_plan


class GateBFreefieldPlanTests(unittest.TestCase):
    def test_physical_geometry_is_consistent_across_grids(self) -> None:
        beam = np.array([0.97, 0.2, -0.13], dtype=float)
        beam /= np.linalg.norm(beam)
        plans = [make_plan(dx, beam) for dx in (0.75, 0.5)]
        for plan, dx in zip(plans, (0.75, 0.5)):
            self.assertLessEqual(abs(plan["source_to_target_distance_mm"] - RADIUS_MM), dx * 0.5)
            shape = np.asarray(plan["model_shape"])
            for key in ("source_center_index_ijk", "target_index_ijk", "entry_index_ijk"):
                point = np.asarray(plan[key])
                self.assertTrue(np.all(point >= 0))
                self.assertTrue(np.all(point < shape))


if __name__ == "__main__":
    unittest.main()
