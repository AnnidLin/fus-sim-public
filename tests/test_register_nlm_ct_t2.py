from __future__ import annotations

import unittest

import numpy as np

from register_nlm_ct_t2 import normalized_mutual_information, rigid_transform, rotation_matrix_xyz


class RegisterNlmCtT2Tests(unittest.TestCase):
    def test_zero_rotation_is_identity(self) -> None:
        np.testing.assert_allclose(rotation_matrix_xyz(np.zeros(3)), np.eye(3), atol=1e-12)

    def test_rigid_transform_maps_moving_center_to_fixed_plus_offset(self) -> None:
        parameters = np.asarray([0, 0, 0, 1, -2, 3], dtype=float)
        transform = rigid_transform(parameters, np.asarray([10, 20, 30]), np.asarray([-4, 5, 8]))
        mapped = transform @ np.asarray([10, 20, 30, 1])
        np.testing.assert_allclose(mapped[:3], [-3, 3, 11])

    def test_nmi_is_higher_for_identical_arrays(self) -> None:
        rng = np.random.default_rng(22)
        fixed = rng.normal(size=(30, 30, 10))
        shuffled = rng.permutation(fixed.ravel()).reshape(fixed.shape)
        valid = np.ones(fixed.shape, dtype=bool)
        self.assertGreater(normalized_mutual_information(fixed, fixed, valid),
                           normalized_mutual_information(fixed, shuffled, valid))


if __name__ == "__main__":
    unittest.main()
