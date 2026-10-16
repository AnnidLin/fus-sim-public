from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.io import savemat

import generate_itrusst_phase_a_figure as figure


class ItrusstPhaseAFigureTests(unittest.TestCase):
    def test_panel_difference_uses_official_peak_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = np.ones((141, 241), dtype=float) * 10.0
            candidate = reference.copy()
            candidate[70, 100] = 11.0
            reference_path = root / "reference.mat"
            candidate_path = root / "candidate.npz"
            comparison_path = root / "comparison.json"
            savemat(reference_path, {"p_amp": reference})
            np.savez_compressed(candidate_path, p_amp=candidate)
            comparison_path.write_text(
                json.dumps(
                    {
                        "benchmark": "BM4",
                        "metrics": {
                            "relative_l2_percent": 1.0,
                            "peak_difference_percent": 10.0,
                            "focal_position_difference_mm": 0.0,
                        },
                    }
                ),
                encoding="utf-8",
            )
            panel = figure.build_panel_data(
                "BM4",
                reference_path,
                candidate_path,
                comparison_path,
            )
        self.assertEqual(panel["pressure_scale_pa"], 10.0)
        self.assertAlmostEqual(panel["difference_percent"][70, 100], 10.0)
        self.assertAlmostEqual(panel["difference_abs_max_percent"], 10.0)

    def test_metadata_preserves_claim_boundary(self) -> None:
        panels = [
            {
                "benchmark": benchmark,
                "pressure_scale_pa": 1.0,
                "difference_abs_max_percent": 1.0,
                "metrics": {},
                "hashes": {},
                "paths": {},
            }
            for benchmark in ("BM1", "BM3", "BM4")
        ]
        metadata = figure.metadata_for_panels(panels)
        self.assertEqual(metadata["panel_order"], ["BM1", "BM3", "BM4"])
        self.assertIn("not paper-grade", metadata["claim_boundary"])


if __name__ == "__main__":
    unittest.main()
