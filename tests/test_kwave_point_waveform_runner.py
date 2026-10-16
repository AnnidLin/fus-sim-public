import unittest

import run_kwave_command as stable_runner
import run_kwave_point_waveform_command


class PointWaveformRunnerTests(unittest.TestCase):
    def test_wrapper_registers_only_expected_script_when_main_runs(self) -> None:
        self.assertNotIn(
            "simulate_source_array_focus_point_waveform.py",
            stable_runner.ALLOWED_SCRIPTS,
        )
        self.assertTrue(callable(run_kwave_point_waveform_command.main))


if __name__ == "__main__":
    unittest.main()
