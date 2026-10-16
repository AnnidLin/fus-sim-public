from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")
DEFAULT_RUN_DIR = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p5_pointwave_20260716/run"
DEFAULT_STATUS_PATH = PROJECT_ROOT / "outputs/overnight_work_summary_20260715/LIVE_STATUS.md"
DEFAULT_REGENERATE = PROJECT_ROOT / "regenerate_paper_route_after_dx05.py"
POLL_INTERVAL_S = 60
MAX_POLL_MIN = 600


def write_status(status_path: Path, message: str) -> None:
    text = f"""# Live Status — 2026-07-16

## Currently running

- **Watcher**: `watch_dx05_and_regenerate.py`

## Latest update

{message}
"""
    status_path.write_text(text, encoding="utf-8")


def run_regeneration(regenerate_script: Path) -> bool:
    command = [str(PYTHON_EXE), str(regenerate_script)]
    result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    log_path = regenerate_script.parent / "regeneration_log.txt"
    log_path.write_text(
        f"returncode: {result.returncode}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}",
        encoding="utf-8",
    )
    return result.returncode == 0


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--status-path", type=Path, default=DEFAULT_STATUS_PATH)
    parser.add_argument("--regenerate-script", type=Path, default=DEFAULT_REGENERATE)
    args = parser.parse_args()

    write_status(args.status_path, f"Watcher started for {args.run_dir}. Polling for pressure_max_mpa.npz + summary.json + target_waveform.")
    start = time.time()
    while True:
        elapsed_min = (time.time() - start) / 60
        if elapsed_min > MAX_POLL_MIN:
            write_status(args.status_path, f"Watcher timed out after {MAX_POLL_MIN} min. Outputs did not appear in {args.run_dir}.")
            return

        if outputs_ready(args.run_dir):
            write_status(args.status_path, f"Outputs detected in {args.run_dir}. Starting regeneration...")
            ok = run_regeneration(args.regenerate_script)
            if ok:
                write_status(args.status_path, "Automatic regeneration completed. Paper-route outputs refreshed.")
            else:
                write_status(args.status_path, "Outputs detected, but regeneration failed. See regeneration_log.txt.")
            return

        write_status(args.status_path, f"Polling for outputs in {args.run_dir}... watcher elapsed: {elapsed_min:.1f} min.")
        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
