from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from analyze_h3_large_matched_baseline_tr_20260730 import (
    build_report,
    report_markdown,
)


class MatchedBaselineTrReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.baseline_dir = self.root / "baseline"
        self.tr_dir = self.root / "tr"
        self.baseline_dir.mkdir()
        self.tr_dir.mkdir()

        model = self.root / "model.npz"
        entry = self.root / "entry.json"
        model.write_bytes(b"model")
        entry.write_text("{}", encoding="utf-8")

        config = {
            "model_path": "model.npz",
            "entry_plan_path": "entry.json",
            "frequency_hz": 250000.0,
            "source_pressure_pa": 1000000.0,
            "transducer_radius_m": 0.074435,
            "aperture_diameter_m": 0.06,
            "tone_burst_cycles": 2,
            "cfl": 0.2,
            "simulation_time_s": 0.0001,
            "pml_size": 12,
            "preset": "quick",
            "backend": "python",
            "device": "cpu",
            "quick_lateral_half_width_m": 0.017,
            "quick_post_target_margin_m": 0.008,
            "alpha_power": 1.5,
            "nearfield_exclusion_m": 0.01,
            "allow_entry_plan_resolution_mismatch": False,
        }
        model_metadata = {
            "model_shape": [123, 64, 67],
            "crop_origin_ijk": [39, 113, 62],
            "target_index_ijk": [112, 23, 43],
        }
        source = {"source_points": 3709, "source_label_counts": {"0": 3709}}
        baseline = {
            "config": config,
            **model_metadata,
            "source": source,
            "pressure": {
                "global_peak_mpa": 4.0,
                "target_window_peak_mpa": 1.0,
                "target_to_global_peak_ratio": 0.25,
                "global_peak_to_target_distance_mm": 56.0,
            },
        }
        calibration = {
            "config": dict(config),
            "model": model_metadata,
            "source": source,
        }
        refocus = {
            "config": dict(config),
            "model": model_metadata,
            "source": source,
            "pressure": {
                "global_peak_mpa": 2.0,
                "target_window_peak_mpa": 1.8,
                "target_to_global_peak_ratio": 0.9,
                "global_peak_to_target_distance_mm": 5.0,
            },
        }
        self._write_json(self.baseline_dir / "summary.json", baseline)
        self._write_json(self.tr_dir / "summary_calibrate.json", calibration)
        self._write_json(self.tr_dir / "summary.json", refocus)
        for path in (
            self.baseline_dir / "pressure_max_mpa.npz",
            self.baseline_dir / "focus_metrics.json",
            self.tr_dir / "element_signals.npz",
            self.tr_dir / "pressure_max_mpa.npz",
            self.tr_dir / "focus_metrics.json",
        ):
            path.write_bytes(path.name.encode("utf-8"))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _write_json(path: Path, value: dict) -> None:
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_equivalent_complete_outputs_are_reused(self) -> None:
        report = build_report(self.root, self.baseline_dir, self.tr_dir)

        self.assertTrue(report["equivalence"]["valid"])
        self.assertTrue(report["artifacts"]["complete"])
        self.assertTrue(report["decision"]["reuse_historical_pressure"])
        self.assertFalse(report["decision"]["new_pressure_execution_required"])
        self.assertAlmostEqual(
            report["comparison"]["target_to_global_peak_ratio"]["factor"], 3.6
        )
        self.assertAlmostEqual(
            report["comparison"]["global_peak_to_target_distance_mm"][
                "reduction"
            ],
            51.0,
        )

    def test_config_drift_blocks_reuse(self) -> None:
        path = self.tr_dir / "summary.json"
        refocus = json.loads(path.read_text(encoding="utf-8"))
        refocus["config"]["cfl"] = 0.1
        self._write_json(path, refocus)

        report = build_report(self.root, self.baseline_dir, self.tr_dir)

        self.assertFalse(report["equivalence"]["valid"])
        self.assertFalse(report["decision"]["reuse_historical_pressure"])
        self.assertTrue(report["decision"]["new_pressure_execution_required"])
        self.assertIn("config.cfl", report["equivalence"]["drift"])

    def test_full_bowl_expectations_and_normalize_are_enforced(self) -> None:
        for name in ("summary_calibrate.json", "summary.json"):
            path = self.tr_dir / name
            summary = json.loads(path.read_text(encoding="utf-8"))
            summary["config"]["normalize_source"] = False
            summary["config"]["calibration_pressure_pa"] = 1000000.0
            self._write_json(path, summary)

        report = build_report(
            self.root,
            self.baseline_dir,
            self.tr_dir,
            expected_model_shape=[133, 98, 101],
            expected_source_points=4971,
            require_tr_normalize=True,
        )

        self.assertFalse(report["equivalence"]["valid"])
        self.assertIn(
            "tr_config.normalize_source_required",
            report["equivalence"]["drift"],
        )
        self.assertIn("model.expected_shape", report["equivalence"]["drift"])
        self.assertIn("source.expected_points", report["equivalence"]["drift"])

    def test_fresh_execution_is_not_reported_as_historical_reuse(self) -> None:
        report = build_report(
            self.root,
            self.baseline_dir,
            self.tr_dir,
            historical_pressure_reuse=False,
        )

        self.assertTrue(report["equivalence"]["valid"])
        self.assertFalse(report["decision"]["reuse_historical_pressure"])
        self.assertFalse(report["decision"]["new_pressure_execution_required"])
        self.assertIn("fresh pressure execution", report["decision"]["reason"])

    def test_standard_intermediate_report_uses_matching_scope_text(self) -> None:
        report = build_report(
            self.root,
            self.baseline_dir,
            self.tr_dir,
            claim_level="matched_standard_intermediate_domain_engineering_evidence",
            historical_pressure_reuse=False,
        )

        markdown = report_markdown(report)

        self.assertIn("Matched standard intermediate-domain result", markdown)
        self.assertIn("full-bowl intermediate-domain", markdown)
        self.assertIn("fresh pressure execution", markdown)
        self.assertNotIn("Matched quick-preset result", markdown)


if __name__ == "__main__":
    unittest.main()
