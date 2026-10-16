from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

import run_pub2_250khz_reference_pair as pair


class Pub2ReferencePairRunnerTests(unittest.TestCase):
    def test_plan_freezes_three_stages_and_no_follow_on_cells(self) -> None:
        value = pair.plan(pair.DEFAULT_OUTPUT_ROOT, 525.0)
        self.assertEqual(
            [item["stage_id"] for item in value["stages"]],
            ["baseline", "tr_calibrate", "tr_refocus"],
        )
        self.assertEqual(
            value["pressure_execution_authorized"],
            ["baseline", "tr_calibrate", "tr_refocus"],
        )
        self.assertFalse(
            value[
                "automatic_follow_on_sensitivity_cells_authorized"
            ]
        )
        self.assertTrue(
            all(
                "--dry-run-quality" not in item["command"]
                for item in value["stages"]
            )
        )

    def test_tr_commands_have_ordered_stages(self) -> None:
        calibrate = pair.child_command(
            pair.STAGES[1], Path("out")
        )
        refocus = pair.child_command(pair.STAGES[2], Path("out"))
        self.assertEqual(
            calibrate[calibrate.index("--stage") + 1], "calibrate"
        )
        self.assertEqual(
            refocus[refocus.index("--stage") + 1], "refocus"
        )

    def test_numeric_npz_validation_rejects_zero_and_nonfinite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = root / "valid.npz"
            zero = root / "zero.npz"
            invalid = root / "invalid.npz"
            misleading = root / "misleading.npz"
            np.savez_compressed(valid, value=np.array([0.0, 1.0]))
            np.savez_compressed(zero, value=np.array([0.0, 0.0]))
            np.savez_compressed(
                invalid, value=np.array([1.0, np.nan])
            )
            np.savez_compressed(
                misleading,
                pressure_max_mpa=np.zeros(2),
                labels=np.ones(2),
            )
            self.assertTrue(pair.numeric_npz_is_finite_nonzero(valid))
            self.assertFalse(pair.numeric_npz_is_finite_nonzero(zero))
            self.assertFalse(pair.numeric_npz_is_finite_nonzero(invalid))
            self.assertFalse(
                pair.numeric_npz_is_finite_nonzero(
                    misleading,
                    required_nonzero_array="pressure_max_mpa",
                )
            )
            self.assertFalse(
                pair.numeric_npz_is_finite_nonzero(
                    valid,
                    required_nonzero_array="missing",
                )
            )

    def test_stage_validation_checks_core_npz_array(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            np.savez_compressed(
                root / "pressure_max_mpa.npz",
                pressure_max_mpa=np.zeros(2),
                labels=np.ones(2),
            )
            (root / "summary.json").write_text("{}", encoding="utf-8")
            (root / "focus_metrics.json").write_text("{}", encoding="utf-8")
            result = pair.validate_stage_outputs(pair.STAGES[0], root)
            self.assertEqual(result["status"], "failed")
            self.assertFalse(
                result["checks"]["pressure_max_mpa.npz.finite_nonzero"]
            )


if __name__ == "__main__":
    unittest.main()
