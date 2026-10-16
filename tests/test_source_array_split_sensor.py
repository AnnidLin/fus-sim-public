import unittest

import numpy as np

from simulate_source_array_focus import LoadedModel
from simulate_source_array_focus_split_sensor import (
    build_pressure_sensor,
    extract_single_sensor_waveform,
    normalize_global_pressure_field,
)


class SplitSensorRecordingTests(unittest.TestCase):
    def setUp(self) -> None:
        shape = (5, 6, 7)
        self.model = LoadedModel(
            labels=None,
            sound_speed=np.full(shape, 1500.0),
            density=np.full(shape, 1000.0),
            alpha_coeff=np.zeros(shape),
            dx_m=0.001,
            target_index_ijk=np.array([2, 3, 4]),
            source_center_index_ijk=None,
            entry_index_ijk=None,
            beam_axis=None,
            entry_plan=None,
            crop_origin_ijk=np.zeros(3, dtype=int),
            source_model_shape=shape,
        )

    def test_waveform_mode_uses_one_point_and_global_extrema(self) -> None:
        sensor = build_pressure_sensor(self.model, True)
        self.assertEqual(int(np.count_nonzero(sensor.mask)), 1)
        self.assertTrue(sensor.mask[2, 3, 4])
        self.assertEqual(sensor.record, ["p", "p_max_all", "p_min_all"])

    def test_field_only_mode_is_unchanged(self) -> None:
        sensor = build_pressure_sensor(self.model, False)
        self.assertTrue(np.all(sensor.mask))
        self.assertEqual(sensor.record, ["p_max", "p_min"])

    def test_backend_axes_and_single_waveform_are_normalized(self) -> None:
        backend_field = np.arange(24).reshape(4, 3, 2)
        normalized = normalize_global_pressure_field(backend_field, (2, 3, 4))
        np.testing.assert_array_equal(normalized, np.transpose(backend_field, (2, 1, 0)))
        waveform = extract_single_sensor_waveform(np.arange(8).reshape(1, 8), 8)
        self.assertEqual(waveform.shape, (8,))
        self.assertEqual(waveform.dtype, np.float32)

    def test_mismatched_shapes_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not match"):
            normalize_global_pressure_field(np.zeros((2, 2)), (2, 3, 4))
        with self.assertRaisesRegex(ValueError, "Expected one"):
            extract_single_sensor_waveform(np.zeros((2, 8)), 8)


if __name__ == "__main__":
    unittest.main()
