from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import run_pub2_pml16_baseline_20260810 as runner


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class Pml16BaselineRunnerTests(unittest.TestCase):
    def dependencies(self, root: Path) -> dict[str, Path]:
        paths = {
            "completion": root / "completion.json",
            "analysis": root / "analysis.json",
            "feedback": root / "feedback.json",
            "matrix_plan": root / "matrix_plan.json",
            "matrix_report": root / "matrix_report.json",
        }
        entry = {
            "cell_id": runner.CELL_ID,
            "method": runner.METHOD,
            "changed_factor": "pml_size",
            "configuration": {"dx_mm": 0.75, "pml_size": 16, "cfl": 0.2},
            "command": [
                "python.exe", "simulate_kwave_3d_focus.py", "--output-dir",
                "old", "--pml-size", "16", "--cfl", "0.2",
                "--dry-run-quality",
            ],
        }
        write_json(paths["completion"], {"status": "completed"})
        write_json(paths["analysis"], {"status": "passed"})
        write_json(paths["feedback"], {
            "status": "reference_pair_complete_sensitivity_pressure_still_blocked"
        })
        write_json(paths["matrix_plan"], {"status": "planned_not_executed", "entries": [entry]})
        write_json(paths["matrix_report"], {
            "status": "passed",
            "results": [{
                "cell_id": runner.CELL_ID,
                "method": runner.METHOD,
                "status": "passed",
                "checks": {"source_background_only": True},
                "simulation_quality": {
                    "grid_size": [137, 98, 101], "pml_size": 16,
                    "cfl": 0.2, "nt": 1867,
                },
                "source": {"source_points": 4971, "source_label_counts": {"0": 4971}},
            }],
        })
        return paths

    def test_build_command_uses_frozen_entry_without_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.dependencies(Path(temporary))
            plan = runner.load_json(paths["matrix_plan"])
            output = Path(temporary) / "output"
            command = runner.build_child_command(plan, output)
            self.assertNotIn("--dry-run-quality", command)
            self.assertEqual(command[command.index("--output-dir") + 1], str(output.resolve()))
            self.assertEqual(command[command.index("--pml-size") + 1], "16")

    def test_preflight_accepts_exact_single_cell(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = runner.preflight(root / "output", self.dependencies(root))
            self.assertEqual(result["status"], "passed")
            self.assertTrue(all(result["checks"].values()))

    def test_preflight_rejects_existing_pressure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            output.mkdir()
            (output / "pressure_max_mpa.npz").write_bytes(b"existing")
            result = runner.preflight(output, self.dependencies(root))
            self.assertEqual(result["status"], "failed")
            self.assertFalse(result["checks"]["no_existing_core_outputs"])


if __name__ == "__main__":
    unittest.main()
