"""Run the fresh PUB.2 dx0.75/PML16 TR calibrate-to-refocus pair."""
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
METHOD = "tr"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / "pub2_250khz_pml16_tr_20260811"
DEFAULT_DRY_RUN_ROOT = ROOT / "outputs" / "pub2_250khz_pml16_tr_dry_run_20260811"
MAXIMUM_MINUTES_PER_STAGE = 240.0
WORKING_SET_GIB = 16.0
STAGES = (pair.STAGES[1], pair.STAGES[2])
DEFAULT_DEPENDENCIES = {
    "evidence": ROOT / "outputs" / "evidence_briefs" / "pub2_250khz_ct_numerical_sensitivity_20260807" / "evidence_brief.json",
    "matrix_plan": ROOT / "outputs" / "pub2_250khz_dry_run_matrix_refined_retry1_20260807" / "dry_run_matrix_plan.json",
    "matrix_report": ROOT / "outputs" / "pub2_250khz_dry_run_matrix_refined_retry1_20260807" / "dry_run_matrix_report.json",
    "baseline_validation": ROOT / "outputs" / "pub2_250khz_pml16_baseline_validation_20260810" / "package_validation.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def frozen_entry(plan: dict[str, Any]) -> dict[str, Any]:
    matches = [item for item in plan.get("entries", []) if item.get("cell_id") == CELL_ID and item.get("method") == METHOD]
    if len(matches) != 1:
        raise ValueError(f"Expected one frozen {CELL_ID}/{METHOD} entry, found {len(matches)}")
    return matches[0]


def stage_command(plan: dict[str, Any], stage: pair.Stage, output_dir: Path, *, dry_run: bool = False) -> list[str]:
    command = [str(value) for value in frozen_entry(plan)["command"]]
    command[0] = sys.executable
    command[command.index("--output-dir") + 1] = str(output_dir.resolve())
    command[command.index("--stage") + 1] = str(stage.tr_stage)
    if dry_run and "--dry-run-quality" not in command:
        command.append("--dry-run-quality")
    if not dry_run and "--dry-run-quality" in command:
        command.remove("--dry-run-quality")
    if stage.stage_id == "tr_refocus" and "--no-record-target-waveform" not in command:
        command.append("--no-record-target-waveform")
    return command


def monitor_command(plan: dict[str, Any], stage: pair.Stage, output_dir: Path) -> list[str]:
    return [
        sys.executable, "-m", "monitor_kwave_process",
        "--output-dir", str(output_dir.resolve()),
        "--checkpoint-sec", "120", "--poll-sec", "5",
        "--stall-stop-min", "20", "--emergency-ceiling-min", "210",
        "--maximum-ceiling-min", f"{MAXIMUM_MINUTES_PER_STAGE:.3f}", "--",
        *stage_command(plan, stage, output_dir),
    ]


def preflight(output_root: Path, dependency_paths: dict[str, Path] | None = None) -> dict[str, Any]:
    paths = DEFAULT_DEPENDENCIES if dependency_paths is None else dependency_paths
    evidence = load_json(paths["evidence"])
    plan = load_json(paths["matrix_plan"])
    report = load_json(paths["matrix_report"])
    baseline_validation = load_json(paths["baseline_validation"])
    entry = frozen_entry(plan)
    results = [item for item in report.get("results", []) if item.get("cell_id") == CELL_ID and item.get("method") == METHOD]
    result = results[0] if len(results) == 1 else {}
    matched = [item for item in report.get("matched_pairs", []) if item.get("cell_id") == CELL_ID]
    match = matched[0] if len(matched) == 1 else {}
    config = entry.get("configuration", {})
    quality = result.get("simulation_quality", {})
    source = result.get("source", {})
    tr_dir = output_root / "tr"
    checks = {
        "execution_amendment_authorized": evidence.get("pml16_tr_matched_pair_completion_amendment_20260811", {}).get("status") == "authorized_pending_runner_test_and_exact_dry_run",
        "pml16_baseline_package_passed": baseline_validation.get("status") == "passed",
        "matrix_report_passed": report.get("status") == "passed" and result.get("status") == "passed",
        "baseline_tr_matrix_pair_matched": match.get("matched") is True and not match.get("baseline_tr_drift"),
        "single_variable_configuration": float(config.get("dx_mm", -1)) == 0.75 and int(config.get("pml_size", -1)) == 16 and float(config.get("cfl", -1)) == 0.2,
        "dry_run_grid_and_time_frozen": quality.get("grid_size") == [137, 98, 101] and int(quality.get("nt", -1)) == 1867 and int(quality.get("pml_size", -1)) == 16 and float(quality.get("cfl", -1)) == 0.2,
        "source_background_only": int(source.get("source_points", -1)) == 4971 and source.get("source_label_counts") == {"0": 4971},
        "no_existing_core_outputs": not any((tr_dir / name).exists() for name in ("element_signals.npz", "pressure_max_mpa.npz", "summary.json", "focus_metrics.json")),
    }
    return {
        "status": "passed" if all(checks.values()) else "failed",
        "cell_id": CELL_ID, "method": METHOD, "checks": checks, "frozen_entry": entry,
        "device_policy": {"thread_environment_limit": 6, "priority": "BelowNormal", "maximum_equivalent_cores": 6.5, "maximum_working_set_gib": WORKING_SET_GIB, "minimum_free_memory_gib": 4.0},
    }


def exact_dry_run(output_root: Path) -> dict[str, Any]:
    gate = preflight(DEFAULT_OUTPUT_ROOT)
    if gate["status"] != "passed":
        raise RuntimeError(f"PML16 TR preflight failed: {gate['checks']}")
    plan = load_json(DEFAULT_DEPENDENCIES["matrix_plan"])
    output_root.mkdir(parents=True, exist_ok=True)
    results = []
    for stage in STAGES:
        stage_dir = output_root / stage.stage_id
        stage_dir.mkdir(parents=True, exist_ok=True)
        command = stage_command(plan, stage, stage_dir, dry_run=True)
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=600)
        (stage_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
        (stage_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
        results.append({"stage_id": stage.stage_id, "return_code": completed.returncode, "command": command})
        if completed.returncode != 0:
            break
    report = {"status": "passed" if len(results) == 2 and all(item["return_code"] == 0 for item in results) else "failed", "at_utc": utc_now(), "preflight": gate, "results": results}
    pair.atomic_json(output_root / "exact_dry_run_report.json", report)
    return report


def run_stage(plan: dict[str, Any], stage: pair.Stage, output_root: Path) -> dict[str, Any]:
    output_dir = output_root / "tr"
    output_dir.mkdir(parents=True, exist_ok=True)
    status_path = output_root / f"{stage.stage_id}_execution_status.json"
    device_path = output_root / f"{stage.stage_id}_device_status.json"
    history_path = output_root / f"{stage.stage_id}_device_history.jsonl"
    command = monitor_command(plan, stage, output_dir)
    environment = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        environment[key] = "6"
    creation_flags = 0x00004000 | 0x08000000 if os.name == "nt" else 0
    stdout_path = output_root / f"{stage.stage_id}_launcher_stdout.txt"
    stderr_path = output_root / f"{stage.stage_id}_launcher_stderr.txt"
    started = time.monotonic()
    stopped_reason: str | None = None
    with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=stdout_handle, stderr=stderr_handle, creationflags=creation_flags)
        set_below_normal_priority(process.pid)
        pair.atomic_json(status_path, {"status": "running", "pid": process.pid, "at_utc": utc_now(), "command": command})
        sampler = ProcessTreeSampler(process.pid)
        thresholds = GuardThresholds(maximum_working_set_gib=WORKING_SET_GIB)
        cpu_streak = 0
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
            pair.atomic_json(device_path, {"status": "stopping" if immediate else "running", "stage_id": stage.stage_id, "latest_sample": sample})
            if immediate:
                stopped_reason = ",".join(immediate)
                terminate_process_tree(process.pid)
                break
            time.sleep(10.0)
        return_code = process.wait()
    validation = pair.validate_stage_outputs(stage, output_dir)
    result = {"stage_id": stage.stage_id, "return_code": return_code, "stopped_reason": stopped_reason, "wall_seconds": time.monotonic() - started, "output_validation": validation, "status": "completed" if return_code == 0 and stopped_reason is None and validation["status"] == "passed" else "failed", "finished_at_utc": utc_now()}
    pair.atomic_json(output_root / f"{stage.stage_id}_stage_result.json", result)
    pair.atomic_json(status_path, {"status": result["status"], "result": result})
    pair.atomic_json(device_path, {"status": result["status"], "stage_id": stage.stage_id, "stage_result": str(output_root / f"{stage.stage_id}_stage_result.json")})
    return result


def run(output_root: Path, dry_run_report: Path) -> dict[str, Any]:
    gate = preflight(output_root)
    dry = load_json(dry_run_report)
    if gate["status"] != "passed" or dry.get("status") != "passed":
        raise RuntimeError(f"PML16 TR launch gate failed: preflight={gate['status']} dry_run={dry.get('status')}")
    output_root.mkdir(parents=True, exist_ok=True)
    pair.atomic_json(output_root / "chain_status.json", {"status": "running", "at_utc": utc_now(), "preflight": gate, "exact_dry_run": str(dry_run_report)})
    plan = load_json(DEFAULT_DEPENDENCIES["matrix_plan"])
    results = []
    for stage in STAGES:
        result = run_stage(plan, stage, output_root)
        results.append(result)
        if result["status"] != "completed":
            break
    chain = {"status": "completed" if len(results) == 2 and all(item["status"] == "completed" for item in results) else "failed", "finished_at_utc": utc_now(), "automatic_rerun": False, "results": results}
    pair.atomic_json(output_root / "chain_status.json", chain)
    return chain


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--dry-run-root", type=Path, default=DEFAULT_DRY_RUN_ROOT)
    parser.add_argument("--exact-dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.exact_dry_run:
            value = exact_dry_run(args.dry_run_root.resolve())
        elif args.execute:
            value = run(args.output_root.resolve(), (args.dry_run_root / "exact_dry_run_report.json").resolve())
        else:
            plan = load_json(DEFAULT_DEPENDENCIES["matrix_plan"])
            value = {"status": "planned_not_executed", "preflight": preflight(args.output_root.resolve()), "commands": [stage_command(plan, stage, args.output_root.resolve() / "tr") for stage in STAGES]}
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, ensure_ascii=False))
    return 0 if value.get("status") in {"passed", "completed", "planned_not_executed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
