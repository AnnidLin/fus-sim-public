from __future__ import annotations

import json
import unittest
from pathlib import Path

from run_hotspot_calibration_20260721 import command, validate_dryrun


ROOT = Path(__file__).resolve().parents[1]
DRYRUN = ROOT / "outputs" / "dual_point_hotspot_constrained_tr_20260720" / "hotspot_calibration_dryrun" / "quality_dry_run_summary.json"


class HotspotCalibrationRunnerTests(unittest.TestCase):
    def test_command_is_exactly_calibrate_at_frozen_hotspot(self) -> None:
        cmd = command(False)
        self.assertEqual(cmd[cmd.index("--stage") + 1], "calibrate")
        self.assertEqual(cmd[cmd.index("--calibration-point-index") + 1], "75,139,113")
        self.assertEqual(cmd[cmd.index("--preset") + 1], "standard")
        self.assertIn("--no-record-target-waveform", cmd)
        self.assertNotIn("--dry-run-quality", cmd)

    def test_dry_run_command_adds_only_quality_flag(self) -> None:
        real = command(False)
        dry = command(True)
        self.assertEqual(dry[:-1], real)
        self.assertEqual(dry[-1], "--dry-run-quality")

    def test_existing_frozen_dryrun_passes_all_gates(self) -> None:
        checks = validate_dryrun(json.loads(DRYRUN.read_text(encoding="utf-8")))
        self.assertEqual(len(checks), 17)
        self.assertTrue(all(checks.values()), checks)

    def test_modified_hotspot_fails_gate(self) -> None:
        data = json.loads(DRYRUN.read_text(encoding="utf-8"))
        data["source"]["calibration_point"]["full_index_ijk"] = [75, 139, 114]
        checks = validate_dryrun(data)
        self.assertFalse(checks["hotspot_full_exact"])


if __name__ == "__main__":
    unittest.main()
