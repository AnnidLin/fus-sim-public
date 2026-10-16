from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")
OUTPUT = Path("outputs/a5_hotspot_suppression_hamming_20260720/offset_y-10p0_z-02p5/tr")
QUALITY = OUTPUT / "quality_dry_run_summary.json"
STATUS = OUTPUT / "runner_status.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write(payload: dict) -> None:
    STATUS.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def verify_preflight() -> dict:
    dry = json.loads(QUALITY.read_text(encoding="utf-8"))
    prep = json.loads((OUTPUT / "hamming_replay_preparation.json").read_text(encoding="utf-8"))
    quality = dry["simulation_quality"]
    source = dry["source"]
    checks = {
        "hamming_prepared": prep["window"] == "hamming" and prep["pressure_execution_authorized"],
        "signals_available": dry["config"]["element_signals_available"] is True,
        "mask_exact": source["time_reversal"]["mask_check"] == "mask_grid_dt_target_exact_match",
        "source_safe": source["source_label_counts"] == {"0": source["source_points"]},
        "numerics": quality["pml_size"] == 12 and quality["cfl"] == 0.2 and quality["ppw_min_sound_speed"] >= 3.99,
        "resource": 0 < quality["voxel_count"] < 2_000_000,
    }
    if not all(checks.values()):
        raise RuntimeError(f"Preflight failed: {checks}")
    return checks


def main() -> None:
    checks = verify_preflight()
    command = [
        str(PYTHON), "simulate_time_reversal_focus.py",
        "--stage", "refocus",
        "--model", "outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/acoustic_model_3d.npz",
        "--entry-plan", "outputs/a5_heldout_d60_trajectory_selection_20260719/offset_y-10p0_z-02p5/entry_plan.json",
        "--output-dir", str(OUTPUT),
        "--sim-time-us", "100", "--pml-size", "12", "--cfl", "0.2",
        "--aperture-mm", "60", "--radius-mm", "74.4353753",
        "--quick-lateral-mm", "17", "--quick-post-target-mm", "8",
        "--preset", "quick", "--cycles", "2", "--no-record-target-waveform",
    ]
    status = {
        "status": "running",
        "intervention": "radial_hamming_aperture_weighting",
        "protocol": "outputs/evidence_briefs/a5_hotspot_suppression_hamming/evidence_brief.md",
        "preflight_checks": checks,
        "command": command,
        "started_utc": now(),
        "checkpoints": [],
    }
    write(status)
    started = time.monotonic()
    next_checkpoint = 120.0
    with (OUTPUT / "runner_refocus_stdout.txt").open("w", encoding="utf-8") as stdout, (OUTPUT / "runner_refocus_stderr.txt").open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        status["pid"] = process.pid
        write(status)
        while process.poll() is None:
            elapsed = time.monotonic() - started
            if elapsed >= 120 * 60:
                process.kill()
                process.wait()
                status["timeout"] = True
                break
            if elapsed >= next_checkpoint:
                status["checkpoints"].append({"elapsed_s": round(elapsed, 1), "recorded_utc": now()})
                write(status)
                next_checkpoint += 120.0
            time.sleep(5)
    returncode = 124 if status.get("timeout") else int(process.returncode)
    complete = returncode == 0 and (OUTPUT / "summary.json").exists() and (OUTPUT / "pressure_max_mpa.npz").exists()
    status.update(
        {
            "status": "kwave_ok" if complete else "runtime_failed",
            "returncode": returncode,
            "elapsed_s": round(time.monotonic() - started, 1),
            "finished_utc": now(),
        }
    )
    write(status)
    print(json.dumps({"status": status["status"], "elapsed_s": status["elapsed_s"]}))
    if not complete:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
