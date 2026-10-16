"""End-to-end time-reversal reciprocity smoke test on a small homogeneous water grid.

Runs the real CLI twice (calibrate -> refocus) on a synthetic homogeneous
model, then asserts:

(a) the refocus pressure field is entirely finite;
(b) the refocus global peak lies within 2 voxels of the target;
(c) the pressure at the target is significantly larger than a random field
    location (target > 5x median of the whole field).

Wall clock must stay well below 5 minutes on the kwave312 interpreter.
Run:  D:\\AIprogram\\python-envs\\kwave312\\Scripts\\python.exe tests\\test_time_reversal_smoke.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = PROJECT_ROOT / "outputs" / "time_reversal_smoke"
MODEL_PATH = WORK_DIR / "smoke_water_model.npz"

GRID_SHAPE = (48, 48, 48)
DX_M = 1e-3
TARGET_IJK = (30, 24, 24)
SOUND_SPEED = 1500.0
DENSITY = 1000.0


def build_smoke_model() -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        MODEL_PATH,
        sound_speed=np.full(GRID_SHAPE, SOUND_SPEED, dtype=np.float32),
        density=np.full(GRID_SHAPE, DENSITY, dtype=np.float32),
        alpha_coeff=np.zeros(GRID_SHAPE, dtype=np.float32),
        labels=np.zeros(GRID_SHAPE, dtype=np.uint8),
        dx_m=np.array(DX_M),
        target_index_ijk=np.array(TARGET_IJK, dtype=np.int64),
    )


def run_stage(stage: str) -> float:
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "simulate_time_reversal_focus.py"),
        "--stage",
        stage,
        "--model",
        str(MODEL_PATH),
        "--output-dir",
        str(WORK_DIR),
        "--preset",
        "smoke",
        "--sim-time-us",
        "45",
        "--cycles",
        "2",
        "--cfl",
        "0.3",
        "--pml-size",
        "8",
        "--aperture-mm",
        "28",
        "--radius-mm",
        "20",
        "--quick-lateral-mm",
        "17",
        "--quick-post-target-mm",
        "8",
    ]
    print(f"[smoke] running {' '.join(cmd)}", flush=True)
    start = time.perf_counter()
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    elapsed = time.perf_counter() - start
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        raise RuntimeError(f"stage {stage} failed with exit code {proc.returncode}")
    print(f"[smoke] stage {stage} finished in {elapsed:.1f} s", flush=True)
    return elapsed


def main() -> None:
    build_smoke_model()
    t0 = time.perf_counter()
    t_cal = run_stage("calibrate")
    t_ref = run_stage("refocus")
    total = time.perf_counter() - t0

    signals_path = WORK_DIR / "element_signals.npz"
    assert signals_path.exists(), "element_signals.npz missing after calibrate"
    stored = np.load(signals_path)
    signals = stored["signals"]
    assert np.all(np.isfinite(signals)), "calibration signals contain non-finite values"
    assert signals.shape[0] == int(np.sum(stored["source_mask"])), "signal/mask point count mismatch"

    field_path = WORK_DIR / "pressure_max_mpa.npz"
    assert field_path.exists(), "pressure_max_mpa.npz missing after refocus"
    pressure = np.load(field_path)["pressure_max_mpa"]

    # (a) field is finite
    assert np.all(np.isfinite(pressure)), "refocus field contains NaN/inf"
    assert float(np.max(pressure)) > 0, "refocus field is all zero"

    # (b) global peak within 2 voxels of the target
    target = np.array(TARGET_IJK) - np.load(field_path)["crop_origin_ijk"]
    peak = np.array(np.unravel_index(np.argmax(pressure), pressure.shape))
    peak_distance_vox = float(np.linalg.norm(peak - target))
    assert peak_distance_vox <= 2.0, (
        f"refocus global peak at {peak.tolist()} is {peak_distance_vox:.2f} voxels "
        f"from target {target.tolist()} (> 2)"
    )

    # (c) target pressure significantly above a random field location
    median_pa = float(np.median(pressure))
    target_pa = float(pressure[tuple(target)])
    ratio = target_pa / median_pa if median_pa > 0 else float("inf")
    assert ratio > 5.0, f"target/median pressure ratio {ratio:.2f} <= 5"

    summary = json.loads((WORK_DIR / "summary.json").read_text(encoding="utf-8"))
    print("[smoke] ---- assertions ----", flush=True)
    print(f"[smoke] finite field: OK (max={float(np.max(pressure)):.4f} MPa)", flush=True)
    print(f"[smoke] peak distance to target: {peak_distance_vox:.2f} voxels (<= 2): OK", flush=True)
    print(f"[smoke] target/median pressure ratio: {ratio:.1f} (> 5): OK", flush=True)
    print(
        f"[smoke] focus metrics: global_peak={summary['pressure']['global_peak_mpa']:.4f} MPa, "
        f"target={summary['pressure']['target_pressure_mpa']:.4f} MPa, "
        f"target/global={summary['pressure']['target_to_global_peak_ratio']:.3f}",
        flush=True,
    )
    print(
        f"[smoke] time alignment policy: {summary['time_alignment']['policy']}, "
        f"nt_recorded={summary['time_reversal']['nt_recorded']}, nt_final={summary['time_alignment']['nt_final']}",
        flush=True,
    )
    print(
        f"[smoke] PASS in {total:.1f} s wall (calibrate {t_cal:.1f} s + refocus {t_ref:.1f} s)",
        flush=True,
    )


if __name__ == "__main__":
    main()
