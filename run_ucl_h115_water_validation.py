"""Guard exactly one UCL H115 homogeneous-water validation simulation."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from windows_process_tree_guard import GuardThresholds, ProcessTreeSampler, breach_reasons, set_below_normal_priority, terminate_process_tree


ROOT = Path(__file__).resolve().parent
PYTHON = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")
MODEL_DIR = ROOT / "outputs" / "ucl_h115_water_model_dx0p5_20260812"
BRIEF = ROOT / "outputs" / "evidence_briefs" / "ucl_h115_water_validation_20260818" / "evidence_brief.json"
MEASUREMENT = ROOT / "outputs" / "ucl_270khz_freefield_summary_20260812" / "summary.json"
CONTRACT = ROOT / "outputs" / "ucl_h115_water_papergrade_dryrun_dx0p5_20260812" / "validation_contract.json"
PML_SIZE = 16
FULL_MODEL = False
RADIUS_MM = 61.39
APERTURE_MM = 50.40


def configure(
    model_dir: Path,
    brief: Path,
    pml_size: int,
    full_model: bool = False,
    radius_mm: float = 61.39,
    aperture_mm: float = 50.40,
) -> None:
    """Configure one explicit H115 run while retaining the guarded workflow."""
    global MODEL_DIR, BRIEF, PML_SIZE, FULL_MODEL, RADIUS_MM, APERTURE_MM
    if pml_size <= 0 or radius_mm <= 0 or aperture_mm <= 0:
        raise ValueError("PML size and source dimensions must be positive")
    if aperture_mm > 2.0 * radius_mm:
        raise ValueError("aperture diameter cannot exceed the source sphere diameter")
    MODEL_DIR = model_dir
    BRIEF = brief
    PML_SIZE = pml_size
    FULL_MODEL = full_model
    RADIUS_MM = radius_mm
    APERTURE_MM = aperture_mm


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def command(output_dir: Path, dry_run: bool) -> list[str]:
    value = [
        str(PYTHON), "simulate_kwave_3d_focus.py", "--model", str(MODEL_DIR / "acoustic_model_3d.npz"),
        "--entry-plan", str(MODEL_DIR / "entry_plan.json"), "--output-dir", str(output_dir),
        "--preset", "standard", "--backend", "cpp", "--device", "cpu", "--frequency-hz", "270000",
        "--cycles", "16", "--sim-time-us", "180", "--cfl", "0.1", "--pml-size", str(PML_SIZE),
        "--aperture-mm", f"{APERTURE_MM:g}", "--radius-mm", f"{RADIUS_MM:g}", "--nearfield-mm", "5",
        "--source-pressure-pa", "1000000",
    ]
    if dry_run:
        value.append("--dry-run-quality")
    if FULL_MODEL:
        value.append("--full")
    return value


def preflight(output_dir: Path) -> dict:
    brief, measurement, contract = load(BRIEF), load(MEASUREMENT), load(CONTRACT)
    checks = {
        "brief_authorized": brief.get("status") == "authorized_pending_exact_dry_run_and_device_gate",
        "measurement_complete": measurement.get("status") == "completed",
        "measurement_hash_verified": measurement.get("input", {}).get("sha256_matches_intake") is True,
        "contract_preregistered": contract.get("status") == "preregistered_before_pressure_simulation",
        "model_exists": (MODEL_DIR / "acoustic_model_3d.npz").is_file(),
        "entry_plan_exists": (MODEL_DIR / "entry_plan.json").is_file(),
        "fresh_output": not any((output_dir / name).exists() for name in ("pressure_max_mpa.npz", "summary.json", "focus_metrics.json")),
    }
    return {"status": "passed" if all(checks.values()) else "failed", "checks": checks}


def exact_dry_run(output_dir: Path) -> dict:
    gate = preflight(output_dir)
    if gate["status"] != "passed":
        raise RuntimeError(f"preflight failed: {gate['checks']}")
    process = subprocess.run(command(output_dir, True), cwd=ROOT, text=True, capture_output=True, timeout=600)
    (output_dir / "dry_run_stdout.txt").write_text(process.stdout, encoding="utf-8")
    (output_dir / "dry_run_stderr.txt").write_text(process.stderr, encoding="utf-8")
    quality_path = output_dir / "quality_dry_run_summary.json"
    quality = load(quality_path) if quality_path.exists() else {}
    brief = load(BRIEF)
    candidate = brief.get("candidate", {})
    required_ppw = float(candidate.get("minimum_ppw", 8.0))
    expected_grid = candidate.get("expected_grid")
    source_labels = quality.get("source", {}).get("source_label_counts", {})
    entry = quality.get("model", {}).get("entry_plan", {})
    checks = {
        "return_code_zero": process.returncode == 0,
        "quality_exists": quality_path.exists(),
        "ppw_meets_brief": float(quality.get("simulation_quality", {}).get("ppw_min_sound_speed", 0)) >= required_ppw,
        "pml_matches_request": int(quality.get("simulation_quality", {}).get("pml_size", 0)) == PML_SIZE,
        "cfl_0p1": float(quality.get("simulation_quality", {}).get("cfl", 0)) == 0.1,
        "memory_under_gate": float(quality.get("simulation_quality", {}).get("memory_estimate", {}).get("estimated_mb", 1e9)) < 16 * 1024,
        "expected_grid": expected_grid is None or quality.get("model", {}).get("model_shape") == expected_grid,
        "source_background_only": bool(source_labels) and set(source_labels) == {"0"},
        "source_target_distance_within_one_voxel": abs(float(entry.get("source_to_target_distance_mm", 1e9)) - RADIUS_MM) <= float(entry.get("dx_m", 0.0)) * 1e3,
        "radius_matches_brief": abs(float(candidate.get("radius_mm", RADIUS_MM)) - RADIUS_MM) < 1e-9,
        "aperture_matches_brief": abs(float(candidate.get("aperture_diameter_mm", APERTURE_MM)) - APERTURE_MM) < 1e-9,
        "full_model_requirement_met": not candidate.get("full_model_required_for_domain_match", False) or quality.get("config", {}).get("quick_mode") is False,
    }
    report = {"status": "passed" if all(checks.values()) else "failed", "at_utc": now(), "command": command(output_dir, True), "checks": checks}
    write_json(output_dir / "exact_dry_run_report.json", report)
    return report


def validate_outputs(output_dir: Path) -> dict:
    paths = {name: output_dir / name for name in ("pressure_max_mpa.npz", "summary.json", "focus_metrics.json")}
    checks = {f"{name}_exists": path.is_file() for name, path in paths.items()}
    if checks["pressure_max_mpa.npz_exists"]:
        with np.load(paths["pressure_max_mpa.npz"]) as data:
            pressure = np.asarray(data["pressure_max_mpa"])
            checks["pressure_finite_nonzero"] = bool(np.isfinite(pressure).all() and float(pressure.max()) > 0)
    else:
        checks["pressure_finite_nonzero"] = False
    return {"status": "passed" if all(checks.values()) else "failed", "checks": checks}


def execute(output_dir: Path, hard_stop_min: float) -> dict:
    dry = load(output_dir / "exact_dry_run_report.json")
    gate = preflight(output_dir)
    if dry.get("status") != "passed" or gate["status"] != "passed":
        raise RuntimeError("launch requires passed exact dry-run and preflight")
    env = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[key] = "6"
    started = time.monotonic()
    status_path, device_path = output_dir / "execution_status.json", output_dir / "device_status.json"
    write_json(status_path, {"status": "starting", "at_utc": now(), "command": command(output_dir, False), "preflight": gate})
    flags = 0x00004000 | 0x08000000 if os.name == "nt" else 0
    with (output_dir / "solver_stdout.txt").open("wb") as stdout, (output_dir / "solver_stderr.txt").open("wb") as stderr:
        process = subprocess.Popen(command(output_dir, False), cwd=ROOT, env=env, stdout=stdout, stderr=stderr, creationflags=flags)
        set_below_normal_priority(process.pid)
        write_json(status_path, {"status": "running", "pid": process.pid, "at_utc": now(), "command": command(output_dir, False), "preflight": gate})
        sampler = ProcessTreeSampler(process.pid)
        thresholds = GuardThresholds(maximum_equivalent_cores=6.5, maximum_working_set_gib=16.0, minimum_free_memory_gib=4.0)
        cpu_streak, stopped = 0, None
        history = output_dir / "device_history.jsonl"
        while process.poll() is None:
            sample = sampler.sample()
            reasons = breach_reasons(sample, thresholds)
            cpu_streak = cpu_streak + 1 if "equivalent_cpu_cores" in reasons else 0
            immediate = [reason for reason in reasons if reason != "equivalent_cpu_cores"]
            if cpu_streak >= 3:
                immediate.append("sustained_equivalent_cpu_cores")
            if time.monotonic() - started > hard_stop_min * 60:
                immediate.append("hard_stop_minutes")
            sample.update({"at_utc": now(), "cpu_breach_streak": cpu_streak, "breach_reasons": immediate})
            with history.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(sample, ensure_ascii=False) + "\n")
            write_json(device_path, {"status": "stopping" if immediate else "running", "latest_sample": sample})
            if immediate:
                stopped = ",".join(immediate)
                terminate_process_tree(process.pid)
                break
            time.sleep(10)
        return_code = process.wait()
    validation = validate_outputs(output_dir)
    result = {"status": "completed" if return_code == 0 and stopped is None and validation["status"] == "passed" else "failed", "return_code": return_code, "stopped_reason": stopped, "wall_seconds": time.monotonic() - started, "output_validation": validation, "finished_at_utc": now()}
    write_json(output_dir / "stage_result.json", result)
    write_json(status_path, {"status": result["status"], "result": result})
    write_json(device_path, {"status": result["status"], "stage_result": str(output_dir / "stage_result.json")})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--hard-stop-min", type=float, default=120.0)
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--brief", type=Path, default=BRIEF)
    parser.add_argument("--pml-size", type=int, default=PML_SIZE)
    parser.add_argument("--radius-mm", type=float, default=RADIUS_MM)
    parser.add_argument("--aperture-mm", type=float, default=APERTURE_MM)
    parser.add_argument("--full-model", action="store_true", help="Disable quick cropping to preserve the model's full physical extent.")
    args = parser.parse_args()
    try:
        configure(args.model_dir, args.brief, args.pml_size, args.full_model, args.radius_mm, args.aperture_mm)
        value = exact_dry_run(args.output_dir) if args.dry_run else execute(args.output_dir, args.hard_stop_min) if args.execute else {"status": "planned_not_executed", "preflight": preflight(args.output_dir), "command": command(args.output_dir, False)}
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return 0 if value.get("status") in {"passed", "completed", "planned_not_executed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
