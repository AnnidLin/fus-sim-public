from __future__ import annotations

import unittest

import numpy as np

from resample_nlm_t2_to_ct_native import block_offset, fixed_to_moving_voxel_mapping


class ResampleNlmT2ToCtNativeTests(unittest.TestCase):
    def test_identity_mapping_is_identity(self) -> None:
        mapping = fixed_to_moving_voxel_mapping(np.eye(4), np.eye(4), np.eye(4))
        np.testing.assert_allclose(mapping, np.eye(4))

    def test_block_offset_accounts_for_global_z_start(self) -> None:
        mapping = np.eye(4)
        mapping[:3, 3] = [1, 2, 3]
        np.testing.assert_allclose(block_offset(mapping, 7), [1, 2, 10])

    def test_world_translation_maps_fixed_back_to_moving(self) -> None:
        moving_to_fixed = np.eye(4)
        moving_to_fixed[:3, 3] = [5, -2, 3]
        mapping = fixed_to_moving_voxel_mapping(np.eye(4), np.eye(4), moving_to_fixed)
        np.testing.assert_allclose(mapping[:3, 3], [-5, 2, -3])


if __name__ == "__main__":
    unittest.main()
