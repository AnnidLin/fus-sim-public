from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROGRESS_PATTERN = re.compile(
    r"(?P<current>\d+)/(?P<total>\d+)\s+\["
    r"(?P<elapsed>[^<\]]+)<(?P<remaining>[^,\]]+),\s*"
    r"(?P<seconds>[0-9.]+)s/step\]"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_duration(value: str) -> float:
    parts = [float(part) for part in value.strip().split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    raise ValueError(f"Unsupported duration: {value!r}")


def parse_kwave_progress(text: str) -> dict[str, Any] | None:
    matches = list(PROGRESS_PATTERN.finditer(text))
    if not matches:
        return None
    match = matches[-1]
    current = int(match.group("current"))
    total = int(match.group("total"))
    return {
        "current_step": current,
        "total_steps": total,
        "fraction": current / total if total else 0.0,
        "elapsed_s": parse_duration(match.group("elapsed")),
        "remaining_s": parse_duration(match.group("remaining")),
        "seconds_per_step": float(match.group("seconds")),
    }


def read_tail(path: Path, max_bytes: int = 512 * 1024) -> str:
    if not path.is_file():
        return ""
    with path.open("rb") as handle:
        size = handle.seek(0, os.SEEK_END)
        handle.seek(max(0, size - max_bytes))
        return handle.read().decode("utf-8", errors="replace")


def adjust_emergency_ceiling(
    *,
    current_ceiling_s: float,
    elapsed_s: float,
    remaining_s: float,
    progress_is_advancing: bool,
    maximum_ceiling_s: float,
) -> float:
    if not progress_is_advancing:
        return current_ceiling_s
    projected_total_s = elapsed_s + remaining_s
    if projected_total_s < current_ceiling_s * 0.90:
        return current_ceiling_s
    proposed = math.ceil(projected_total_s * 1.25 / 60.0) * 60.0
    return min(maximum_ceiling_s, max(current_ceiling_s, proposed))


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def append_history(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def core_output_exists(output_dir: Path) -> dict[str, bool]:
    return {
        "pressure": (output_dir / "pressure_max_mpa.npz").is_file(),
        "summary": (output_dir / "summary.json").is_file(),
    }


def stop_process(process: subprocess.Popen[Any]) -> None:
    process.terminate()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=30)


def supervise(
    *,
    command: list[str],
    output_dir: Path,
    checkpoint_sec: float = 120.0,
    poll_sec: float = 5.0,
    stall_stop_sec: float = 1800.0,
    emergency_ceiling_sec: float = 9000.0,
    maximum_ceiling_sec: float = 21600.0,
) -> dict[str, Any]:
    if not command:
        raise ValueError("command must not be empty")
    if checkpoint_sec <= 0 or poll_sec <= 0 or stall_stop_sec <= 0:
        raise ValueError("monitor intervals must be positive")
    if emergency_ceiling_sec <= 0 or maximum_ceiling_sec < emergency_ceiling_sec:
        raise ValueError("invalid emergency ceiling")

    output_dir.mkdir(parents=True, exist_ok=True)
    status_path = output_dir / "monitor_status.json"
    history_path = output_dir / "monitor_history.jsonl"
    stdout_path = output_dir / "monitored_stdout.txt"
    stderr_path = output_dir / "monitored_stderr.txt"
    environment = os.environ.copy()
    temporary_dir = ROOT / ".tmp"
    matplotlib_dir = temporary_dir / "mplconfig-monitored-kwave"
    temporary_dir.mkdir(parents=True, exist_ok=True)
    matplotlib_dir.mkdir(parents=True, exist_ok=True)
    environment["TEMP"] = str(temporary_dir)
    environment["TMP"] = str(temporary_dir)
    environment["MPLCONFIGDIR"] = str(matplotlib_dir)

    started = time.monotonic()
    last_checkpoint = started - checkpoint_sec
    last_activity = started
    last_stdout_size = stdout_path.stat().st_size if stdout_path.exists() else 0
    last_stderr_size = stderr_path.stat().st_size if stderr_path.exists() else 0
    last_progress_step: int | None = None
    heartbeat_count = 0
    ceiling_adjustments: list[dict[str, Any]] = []

    with (
        stdout_path.open("a", encoding="utf-8") as stdout_handle,
        stderr_path.open("a", encoding="utf-8") as stderr_handle,
    ):
        stdout_handle.write(f"\n[MONITOR START {utc_now()}]\n")
        stderr_handle.write(f"\n[MONITOR START {utc_now()}]\n")
        stdout_handle.flush()
        stderr_handle.flush()
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=environment,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
        )

        status: dict[str, Any] = {
            "monitor_version": "1.0.0",
            "status": "running",
            "pid": process.pid,
            "command": command,
            "output_dir": str(output_dir),
            "started_at_utc": utc_now(),
            "checkpoint_sec": checkpoint_sec,
            "stall_stop_sec": stall_stop_sec,
            "emergency_ceiling_s": emergency_ceiling_sec,
            "maximum_ceiling_s": maximum_ceiling_sec,
            "ceiling_adjustments": ceiling_adjustments,
            "heartbeat_count": 0,
        }

        while True:
            now = time.monotonic()
            return_code = process.poll()
            stdout_size = stdout_path.stat().st_size
            stderr_size = stderr_path.stat().st_size
            log_advanced = (
                stdout_size > last_stdout_size or stderr_size > last_stderr_size
            )
            if log_advanced:
                last_activity = now
                last_stdout_size = stdout_size
                last_stderr_size = stderr_size

            if now - last_checkpoint >= checkpoint_sec or return_code is not None:
                stderr_progress = parse_kwave_progress(read_tail(stderr_path))
                stdout_progress = parse_kwave_progress(read_tail(stdout_path))
                progress = stdout_progress or stderr_progress
                progress_advancing = (
                    progress is not None
                    and (
                        last_progress_step is None
                        or progress["current_step"] > last_progress_step
                    )
                )
                if progress_advancing:
                    last_activity = now
                    last_progress_step = progress["current_step"]

                elapsed_s = now - started
                if progress is not None:
                    adjusted = adjust_emergency_ceiling(
                        current_ceiling_s=emergency_ceiling_sec,
                        elapsed_s=elapsed_s,
                        remaining_s=progress["remaining_s"],
                        progress_is_advancing=progress_advancing,
                        maximum_ceiling_s=maximum_ceiling_sec,
                    )
                    if adjusted > emergency_ceiling_sec:
                        ceiling_adjustments.append(
                            {
                                "at_elapsed_s": elapsed_s,
                                "old_ceiling_s": emergency_ceiling_sec,
                                "new_ceiling_s": adjusted,
                                "reason": "active progress projects close to current emergency ceiling",
                            }
                        )
                        emergency_ceiling_sec = adjusted

                heartbeat_count += 1
                status.update(
                    {
                        "heartbeat_at_utc": utc_now(),
                        "heartbeat_count": heartbeat_count,
                        "elapsed_s": elapsed_s,
                        "return_code": return_code,
                        "progress": progress,
                        "progress_is_advancing": progress_advancing,
                        "seconds_since_log_or_progress_activity": now - last_activity,
                        "stdout_size_bytes": stdout_size,
                        "stderr_size_bytes": stderr_size,
                        "emergency_ceiling_s": emergency_ceiling_sec,
                        "ceiling_adjustments": ceiling_adjustments,
                        "core_output_exists": core_output_exists(output_dir),
                    }
                )
                atomic_write_json(status_path, status)
                append_history(history_path, status)
                last_checkpoint = now

            if return_code is not None:
                core_exists = core_output_exists(output_dir)
                status["return_code"] = return_code
                status["core_output_exists"] = core_exists
                status["finished_at_utc"] = utc_now()
                status["elapsed_s"] = time.monotonic() - started
                status["status"] = (
                    "completed"
                    if return_code == 0 and all(core_exists.values())
                    else "failed_or_incomplete"
                )
                atomic_write_json(status_path, status)
                append_history(history_path, status)
                return status

            if now - last_activity >= stall_stop_sec:
                stop_process(process)
                status.update(
                    {
                        "status": "stalled_stopped",
                        "finished_at_utc": utc_now(),
                        "elapsed_s": time.monotonic() - started,
                        "stop_reason": "no log or progress activity within stall window",
                        "core_output_exists": core_output_exists(output_dir),
                    }
                )
                atomic_write_json(status_path, status)
                append_history(history_path, status)
                return status

            if now - started >= emergency_ceiling_sec:
                stop_process(process)
                status.update(
                    {
                        "status": "emergency_ceiling_stopped",
                        "finished_at_utc": utc_now(),
                        "elapsed_s": time.monotonic() - started,
                        "stop_reason": (
                            "maximum monitored wall time reached after dynamic adjustments"
                        ),
                        "core_output_exists": core_output_exists(output_dir),
                    }
                )
                atomic_write_json(status_path, status)
                append_history(history_path, status)
                return status

            time.sleep(poll_sec)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Supervise one k-Wave process with heartbeat, dynamic ETA, and stall protection."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--checkpoint-sec", type=float, default=120.0)
    parser.add_argument("--poll-sec", type=float, default=5.0)
    parser.add_argument("--stall-stop-min", type=float, default=30.0)
    parser.add_argument("--emergency-ceiling-min", type=float, default=150.0)
    parser.add_argument("--maximum-ceiling-min", type=float, default=360.0)
    parser.add_argument(
        "--allow-existing-core-output",
        action="store_true",
        help="Allow a directory that already contains summary/pressure core outputs.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("A child command is required after --")
    if any(core_output_exists(args.output_dir).values()) and not args.allow_existing_core_output:
        raise SystemExit("Refusing output directory with existing core output")
    result = supervise(
        command=command,
        output_dir=args.output_dir,
        checkpoint_sec=args.checkpoint_sec,
        poll_sec=args.poll_sec,
        stall_stop_sec=args.stall_stop_min * 60.0,
        emergency_ceiling_sec=args.emergency_ceiling_min * 60.0,
        maximum_ceiling_sec=args.maximum_ceiling_min * 60.0,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "elapsed_s": result.get("elapsed_s"),
                "output_dir": result["output_dir"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
