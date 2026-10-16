"""Watch for the dx0.375 point-wave run to land, then run the mechanical closeout chain.

Pattern follows watch_dx05_and_regenerate.py (established 2026-07-16).

Chain (in order, stop-on-fail for generators, validators always run):
  1. generate_d60_grid_convergence_three_level_20260719.py  (pending -> three-level report)
  2. generate_run_ledger.py
  3. generate_evidence_registry.py
  4. generate_reproducibility_manifest.py
  5. generate_final_reproducibility_package.py
  6-10. validate_run_ledger / validate_evidence_registry /
        validate_reproducibility_manifest / validate_final_reproducibility_package /
        validate_gate_state_machine

Deliberately NOT done here (agent judgment required, next session):
  - paper-route regeneration (regenerate_paper_route_after_dx05.py)
  - document updates (ACTIVE_WORK_SUMMARY / HANDOFF_LOG / AI_PROJECT_SNAPSHOT / AI_TODO)
  - git commit

Outputs: CLOSEOUT_STATUS.md (live) + closeout_log_20260719.json (final record)
next to the run directory.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")
DEFAULT_RUN_DIR = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p375_pointwave_20260718/run"
DEFAULT_STATUS_PATH = DEFAULT_RUN_DIR.parent / "CLOSEOUT_STATUS.md"
DEFAULT_LOG_PATH = DEFAULT_RUN_DIR.parent / "closeout_log_20260719.json"
POLL_INTERVAL_S = 60
DEFAULT_MAX_POLL_MIN = 720  # dx0.375 ETA 2026-07-19 17:00-20:00; watcher starts ~10:45

GENERATORS = [
    "generate_d60_grid_convergence_three_level_20260719.py",
    "generate_run_ledger.py",
    "generate_evidence_registry.py",
    "generate_reproducibility_manifest.py",
    "generate_final_reproducibility_package.py",
]
VALIDATORS = [
    "validate_run_ledger.py",
    "validate_evidence_registry.py",
    "validate_reproducibility_manifest.py",
    "validate_final_reproducibility_package.py",
    "validate_gate_state_machine.py",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_status(status_path: Path, message: str) -> None:
    text = f"""# dx0.375 Closeout Live Status

- **Watcher**: `watch_dx0375_and_closeout_20260719.py`
- **Updated (UTC)**: {utc_now()}

## Latest update

{message}
"""
    status_path.write_text(text, encoding="utf-8")


def outputs_ready(run_dir: Path) -> bool:
    pressure_path = run_dir / "pressure_max_mpa.npz"
    summary_path = run_dir / "summary.json"
    if not pressure_path.exists() or not summary_path.exists():
        return False
    try:
        with np.load(pressure_path) as data:
            has_waveform = "target_waveform" in data.files
            finite = bool(np.all(np.isfinite(data["pressure_max_mpa"])))
        return has_waveform and finite
    except Exception:
        return False


def run_script(script: str) -> dict[str, object]:
    command = [str(PYTHON_EXE), str(PROJECT_ROOT / script)]
    result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    return {
        "script": script,
        "returncode": result.returncode,
        "stdout_tail": result.stdout.strip().splitlines()[-3:] if result.stdout else [],
        "stderr_tail": result.stderr.strip()[-500:] if result.stderr else "",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--status-path", type=Path, default=DEFAULT_STATUS_PATH)
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--max-poll-min", type=float, default=DEFAULT_MAX_POLL_MIN)
    args = parser.parse_args()

    write_status(args.status_path, f"Watcher started. Polling {args.run_dir} for pressure_max_mpa.npz + summary.json + target_waveform (finite check).")
    start = time.time()
    while True:
        elapsed_min = (time.time() - start) / 60
        if elapsed_min > args.max_poll_min:
            write_status(args.status_path, f"Watcher timed out after {args.max_poll_min} min. Outputs did not appear. Manual closeout required.")
            return

        if outputs_ready(args.run_dir):
            break

        write_status(args.status_path, f"Polling... watcher elapsed {elapsed_min:.1f} min of max {args.max_poll_min} min.")
        time.sleep(POLL_INTERVAL_S)

    write_status(args.status_path, "Outputs detected. Starting closeout chain (1 three-level generator + 4 governance generators + 5 validators)...")
    results: list[dict[str, object]] = []
    failed_at: str | None = None
    for script in GENERATORS:
        info = run_script(script)
        info["phase"] = "generator"
        results.append(info)
        if info["returncode"] != 0:
            failed_at = script
            break
    for script in VALIDATORS:
        info = run_script(script)
        info["phase"] = "validator"
        results.append(info)
        if info["returncode"] != 0 and failed_at is None:
            failed_at = script

    record = {
        "finished_at_utc": utc_now(),
        "run_dir": str(args.run_dir),
        "failed_at": failed_at,
        "all_green": failed_at is None,
        "results": results,
    }
    args.log_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    if failed_at is None:
        write_status(args.status_path, f"Closeout chain ALL GREEN. Log: {args.log_path.name}. Remaining for next session: docs update + git commit (and paper-route decision).")
    else:
        write_status(args.status_path, f"Closeout chain FAILED at {failed_at}. See {args.log_path.name} for stderr tails.")


if __name__ == "__main__":
    main()
