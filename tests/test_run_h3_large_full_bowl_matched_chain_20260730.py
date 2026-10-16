from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from run_h3_large_full_bowl_matched_chain_20260730 import (
    STAGES,
    child_command,
    validate_dry_run_pair,
)


class FullBowlMatchedChainTests(unittest.TestCase):
    def test_stage_order_and_frozen_parameters(self) -> None:
        self.assertEqual([stage.name for stage in STAGES], ["baseline", "calibrate", "refocus"])

        for stage in STAGES:
            command = child_command(
                stage, Path(__file__).resolve().parents[1] / "outputs" / "test"
            )
            rendered = " ".join(command)
            self.assertIn("--preset standard", rendered)
            self.assertIn("--frequency-hz 250000", rendered)
            self.assertIn("--cycles 2", rendered)
            self.assertIn("--sim-time-us 100", rendered)
            self.assertIn("--pml-size 12", rendered)
            self.assertIn("--cfl 0.2", rendered)
            self.assertIn("--quick-lateral-mm 30", rendered)
            self.assertIn("--quick-post-target-mm 16", rendered)
            self.assertIn("--aperture-mm 60", rendered)
            self.assertIn("--radius-mm 74.435", rendered)
            self.assertNotIn("--full", command)

    def test_dry_run_pair_requires_full_background_bowl(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = root / "baseline.json"
            tr = root / "tr.json"
            value = {
                "dry_run_quality_only": True,
                "config": {"quick_mode": True},
                "source": {
                    "source_points": 4971,
                    "source_label_counts": {"0": 4971},
                },
                "simulation_quality": {
                    "preset": "standard",
                    "grid_size": [133, 98, 101],
                    "voxel_count": 1316434,
                    "nt": 1867,
                    "ppw_min_sound_speed": 8.0,
                    "pml_size": 12,
                    "cfl": 0.2,
                },
            }
            baseline.write_text(json.dumps(value), encoding="utf-8")
            tr.write_text(json.dumps(value), encoding="utf-8")

            result = validate_dry_run_pair(baseline, tr)
            self.assertEqual(result["source_points"], 4971)
            self.assertEqual(result["grid_size"], [133, 98, 101])

            drifted = json.loads(tr.read_text(encoding="utf-8"))
            drifted["source"]["source_points"] = 4970
            tr.write_text(json.dumps(drifted), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "dry-run drift"):
                validate_dry_run_pair(baseline, tr)


if __name__ == "__main__":
    unittest.main()
