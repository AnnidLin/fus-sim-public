from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import validate_pub2_reference_package as module


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def write_history(path: Path, *, cores: float = 1.0) -> None:
    path.write_text(
        "\n".join(
            json.dumps(
                {
                    "equivalent_cores": value,
                    "working_set_gib": 2.0,
                    "system_free_memory_gib": 20.0,
                    "breach_reasons": [],
                }
            )
            for value in (None, cores)
        )
        + "\n",
        encoding="utf-8",
    )


class ValidatePub2ReferencePackageTests(unittest.TestCase):
    def test_recovery_paths_are_selected_for_refocus(self) -> None:
        root = Path("pair")
        chain = {"recovery_attempt_id": "recovery2"}
        self.assertEqual(
            module.completed_device_history_path(root, chain, "tr_refocus").name,
            "recovery2_device_history.jsonl",
        )
        self.assertEqual(
            module.completed_snapshot_path(root, chain, "tr_refocus").name,
            "recovery2",
        )

    def make_package(self, root: Path) -> tuple[Path, Path, Path]:
        chain = root / "chain"
        write_json(
            chain / "chain_status.json",
            {
                "status": "completed",
                "preflight": {"status": "passed"},
                "pressure_scope": list(module.EXPECTED_STAGES),
                "automatic_follow_on_sensitivity_cells_authorized": False,
                "stages": [
                    {"stage_id": stage, "status": "completed"}
                    for stage in module.EXPECTED_STAGES
                ],
            },
        )
        (chain / "baseline").mkdir(parents=True, exist_ok=True)
        (chain / "tr").mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            chain / "baseline" / "pressure_max_mpa.npz",
            pressure_max_mpa=np.ones((2, 2), dtype=np.float32),
        )
        np.savez_compressed(
            chain / "tr" / "element_signals.npz",
            signals=np.ones((2, 3), dtype=np.float32),
        )
        np.savez_compressed(
            chain / "tr" / "pressure_max_mpa.npz",
            pressure_max_mpa=np.ones((2, 2), dtype=np.float32),
        )
        for path in (
            chain / "baseline" / "summary.json",
            chain / "baseline" / "focus_metrics.json",
            chain / "tr" / "summary_calibrate.json",
            chain / "tr" / "summary.json",
            chain / "tr" / "focus_metrics.json",
        ):
            write_json(path, {})
        for stage in module.EXPECTED_STAGES:
            write_history(chain / f"{stage}_device_history.jsonl")
            snapshot = chain / "monitor_snapshots" / stage
            write_json(snapshot / "monitor_status.json", {"status": "completed"})
            write_json(snapshot / "monitor_attention.json", {})
            (snapshot / "monitor_history.jsonl").write_text(
                "{}\n", encoding="utf-8"
            )
            (snapshot / "monitored_stdout.txt").write_text(
                "ok", encoding="utf-8"
            )
            (snapshot / "monitored_stderr.txt").write_text(
                "ok", encoding="utf-8"
            )
        analysis = root / "analysis.json"
        feedback = root / "feedback.json"
        write_json(
            analysis,
            {
                "status": "passed",
                "decision": {
                    "fresh_reference_pair_valid": True,
                    "historical_pair_promoted": False,
                },
            },
        )
        write_json(
            feedback,
            {
                "pub2_reference_gate_complete": True,
                "pub2_numerical_sensitivity_complete": False,
                "paper_grade_convergence_claim_allowed": False,
                "clinical_safety_claim_allowed": False,
            },
        )
        return chain, analysis, feedback

    def test_core_array_validation_rejects_wrong_key_and_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wrong = root / "wrong.npz"
            zero = root / "zero.npz"
            np.savez_compressed(wrong, metadata=np.ones(2))
            np.savez_compressed(zero, pressure=np.zeros(2))
            self.assertFalse(
                module.validate_core_array(wrong, "pressure")["passed"]
            )
            self.assertFalse(
                module.validate_core_array(zero, "pressure")["passed"]
            )

    def test_device_history_enforces_absolute_resource_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "history.jsonl"
            write_history(path, cores=6.6)
            result = module.validate_device_history(path)
            self.assertFalse(result["passed"])
            self.assertFalse(
                result["checks"][
                    "maximum_equivalent_cores_at_or_below_6p5"
                ]
            )

    def test_recovered_refocus_accepts_raised_working_set_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "history.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "equivalent_cores": 1.0,
                        "working_set_gib": 12.5,
                        "system_free_memory_gib": 8.0,
                        "breach_reasons": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertFalse(module.validate_device_history(path)["passed"])
            raised = module.validate_device_history(
                path, maximum_working_set_gib=16.0
            )
            self.assertTrue(raised["passed"])
            self.assertEqual(raised["authorized_working_set_limit_gib"], 16.0)

    def test_complete_synthetic_package_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            inputs = self.make_package(Path(temporary))
            report = module.validate_package(*inputs)
            self.assertEqual(report["status"], "passed")
            self.assertFalse(
                report["decision"]["sensitivity_pressure_authorized"]
            )

    def test_missing_monitor_snapshot_fails_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            chain, analysis, feedback = self.make_package(Path(temporary))
            (
                chain
                / "monitor_snapshots"
                / "tr_refocus"
                / "monitored_stdout.txt"
            ).unlink()
            report = module.validate_package(chain, analysis, feedback)
            self.assertEqual(report["status"], "failed")
            self.assertFalse(report["checks"]["monitor_snapshots_passed"])


if __name__ == "__main__":
    unittest.main()
