from __future__ import annotations

import unittest

import nibabel as nib
import numpy as np

from build_nlm_acoustic_model_with_affine import explicit_isotropic_grid, roundtrip_max_error_voxels


class BuildNlmAcousticModelWithAffineTests(unittest.TestCase):
    def test_explicit_grid_has_requested_spacing_and_expected_shape(self) -> None:
        image = nib.Nifti1Image(np.zeros((10, 20, 30), dtype=np.float32), np.diag([0.5, 1.0, 2.0, 1.0]))
        shape, affine = explicit_isotropic_grid(image, 1.0)
        self.assertEqual(shape, (5, 20, 60))
        np.testing.assert_allclose(np.linalg.norm(affine[:3, :3], axis=0), [1.0, 1.0, 1.0])

    def test_affine_roundtrip_is_numerically_exact(self) -> None:
        affine = np.asarray([[0.75, 0, 0, -120], [0, 0.75, 0, -190], [0, 0, 0.75, -230], [0, 0, 0, 1]])
        self.assertLess(roundtrip_max_error_voxels(affine, (334, 334, 311)), 1e-10)


if __name__ == "__main__":
    unittest.main()
