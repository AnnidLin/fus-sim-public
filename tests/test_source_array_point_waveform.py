import unittest

import numpy as np

from simulate_source_array_focus_point_waveform import _crop_external_pml


class PointWaveformOnlineExtremaTests(unittest.TestCase):
    def test_external_pml_crop_restores_original_shape(self) -> None:
        expanded = np.arange(8 * 9 * 10).reshape(8, 9, 10)
        cropped = _crop_external_pml(expanded, (1, 2, 3))
        self.assertEqual(cropped.shape, (6, 5, 4))
        np.testing.assert_array_equal(cropped, expanded[1:-1, 2:-2, 3:-3])

    def test_zero_pml_axis_is_not_emptied(self) -> None:
        expanded = np.zeros((3, 4, 5))
        self.assertEqual(_crop_external_pml(expanded, (0, 1, 1)).shape, (3, 2, 3))


if __name__ == "__main__":
    unittest.main()
