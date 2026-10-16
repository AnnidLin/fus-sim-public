from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import run_pub2_sensitivity_cell as runner


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def fake_deps(root: Path, cell_id: str, method: str, dx: float, pml: int, cfl: float,
              grid: list[int], nt: int, src_pts: int) -> dict[str, Path]:
    paths = {
        "completion": root / "completion.json",
        "matrix_plan": root / "matrix_plan.json",
        "matrix_report": root / "matrix_report.json",
    }
    entry = {
        "cell_id": cell_id, "method": method, "changed_factor": "dx_mm",
        "configuration": {"dx_mm": dx, "pml_size": pml, "cfl": cfl},
        "command": [
            "python.exe", "simulate_kwave_3d_focus.py", "--output-dir", "old",
            "--pml-size", str(pml), "--cfl", str(cfl), "--dry-run-quality",
        ],
    }
    write_json(paths["completion"], {"status": "completed"})
    write_json(paths["matrix_plan"], {"status": "planned_not_executed", "entries": [entry]})
    write_json(paths["matrix_report"], {
        "status": "passed",
        "results": [{
            "cell_id": cell_id, "method": method, "status": "passed",
            "simulation_quality": {"grid_size": grid, "nt": nt, "pml_size": pml, "cfl": cfl},
            "source": {"source_points": src_pts, "source_label_counts": {"0": src_pts}},
        }],
        "matched_pairs": [{"cell_id": cell_id, "matched": True, "baseline_tr_drift": False}],
    })
    return paths


class SensitivityCellRunnerTests(unittest.TestCase):
    def test_cell_table_has_three_remaining_cells(self) -> None:
        self.assertEqual(set(runner._CELLS), {
            "dx0p5_grid", "dx0p75_cfl0p1", "dx0p75_domain_lat34_post20",
        })

    def test_stages_for_baseline_and_tr(self) -> None:
        self.assertEqual([s.stage_id for s in runner.stages_for("baseline")], ["baseline"])
        self.assertEqual([s.stage_id for s in runner.stages_for("tr")], ["tr_calibrate", "tr_refocus"])

    def test_child_command_tr_rewrites_stage_and_adds_no_record(self) -> None:
        cell = runner.cell_for("dx0p75_cfl0p1")
        entry = {
            "cell_id": "dx0p75_cfl0p1", "method": "tr", "changed_factor": "cfl",
            "configuration": {"dx_mm": 0.75, "pml_size": 12, "cfl": 0.1},
            "command": ["python.exe", "simulate_time_reversal_focus.py", "--stage", "auto",
                        "--output-dir", "old", "--dry-run-quality"],
        }
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "tr"
            cmd = runner.child_command(cell, "tr", runner.stages_for("tr")[1], out, dry_run=False, entry=entry)
            self.assertNotIn("--dry-run-quality", cmd)
            self.assertEqual(cmd[cmd.index("--stage") + 1], "refocus")
            self.assertIn("--no-record-target-waveform", cmd)
            self.assertEqual(cmd[cmd.index("--output-dir") + 1], str(out.resolve()))

    def test_preflight_passes_exact_cell(self) -> None:
        cell = runner.cell_for("dx0p5_grid")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deps = fake_deps(root, "dx0p5_grid", "baseline", 0.5, 12, 0.2, [192, 146, 151], 2800, 11094)
            result = runner.preflight(cell, "baseline", deps=deps, output_dir=root / "out")
            self.assertEqual(result["status"], "passed")
            self.assertTrue(all(result["checks"].values()))

    def test_preflight_rejects_existing_output(self) -> None:
        cell = runner.cell_for("dx0p75_domain_lat34_post20")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deps = fake_deps(root, "dx0p75_domain_lat34_post20", "baseline", 0.75, 12, 0.2, [139, 108, 111], 1867, 4971)
            out = root / "out"
            out.mkdir()
            (out / "pressure_max_mpa.npz").write_bytes(b"existing")
            result = runner.preflight(cell, "baseline", deps=deps, output_dir=out)
            self.assertEqual(result["status"], "failed")
            self.assertFalse(result["checks"]["no_existing_core_outputs"])


if __name__ == "__main__":
    unittest.main()
