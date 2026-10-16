from __future__ import annotations

import unittest

import numpy as np

from generate_bbb_element_plan_h3_20260722 import mask_hash


class H3ElementPlanTests(unittest.TestCase):
    def test_mask_hash_uses_uint8_c_order(self) -> None:
        mask = np.array([[0, 1, 1], [0, 0, 1]], dtype=np.int64)
        self.assertEqual(mask_hash(mask), mask_hash(mask.astype(np.uint8)))
        self.assertNotEqual(mask_hash(mask), mask_hash(mask.T.copy()))


if __name__ == "__main__":
    unittest.main()
