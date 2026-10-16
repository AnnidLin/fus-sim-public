from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import audit_pub2_250khz_reuse as audit


def write_summary(
    directory: Path,
    *,
    pml: int = 12,
    alpha_status: str = "missing_alpha_semantics",
) -> Path:
    directory.mkdir(parents=True)
    summary = {
        "description": "Small 3D k-Wave pressure simulation",
        "config": {
            "frequency_hz": 250000,
            "preset": "standard",
            "model_path": "model.npz",
            "entry_plan_path": "entry.json",
            "pml_size": pml,
            "cfl": 0.2,
            "source_pressure_pa": 1_000_000,
            "transducer_radius_m": 0.074435,
            "aperture_diameter_m": 0.06,
            "tone_burst_cycles": 2,
            "quick_lateral_half_width_m": 0.03,
            "quick_post_target_margin_m": 0.016,
            "backend": "python",
            "device": "cpu",
        },
        "simulation_quality": {
            "dx_mm": 0.75,
            "grid_size": [10, 11, 12],
            "voxel_count": 1320,
        },
        "runtime": {"nt": 100, "dt_s": 1e-7},
        "alpha_semantics": {
            "alpha_semantics_status": alpha_status,
            "pressure_allowed_by_alpha_semantics": True,
        },
    }
    path = directory / "summary.json"
    path.write_text(json.dumps(summary), encoding="utf-8")
    (directory / "pressure_max_mpa.npz").write_bytes(b"field")
    (directory / "focus_metrics.json").write_text("{}", encoding="utf-8")
    return path


class Pub2250khzReuseAuditTests(unittest.TestCase):
    def test_missing_alpha_semantics_blocks_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = write_summary(Path(temporary) / "run")
            record = audit.extract_record(path)
        self.assertEqual(record["pub2_reuse_status"], "context_only_or_blocked")
        self.assertIn("missing_alpha_semantics", record["pub2_reuse_blockers"])

    def test_detects_exact_single_variable_pml_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            left = write_summary(root / "pml12", pml=12, alpha_status="resolved")
            right = write_summary(root / "pml16", pml=16, alpha_status="resolved")
            report = audit.build_report([left, right])
        self.assertEqual(len(report["single_variable_pairs"]), 1)
        pair = report["single_variable_pairs"][0]
        self.assertEqual(pair["changed_field"], "pml_size")
        self.assertTrue(pair["eligible"])
        self.assertFalse(report["decision"]["pressure_execution_authorized"])

    def test_discovery_filters_to_250khz(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected = write_summary(root / "run250")
            other = write_summary(root / "run500")
            value = json.loads(other.read_text(encoding="utf-8"))
            value["config"]["frequency_hz"] = 500000
            other.write_text(json.dumps(value), encoding="utf-8")
            paths = audit.discover_summaries(root)
        self.assertEqual(paths, [expected])


if __name__ == "__main__":
    unittest.main()
