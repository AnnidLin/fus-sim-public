from __future__ import annotations

import json
import unittest
from pathlib import Path

from run_dual_point_constrained_refocus_20260721 import command, validate_dryrun


ROOT = Path(__file__).resolve().parents[1]


class DualPointConstrainedRefocusRunnerTests(unittest.TestCase):
    def test_command_is_frozen_refocus(self) -> None:
        cmd = command(False)
        self.assertEqual(cmd[cmd.index("--stage") + 1], "refocus")
        self.assertEqual(cmd[cmd.index("--source-pressure-pa") + 1], "1000000")
        self.assertIn("--normalize", cmd)
        self.assertNotIn("--calibration-point-index", cmd)

    def test_dry_run_adds_only_quality_flag(self) -> None:
        self.assertEqual(command(True)[:-1], command(False))
        self.assertEqual(command(True)[-1], "--dry-run-quality")

    def test_validator_rejects_missing_signals(self) -> None:
        fixture_path = ROOT / "outputs" / "dual_point_hotspot_constrained_tr_20260720" / "hotspot_calibration_dryrun" / "quality_dry_run_summary.json"
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        data["config"]["stage"] = "refocus"
        data["config"]["element_signals_available"] = False
        data["config"]["nt_recorded"] = None
        data["source"]["time_reversal"] = {"mask_check": "not_checked_dry_run", "normalize_source": True, "source_pressure_pa": 1000000.0}
        checks = validate_dryrun(data)
        self.assertFalse(checks["element_signals_available"])
        self.assertFalse(checks["nt_recorded_exact"])
        self.assertFalse(checks["mask_grid_dt_target_exact"])


if __name__ == "__main__":
    unittest.main()
