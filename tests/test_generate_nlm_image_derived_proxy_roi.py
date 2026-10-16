from __future__ import annotations

import unittest

import numpy as np

from generate_nlm_image_derived_proxy_roi import ProxyROIError, largest_component, spherical_mask


class NlmImageDerivedProxyROITests(unittest.TestCase):
    def test_largest_component_excludes_smaller_island(self) -> None:
        mask = np.zeros((12, 12), dtype=bool)
        mask[1:3, 1:3] = True
        mask[5:11, 4:10] = True
        selected = largest_component(mask)
        self.assertEqual(int(selected.sum()), 36)

    def test_sphere_uses_physical_spacing(self) -> None:
        mask = spherical_mask((11, 11, 11), (5, 5, 5), (1.0, 1.0, 2.0), 2.1)
        self.assertTrue(mask[7, 5, 5])
        self.assertTrue(mask[5, 5, 6])
        self.assertFalse(mask[5, 5, 7])

    def test_nonpositive_radius_is_rejected(self) -> None:
        with self.assertRaises(ProxyROIError):
            spherical_mask((5, 5, 5), (2, 2, 2), (1.0, 1.0, 1.0), 0.0)


if __name__ == "__main__":
    unittest.main()
