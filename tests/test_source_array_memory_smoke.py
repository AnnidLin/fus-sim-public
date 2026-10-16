import unittest

from simulate_source_array_focus import SourceArrayConfig, enforce_simulation_time


class ShortMemorySmokeTests(unittest.TestCase):
    def test_paper_grade_short_run_is_rejected_by_default(self) -> None:
        config = SourceArrayConfig(preset="paper_grade", simulation_time_s=1e-6)
        with self.assertRaisesRegex(ValueError, "Simulation Time Truncation Danger"):
            enforce_simulation_time(config, distance_m=0.074)

    def test_explicit_memory_smoke_preserves_short_time(self) -> None:
        config = SourceArrayConfig(
            preset="paper_grade",
            simulation_time_s=1e-6,
            allow_short_memory_smoke=True,
        )
        adjusted = enforce_simulation_time(config, distance_m=0.074)
        self.assertEqual(adjusted.simulation_time_s, 1e-6)


if __name__ == "__main__":
    unittest.main()
