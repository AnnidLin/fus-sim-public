from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")
MODEL = Path("outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/acoustic_model_3d.npz")
SELECTION = Path("outputs/a5_heldout_d60_trajectory_selection_20260719")
OUTPUT = Path("outputs/a5_heldout_tr_confirmation_20260719")
TRAJECTORIES = ["offset_y-10p0_z-02p5", "offset_y+05p0_z+05p0", "offset_y+12p5_z-15p0"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def command(stage: str, trajectory: str, dry_run: bool) -> list[str]:
    result = [
        str(PYTHON), "simulate_time_reversal_focus.py",
        "--stage", stage,
        "--model", str(MODEL),
        "--entry-plan", str(SELECTION / trajectory / "entry_plan.json"),
        "--output-dir", str(OUTPUT / trajectory / "tr"),
        "--sim-time-us", "100",
        "--pml-size", "12",
        "--cfl", "0.2",
        "--aperture-mm", "60",
        "--radius-mm", "74.4353753",
        "--quick-lateral-mm", "17",
        "--quick-post-target-mm", "8",
        "--preset", "quick",
        "--cycles", "2",
        "--no-record-target-waveform",
    ]
    if dry_run:
        result.append("--dry-run-quality")
    return result


def write_status(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def run_stage(trajectory: str, stage: str, dry_run: bool, status: dict) -> bool:
    arm = OUTPUT / trajectory / "tr"
    arm.mkdir(parents=True, exist_ok=True)
    label = f"{stage}_dry_run" if dry_run else stage
    cmd = command(stage, trajectory, dry_run)
    record = {"stage": label, "command": cmd, "started_utc": now()}
    status["stages"].append(record)
    write_status(arm / "runner_status.json", status)
    started = time.monotonic()
    with (arm / f"runner_{label}_stdout.txt").open("w", encoding="utf-8") as stdout, (arm / f"runner_{label}_stderr.txt").open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(cmd, cwd=ROOT, stdout=stdout, stderr=stderr)
        record["pid"] = process.pid
        record["checkpoints"] = []
        next_checkpoint = 120.0
        while process.poll() is None:
            elapsed = time.monotonic() - started
            if elapsed >= 150 * 60:
                process.kill()
                process.wait()
                record["timeout"] = True
                break
            if elapsed >= next_checkpoint:
                record["checkpoints"].append({"elapsed_s": round(elapsed, 1), "recorded_utc": now()})
                write_status(arm / "runner_status.json", status)
                next_checkpoint += 120.0
            time.sleep(5)
        returncode = 124 if record.get("timeout") else int(process.returncode)
    record.update({"returncode": returncode, "elapsed_s": round(time.monotonic() - started, 1), "finished_utc": now()})
    if dry_run:
        summary = arm / "quality_dry_run_summary.json"
        gate_pass = returncode == 0 and summary.exists()
        if gate_pass:
            data = json.loads(summary.read_text(encoding="utf-8"))
            quality = data.get("simulation_quality", {})
            source = data.get("source", {})
            labels = source.get("source_label_counts", {})
            gate_pass = bool(
                data.get("dry_run_quality_only")
                and quality.get("ppw_min_sound_speed", 0) >= 3.99
                and quality.get("pml_size") == 12
                and quality.get("cfl") == 0.2
                and quality.get("voxel_count", 0) > 0
                and quality.get("voxel_count", 0) < 2_000_000
                and labels == {"0": source.get("source_points")}
            )
        record["gate"] = "gate_pass" if gate_pass else "gate_fail"
        write_status(arm / "runner_status.json", status)
        return gate_pass
    write_status(arm / "runner_status.json", status)
    return returncode == 0


def run_trajectory(trajectory: str) -> bool:
    arm = OUTPUT / trajectory / "tr"
    status_path = arm / "runner_status.json"
    if status_path.exists() and (arm / "summary.json").exists():
        previous = json.loads(status_path.read_text(encoding="utf-8"))
        if previous.get("status") == "kwave_ok":
            print(json.dumps({"trajectory": trajectory, "status": "already_complete"}), flush=True)
            return True
    status = {
        "trajectory": trajectory,
        "arm": "tr",
        "status": "running",
        "protocol": "outputs/evidence_briefs/a5_heldout_tr_confirmation/evidence_brief.md",
        "started_utc": now(),
        "stages": [],
    }
    write_status(status_path, status)
    for stage in ("calibrate", "refocus"):
        if stage == "calibrate" and (arm / "summary_calibrate.json").exists() and (arm / "element_signals.npz").exists():
            status["stages"].append({"stage": "calibrate", "status": "reused_complete_checkpoint", "recorded_utc": now()})
            write_status(status_path, status)
            continue
        if not run_stage(trajectory, stage, True, status):
            status.update({"status": "dry_run_failed", "failed_stage": stage, "finished_utc": now()})
            write_status(status_path, status)
            return False
        if not run_stage(trajectory, stage, False, status):
            status.update({"status": "runtime_failed", "failed_stage": stage, "finished_utc": now()})
            write_status(status_path, status)
            return False
    complete = (arm / "summary.json").exists() and (arm / "pressure_max_mpa.npz").exists()
    status.update({"status": "kwave_ok" if complete else "output_incomplete", "finished_utc": now()})
    write_status(status_path, status)
    print(json.dumps({"trajectory": trajectory, "status": status["status"]}), flush=True)
    return complete


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = {trajectory: run_trajectory(trajectory) for trajectory in TRAJECTORIES}
    overall = {"status": "complete" if all(results.values()) else "completed_with_failures", "finished_utc": now(), "results": results}
    write_status(OUTPUT / "execution_summary.json", overall)
    print(json.dumps(overall), flush=True)
    if not all(results.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
