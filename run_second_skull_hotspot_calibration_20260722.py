from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")
OUTPUT = ROOT / "outputs" / "second_skull_hotspot_calibration_20260722" / "run"
EVIDENCE = ROOT / "outputs" / "evidence_briefs" / "second_skull_hotspot_calibration_20260722" / "evidence_brief.json"
MODEL = Path("outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/acoustic_model_3d.npz")
ENTRY_PLAN = Path("outputs/a5_heldout_d60_trajectory_selection_20260719/offset_y-10p0_z-02p5/entry_plan.json")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def command(dry_run: bool) -> list[str]:
    result = [
        str(PYTHON), "simulate_time_reversal_focus.py",
        "--stage", "calibrate",
        "--model", str(MODEL),
        "--entry-plan", str(ENTRY_PLAN),
        "--calibration-point-index", "77,120,97",
        "--output-dir", str(OUTPUT.relative_to(ROOT)),
        "--preset", "standard",
        "--sim-time-us", "100",
        "--frequency-hz", "500000",
        "--cycles", "2",
        "--calibration-pressure-pa", "1000000",
        "--pml-size", "12",
        "--cfl", "0.2",
        "--aperture-mm", "60",
        "--radius-mm", "74.4353753",
        "--quick-lateral-mm", "17",
        "--quick-post-target-mm", "8",
        "--no-record-target-waveform",
        "--backend", "python",
        "--device", "cpu",
    ]
    if dry_run:
        result.append("--dry-run-quality")
    return result


def validate_dryrun(summary: dict) -> dict[str, bool]:
    cfg = summary["config"]
    model = summary["model"]
    source = summary["source"]
    point = source["calibration_point"]
    quality = summary["simulation_quality"]
    checks = {
        "dry_run_only": summary.get("dry_run_quality_only") is True,
        "grid_exact": model["model_shape"] == [125, 60, 50],
        "crop_exact": model["crop_origin_ijk"] == [37, 100, 79],
        "target_exact": model["target_index_ijk"] == [114, 36, 26],
        "hotspot_full_exact": point["full_index_ijk"] == [77, 120, 97],
        "hotspot_local_exact": point["local_index_ijk"] == [40, 20, 18],
        "hotspot_is_skull": point["material_label"] == 2,
        "bowl_target_frozen": point["bowl_geometry_target_local_ijk"] == [114, 36, 26],
        "calibration_independent": point["independent_of_bowl_geometry"] is True,
        "source_points_exact": source["source_points"] == 2979,
        "source_background_only": source["source_label_counts"] == {"0": 2979},
        "frequency_cycles_exact": cfg["frequency_hz"] == 500000.0 and cfg["tone_burst_cycles"] == 2,
        "geometry_exact": abs(cfg["aperture_diameter_m"] - 0.06) < 1e-12 and abs(cfg["transducer_radius_m"] - 0.0744353753) < 1e-12,
        "pml_cfl_ppw_exact": cfg["pml_size"] == 12 and cfg["cfl"] == 0.2 and abs(quality["ppw_min_sound_speed"] - 4.0) < 1e-6,
        "backend_cpu_exact": cfg["backend"] == "python" and cfg["device"] == "cpu",
        "target_waveform_disabled": cfg["record_target_waveform"] is False,
        "resource_bound": quality["voxel_count"] == 375000 and quality["nt"] == 1867,
    }
    return {name: bool(value) for name, value in checks.items()}


def write_status(status: dict) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "runner_status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")


def execute(cmd: list[str], status: dict, checkpoint_s: int, hard_stop_s: int) -> int:
    started = time.monotonic()
    with (OUTPUT / "runner_stdout.txt").open("w", encoding="utf-8") as stdout, (OUTPUT / "runner_stderr.txt").open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(cmd, cwd=ROOT, stdout=stdout, stderr=stderr)
        status["pid"] = process.pid
        status["checkpoints"] = []
        write_status(status)
        next_checkpoint = float(checkpoint_s)
        while process.poll() is None:
            elapsed = time.monotonic() - started
            if elapsed >= hard_stop_s:
                process.kill()
                process.wait()
                status.update({"hard_stop_triggered": True, "elapsed_s": round(elapsed, 1)})
                write_status(status)
                return 124
            if elapsed >= next_checkpoint:
                status["checkpoints"].append({"elapsed_s": round(elapsed, 1), "recorded_utc": now()})
                status["elapsed_s"] = round(elapsed, 1)
                write_status(status)
                next_checkpoint += checkpoint_s
            time.sleep(5)
    status["elapsed_s"] = round(time.monotonic() - started, 1)
    return int(process.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run exactly one second skull-hotspot calibration.")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    if evidence["authorization"]["hotspot_calibration_pressure_runs"] != 1:
        raise ValueError("Evidence Brief does not authorize exactly one calibration")
    if (OUTPUT / "element_signals.npz").exists() or (OUTPUT / "summary_calibrate.json").exists():
        raise FileExistsError("Exactly-one calibration output already exists")
    resource = evidence["resource_gate"]
    status = {
        "status": "dry_run_started",
        "evidence_brief": str(EVIDENCE.relative_to(ROOT)),
        "output_dir": str(OUTPUT.relative_to(ROOT)),
        "pressure_run_limit": 1,
        "pressure_runs_started": 0,
        "checkpoint_s": resource["checkpoint_s"],
        "hard_stop_s": resource["hard_stop_s"],
        "expected_runtime_s_range": resource["expected_runtime_s_range"],
        "dry_run_command": command(True),
        "execution_command": command(False),
        "started_utc": now(),
    }
    write_status(status)
    dry = subprocess.run(command(True), cwd=ROOT, capture_output=True, text=True, timeout=120, check=False)
    (OUTPUT / "runner_dry_run_stdout.txt").write_text(dry.stdout, encoding="utf-8")
    (OUTPUT / "runner_dry_run_stderr.txt").write_text(dry.stderr, encoding="utf-8")
    dry_path = OUTPUT / "quality_dry_run_summary.json"
    if dry.returncode != 0 or not dry_path.exists():
        status.update({"status": "dry_run_failed", "dry_run_returncode": dry.returncode})
        write_status(status)
        raise SystemExit(1)
    checks = validate_dryrun(json.loads(dry_path.read_text(encoding="utf-8")))
    status.update({"dry_run_checks": checks, "dry_run_gate": "pass" if all(checks.values()) else "fail"})
    if not all(checks.values()):
        status["status"] = "dry_run_gate_failed"
        write_status(status)
        raise SystemExit(1)
    if not args.execute:
        status["status"] = "planned_not_executed"
        write_status(status)
        print(json.dumps({"status": status["status"], "checks": sum(checks.values()), "total": len(checks)}))
        return
    status.update({"status": "calibration_running", "pressure_runs_started": 1, "execution_started_utc": now()})
    write_status(status)
    returncode = execute(command(False), status, resource["checkpoint_s"], resource["hard_stop_s"])
    signals = OUTPUT / "element_signals.npz"
    summary = OUTPUT / "summary_calibrate.json"
    complete = returncode == 0 and signals.exists() and summary.exists()
    status.update({
        "status": "kwave_ok" if complete else "kwave_failed_or_incomplete",
        "returncode": returncode,
        "execution_finished_utc": now(),
        "element_signals_exists": signals.exists(),
        "summary_calibrate_exists": summary.exists(),
        "element_signals_sha256": hashlib.sha256(signals.read_bytes()).hexdigest() if signals.exists() else None,
    })
    write_status(status)
    print(json.dumps({"status": status["status"], "elapsed_s": status.get("elapsed_s")}))
    if not complete:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
