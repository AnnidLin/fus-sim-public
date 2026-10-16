"""Durable refocus-only recovery for the PUB.2 250 kHz reference pair.

The original chain and first recovery attempt remain immutable evidence. This
driver reuses completed calibration signals, runs only ``tr_refocus``, writes
attempt-scoped watchdog records, and never rewrites ``chain_status.json``.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

import run_pub2_250khz_reference_pair as pair
from windows_process_tree_guard import (
    GuardThresholds,
    ProcessTreeSampler,
    breach_reasons,
    set_below_normal_priority,
    terminate_process_tree,
)

ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / "pub2_250khz_reference_pair_throttled_20260807"
DEFAULT_ATTEMPT_ID = "tr_refocus_recovery2_20260809"
RAISED_WORKING_SET_GIB = 16.0
MAXIMUM_MINUTES = 210.0
RECORD_TARGET_WAVEFORM = False
MONITOR_FILES = (
    "monitor_status.json", "monitor_history.jsonl", "monitor_attention.json",
    "monitored_stdout.txt", "monitored_stderr.txt",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def refocus_stage() -> "pair.Stage":
    return next(stage for stage in pair.STAGES if stage.stage_id == "tr_refocus")


def recovery_child_command(stage: "pair.Stage", output_dir: Path) -> list[str]:
    """Build the unchanged refocus solve with optional diagnostics disabled.

    The solver uses a full-grid sensor for p_max/p_min. Recording ``p`` on that
    same mask materialises a full space-time field although only one target
    trace is retained. It is not an acceptance artifact and does not affect
    propagation, so recovery attempts disable it to remove that memory load.
    """
    command = pair.child_command(stage, output_dir)
    if not RECORD_TARGET_WAVEFORM:
        command.append("--no-record-target-waveform")
    return command


def recovery_monitor_command(stage: "pair.Stage", output_dir: Path) -> list[str]:
    command = pair.monitor_command(stage, output_dir, MAXIMUM_MINUTES)
    separator = command.index("--")
    return [*command[: separator + 1], *recovery_child_command(stage, output_dir)]


def validate_calibration(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as archive:
        if "signals" not in archive:
            return {"passed": False, "reason": "signals array missing"}
        signals = np.asarray(archive["signals"])
        finite = bool(np.issubdtype(signals.dtype, np.number) and np.isfinite(signals).all())
        nonzero = bool(finite and np.any(np.abs(signals) > 0))
        return {
            "passed": finite and nonzero and signals.ndim == 2,
            "shape": list(signals.shape), "dtype": str(signals.dtype),
            "finite": finite, "nonzero": nonzero,
        }


def attempt_artifact_paths(output_root: Path, attempt_id: str) -> dict[str, Path]:
    return {
        "driver_log": output_root / f"{attempt_id}_driver.log",
        "launcher_stdout": output_root / f"{attempt_id}_launcher_stdout.txt",
        "launcher_stderr": output_root / f"{attempt_id}_launcher_stderr.txt",
        "device_history": output_root / f"{attempt_id}_device_history.jsonl",
        "device_status": output_root / f"{attempt_id}_device_status.json",
        "attempt_status": output_root / f"{attempt_id}_attempt_status.json",
        "stage_result": output_root / f"{attempt_id}_stage_result.json",
    }


def preflight(output_root: Path, attempt_id: str) -> dict[str, Any]:
    tr_dir = output_root / "tr"
    original_chain = load_json(output_root / "chain_status.json")
    stages = {item.get("stage_id"): item for item in original_chain.get("stages", [])}
    calibration_path = tr_dir / "element_signals.npz"
    calibration = validate_calibration(calibration_path) if calibration_path.is_file() else {"passed": False}
    summary_valid = False
    try:
        load_json(tr_dir / "summary_calibrate.json")
        summary_valid = True
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    attempt_paths = attempt_artifact_paths(output_root, attempt_id)
    checks = {
        "original_chain_failed_only_at_refocus": (
            original_chain.get("status") == "failed"
            and stages.get("baseline", {}).get("status") == "completed"
            and stages.get("tr_calibrate", {}).get("status") == "completed"
            and stages.get("tr_refocus", {}).get("status") == "failed"
            and stages["tr_refocus"].get("stopped_reason") == "process_tree_working_set"
        ),
        "calibration_signals_finite_nonzero_2d": calibration.get("passed") is True,
        "calibration_summary_valid": summary_valid,
        "no_final_refocus_outputs": not any(
            (tr_dir / name).exists()
            for name in ("pressure_max_mpa.npz", "summary.json", "focus_metrics.json")
        ),
        "no_existing_completion_status": not (output_root / "reference_completion_status.json").exists(),
        "attempt_id_unused": not any(path.exists() for path in attempt_paths.values()),
        "base_preflight_still_passes": pair.preflight().get("status") == "passed",
    }
    return {
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks, "calibration": calibration,
        "attempt_id": attempt_id, "scope": ["tr_refocus"],
        "device_policy": {
            "thread_environment_limit": 6, "priority": "BelowNormal",
            "maximum_equivalent_cores": 6.5,
            "maximum_working_set_gib": RAISED_WORKING_SET_GIB,
            "minimum_free_memory_gib": 4.0,
        },
    }


def snapshot_monitor(output_root: Path, name: str) -> Path:
    source_dir = output_root / "tr"
    snapshot = output_root / "monitor_snapshots" / name
    snapshot.mkdir(parents=True, exist_ok=False)
    copied = 0
    for filename in MONITOR_FILES:
        source = source_dir / filename
        if source.exists():
            shutil.copy2(source, snapshot / filename)
            copied += 1
    if copied == 0:
        raise FileNotFoundError("No monitor artifacts available to snapshot.")
    return snapshot


def build_completion_status(
    output_root: Path,
    attempt_id: str,
    result: dict[str, Any],
    preflight_result: dict[str, Any],
) -> dict[str, Any]:
    original_path = output_root / "chain_status.json"
    original = load_json(original_path)
    stages = {item["stage_id"]: item for item in original["stages"]}
    return {
        "schema_version": "1.0", "status": "completed",
        "completion_mode": "refocus_only_recovery",
        "original_chain_status": str(original_path),
        "original_chain_terminal_status": original.get("status"),
        "original_chain_stop_reason": original.get("stop_reason"),
        "preflight": original.get("preflight"),
        "recovery_preflight": preflight_result,
        "stages": [stages["baseline"], stages["tr_calibrate"], result],
        "pressure_scope": list(original.get("pressure_scope", [])),
        "automatic_follow_on_sensitivity_cells_authorized": False,
        "recovery_attempt_id": attempt_id, "finished_at_utc": utc_now(),
        "claim_boundary": (
            "Completion closes only the fresh dx0.75 baseline/TR reference pair. "
            "It does not authorize sensitivity pressure cells or establish convergence, efficacy or safety."
        ),
    }


def run_refocus_only(output_root: Path, attempt_id: str) -> dict[str, Any]:
    preflight_result = preflight(output_root, attempt_id)
    if preflight_result["status"] != "passed":
        raise RuntimeError(f"Recovery preflight failed: {preflight_result['checks']}")
    paths = attempt_artifact_paths(output_root, attempt_id)
    pair.atomic_json(paths["attempt_status"], {
        "status": "starting", "attempt_id": attempt_id, "at_utc": utc_now(),
        "preflight": preflight_result,
    })
    prior_snapshot = snapshot_monitor(output_root, f"before_{attempt_id}")
    tr_dir = (output_root / "tr").resolve()
    stage = refocus_stage()
    environment = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        environment[key] = "6"
    command = recovery_monitor_command(stage, tr_dir)
    creation_flags = 0x00004000 | 0x08000000 if os.name == "nt" else 0

    def log(message: str) -> None:
        marker = f"[{utc_now()}] {message}"
        print(marker, flush=True)
        with paths["driver_log"].open("a", encoding="utf-8") as handle:
            handle.write(marker + "\n")

    log(f"Launching durable recovery {attempt_id}: {' '.join(command)}")
    with paths["launcher_stdout"].open("wb") as stdout_handle, paths["launcher_stderr"].open("wb") as stderr_handle:
        process = subprocess.Popen(
            command, cwd=ROOT, env=environment,
            stdout=stdout_handle, stderr=stderr_handle,
            creationflags=creation_flags,
        )
        set_below_normal_priority(process.pid)
        pair.atomic_json(paths["attempt_status"], {
            "status": "running", "attempt_id": attempt_id, "pid": process.pid,
            "at_utc": utc_now(), "prior_monitor_snapshot": str(prior_snapshot),
            "preflight": preflight_result,
        })
        sampler = ProcessTreeSampler(process.pid)
        thresholds = GuardThresholds(maximum_working_set_gib=RAISED_WORKING_SET_GIB)
        cpu_breach_streak = 0
        stopped_reason: str | None = None
        next_log = time.monotonic() + 60.0
        while process.poll() is None:
            sample = sampler.sample()
            sample["at_utc"] = utc_now()
            reasons = breach_reasons(sample, thresholds)
            cpu_breach_streak = cpu_breach_streak + 1 if "equivalent_cpu_cores" in reasons else 0
            immediate = [reason for reason in reasons if reason != "equivalent_cpu_cores"]
            if cpu_breach_streak >= 3:
                immediate.append("sustained_equivalent_cpu_cores")
            sample["cpu_breach_streak"] = cpu_breach_streak
            sample["breach_reasons"] = immediate
            with paths["device_history"].open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(sample, ensure_ascii=False) + "\n")
            pair.atomic_json(paths["device_status"], {
                "status": "stopping" if immediate else "running",
                "attempt_id": attempt_id, "stage": "tr_refocus",
                "latest_sample": sample,
                "guard_working_set_gib_limit": RAISED_WORKING_SET_GIB,
            })
            if immediate:
                stopped_reason = ",".join(immediate)
                log(f"Guard breach -> {stopped_reason}; terminating process tree.")
                terminate_process_tree(process.pid)
                break
            if time.monotonic() >= next_log:
                log(
                    f"device cores={sample.get('equivalent_cores')} "
                    f"ws_gib={sample.get('working_set_gib'):.3f} "
                    f"free_gib={sample.get('system_free_memory_gib'):.3f}"
                )
                next_log += 60.0
            time.sleep(10.0)
        return_code = process.wait()

    validation = pair.validate_stage_outputs(stage, tr_dir)
    result = {
        "stage_id": "tr_refocus", "recovery_attempt": attempt_id,
        "guard_working_set_gib_limit": RAISED_WORKING_SET_GIB,
        "return_code": return_code, "stopped_reason": stopped_reason,
        "output_validation": validation,
        "status": (
            "completed"
            if return_code == 0 and stopped_reason is None and validation["status"] == "passed"
            else "failed"
        ),
    }
    pair.atomic_json(paths["stage_result"], result)
    completed_snapshot = snapshot_monitor(output_root, attempt_id)
    pair.atomic_json(paths["device_status"], {
        "status": result["status"], "attempt_id": attempt_id,
        "stage": "tr_refocus", "stage_result": str(paths["stage_result"]),
        "monitor_snapshot": str(completed_snapshot),
        "guard_working_set_gib_limit": RAISED_WORKING_SET_GIB,
    })
    if result["status"] == "completed":
        pair.atomic_json(
            output_root / "reference_completion_status.json",
            build_completion_status(output_root, attempt_id, result, preflight_result),
        )
    pair.atomic_json(paths["attempt_status"], {
        "status": result["status"], "attempt_id": attempt_id,
        "finished_at_utc": utc_now(), "result": result,
    })
    log(f"Recovery finished with status={result['status']} return_code={return_code}")
    return result


def plan(output_root: Path, attempt_id: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0", "status": "planned_not_executed",
        "attempt_id": attempt_id, "preflight": preflight(output_root, attempt_id),
        "stage": "tr_refocus", "output_dir": str(output_root / "tr"),
        "working_set_guard_gib": RAISED_WORKING_SET_GIB,
        "maximum_minutes": MAXIMUM_MINUTES,
        "command": recovery_child_command(refocus_stage(), output_root / "tr"),
        "automatic_follow_on_sensitivity_cells_authorized": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--attempt-id", default=DEFAULT_ATTEMPT_ID)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_root.resolve()
    if not args.execute:
        value = plan(output_root, args.attempt_id)
        print(json.dumps(value, indent=2, ensure_ascii=False))
        return 0 if value["preflight"]["status"] == "passed" else 1
    try:
        result = run_refocus_only(output_root, args.attempt_id)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
