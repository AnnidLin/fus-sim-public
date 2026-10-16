from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import run_pub2_refocus_only_recovery2 as recovery


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class RefocusOnlyRecoveryTests(unittest.TestCase):
    def make_root(self, root: Path) -> Path:
        output = root / "pair"
        write_json(output / "chain_status.json", {
            "status": "failed", "stop_reason": "Stage tr_refocus did not complete.",
            "preflight": {"status": "passed"},
            "pressure_scope": ["baseline", "tr_calibrate", "tr_refocus"],
            "automatic_follow_on_sensitivity_cells_authorized": False,
            "stages": [
                {"stage_id": "baseline", "status": "completed"},
                {"stage_id": "tr_calibrate", "status": "completed"},
                {"stage_id": "tr_refocus", "status": "failed", "stopped_reason": "process_tree_working_set"},
            ],
        })
        (output / "tr").mkdir(parents=True)
        np.savez_compressed(output / "tr" / "element_signals.npz", signals=np.ones((3, 4), dtype=np.float32))
        write_json(output / "tr" / "summary_calibrate.json", {})
        return output

    def test_calibration_validation_requires_finite_nonzero_2d_signals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "signals.npz"
            np.savez_compressed(path, signals=np.ones((2, 3), dtype=np.float32))
            self.assertTrue(recovery.validate_calibration(path)["passed"])
            np.savez_compressed(path, signals=np.zeros((2, 3), dtype=np.float32))
            self.assertFalse(recovery.validate_calibration(path)["passed"])

    def test_preflight_accepts_exact_failed_chain_without_final_field(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = self.make_root(Path(temporary))
            original = recovery.pair.preflight
            recovery.pair.preflight = lambda: {"status": "passed"}
            try:
                result = recovery.preflight(output, "attempt2")
            finally:
                recovery.pair.preflight = original
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["scope"], ["tr_refocus"])

    def test_preflight_rejects_existing_final_pressure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = self.make_root(Path(temporary))
            np.savez_compressed(output / "tr" / "pressure_max_mpa.npz", pressure_max_mpa=np.ones(2))
            original = recovery.pair.preflight
            recovery.pair.preflight = lambda: {"status": "passed"}
            try:
                result = recovery.preflight(output, "attempt2")
            finally:
                recovery.pair.preflight = original
            self.assertEqual(result["status"], "failed")
            self.assertFalse(result["checks"]["no_final_refocus_outputs"])

    def test_completion_status_preserves_original_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = self.make_root(Path(temporary))
            result = {"stage_id": "tr_refocus", "status": "completed", "output_validation": {"status": "passed"}}
            completion = recovery.build_completion_status(output, "attempt2", result, {"status": "passed"})
            self.assertEqual(completion["status"], "completed")
            self.assertEqual(completion["original_chain_terminal_status"], "failed")
            self.assertEqual(completion["stages"][-1], result)
            self.assertFalse(completion["automatic_follow_on_sensitivity_cells_authorized"])

    def test_recovery_command_disables_full_grid_target_waveform_recording(self) -> None:
        stage = recovery.refocus_stage()
        command = recovery.recovery_monitor_command(stage, Path("tr"))
        self.assertIn("--no-record-target-waveform", command)
        self.assertEqual(command.count("simulate_time_reversal_focus.py"), 1)


if __name__ == "__main__":
    unittest.main()
