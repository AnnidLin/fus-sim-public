import unittest

import numpy as np

from summarize_ucl_270khz_freefield import (
    MINUS_6DB_AMPLITUDE,
    carrier_projector,
    continuous_threshold_width,
    fit_carrier,
    integer_cycle_slice,
    interpolate_calibration,
    refined_peak_coordinate,
    threshold_region,
)


class UclFreefieldSummaryTests(unittest.TestCase):
    def test_integer_cycle_crop_is_centred_and_near_five_cycles(self) -> None:
        selected = integer_cycle_slice(1000, 20e-9, 270e3)
        self.assertEqual(selected.stop - selected.start, 926)
        self.assertLess(abs((selected.stop - selected.start) * 20e-9 * 270e3 - 5.0), 0.001)
        self.assertLessEqual(abs(selected.start - (1000 - selected.stop)), 1)

    def test_carrier_fit_recovers_peak_amplitude_and_offset(self) -> None:
        dt = 20e-9
        frequency = 270e3
        selected = integer_cycle_slice(1000, dt, frequency)
        samples = selected.stop - selected.start
        time = np.arange(samples) * dt
        wave = 0.012 * np.sin(2 * np.pi * frequency * time + 0.37) - 0.0002
        amplitude, phase, offset = fit_carrier(wave[None, :], carrier_projector(samples, dt, frequency))
        self.assertAlmostEqual(float(amplitude[0]), 0.012, places=12)
        self.assertAlmostEqual(float(phase[0]), 0.37, places=12)
        self.assertAlmostEqual(float(offset[0]), -0.0002, places=12)

    def test_frequency_response_interpolation_uses_documented_rows(self) -> None:
        response = np.array(
            [[[250e3, 300e3], [2.3e-8, 2.4e-8], [9.0, 9.0], [0.17, 0.192], [5.0, 5.0]]]
        )
        calibration = interpolate_calibration(response, 270e3)
        self.assertAlmostEqual(calibration["sensitivity_v_per_pa"], 2.34e-8, places=16)
        self.assertAlmostEqual(calibration["phase_rad"], 0.1788, places=12)

    def test_continuous_minus6db_width_and_refined_peak(self) -> None:
        x = np.linspace(-5.0, 5.0, 101)
        amplitude = np.exp(-(x / 2.0) ** 2)
        width = continuous_threshold_width(x, amplitude, MINUS_6DB_AMPLITUDE)
        expected = 4.0 * np.sqrt(-np.log(MINUS_6DB_AMPLITUDE))
        self.assertAlmostEqual(width, expected, places=2)
        self.assertAlmostEqual(refined_peak_coordinate(x + 0.03, amplitude), 0.03, places=12)

    def test_threshold_region_reports_censoring_without_fake_width(self) -> None:
        x = np.arange(5, dtype=float)
        amplitude = np.array([0.8, 0.9, 1.0, 0.7, 0.2])
        result = threshold_region(x, amplitude, 0.5)
        self.assertEqual(result["status"], "left_censored")
        self.assertIsNone(result["width"])
        self.assertGreater(result["lower_bound"], 3.0)


if __name__ == "__main__":
    unittest.main()
