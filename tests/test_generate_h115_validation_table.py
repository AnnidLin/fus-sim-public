from __future__ import annotations

import unittest

from generate_h115_methods_table import row as methods_row
from generate_h115_validation_table import METRICS, build_rows


class H115ValidationTableTests(unittest.TestCase):
    def test_emits_one_row_per_frozen_endpoint_and_case(self) -> None:
        data = {
            "axial_held_out": {
                "peak_position_difference_mm": 1.0,
                "normalized_relative_l2_percent": 2.0,
            },
            "transverse_held_out": {
                "peak_pressure_error_percent": 3.0,
                "peak_position_difference_mm": 4.0,
                "normalized_correlation": 0.9,
                "normalized_relative_l2_percent": 5.0,
                "x_width_error_percent": 6.0,
                "y_width_error_percent": 7.0,
            },
            "checks": {metric[-1]: index % 2 == 0 for index, metric in enumerate(METRICS)},
        }
        rows = build_rows([("case-a", data), ("case-b", data)])
        self.assertEqual(len(rows), 16)
        self.assertEqual(sum(row["status"] == "pass" for row in rows), 8)
        self.assertEqual(sum(row["status"] == "fail" for row in rows), 8)

    def test_methods_row_preserves_device_and_quality_boundaries(self) -> None:
        summary = {
            "config": {"transducer_radius_m": 0.06139, "aperture_diameter_m": 0.0504, "pml_size": 16, "cfl": 0.1, "tone_burst_cycles": 16, "simulation_time_s": 180e-6},
            "simulation_quality": {"ppw_min_sound_speed": 10.98, "evidence_level": "engineering", "is_paper_grade": False},
            "runtime": {"dt_s": 3.37e-8, "nt": 5337, "runtime_s": 60.0},
            "dx_m": 0.0005,
            "model_shape": [201, 161, 161],
            "source": {"source_points": 7997},
        }
        package = {"device_extrema": {"max_equivalent_cores": 5.9, "max_working_set_gib": 1.2, "min_system_free_memory_gib": 17.0}}
        item = methods_row("effective", summary, package, "paper")
        self.assertEqual(item["pml_thickness_mm"], 8.0)
        self.assertFalse(item["is_paper_grade"])
        self.assertEqual(item["source_points"], 7997)


if __name__ == "__main__":
    unittest.main()
