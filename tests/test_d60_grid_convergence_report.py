import unittest

from generate_d60_grid_convergence_report import percent_change


class GridConvergenceReportTests(unittest.TestCase):
    def test_percent_change_uses_fine_grid_as_reference(self) -> None:
        self.assertAlmostEqual(percent_change(9.5, 10.0), 5.0)

    def test_percent_change_is_symmetric_in_difference_only(self) -> None:
        self.assertAlmostEqual(percent_change(10.5, 10.0), 5.0)


if __name__ == "__main__":
    unittest.main()
