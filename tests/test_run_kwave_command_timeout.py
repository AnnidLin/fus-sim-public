from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from run_kwave_command import PROJECT_ROOT, run_runner


class RunKwaveCommandTimeoutTests(unittest.TestCase):
    def test_timeout_is_recorded_with_partial_stage_artifacts(self) -> None:
        temp_root = PROJECT_ROOT / ".tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as temp:
            output_dir = Path(temp) / "timeout_case"
            calls = 0

            def fake_capture(command, stdout_path, stderr_path, timeout_s=None):
                nonlocal calls
                calls += 1
                stdout_path.parent.mkdir(parents=True, exist_ok=True)
                stdout_path.write_text("", encoding="utf-8")
                stderr_path.write_text("", encoding="utf-8")
                if calls == 1:
                    (output_dir / "quality_dry_run_summary.json").write_text(
                        "{}", encoding="utf-8"
                    )
                    return subprocess.CompletedProcess(command, 0)
                (output_dir / "summary_calibrate.json").write_text(
                    "{}", encoding="utf-8"
                )
                raise subprocess.TimeoutExpired(command, timeout_s)

            args = argparse.Namespace(
                script="simulate_time_reversal_focus.py",
                output_dir=str(output_dir),
                preset="quick",
                execute=True,
                allow_existing_output=False,
                checkpoint_sec=120,
                hard_stop_min=0.01,
                python_exe="python",
            )
            with (
                patch("run_kwave_command.run_command_capture", side_effect=fake_capture),
                patch("run_kwave_command.build_environment_record", return_value={}),
            ):
                status = run_runner(args, [])

            self.assertEqual(status["status"], "timeout_partial_output")
            self.assertTrue(status["execution"]["timed_out"])
            self.assertIsNone(status["execution"]["exit_code"])
            self.assertTrue(
                status["execution"]["partial_artifacts"]["summary_calibrate.json"]
            )
            persisted = json.loads(
                (output_dir / "runner_status.json").read_text(encoding="utf-8")
            )
            self.assertEqual(persisted["status"], "timeout_partial_output")


if __name__ == "__main__":
    unittest.main()
