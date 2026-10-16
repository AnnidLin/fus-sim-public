from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import run_itrusst_phase_a_case as chain


class ItrusstPhaseACaseChainTests(unittest.TestCase):
    def test_bm4_plan_has_frozen_gate_order_and_device_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary) / "bm4"
            plan = chain.build_plan("BM4", output_root, 600.0)
        self.assertEqual(
            [stage["name"] for stage in plan["stages"]],
            [
                "nominal_dry_run",
                "smoke",
                "smoke_validation",
                "nominal",
                "official_comparison",
            ],
        )
        self.assertEqual(plan["device_policy"]["omp_threads"], 6)
        self.assertEqual(plan["device_policy"]["priority"], "below_normal")
        rendered = [
            " ".join(stage["command"])
            for stage in plan["stages"]
        ]
        self.assertIn("--dry-run-quality", rendered[0])
        self.assertIn("--omp-threads 6", rendered[0])
        self.assertIn("-m monitor_kwave_process", rendered[1])
        self.assertIn("analyze_itrusst_benchmark.py validate", rendered[2])
        self.assertIn("-m monitor_kwave_process", rendered[3])
        self.assertIn("analyze_itrusst_benchmark.py compare", rendered[4])
        self.assertIn("--benchmark BM4", rendered[0])
        self.assertIn("--benchmark BM4", rendered[1])
        self.assertIn("--benchmark 4", rendered[2])
        self.assertIn("--benchmark BM4", rendered[3])

    def test_monitored_stage_is_limited_to_remaining_chain_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary) / "bm4"
            plan = chain.build_plan("BM4", output_root, 600.0)
        command = plan["stages"][1]["command"]
        constrained = chain.constrain_monitored_budget(command, 93.25)
        self.assertEqual(
            constrained[constrained.index("--maximum-ceiling-min") + 1],
            "93.250",
        )
        self.assertEqual(
            constrained[constrained.index("--emergency-ceiling-min") + 1],
            "93.250",
        )

    def test_plan_refuses_existing_controlled_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary) / "bm4"
            plan = chain.build_plan("BM4", output_root, 600.0)
            dry_run = output_root / "dry_run"
            dry_run.mkdir(parents=True)
            (dry_run / "dry_run_quality.json").write_text(
                "{}",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
                chain.ensure_new_outputs(plan)

    def test_reference_path_is_frozen_to_source_one_kwave(self) -> None:
        path = chain.reference_path("BM4")
        self.assertEqual(path.name, "PH1-BM4-SC1_KWAVE.mat")
        with self.assertRaisesRegex(ValueError, "unsupported"):
            chain.reference_path("BM7")


if __name__ == "__main__":
    unittest.main()
