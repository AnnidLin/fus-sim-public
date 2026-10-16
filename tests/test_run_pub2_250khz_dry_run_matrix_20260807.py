from __future__ import annotations

import unittest

import run_pub2_250khz_dry_run_matrix as matrix


class Pub2DryRunMatrixTests(unittest.TestCase):
    def test_plan_contains_six_cells_and_twelve_dry_runs(self) -> None:
        plan = matrix.matrix_plan()
        self.assertEqual(plan["cell_count"], 6)
        self.assertEqual(plan["dry_run_count"], 12)
        self.assertFalse(plan["pressure_execution_authorized"])
        self.assertTrue(
            all(
                "--dry-run-quality" in item["command"]
                for item in plan["entries"]
            )
        )

    def test_each_nonreference_cell_changes_one_declared_factor(self) -> None:
        factors = [cell.changed_factor for cell in matrix.CELLS]
        self.assertEqual(
            factors,
            [
                "dx_mm",
                "reference",
                "dx_mm",
                "pml_size",
                "cfl",
                "domain_extent",
            ],
        )
        reference = matrix.CELLS[1]
        for cell in matrix.CELLS:
            changed = set()
            if cell.dx_mm != reference.dx_mm:
                changed.add("dx_mm")
            if cell.pml_size != reference.pml_size:
                changed.add("pml_size")
            if cell.cfl != reference.cfl:
                changed.add("cfl")
            if (
                cell.lateral_mm,
                cell.post_target_mm,
            ) != (
                reference.lateral_mm,
                reference.post_target_mm,
            ):
                changed.add("domain_extent")
            expected = set() if cell.changed_factor == "reference" else {
                cell.changed_factor
            }
            self.assertEqual(changed, expected, cell.cell_id)

    def test_pair_drift_reports_quality_and_source_mismatch(self) -> None:
        baseline = {
            "simulation_quality": {
                field: 1 for field in matrix.QUALITY_FIELDS
            },
            "source": {
                "source_points": 10,
                "source_label_counts": {"0": 10},
            },
        }
        tr = {
            "simulation_quality": {
                field: 1 for field in matrix.QUALITY_FIELDS
            },
            "source": {
                "source_points": 9,
                "source_label_counts": {"0": 9},
            },
        }
        tr["simulation_quality"]["cfl"] = 0.1
        drift = matrix.pair_drift(baseline, tr)
        self.assertEqual(set(drift), {"cfl", "source.source_points", "source.source_label_counts"})

    def test_tr_command_is_refocus_dry_run(self) -> None:
        command = matrix.command_for(
            matrix.CELLS[1],
            "tr",
            matrix.OUTPUT_ROOT / "probe",
        )
        self.assertIn("simulate_time_reversal_focus.py", command)
        self.assertEqual(command[command.index("--stage") + 1], "refocus")
        self.assertIn("--dry-run-quality", command)

    def test_markdown_keeps_pressure_blocked(self) -> None:
        result = {
            "cell_id": "dx0p75_reference",
            "method": "baseline",
            "simulation_quality": {
                "grid_size": [2, 3, 4],
                "voxel_count": 24,
                "nt": 10,
                "pml_size": 12,
                "cfl": 0.2,
            },
            "ppw_min_sound_speed": 8.0,
            "memory_estimate": {"estimated_mb": 1.25},
            "source": {"source_points": 5},
        }
        report = {
            "status": "passed",
            "results": [result],
            "matched_pairs": [
                {
                    "cell_id": "dx0p75_reference",
                    "matched": True,
                }
            ],
            "claim_boundary": "dry run only",
        }
        markdown = matrix.render_report_markdown(report)
        self.assertIn("Pressure execution authorized: **no**", markdown)
        self.assertIn("2x3x4", markdown)
        self.assertIn("dry run only", markdown)


if __name__ == "__main__":
    unittest.main()
