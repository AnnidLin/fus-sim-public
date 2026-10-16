import unittest

import numpy as np

from simulate_source_array_focus import compute_apodization_weights


class SourceArrayApodizationTests(unittest.TestCase):
    def test_radial_tukey_preserves_center_and_tapers_only_rim(self) -> None:
        u = np.array([0.0, 0.25, 0.5, 0.7, 0.85, 1.0])

        weights = compute_apodization_weights(u, 1.0, "tukey", 0.3)

        np.testing.assert_allclose(weights, [1.0, 1.0, 1.0, 1.0, 0.5, 0.0], atol=1e-12)
        self.assertTrue(np.all(np.diff(weights) <= 1e-12))

    def test_radial_tukey_boundary_parameters(self) -> None:
        u = np.linspace(0.0, 1.0, 11)

        np.testing.assert_allclose(
            compute_apodization_weights(u, 1.0, "tukey", 0.0),
            np.ones_like(u),
        )
        np.testing.assert_allclose(
            compute_apodization_weights(u, 1.0, "tukey", 1.0),
            compute_apodization_weights(u, 1.0, "hann", 0.5),
        )

    def test_existing_hann_and_hamming_center_to_rim_behavior(self) -> None:
        u = np.array([0.0, 1.0])

        np.testing.assert_allclose(
            compute_apodization_weights(u, 1.0, "hann", 0.5),
            [1.0, 0.0],
        )
        np.testing.assert_allclose(
            compute_apodization_weights(u, 1.0, "hamming", 0.5),
            [1.0, 0.08],
        )


if __name__ == "__main__":
    unittest.main()
