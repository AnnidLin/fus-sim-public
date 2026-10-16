from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import run_pub2_pml16_tr_pair_20260811 as runner


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class Pml16TrPairRunnerTests(unittest.TestCase):
    def dependencies(self, root: Path) -> dict[str, Path]:
        paths = {key: root / f"{key}.json" for key in runner.DEFAULT_DEPENDENCIES}
        entry = {"cell_id": runner.CELL_ID, "method": runner.METHOD, "changed_factor": "pml_size", "configuration": {"dx_mm": 0.75, "pml_size": 16, "cfl": 0.2}, "command": ["python.exe", "simulate_time_reversal_focus.py", "--stage", "refocus", "--output-dir", "old", "--pml-size", "16", "--cfl", "0.2", "--dry-run-quality"]}
        write_json(paths["evidence"], {"pml16_tr_matched_pair_completion_amendment_20260811": {"status": "authorized_pending_runner_test_and_exact_dry_run"}})
        write_json(paths["matrix_plan"], {"entries": [entry]})
        write_json(paths["matrix_report"], {"status": "passed", "results": [{"cell_id": runner.CELL_ID, "method": runner.METHOD, "status": "passed", "simulation_quality": {"grid_size": [137, 98, 101], "pml_size": 16, "cfl": 0.2, "nt": 1867}, "source": {"source_points": 4971, "source_label_counts": {"0": 4971}}}], "matched_pairs": [{"cell_id": runner.CELL_ID, "matched": True, "baseline_tr_drift": {}}]})
        write_json(paths["baseline_validation"], {"status": "passed"})
        return paths

    def test_stage_commands_are_exact_and_low_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.dependencies(Path(temporary))
            plan = runner.load_json(paths["matrix_plan"])
            calibrate = runner.stage_command(plan, runner.STAGES[0], Path(temporary) / "tr")
            refocus = runner.stage_command(plan, runner.STAGES[1], Path(temporary) / "tr")
            self.assertEqual(calibrate[calibrate.index("--stage") + 1], "calibrate")
            self.assertNotIn("--dry-run-quality", calibrate)
            self.assertIn("--no-record-target-waveform", refocus)

    def test_exact_dry_run_command_preserves_quality_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.dependencies(Path(temporary))
            command = runner.stage_command(runner.load_json(paths["matrix_plan"]), runner.STAGES[1], Path(temporary) / "tr", dry_run=True)
            self.assertIn("--dry-run-quality", command)
            self.assertIn("--no-record-target-waveform", command)

    def test_preflight_accepts_frozen_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = runner.preflight(root / "output", self.dependencies(root))
            self.assertEqual(result["status"], "passed")
            self.assertTrue(all(result["checks"].values()))

    def test_preflight_rejects_existing_calibration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output" / "tr"
            output.mkdir(parents=True)
            (output / "element_signals.npz").write_bytes(b"existing")
            result = runner.preflight(root / "output", self.dependencies(root))
            self.assertEqual(result["status"], "failed")
            self.assertFalse(result["checks"]["no_existing_core_outputs"])


if __name__ == "__main__":
    unittest.main()
