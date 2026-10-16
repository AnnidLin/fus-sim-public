from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from monitor_kwave_process import parse_kwave_progress, supervise


class MonitorTokenEfficiencyTests(unittest.TestCase):
    def test_parses_steps_per_second_progress(self) -> None:
        progress = parse_kwave_progress(
            "k-Wave:  64%|x| 2403/3750 [33:59<08:25, 1.17step/s]\n"
        )
        self.assertIsNotNone(progress)
        assert progress is not None
        self.assertEqual(progress["current_step"], 2403)
        self.assertEqual(progress["total_steps"], 3750)
        self.assertAlmostEqual(progress["seconds_per_step"], 1 / 1.17)

    def test_calibration_uses_stage_specific_completion_and_attention(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp)
            child_code = (
                "import pathlib,sys;"
                "p=pathlib.Path(sys.argv[1]);"
                "(p/'element_signals.npz').write_bytes(b'ok');"
                "(p/'summary_calibrate.json').write_text('{}',encoding='utf-8')"
            )
            result = supervise(
                command=[
                    sys.executable, "-c", child_code, str(output_dir),
                    "--stage", "calibrate",
                ],
                output_dir=output_dir,
                checkpoint_sec=0.01,
                poll_sec=0.01,
                stall_stop_sec=1.0,
                emergency_ceiling_sec=5.0,
                maximum_ceiling_sec=10.0,
            )
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["stage"], "calibrate")
            self.assertTrue(result["expected_output_exists"]["element_signals"])
            attention = json.loads(
                (output_dir / "monitor_attention.json").read_text(encoding="utf-8")
            )
            self.assertEqual(attention["event"], "completed")
            self.assertEqual(attention["stage"], "calibrate")
            self.assertNotIn("command", attention)
            self.assertNotIn("progress_history", attention)


if __name__ == "__main__":
    unittest.main()
