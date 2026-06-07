from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from simulation_environment import build_environment_record


PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")
ALLOWED_SCRIPTS = {"simulate_freefield_transducer.py", "simulate_kwave_3d_focus.py"}
LOCKED_OUTPUT_PREFIXES = (
    PROJECT_ROOT / "outputs" / "freefield_calibration",
    PROJECT_ROOT / "outputs" / "ct_transducer_stability_target_020",
    PROJECT_ROOT / "outputs" / "case_refinement_runs",
    PROJECT_ROOT / "outputs" / "visible_human_quick_smoke_runs",
    PROJECT_ROOT / "outputs" / "pennes_protocol_dose_target_020",
)


def split_script_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(description="Plan or run a k-Wave command through the stable runner.")
    parser.add_argument("--script", required=True, choices=sorted(ALLOWED_SCRIPTS))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--preset", choices=["smoke", "quick", "standard", "paper_grade"], default="quick")
    parser.add_argument("--execute", action="store_true", help="Actually run k-Wave after the mandatory dry-run quality check.")
    parser.add_argument("--allow-existing-output", action="store_true")
    parser.add_argument("--checkpoint-sec", type=int, default=120)
    parser.add_argument("--hard-stop-min", type=float, default=10.0)
    parser.add_argument("--python-exe", default=str(PYTHON_EXE))
    args, remaining = parser.parse_known_args(argv)
    return args, remaining


def ensure_safe_output_dir(output_dir: Path, allow_existing_output: bool) -> None:
    resolved = output_dir.resolve()
    for prefix in LOCKED_OUTPUT_PREFIXES:
        try:
            resolved.relative_to(prefix.resolve())
        except ValueError:
            continue
        raise ValueError(f"Refusing to use locked output directory: {output_dir}")
    pressure_file = output_dir / "pressure_max_mpa.npz"
    if pressure_file.exists() and not allow_existing_output:
        raise FileExistsError(f"{pressure_file} already exists. Use --allow-existing-output only if overwriting is intentional.")


def expected_core_outputs(script: str, output_dir: Path) -> dict[str, str]:
    if script == "simulate_freefield_transducer.py":
        return {
            "pressure": str(output_dir / "pressure_max_mpa.npz"),
            "summary": str(output_dir / "freefield_summary.json"),
        }
    return {
        "pressure": str(output_dir / "pressure_max_mpa.npz"),
        "summary": str(output_dir / "summary.json"),
    }


def output_exists_map(paths: dict[str, str]) -> dict[str, bool]:
    return {key: Path(value).exists() for key, value in paths.items()}


def build_script_command(args: argparse.Namespace, passthrough: list[str], *, dry_run: bool) -> list[str]:
    command = [
        args.python_exe,
        args.script,
        "--output-dir",
        str(Path(args.output_dir)),
        "--preset",
        args.preset,
    ]
    command.extend(passthrough)
    if dry_run:
        command.append("--dry-run-quality")
    return command


def run_command_capture(command: list[str], stdout_path: Path, stderr_path: Path, timeout_s: float | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    tmp_dir = PROJECT_ROOT / ".tmp"
    mpl_dir = tmp_dir / "mplconfig-kwave-runner"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    mpl_dir.mkdir(parents=True, exist_ok=True)
    env["TEMP"] = str(tmp_dir)
    env["TMP"] = str(tmp_dir)
    env["MPLCONFIGDIR"] = str(mpl_dir)
    with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open("w", encoding="utf-8") as stderr_handle:
        return subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=env,
            text=True,
            stdout=stdout_handle,
            stderr=stderr_handle,
            timeout=timeout_s,
            check=False,
        )


def write_status(output_dir: Path, status: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "runner_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def run_runner(args: argparse.Namespace, passthrough: list[str]) -> dict[str, Any]:
    output_dir = Path(args.output_dir)
    ensure_safe_output_dir(output_dir, args.allow_existing_output)
    output_dir.mkdir(parents=True, exist_ok=True)
    core_outputs = expected_core_outputs(args.script, output_dir)
    dry_run_command = build_script_command(args, passthrough, dry_run=True)
    real_command = build_script_command(args, passthrough, dry_run=False)
    status: dict[str, Any] = {
        "description": "Stable k-Wave runner status. Runner plans by default and executes only with --execute.",
        "execute": bool(args.execute),
        "script": args.script,
        "preset": args.preset,
        "output_dir": str(output_dir),
        "dry_run_command": dry_run_command,
        "real_command": real_command,
        "core_outputs": core_outputs,
        "checkpoint_sec": args.checkpoint_sec,
        "hard_stop_min": args.hard_stop_min,
        "uses_start_process": False,
        "uses_powershell_job": False,
        "environment_record": build_environment_record(),
    }

    dry_result = run_command_capture(
        dry_run_command,
        output_dir / "runner_dry_run_stdout.txt",
        output_dir / "runner_dry_run_stderr.txt",
        timeout_s=max(60.0, args.hard_stop_min * 60.0),
    )
    dry_summary = output_dir / "quality_dry_run_summary.json"
    status["dry_run"] = {
        "exit_code": dry_result.returncode,
        "quality_summary_exists": dry_summary.exists(),
        "quality_summary_path": str(dry_summary),
    }
    if dry_result.returncode != 0 or not dry_summary.exists():
        status["status"] = "dry_run_failed"
        write_status(output_dir, status)
        return status

    if not args.execute:
        status["status"] = "planned_not_executed"
        status["core_output_exists"] = output_exists_map(core_outputs)
        write_status(output_dir, status)
        return status

    start = time.time()
    timeout_s = args.hard_stop_min * 60.0
    real_result = run_command_capture(
        real_command,
        output_dir / "runner_stdout.txt",
        output_dir / "runner_stderr.txt",
        timeout_s=timeout_s,
    )
    elapsed = time.time() - start
    core_exists = output_exists_map(core_outputs)
    status["execution"] = {
        "exit_code": real_result.returncode,
        "runtime_s": elapsed,
        "core_output_exists": core_exists,
    }
    if real_result.returncode == 0 and all(core_exists.values()):
        status["status"] = "kwave_ok"
    elif elapsed >= timeout_s and not any(core_exists.values()):
        status["status"] = "timeout_no_core_output"
    else:
        status["status"] = "kwave_failed_or_incomplete"
    write_status(output_dir, status)
    return status


def main() -> None:
    args, passthrough = split_script_args(sys.argv[1:])
    status = run_runner(args, passthrough)
    print(json.dumps({"status": status.get("status"), "output_dir": status.get("output_dir")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
