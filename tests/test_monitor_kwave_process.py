from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from monitor_kwave_process import (
    adjust_emergency_ceiling,
    expected_output_exists,
    parse_kwave_progress,
    stage_from_command,
    supervise,
)


class MonitorKwaveProcessTests(unittest.TestCase):
    def test_itrusst_stage_uses_harmonic_outputs(self) -> None:
        command = ["python", "simulate_itrusst_bm1.py", "--stage", "itrusst_bm1"]
        self.assertEqual(stage_from_command(command), "itrusst_bm1")
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp)
            (output_dir / "p_amp.npz").write_bytes(b"ok")
            (output_dir / "summary.json").write_text("{}", encoding="utf-8")
            outputs = expected_output_exists(output_dir, "itrusst_bm1")
            self.assertTrue(all(outputs.values()))

    def test_parses_latest_tqdm_progress(self) -> None:
        text = (
            "k-Wave:  50%|x| 941/1883 [0:40:00<40:10, 2.56s/step]\n"
            "k-Wave:  99%|x| 1855/1883 [1:20:19<01:11, 2.55s/step]\n"
        )
        progress = parse_kwave_progress(text)
        self.assertIsNotNone(progress)
        assert progress is not None
        self.assertEqual(progress["current_step"], 1855)
        self.assertEqual(progress["total_steps"], 1883)
        self.assertAlmostEqual(progress["fraction"], 1855 / 1883)
        self.assertEqual(progress["elapsed_s"], 4819.0)
        self.assertEqual(progress["remaining_s"], 71.0)

    def test_progress_is_scoped_to_latest_appended_monitor_run(self) -> None:
        text = (
            "[MONITOR START old]\n"
            "k-Wave: 82/1883 [03:15<1:07:39, 2.25s/step]\n"
            "[MONITOR START recovery2]\n"
            "k-Wave: 21/1883 [02:02<2:59:40, 5.79s/step]\n"
        )
        progress = parse_kwave_progress(text)
        self.assertIsNotNone(progress)
        assert progress is not None
        self.assertEqual(progress["current_step"], 21)
        self.assertEqual(progress["total_steps"], 1883)

    def test_parses_latest_omp_table_progress(self) -> None:
        text = (
            "|     5%   |       14.579s  |    274.999s  |  07/08/26 00:03:04 |\n"
            "|    10%   |       32.274s  |    289.351s  |  07/08/26 00:03:36 |\n"
        )
        progress = parse_kwave_progress(text)
        self.assertIsNotNone(progress)
        assert progress is not None
        self.assertEqual(progress["current_step"], 10)
        self.assertEqual(progress["total_steps"], 100)
        self.assertAlmostEqual(progress["fraction"], 0.10)
        self.assertAlmostEqual(progress["elapsed_s"], 32.274)
        self.assertAlmostEqual(progress["remaining_s"], 289.351)
        self.assertEqual(progress["format"], "omp_percent_table")

    def test_active_progress_extends_tight_emergency_ceiling(self) -> None:
        result = adjust_emergency_ceiling(
            current_ceiling_s=7200,
            elapsed_s=6900,
            remaining_s=900,
            progress_is_advancing=True,
            maximum_ceiling_s=18000,
        )
        self.assertGreater(result, 7200)
        self.assertGreaterEqual(result, int((6900 + 900) * 1.25))

    def test_stable_budget_is_not_extended(self) -> None:
        self.assertEqual(
            adjust_emergency_ceiling(
                current_ceiling_s=9000,
                elapsed_s=3000,
                remaining_s=1200,
                progress_is_advancing=True,
                maximum_ceiling_s=18000,
            ),
            9000,
        )

    def test_supervisor_records_heartbeat_and_complete_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp)
            child_code = (
                "import pathlib,sys,time;"
                "p=pathlib.Path(sys.argv[1]);"
                "[(sys.stderr.write(f'k-Wave: {i}/4 [00:0{i}<00:0{4-i}, 1.00s/step]\\n'),"
                "sys.stderr.flush(),time.sleep(0.03)) for i in range(1,5)];"
                "(p/'pressure_max_mpa.npz').write_bytes(b'ok');"
                "(p/'summary.json').write_text('{}',encoding='utf-8');"
                "(p/'focus_metrics.json').write_text('{}',encoding='utf-8')"
            )
            result = supervise(
                command=[sys.executable, "-c", child_code, str(output_dir)],
                output_dir=output_dir,
                checkpoint_sec=0.02,
                poll_sec=0.01,
                stall_stop_sec=1.0,
                emergency_ceiling_sec=5.0,
                maximum_ceiling_sec=10.0,
            )
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["stage"], "auto")
            self.assertTrue(all(result["expected_output_exists"].values()))
            persisted = json.loads(
                (output_dir / "monitor_status.json").read_text(encoding="utf-8")
            )
            self.assertEqual(persisted["status"], "completed")
            self.assertGreaterEqual(persisted["heartbeat_count"], 1)
            self.assertTrue((output_dir / "monitor_history.jsonl").is_file())

    def test_supervisor_parses_omp_progress_from_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp)
            child_code = (
                "import pathlib,sys,time;"
                "p=pathlib.Path(sys.argv[1]);"
                "print('|    35%   |       12.500s  |     23.200s  |  now |',flush=True);"
                "time.sleep(0.04);"
                "(p/'pressure_max_mpa.npz').write_bytes(b'ok');"
                "(p/'summary.json').write_text('{}',encoding='utf-8');"
                "(p/'focus_metrics.json').write_text('{}',encoding='utf-8')"
            )
            result = supervise(
                command=[sys.executable, "-c", child_code, str(output_dir)],
                output_dir=output_dir,
                checkpoint_sec=0.01,
                poll_sec=0.01,
                stall_stop_sec=1.0,
                emergency_ceiling_sec=5.0,
                maximum_ceiling_sec=10.0,
            )
            self.assertIsNotNone(result["progress"])
            self.assertEqual(result["progress"]["format"], "omp_percent_table")
            self.assertEqual(result["progress"]["current_step"], 35)


if __name__ == "__main__":
    unittest.main()
