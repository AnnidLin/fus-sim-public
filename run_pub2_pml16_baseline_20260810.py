"""Run the one-variable PUB.2 dx0.75/PML16 baseline sensitivity cell."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_pub2_250khz_reference_pair as pair
from windows_process_tree_guard import (
    GuardThresholds,
    ProcessTreeSampler,
    breach_reasons,
    set_below_normal_priority,
    terminate_process_tree,
)

ROOT = Path(__file__).resolve().parent
CELL_ID = "dx0p75_pml16"
METHOD = "baseline"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "pub2_250khz_pml16_baseline_20260810"
MAXIMUM_MINUTES = 240.0
WORKING_SET_GIB = 16.0
DEFAULT_DEPENDENCIES = {
    "completion": ROOT / "outputs" / "pub2_250khz_reference_pair_throttled_20260807" / "reference_completion_status.json",
    "analysis": ROOT / "outputs" / "pub2_250khz_reference_analysis_20260807" / "reference_pair_analysis.json",
    "feedback": ROOT / "outputs" / "evidence_briefs" / "pub2_250khz_ct_numerical_sensitivity_20260807" / "gap_feedback.json",
    "matrix_plan": ROOT / "outputs" / "pub2_250khz_dry_run_matrix_refined_retry1_20260807" / "dry_run_matrix_plan.json",
    "matrix_report": ROOT / "outputs" / "pub2_250khz_dry_run_matrix_refined_retry1_20260807" / "dry_run_matrix_report.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def frozen_entry(plan: dict[str, Any]) -> dict[str, Any]:
    matches = [
        item for item in plan.get("entries", [])
        if item.get("cell_id") == CELL_ID and item.get("method") == METHOD
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one frozen {CELL_ID}/{METHOD} entry, found {len(matches)}")
    return matches[0]


def build_child_command(plan: dict[str, Any], output_dir: Path) -> list[str]:
    command = [str(value) for value in frozen_entry(plan)["command"]]
    if "--dry-run-quality" in command:
        command.remove("--dry-run-quality")
    command[0] = sys.executable
    command[command.index("--output-dir") + 1] = str(output_dir.resolve())
    return command


def build_monitor_command(plan: dict[str, Any], output_dir: Path) -> list[str]:
    return [
        sys.executable, "-m", "monitor_kwave_process",
        "--output-dir", str(output_dir.resolve()),
        "--checkpoint-sec", "120", "--poll-sec", "5",
        "--stall-stop-min", "20", "--emergency-ceiling-min", "210",
        "--maximum-ceiling-min", f"{MAXIMUM_MINUTES:.3f}", "--",
        *build_child_command(plan, output_dir),
    ]


def preflight(
    output_dir: Path,
    dependency_paths: dict[str, Path] | None = None,
) -> dict[str, Any]:
    paths = DEFAULT_DEPENDENCIES if dependency_paths is None else dependency_paths
    completion = load_json(paths["completion"])
    analysis = load_json(paths["analysis"])
    feedback = load_json(paths["feedback"])
    plan = load_json(paths["matrix_plan"])
    report = load_json(paths["matrix_report"])
    entry = frozen_entry(plan)
    results = [
        item for item in report.get("results", [])
        if item.get("cell_id") == CELL_ID and item.get("method") == METHOD
    ]
    result = results[0] if len(results) == 1 else {}
    config = entry.get("configuration", {})
    quality = result.get("simulation_quality", {})
    source = result.get("source", {})
    checks = {
        "reference_completion_passed": completion.get("status") == "completed",
        "reference_analysis_passed": analysis.get("status") == "passed",
        "reference_feedback_closed": feedback.get("status") == "reference_pair_complete_sensitivity_pressure_still_blocked",
        "matrix_plan_exact_entry": entry.get("changed_factor") == "pml_size",
        "matrix_report_passed": report.get("status") == "passed" and result.get("status") == "passed",
        "single_variable_configuration": (
            float(config.get("dx_mm", -1)) == 0.75
            and int(config.get("pml_size", -1)) == 16
            and float(config.get("cfl", -1)) == 0.2
        ),
        "dry_run_grid_and_time_frozen": (
            quality.get("grid_size") == [137, 98, 101]
            and int(quality.get("nt", -1)) == 1867
            and int(quality.get("pml_size", -1)) == 16
            and float(quality.get("cfl", -1)) == 0.2
        ),
        "source_background_only": (
            int(source.get("source_points", -1)) == 4971
            and source.get("source_label_counts") == {"0": 4971}
        ),
        "no_existing_core_outputs": not any(
            (output_dir / name).exists()
            for name in ("pressure_max_mpa.npz", "summary.json", "focus_metrics.json")
        ),
    }
    return {
        "status": "passed" if all(checks.values()) else "failed",
        "cell_id": CELL_ID, "method": METHOD, "checks": checks,
        "frozen_entry": entry,
        "device_policy": {
            "thread_environment_limit": 6, "priority": "BelowNormal",
            "maximum_equivalent_cores": 6.5,
            "maximum_working_set_gib": WORKING_SET_GIB,
            "minimum_free_memory_gib": 4.0,
        },
    }


def run(output_dir: Path) -> dict[str, Any]:
    gate = preflight(output_dir)
    if gate["status"] != "passed":
        raise RuntimeError(f"PML16 baseline preflight failed: {gate['checks']}")
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = load_json(DEFAULT_DEPENDENCIES["matrix_plan"])
    command = build_monitor_command(plan, output_dir)
    status_path = output_dir / "execution_status.json"
    device_path = output_dir / "device_status.json"
    history_path = output_dir / "device_history.jsonl"
    log_path = output_dir / "driver.log"
    stdout_path = output_dir / "launcher_stdout.txt"
    stderr_path = output_dir / "launcher_stderr.txt"
    pair.atomic_json(status_path, {"status": "starting", "at_utc": utc_now(), "preflight": gate})
    environment = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        environment[key] = "6"
    creation_flags = 0x00004000 | 0x08000000 if os.name == "nt" else 0

    def log(message: str) -> None:
        marker = f"[{utc_now()}] {message}"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(marker + "\n")

    log("Launching: " + " ".join(command))
    with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
        process = subprocess.Popen(
            command, cwd=ROOT, env=environment,
            stdout=stdout_handle, stderr=stderr_handle,
            creationflags=creation_flags,
        )
        set_below_normal_priority(process.pid)
        pair.atomic_json(status_path, {
            "status": "running", "pid": process.pid, "at_utc": utc_now(),
            "preflight": gate, "command": command,
        })
        sampler = ProcessTreeSampler(process.pid)
        thresholds = GuardThresholds(maximum_working_set_gib=WORKING_SET_GIB)
        cpu_streak = 0
        stopped_reason: str | None = None
        while process.poll() is None:
            sample = sampler.sample()
            sample["at_utc"] = utc_now()
            reasons = breach_reasons(sample, thresholds)
            cpu_streak = cpu_streak + 1 if "equivalent_cpu_cores" in reasons else 0
            immediate = [reason for reason in reasons if reason != "equivalent_cpu_cores"]
            if cpu_streak >= 3:
                immediate.append("sustained_equivalent_cpu_cores")
            sample["cpu_breach_streak"] = cpu_streak
            sample["breach_reasons"] = immediate
            with history_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(sample, ensure_ascii=False) + "\n")
            pair.atomic_json(device_path, {
                "status": "stopping" if immediate else "running",
                "cell_id": CELL_ID, "latest_sample": sample,
            })
            if immediate:
                stopped_reason = ",".join(immediate)
                log(f"Guard breach -> {stopped_reason}; terminating process tree.")
                terminate_process_tree(process.pid)
                break
            time.sleep(10.0)
        return_code = process.wait()

    validation = pair.validate_stage_outputs(pair.STAGES[0], output_dir)
    result = {
        "cell_id": CELL_ID, "method": METHOD, "return_code": return_code,
        "stopped_reason": stopped_reason, "output_validation": validation,
        "status": "completed" if return_code == 0 and stopped_reason is None and validation["status"] == "passed" else "failed",
        "finished_at_utc": utc_now(),
    }
    pair.atomic_json(output_dir / "stage_result.json", result)
    pair.atomic_json(status_path, {"status": result["status"], "result": result})
    pair.atomic_json(device_path, {"status": result["status"], "cell_id": CELL_ID, "stage_result": str(output_dir / "stage_result.json")})
    log(f"Finished with status={result['status']} return_code={return_code}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    if not args.execute:
        gate = preflight(output_dir)
        value = {
            "status": "planned_not_executed", "preflight": gate,
            "output_dir": str(output_dir),
            "command": build_child_command(load_json(DEFAULT_DEPENDENCIES["matrix_plan"]), output_dir),
            "maximum_minutes": MAXIMUM_MINUTES,
        }
        print(json.dumps(value, indent=2, ensure_ascii=False))
        return 0 if gate["status"] == "passed" else 1
    try:
        result = run(output_dir)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
