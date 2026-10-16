from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import analyze_pub2_reference_pair as module


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def pressure_metrics(scale: float = 1.0) -> dict:
    return {
        "global_peak_mpa": 2.0 * scale,
        "global_peak_index_ijk": [1, 1, 1],
        "global_peak_to_target_distance_mm": 2.0,
        "target_pressure_mpa": 0.5 * scale,
        "target_window_peak_mpa": 1.0 * scale,
        "target_window_peak_index_ijk": [2, 2, 2],
        "target_to_global_peak_ratio": 0.25,
        "effective_peak_mpa": 1.5 * scale,
        "effective_peak_index_ijk": [2, 1, 1],
        "effective_peak_to_target_distance_mm": 1.0,
        "target_to_effective_peak_ratio": 1 / 3,
        "beam_axis_effective_peak_mpa": 1.25 * scale,
        "beam_axis_effective_peak_index_ijk": [2, 2, 1],
        "beam_axis_effective_peak_to_target_distance_mm": 0.75,
        "target_to_beam_axis_effective_peak_ratio": 0.4,
        "post_entry_peak_mpa": 1.75 * scale,
        "post_entry_peak_index_ijk": [1, 2, 1],
        "post_entry_peak_to_target_distance_mm": 1.5,
        "target_to_post_entry_peak_ratio": 2 / 7,
    }


def config() -> dict:
    return {key: index + 1 for index, key in enumerate(module.CONFIG_FIELDS)}


def write_field(path: Path, pressure: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    shape = pressure.shape
    np.savez_compressed(
        path,
        pressure_max_mpa=pressure.astype(np.float32),
        dx_m=np.asarray(0.001, dtype=np.float32),
        target_index_ijk=np.asarray([1, 1, 1], dtype=np.int32),
        crop_origin_ijk=np.asarray([0, 0, 0], dtype=np.int32),
        source_mask=np.zeros(shape, dtype=np.uint8),
        labels=np.ones(shape, dtype=np.uint8),
        nearfield_exclusion_m=np.asarray(0.001, dtype=np.float32),
        source_center_index_ijk=np.asarray([0, 1, 1], dtype=np.int32),
        beam_axis=np.asarray([1, 0, 0], dtype=np.int32),
        entry_index_ijk=np.asarray([1, 1, 1], dtype=np.int32),
    )


class AnalyzePub2ReferencePairTests(unittest.TestCase):
    def test_recovered_completion_status_is_preferred(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_json(root / "chain_status.json", {"status": "failed"})
            write_json(
                root / "reference_completion_status.json",
                {"status": "completed"},
            )
            self.assertEqual(
                module.resolved_chain_status_path(root).name,
                "reference_completion_status.json",
            )

    def test_compare_field_classifies_exact_and_material_difference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old = root / "old.npz"
            exact = root / "exact.npz"
            changed = root / "changed.npz"
            field = np.arange(27, dtype=np.float32).reshape(3, 3, 3)
            write_field(old, field)
            write_field(exact, field)
            write_field(changed, field * 1.1)
            exact_result = module.compare_field_npz(exact, old)
            changed_result = module.compare_field_npz(changed, old)
            self.assertEqual(
                exact_result["reproducibility_class"], "bitwise_exact"
            )
            self.assertTrue(exact_result["metadata_arrays_all_equal"])
            self.assertEqual(
                changed_result["reproducibility_class"],
                "material_difference_observed",
            )

    def test_validate_chain_requires_exact_completed_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_json(
                root / "chain_status.json",
                {
                    "status": "completed",
                    "preflight": {"status": "passed"},
                    "pressure_scope": [
                        "baseline",
                        "tr_calibrate",
                        "tr_refocus",
                    ],
                    "automatic_follow_on_sensitivity_cells_authorized": False,
                    "stages": [
                        {"stage_id": stage, "status": "completed"}
                        for stage in (
                            "baseline",
                            "tr_calibrate",
                            "tr_refocus",
                        )
                    ],
                },
            )
            self.assertTrue(module.validate_chain(root)["passed"])

    def test_build_report_separates_reproduction_and_method_contrast(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fresh = root / "fresh"
            historical = root / "historical"
            write_json(
                fresh / "chain_status.json",
                {
                    "status": "completed",
                    "preflight": {"status": "passed"},
                    "pressure_scope": [
                        "baseline",
                        "tr_calibrate",
                        "tr_refocus",
                    ],
                    "automatic_follow_on_sensitivity_cells_authorized": False,
                    "stages": [
                        {"stage_id": stage, "status": "completed"}
                        for stage in (
                            "baseline",
                            "tr_calibrate",
                            "tr_refocus",
                        )
                    ],
                },
            )
            field = np.arange(27, dtype=np.float32).reshape(3, 3, 3)
            for method, (fresh_subdir, old_subdir) in module.METHODS.items():
                scale = 2.0 if method == "time_reversal" else 1.0
                write_json(
                    fresh / fresh_subdir / "summary.json",
                    {"config": config(), "pressure": pressure_metrics(scale)},
                )
                write_json(
                    historical / old_subdir / "summary.json",
                    {"config": config(), "pressure": pressure_metrics(scale)},
                )
                write_field(
                    fresh / fresh_subdir / "pressure_max_mpa.npz", field * scale
                )
                write_field(
                    historical / old_subdir / "pressure_max_mpa.npz",
                    field * scale,
                )
            equivalence = root / "equivalence.json"
            family = root / "family.json"
            write_json(
                equivalence,
                {
                    "status": "passed",
                    "physical_arrays_equal": True,
                    "candidate_alpha_metadata_matches": True,
                },
            )
            write_json(
                family,
                {
                    "candidates": [
                        {
                            "candidate_id": "dx0p75",
                            "diagnostics": {
                                "passed": True,
                                "source_physical_error_mm": 0,
                                "target_physical_error_mm": 0,
                                "source_target_distance_delta_mm": 0,
                                "beam_angle_delta_deg": 0,
                            },
                        }
                    ]
                },
            )
            report = module.build_report(
                fresh, historical, equivalence, family
            )
            self.assertEqual(report["status"], "passed")
            self.assertFalse(report["decision"]["historical_pair_promoted"])
            self.assertFalse(
                report["decision"]["automatic_sensitivity_pressure_authorized"]
            )
            contrast = report["fresh_method_contrast"]["metrics"]
            self.assertEqual(
                contrast["target_to_global_peak_ratio"]["tr_over_baseline"],
                1.0,
            )

    def test_incomplete_chain_is_rejected_before_field_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_json(
                root / "chain_status.json",
                {
                    "status": "running",
                    "preflight": {"status": "passed"},
                    "pressure_scope": [
                        "baseline",
                        "tr_calibrate",
                        "tr_refocus",
                    ],
                    "automatic_follow_on_sensitivity_cells_authorized": False,
                    "stages": [],
                },
            )
            with self.assertRaisesRegex(ValueError, "incomplete"):
                module.build_report(
                    root,
                    root / "old",
                    root / "missing-equivalence.json",
                    root / "missing-family.json",
                )


if __name__ == "__main__":
    unittest.main()
