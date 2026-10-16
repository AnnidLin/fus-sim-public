from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import generate_itrusst_phase_a_summary as phase_a


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


class ItrusstPhaseASummaryTests(unittest.TestCase):
    def make_case(self, root: Path, benchmark: str, offset: float) -> Path:
        case = root / benchmark.lower()
        case.mkdir()
        write_json(
            case / "comparison.json",
            {
                "benchmark": benchmark,
                "metrics": {
                    "relative_l2_percent": 1.0 + offset,
                    "relative_linf_percent": 2.0 + offset,
                    "peak_difference_percent": 3.0 + offset,
                    "focal_position_difference_mm": 0.5 + offset,
                    "reference_peak": 100.0,
                    "candidate_peak": 99.0,
                    "reference_peak_index": [2, 3],
                    "candidate_peak_index": [2, 4],
                    "reference_widths": {},
                    "candidate_widths_at_reference_peak": {},
                },
            },
        )
        write_json(
            case / "summary.json",
            {
                "benchmark": benchmark,
                "runtime_s": 10.0 + offset,
                "config": {
                    "coordinate_system": "axisymmetric",
                    "dx_mm": 0.25,
                    "comparison_dx_mm": 0.5,
                },
                "derived": {
                    "ppw": 12.0,
                    "points_per_period": 144,
                    "nt": 8640,
                    "omp_threads": 6,
                },
            },
        )
        write_json(case / "monitor_status.json", {"status": "completed", "elapsed_s": 12.0})
        np.savez_compressed(case / "p_amp.npz", p_amp=np.ones((2, 2)))
        return case

    def test_builds_three_case_summary_without_post_hoc_pass_line(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cases = {
                benchmark: self.make_case(root, benchmark, index)
                for index, benchmark in enumerate(("BM1", "BM3", "BM4"))
            }
            report = phase_a.build_summary(cases)
        self.assertEqual(report["status"], "complete")
        self.assertEqual(
            [case["benchmark"] for case in report["cases"]],
            ["BM1", "BM3", "BM4"],
        )
        policy = report["interpretation_policy"]
        self.assertIsNone(policy["pre_registered_project_pass_threshold"])
        self.assertTrue(policy["cross_model_statistics_are_context_only"])

    def test_package_contains_json_csv_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cases = {
                benchmark: self.make_case(root, benchmark, index)
                for index, benchmark in enumerate(("BM1", "BM3", "BM4"))
            }
            report = phase_a.build_summary(cases)
            paths = phase_a.write_package(report, root / "package")
            for path in paths.values():
                self.assertTrue(Path(path).is_file())
            markdown = Path(paths["markdown"]).read_text(encoding="utf-8")
            self.assertIn("BM4", markdown)
            self.assertIn("not a post hoc project pass line", markdown)


if __name__ == "__main__":
    unittest.main()
