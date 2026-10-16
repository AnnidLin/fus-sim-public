from __future__ import annotations

import json
import unittest
from pathlib import Path

from run_second_skull_hotspot_calibration_20260722 import command, validate_dryrun


ROOT = Path(__file__).resolve().parents[1]


class SecondSkullHotspotCalibrationTests(unittest.TestCase):
    def test_command_freezes_new_hotspot(self) -> None:
        cmd = command(False)
        self.assertEqual(cmd[cmd.index("--stage") + 1], "calibrate")
        self.assertEqual(cmd[cmd.index("--calibration-point-index") + 1], "77,120,97")
        self.assertNotIn("--dry-run-quality", cmd)

    def test_dry_run_adds_only_quality_flag(self) -> None:
        self.assertEqual(command(True)[:-1], command(False))
        self.assertEqual(command(True)[-1], "--dry-run-quality")

    def test_validator_rejects_old_hotspot_fixture(self) -> None:
        path = ROOT / "outputs" / "dual_point_hotspot_constrained_tr_20260720" / "hotspot_calibration_dryrun" / "quality_dry_run_summary.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        checks = validate_dryrun(data)
        self.assertFalse(checks["hotspot_full_exact"])
        self.assertFalse(checks["hotspot_local_exact"])


if __name__ == "__main__":
    unittest.main()
