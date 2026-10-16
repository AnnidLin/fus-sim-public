from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import run_pub2_cfl0p1_baseline_20260812 as runner


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class CflBaselineRunnerTests(unittest.TestCase):
    def deps(self, root: Path) -> dict[str, Path]:
        paths = {key: root / f"{key}.json" for key in runner.DEPENDENCIES}
        entry = {"cell_id": runner.CELL_ID, "method": runner.METHOD, "configuration": {"dx_mm": 0.75, "pml_size": 12, "cfl": 0.1}, "command": ["python", "simulate_kwave_3d_focus.py", "--output-dir", "old", "--cfl", "0.1", "--dry-run-quality"]}
        write(paths["evidence"], {
            "cfl0p1_baseline_time_step_amendment_20260812": {"status": "authorized_pending_runner_test_and_exact_dry_run"},
            "cfl0p1_baseline_recovery1_amendment_20260812": {"status": "authorized_pending_runner_test_exact_dry_run_and_device_gate"},
        })
        write(paths["pml16_validation"], {"status": "passed"})
        write(paths["matrix_plan"], {"entries": [entry]})
        write(paths["matrix_report"], {"status": "passed", "results": [{"cell_id": runner.CELL_ID, "method": runner.METHOD, "status": "passed", "simulation_quality": {"grid_size": [133, 98, 101], "nt": 3734, "cfl": 0.1}, "source": {"source_points": 4971, "source_label_counts": {"0": 4971}}}]})
        return paths

    def test_command_and_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deps = self.deps(root)
            command = runner.child_command(runner.load(deps["matrix_plan"]), root / "output")
            self.assertNotIn("--dry-run-quality", command)
            self.assertEqual(command[command.index("--cfl") + 1], "0.1")
            self.assertEqual(runner.preflight(root / "output", deps)["status"], "passed")

    def test_preflight_rejects_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            output.mkdir()
            (output / "summary.json").write_text("{}", encoding="utf-8")
            self.assertEqual(runner.preflight(output, self.deps(root))["status"], "failed")

    def test_exact_dry_run_preflights_requested_recovery_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deps = self.deps(root)
            target = root / "recovery"
            self.assertEqual(runner.preflight(target, deps)["status"], "passed")


if __name__ == "__main__":
    unittest.main()
