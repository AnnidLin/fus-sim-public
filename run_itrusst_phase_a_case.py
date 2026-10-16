#!/usr/bin/env python3
"""Run one focused-bowl ITRUSST Phase-I case through all controlled gates."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REFERENCE_ROOT = (
    ROOT
    / "outputs"
    / "itrusst_benchmark_pub1_20260803"
    / "official_reference_subset"
    / "KWAVE"
)
SUPPORTED_BENCHMARKS = ("BM1", "BM3", "BM4")
CORE_OUTPUTS = ("p_amp.npz", "summary.json", "monitor_status.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def set_below_normal_priority() -> dict[str, Any]:
    report = {
        "requested": "below_normal",
        "platform": os.name,
        "applied": False,
    }
    if os.name != "nt":
        report["reason"] = "Windows priority class is not available"
        return report
    below_normal_priority_class = 0x00004000
    kernel32 = ctypes.windll.kernel32
    process = kernel32.GetCurrentProcess()
    applied = bool(kernel32.SetPriorityClass(process, below_normal_priority_class))
    report["applied"] = applied
    if not applied:
        report["reason"] = f"SetPriorityClass failed with {kernel32.GetLastError()}"
    return report


def reference_path(benchmark: str) -> Path:
    if benchmark not in SUPPORTED_BENCHMARKS:
        raise ValueError(f"unsupported benchmark: {benchmark}")
    return REFERENCE_ROOT / f"PH1-{benchmark}-SC1_KWAVE.mat"


def simulation_command(
    benchmark: str,
    preset: str,
    output_dir: Path,
    mode: str,
) -> list[str]:
    if preset not in {"smoke", "benchmark-nominal"}:
        raise ValueError(f"unsupported preset: {preset}")
    if mode not in {"dry-run-quality", "execute"}:
        raise ValueError(f"unsupported mode: {mode}")
    return [
        sys.executable,
        "simulate_itrusst_bm1.py",
        "--benchmark",
        benchmark,
        "--preset",
        preset,
        "--coordinate-system",
        "axisymmetric",
        "--omp-threads",
        "6",
        "--stage",
        "itrusst_bm1",
        f"--{mode}",
        "--output-dir",
        str(output_dir),
    ]


def monitored_command(
    child_command: list[str],
    output_dir: Path,
    maximum_minutes: float,
) -> list[str]:
    return [
        sys.executable,
        "-m",
        "monitor_kwave_process",
        "--output-dir",
        str(output_dir),
        "--checkpoint-sec",
        "120",
        "--poll-sec",
        "5",
        "--stall-stop-min",
        "20",
        "--emergency-ceiling-min",
        f"{min(240.0, maximum_minutes):.3f}",
        "--maximum-ceiling-min",
        f"{maximum_minutes:.3f}",
        "--",
        *child_command,
    ]


def validation_command(benchmark: str, output_dir: Path) -> list[str]:
    return [
        sys.executable,
        "analyze_itrusst_benchmark.py",
        "validate",
        "--candidate",
        str(output_dir / "p_amp.npz"),
        "--benchmark",
        benchmark.removeprefix("BM"),
        "--source",
        "1",
        "--claim-level",
        "workflow_smoke_only",
        "--output",
        str(output_dir / "smoke_validation.json"),
    ]


def comparison_command(benchmark: str, output_dir: Path) -> list[str]:
    return [
        sys.executable,
        "analyze_itrusst_benchmark.py",
        "compare",
        "--reference",
        str(reference_path(benchmark)),
        "--candidate",
        str(output_dir / "p_amp.npz"),
        "--benchmark",
        benchmark.removeprefix("BM"),
        "--source",
        "1",
        "--reference-model",
        "KWAVE_OFFICIAL_PPW60",
        "--candidate-model",
        "FUS_SIM_AXISYMMETRIC_PPW12",
        "--output",
        str(output_dir / "comparison.json"),
    ]


def build_plan(
    benchmark: str,
    output_root: Path,
    maximum_minutes: float,
) -> dict[str, Any]:
    dry_run_dir = output_root / "dry_run"
    smoke_dir = output_root / "smoke"
    nominal_dir = output_root / "nominal"
    return {
        "schema_version": "1.0",
        "benchmark": benchmark,
        "source": 1,
        "coordinate_system": "axisymmetric",
        "maximum_minutes": maximum_minutes,
        "device_policy": {
            "priority": "below_normal",
            "omp_threads": 6,
        },
        "stages": [
            {
                "name": "nominal_dry_run",
                "output_dir": str(dry_run_dir),
                "command": simulation_command(
                    benchmark,
                    "benchmark-nominal",
                    dry_run_dir,
                    "dry-run-quality",
                ),
                "required_outputs": ["dry_run_quality.json"],
            },
            {
                "name": "smoke",
                "output_dir": str(smoke_dir),
                "command": monitored_command(
                    simulation_command(
                        benchmark,
                        "smoke",
                        smoke_dir,
                        "execute",
                    ),
                    smoke_dir,
                    maximum_minutes,
                ),
                "required_outputs": list(CORE_OUTPUTS),
            },
            {
                "name": "smoke_validation",
                "output_dir": str(smoke_dir),
                "command": validation_command(benchmark, smoke_dir),
                "required_outputs": ["smoke_validation.json"],
            },
            {
                "name": "nominal",
                "output_dir": str(nominal_dir),
                "command": monitored_command(
                    simulation_command(
                        benchmark,
                        "benchmark-nominal",
                        nominal_dir,
                        "execute",
                    ),
                    nominal_dir,
                    maximum_minutes,
                ),
                "required_outputs": list(CORE_OUTPUTS),
            },
            {
                "name": "official_comparison",
                "output_dir": str(nominal_dir),
                "command": comparison_command(benchmark, nominal_dir),
                "required_outputs": ["comparison.json"],
            },
        ],
    }


def ensure_new_outputs(plan: dict[str, Any]) -> None:
    collisions: list[str] = []
    for stage in plan["stages"]:
        output_dir = Path(stage["output_dir"])
        for name in stage["required_outputs"]:
            path = output_dir / name
            if path.exists():
                collisions.append(str(path))
    if collisions:
        raise RuntimeError(
            "refusing to overwrite controlled outputs: " + ", ".join(collisions)
        )


def constrain_monitored_budget(
    command: list[str],
    remaining_minutes: float,
) -> list[str]:
    constrained = list(command)
    if "monitor_kwave_process" not in constrained:
        return constrained
    emergency_index = constrained.index("--emergency-ceiling-min") + 1
    maximum_index = constrained.index("--maximum-ceiling-min") + 1
    constrained[emergency_index] = f"{min(240.0, remaining_minutes):.3f}"
    constrained[maximum_index] = f"{remaining_minutes:.3f}"
    return constrained


def run_plan(plan: dict[str, Any], output_root: Path) -> int:
    ensure_new_outputs(plan)
    reference = reference_path(plan["benchmark"])
    if not reference.is_file():
        raise FileNotFoundError(f"official reference missing: {reference}")
    priority = set_below_normal_priority()
    started = time.monotonic()
    status: dict[str, Any] = {
        **plan,
        "status": "running",
        "started_at_utc": utc_now(),
        "priority": priority,
    }
    for stage in status["stages"]:
        stage["status"] = "pending"
        stage["return_code"] = None
    status_path = output_root / "chain_status.json"
    atomic_write_json(status_path, status)

    for stage in status["stages"]:
        elapsed_minutes = (time.monotonic() - started) / 60.0
        remaining_minutes = plan["maximum_minutes"] - elapsed_minutes
        if remaining_minutes <= 0:
            status["status"] = "budget_exhausted"
            status["failed_stage"] = stage["name"]
            atomic_write_json(status_path, status)
            return 2
        stage["command"] = constrain_monitored_budget(
            stage["command"],
            remaining_minutes,
        )
        stage["remaining_chain_budget_minutes_at_start"] = remaining_minutes
        stage["status"] = "running"
        stage["started_at_utc"] = utc_now()
        atomic_write_json(status_path, status)
        completed = subprocess.run(stage["command"], cwd=ROOT, check=False)
        stage["return_code"] = completed.returncode
        stage["finished_at_utc"] = utc_now()
        stage["required_outputs_complete"] = all(
            (Path(stage["output_dir"]) / name).is_file()
            for name in stage["required_outputs"]
        )
        stage["status"] = (
            "completed"
            if completed.returncode == 0 and stage["required_outputs_complete"]
            else "failed"
        )
        if stage["status"] != "completed":
            status["status"] = "failed"
            status["failed_stage"] = stage["name"]
            atomic_write_json(status_path, status)
            return 1
        atomic_write_json(status_path, status)

    status["status"] = "completed"
    status["finished_at_utc"] = utc_now()
    status["elapsed_minutes"] = (time.monotonic() - started) / 60.0
    atomic_write_json(status_path, status)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", choices=SUPPORTED_BENCHMARKS, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--maximum-minutes", type=float, default=600.0)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the controlled chain; otherwise print its machine-readable plan.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_root = args.output_root.resolve()
    plan = build_plan(args.benchmark, output_root, args.maximum_minutes)
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    return run_plan(plan, output_root)


if __name__ == "__main__":
    raise SystemExit(main())
