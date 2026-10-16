from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import generate_pub2_reference_gap_feedback as module


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
                    "at_utc": f"sample-{index}",
                }
            )
            for index, value in enumerate((None, cores, cores + 0.1))
        )
        + "\n",
        encoding="utf-8",
    )


def analysis() -> dict:
    field = {
        "configuration": {"matched": True},
        "field_reproducibility": {
            "reproducibility_class": "bitwise_exact",
            "relative_l2": 0.0,
            "relative_linf": 0.0,
            "metadata_arrays_all_equal": True,
        },
    }
    return {
        "status": "passed",
        "decision": {
            "fresh_reference_pair_valid": True,
            "historical_pair_promoted": False,
            "automatic_sensitivity_pressure_authorized": False,
        },
        "same_method_historical_reproducibility": {
            "baseline": field,
            "time_reversal": field,
        },
        "fresh_method_contrast": {
            "metrics": {
                "target_to_global_peak_ratio": {
                    "baseline": 0.5,
                    "time_reversal": 0.9,
                    "difference": 0.4,
                    "tr_over_baseline": 1.8,
                }
            }
        },
    }


class GeneratePub2ReferenceGapFeedbackTests(unittest.TestCase):
    def test_recovery_device_history_is_selected_for_refocus(self) -> None:
        root = Path("pair")
        selected = module.device_history_path(
            root,
            {"recovery_attempt_id": "recovery2"},
            "tr_refocus",
        )
        self.assertEqual(selected.name, "recovery2_device_history.jsonl")

    def make_inputs(self, root: Path, *, chain_status: str = "completed"):
        chain_root = root / "chain"
        chain_root.mkdir()
        write_json(
            chain_root / "chain_status.json",
            {
                "status": chain_status,
                "preflight": {"status": "passed"},
                "automatic_follow_on_sensitivity_cells_authorized": False,
                "stages": [
                    {
                        "stage_id": stage,
                        "status": "completed",
                        "output_validation": {"status": "passed"},
                    }
                    for stage in module.EXPECTED_STAGES
                ],
            },
        )
        for stage in module.EXPECTED_STAGES:
            write_history(chain_root / f"{stage}_device_history.jsonl")
        analysis_path = root / "analysis.json"
        brief_path = root / "brief.json"
        write_json(analysis_path, analysis())
        write_json(
            brief_path,
            {
                "brief_id": (
                    "pub2_250khz_ct_numerical_sensitivity_20260807"
                )
            },
        )
        return chain_root, analysis_path, brief_path

    def test_history_summary_preserves_resource_extrema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "history.jsonl"
            write_history(path, cores=1.5)
            summary = module.summarize_device_history(path)
            self.assertEqual(summary["sample_count"], 3)
            self.assertAlmostEqual(summary["maximum_equivalent_cores"], 1.6)
            self.assertTrue(summary["passed"])

    def test_feedback_is_fail_closed_for_sensitivity_pressure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = self.make_inputs(root)
            feedback = module.build_feedback(*inputs)
            self.assertTrue(feedback["pub2_reference_gate_complete"])
            self.assertFalse(feedback["pub2_numerical_sensitivity_complete"])
            self.assertEqual(
                feedback["execution_performed"]["sensitivity_pressure_cells"],
                [],
            )
            self.assertFalse(
                feedback["paper_grade_convergence_claim_allowed"]
            )
            self.assertTrue(feedback["device_guard"]["all_stages_passed"])

    def test_running_chain_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = self.make_inputs(root, chain_status="running")
            with self.assertRaisesRegex(ValueError, "chain_completed"):
                module.build_feedback(*inputs)

    def test_device_breach_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            chain_root, analysis_path, brief_path = self.make_inputs(root)
            breach_path = chain_root / "baseline_device_history.jsonl"
            breach_path.write_text(
                json.dumps(
                    {
                        "equivalent_cores": 7.0,
                        "working_set_gib": 2.0,
                        "system_free_memory_gib": 20.0,
                        "breach_reasons": ["sustained_equivalent_cpu_cores"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "breach"):
                module.build_feedback(
                    chain_root, analysis_path, brief_path
                )


if __name__ == "__main__":
    unittest.main()
