"""Run the PUB.2 dx0.75/CFL0.1 baseline time-step sensitivity cell."""
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
from windows_process_tree_guard import GuardThresholds, ProcessTreeSampler, breach_reasons, set_below_normal_priority, terminate_process_tree

ROOT = Path(__file__).resolve().parent
CELL_ID, METHOD = "dx0p75_cfl0p1", "baseline"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "pub2_250khz_cfl0p1_baseline_20260812"
DEFAULT_DRY_RUN_DIR = ROOT / "outputs" / "pub2_250khz_cfl0p1_baseline_dry_run_20260812"
MAXIMUM_MINUTES, WORKING_SET_GIB = 360.0, 16.0
DEPENDENCIES = {
    "evidence": ROOT / "outputs" / "evidence_briefs" / "pub2_250khz_ct_numerical_sensitivity_20260807" / "evidence_brief.json",
    "pml16_validation": ROOT / "outputs" / "pub2_250khz_pml16_tr_validation_20260812" / "package_validation.json",
    "matrix_plan": ROOT / "outputs" / "pub2_250khz_dry_run_matrix_refined_retry1_20260807" / "dry_run_matrix_plan.json",
    "matrix_report": ROOT / "outputs" / "pub2_250khz_dry_run_matrix_refined_retry1_20260807" / "dry_run_matrix_report.json",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def frozen_entry(plan: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in plan.get("entries", []) if row.get("cell_id") == CELL_ID and row.get("method") == METHOD]
    if len(rows) != 1:
        raise ValueError(f"Expected one {CELL_ID}/{METHOD} entry, found {len(rows)}")
    return rows[0]


def child_command(plan: dict[str, Any], output_dir: Path, *, dry_run: bool = False) -> list[str]:
    command = [str(value) for value in frozen_entry(plan)["command"]]
    command[0] = sys.executable
    command[command.index("--output-dir") + 1] = str(output_dir.resolve())
    if dry_run and "--dry-run-quality" not in command:
        command.append("--dry-run-quality")
    if not dry_run and "--dry-run-quality" in command:
        command.remove("--dry-run-quality")
    return command


def preflight(output_dir: Path, paths: dict[str, Path] | None = None) -> dict[str, Any]:
    deps = DEPENDENCIES if paths is None else paths
    evidence, validation = load(deps["evidence"]), load(deps["pml16_validation"])
    plan, report = load(deps["matrix_plan"]), load(deps["matrix_report"])
    entry = frozen_entry(plan)
    rows = [row for row in report.get("results", []) if row.get("cell_id") == CELL_ID and row.get("method") == METHOD]
    result = rows[0] if len(rows) == 1 else {}
    config, quality, source = entry.get("configuration", {}), result.get("simulation_quality", {}), result.get("source", {})
    checks = {
        "amendment_authorized": evidence.get("cfl0p1_baseline_time_step_amendment_20260812", {}).get("status") == "authorized_pending_runner_test_and_exact_dry_run",
        "recovery_authorized": output_dir.resolve() == DEFAULT_OUTPUT_DIR.resolve()
        or evidence.get("cfl0p1_baseline_recovery1_amendment_20260812", {}).get("status")
        == "authorized_pending_runner_test_exact_dry_run_and_device_gate",
        "previous_pair_validated": validation.get("status") == "passed",
        "matrix_cell_passed": report.get("status") == "passed" and result.get("status") == "passed",
        "single_variable_config": float(config.get("dx_mm", -1)) == 0.75 and int(config.get("pml_size", -1)) == 12 and float(config.get("cfl", -1)) == 0.1,
        "grid_time_frozen": quality.get("grid_size") == [133, 98, 101] and int(quality.get("nt", -1)) == 3734 and float(quality.get("cfl", -1)) == 0.1,
        "source_background_only": int(source.get("source_points", -1)) == 4971 and source.get("source_label_counts") == {"0": 4971},
        "no_existing_core_outputs": not any((output_dir / name).exists() for name in ("pressure_max_mpa.npz", "summary.json", "focus_metrics.json")),
    }
    return {"status": "passed" if all(checks.values()) else "failed", "checks": checks, "cell_id": CELL_ID, "method": METHOD}


def exact_dry_run(output_dir: Path, target_output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    gate = preflight(target_output_dir)
    if gate["status"] != "passed":
        raise RuntimeError(f"Preflight failed: {gate['checks']}")
    output_dir.mkdir(parents=True, exist_ok=True)
    command = child_command(load(DEPENDENCIES["matrix_plan"]), output_dir, dry_run=True)
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=600)
    (output_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (output_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    report = {"status": "passed" if completed.returncode == 0 else "failed", "at_utc": now(), "return_code": completed.returncode, "preflight": gate, "command": command}
    pair.atomic_json(output_dir / "exact_dry_run_report.json", report)
    return report


def run(output_dir: Path, dry_report: Path) -> dict[str, Any]:
    gate, dry = preflight(output_dir), load(dry_report)
    if gate["status"] != "passed" or dry.get("status") != "passed":
        raise RuntimeError(f"Launch gate failed: preflight={gate['status']} dry={dry.get('status')}")
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "monitor_kwave_process", "--output-dir", str(output_dir.resolve()), "--checkpoint-sec", "120", "--poll-sec", "5", "--stall-stop-min", "20", "--emergency-ceiling-min", "330", "--maximum-ceiling-min", f"{MAXIMUM_MINUTES:.3f}", "--", *child_command(load(DEPENDENCIES["matrix_plan"]), output_dir)]
    status_path, device_path = output_dir / "execution_status.json", output_dir / "device_status.json"
    history_path = output_dir / "device_history.jsonl"
    pair.atomic_json(status_path, {"status": "starting", "at_utc": now(), "preflight": gate})
    env = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[key] = "6"
    flags = 0x00004000 | 0x08000000 if os.name == "nt" else 0
    started, stopped = time.monotonic(), None
    with (output_dir / "launcher_stdout.txt").open("wb") as stdout, (output_dir / "launcher_stderr.txt").open("wb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, creationflags=flags)
        set_below_normal_priority(process.pid)
        pair.atomic_json(status_path, {"status": "running", "pid": process.pid, "at_utc": now(), "preflight": gate, "command": command})
        sampler, thresholds, cpu_streak = ProcessTreeSampler(process.pid), GuardThresholds(maximum_working_set_gib=WORKING_SET_GIB), 0
        while process.poll() is None:
            sample = sampler.sample()
            sample["at_utc"] = now()
            reasons = breach_reasons(sample, thresholds)
            cpu_streak = cpu_streak + 1 if "equivalent_cpu_cores" in reasons else 0
            immediate = [reason for reason in reasons if reason != "equivalent_cpu_cores"]
            if cpu_streak >= 3:
                immediate.append("sustained_equivalent_cpu_cores")
            sample.update({"cpu_breach_streak": cpu_streak, "breach_reasons": immediate})
            with history_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(sample, ensure_ascii=False) + "\n")
            pair.atomic_json(device_path, {"status": "stopping" if immediate else "running", "latest_sample": sample})
            if immediate:
                stopped = ",".join(immediate)
                terminate_process_tree(process.pid)
                break
            time.sleep(10)
        return_code = process.wait()
    validation = pair.validate_stage_outputs(pair.STAGES[0], output_dir)
    result = {"cell_id": CELL_ID, "method": METHOD, "return_code": return_code, "stopped_reason": stopped, "wall_seconds": time.monotonic() - started, "output_validation": validation, "status": "completed" if return_code == 0 and stopped is None and validation["status"] == "passed" else "failed", "finished_at_utc": now()}
    pair.atomic_json(output_dir / "stage_result.json", result)
    pair.atomic_json(status_path, {"status": result["status"], "result": result})
    pair.atomic_json(device_path, {"status": result["status"], "stage_result": str(output_dir / "stage_result.json")})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dry-run-dir", type=Path, default=DEFAULT_DRY_RUN_DIR)
    parser.add_argument("--exact-dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        if args.exact_dry_run:
            value = exact_dry_run(args.dry_run_dir.resolve(), args.output_dir.resolve())
        elif args.execute:
            value = run(args.output_dir.resolve(), (args.dry_run_dir / "exact_dry_run_report.json").resolve())
        else:
            value = {"status": "planned_not_executed", "preflight": preflight(args.output_dir.resolve()), "command": child_command(load(DEPENDENCIES["matrix_plan"]), args.output_dir.resolve())}
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, ensure_ascii=False))
    return 0 if value.get("status") in {"passed", "completed", "planned_not_executed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
