from __future__ import annotations

import unittest

from generate_ucl_h115_grid_sensitivity_figure import failed_gate_ratios


class FigureSchemaTests(unittest.TestCase):
    def test_reads_frozen_comparison_schema(self) -> None:
        comparison = {
            "axial_held_out": {"peak_position_difference_mm": 2.0},
            "transverse_held_out": {"normalized_relative_l2_percent": 15.0, "y_width_error_percent": 30.0},
        }
        self.assertEqual(failed_gate_ratios(comparison), [2.0, 1.5])


if __name__ == "__main__":
    unittest.main()
