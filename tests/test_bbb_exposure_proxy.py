from __future__ import annotations

import math
import unittest

from bbb_exposure_proxy import (
    ExposureProxyError,
    build_proxy,
    mechanical_index,
    pulse_timing,
    sensitivity_levels,
    validate_microbubble,
)


class BBBExposureProxyTests(unittest.TestCase):
    def test_mechanical_index_matches_definition(self) -> None:
        value = mechanical_index(500000.0, 250000.0, "waveform_derived_insitu_pnp")
        self.assertAlmostEqual(value, 1.0)

    def test_mi_rejects_pressure_magnitude_semantics(self) -> None:
        with self.assertRaisesRegex(ExposureProxyError, "requires waveform"):
            mechanical_index(500000.0, 500000.0, "absolute_peak_magnitude")

    def test_pulse_timing_matches_analytic_values(self) -> None:
        result = pulse_timing(500000.0, 5000, 10.0, 2.0)
        self.assertAlmostEqual(result["burst_duration_s"], 0.01)
        self.assertAlmostEqual(result["duty_cycle_fraction"], 0.1)
        self.assertEqual(result["pulse_count"], 20)
        self.assertAlmostEqual(result["total_on_time_s"], 0.2)

    def test_rejects_duty_cycle_above_one(self) -> None:
        with self.assertRaisesRegex(ExposureProxyError, "above one"):
            pulse_timing(100.0, 100, 2.0, 1.0)

    def test_microbubble_fields_are_all_or_none(self) -> None:
        validate_microbubble({"status": "not_specified", "product": None, "dose": None, "timing": None})
        with self.assertRaisesRegex(ExposureProxyError, "requires product"):
            validate_microbubble({"status": "protocol_input", "product": "x", "dose": None, "timing": "before"})

    def test_sensitivity_scaling_is_linear_and_quadratic(self) -> None:
        rows = sensitivity_levels(1e6, 1e6, [0.8, 1.0, 1.2])
        self.assertEqual([row["pnp_pa"] for row in rows], [8e5, 1e6, 1.2e6])
        self.assertAlmostEqual(rows[2]["relative_intensity_proxy"], 1.44)
        self.assertAlmostEqual(rows[2]["mechanical_index"], 1.2)

    def test_current_boundary_keeps_mi_null(self) -> None:
        result = build_proxy(
            500000.0,
            2e6,
            "absolute_peak_magnitude_not_waveform_pnp",
            {"status": "not_specified", "product": None, "dose": None, "timing": None},
        )
        self.assertIsNone(result["mechanical_index"])
        self.assertEqual(result["mi_status"], "blocked_no_waveform_pnp")
        self.assertFalse(result["clinical_dose_recommendation"])


if __name__ == "__main__":
    unittest.main()
