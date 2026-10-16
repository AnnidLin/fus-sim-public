from __future__ import annotations

import unittest

import numpy as np

from register_nlm_ct_t2 import dice_score
from register_nlm_ct_t2_outer_head import make_outer_head_masks


class RegisterNlmCtT2OuterHeadTests(unittest.TestCase):
    def test_outer_head_mask_does_not_collapse_to_bright_core(self) -> None:
        grid = np.indices((30, 30, 20))
        radius = np.sqrt(sum((axis - center) ** 2 for axis, center in zip(grid, (15, 15, 10))))
        ct = np.where(radius < 9, 50.0, -1000.0)
        t2 = np.where(radius < 9, 10.0, 0.0)
        t2[radius < 4] = 500.0
        ct_mask, t2_mask, threshold = make_outer_head_masks(ct, t2)
        self.assertLess(threshold, 20.0)
        self.assertGreater(dice_score(ct_mask, t2_mask), 0.95)


if __name__ == "__main__":
    unittest.main()
