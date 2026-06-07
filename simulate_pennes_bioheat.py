from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

PROJECT_ROOT_LOCAL = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT_LOCAL / "outputs" / "mplconfig-kwave312"))
(PROJECT_ROOT_LOCAL / "outputs" / "mplconfig-kwave312").mkdir(parents=True, exist_ok=True)

import matplotlib.pyplot as plt
import numpy as np

from estimate_temperature_rise import (
    PROJECT_ROOT,
    compute_temperature_rise,
    load_cropped_model,
    load_pressure,
    save_slice,
    window_peak,
)


def material_maps(
    labels: np.ndarray | None,
    shape: tuple[int, int, int],
    soft_perfusion_s: float = 0.003,
    skull_conductivity: float = 0.32,
    soft_conductivity: float = 0.50,
    skull_specific_heat: float = 1300.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cp = np.full(shape, 3600.0, dtype=np.float32)
    conductivity = np.full(shape, float(soft_conductivity), dtype=np.float32)
    perfusion_s = np.zeros(shape, dtype=np.float32)
    if labels is None:
        perfusion_s.fill(float(soft_perfusion_s))
        return cp, conductivity, perfusion_s

    cp[labels == 0] = 4180.0
    cp[labels == 1] = 3600.0
    cp[labels == 2] = float(skull_specific_heat)
    conductivity[labels == 0] = 0.60
    conductivity[labels == 1] = float(soft_conductivity)
    conductivity[labels == 2] = float(skull_conductivity)
    perfusion_s[labels == 1] = float(soft_perfusion_s)
    return cp, conductivity, perfusion_s


def laplacian_neumann(volume: np.ndarray, dx_m: float) -> np.ndarray:
    padded = np.pad(volume, 1, mode="edge")
    return (
        padded[2:, 1:-1, 1:-1]
        + padded[:-2, 1:-1, 1:-1]
        + padded[1:-1, 2:, 1:-1]
        + padded[1:-1, :-2, 1:-1]
        + padded[1:-1, 1:-1, 2:]
        + padded[1:-1, 1:-1, :-2]
        - 6.0 * volume
    ) / (dx_m * dx_m)


def stable_dt_s(density: np.ndarray, cp: np.ndarray, conductivity: np.ndarray, dx_m: float) -> float:
    diffusivity = conductivity / np.maximum(density * cp, 1.0)
    max_diffusivity = float(np.max(diffusivity))
    if max_diffusivity <= 0:
        return 1.0
    return 0.45 * dx_m * dx_m / (6.0 * max_diffusivity)


def run_pennes(
    heat_source_w_m3: np.ndarray,
    density: np.ndarray,
    cp: np.ndarray,
    conductivity: np.ndarray,
    perfusion_s: np.ndarray,
    dx_m: float,
    duration_s: float,
    requested_dt_s: float,
    duty_cycle: float,
    pulse_mode: str,
    pulse_schedule: list[dict[str, float]],
    initial_temp_c: float,
    blood_temp_c: float,
    target: list[int],
    labels: np.ndarray | None = None,
    cooling_protocol: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, float]], float, int]:
    dt_limit = stable_dt_s(density, cp, conductivity, dx_m)
    dt_s = min(float(requested_dt_s), dt_limit)
    steps = max(1, int(np.ceil(duration_s / dt_s)))
    dt_s = duration_s / steps
    temp = np.full(heat_source_w_m3.shape, float(initial_temp_c), dtype=np.float32)
    temp_max = np.full(heat_source_w_m3.shape, float(initial_temp_c), dtype=np.float32)
    cem43 = np.zeros(heat_source_w_m3.shape, dtype=np.float32)
    cem43_iso = np.zeros(heat_source_w_m3.shape, dtype=np.float32)
    inv_capacity = 1.0 / np.maximum(density * cp, 1.0)
    diffusivity = conductivity * inv_capacity
    curve: list[dict[str, float]] = []

    sample_every = max(1, steps // 200)
    for step in range(1, steps + 1):
        t0 = (step - 1) * dt_s
        t1 = step * dt_s
        
        # Gao 2022 Cooling Protocol: 5s 加热 + 15s 冷却
        if cooling_protocol and t0 >= 5.0:
            heat_factor = 0.0
        else:
            heat_factor = pulse_overlap_fraction(pulse_schedule, t0, t1) if pulse_mode == "explicit" else float(duty_cycle)
            
        lap = laplacian_neumann(temp, dx_m)
        dtemp_dt = diffusivity * lap + heat_factor * heat_source_w_m3 * inv_capacity - perfusion_s * (temp - float(blood_temp_c))
        temp = temp + dt_s * dtemp_dt.astype(np.float32)
        temp_max = np.maximum(temp_max, temp)
        
        # Calculate CEM43 (k-Wave version)
        # R = 0.25 (37 <= T < 43) + 0.5 (T >= 43)
        R = np.zeros_like(temp)
        R[(temp >= 37.0) & (temp < 43.0)] = 0.25
        R[temp >= 43.0] = 0.5
        
        valid_mask = R > 0
        if np.any(valid_mask):
            cem43[valid_mask] += (dt_s / 60.0) * (R[valid_mask] ** (43.0 - temp[valid_mask]))
            
        # Calculate CEM43_iso (ISO version)
        # R_iso = 0.5 (T_max >= 43 or T >= 43)
        # R_iso = 0.25 (T_max < 43 and 39 <= T < 43)
        R_iso = np.zeros_like(temp)
        R_iso[(temp_max >= 43.0) | (temp >= 43.0)] = 0.5
        R_iso[(temp_max < 43.0) & (temp >= 39.0) & (temp < 43.0)] = 0.25
        
        valid_mask_iso = R_iso > 0
        if np.any(valid_mask_iso):
            cem43_iso[valid_mask_iso] += (dt_s / 60.0) * (R_iso[valid_mask_iso] ** (43.0 - temp[valid_mask_iso]))
        
        # If T >= 57.0, ISO version instantly becomes infinity
        cem43_iso[temp >= 57.0] = np.inf

        if step == 1 or step == steps or step % sample_every == 0:
            rise = temp - float(initial_temp_c)
            
            skull_max_temp = float(initial_temp_c)
            skull_max_rise = 0.0
            if labels is not None:
                skull_mask = (labels == 2)
                if np.any(skull_mask):
                    skull_max_temp = float(np.max(temp[skull_mask]))
                    skull_max_rise = float(np.max(rise[skull_mask]))
            
            curve.append(
                {
                    "time_s": float(step * dt_s),
                    "max_temperature_c": float(np.max(temp)),
                    "max_temperature_rise_c": float(np.max(rise)),
                    "target_temperature_c": float(temp[tuple(target)]),
                    "target_temperature_rise_c": float(rise[tuple(target)]),
                    "skull_max_temperature_c": skull_max_temp,
                    "skull_max_temperature_rise_c": skull_max_rise,
                    "max_cem43": float(np.max(cem43)),
                    "max_cem43_iso": float(np.max(cem43_iso)),
                    "target_cem43": float(cem43[tuple(target)]),
                    "target_cem43_iso": float(cem43_iso[tuple(target)]),
                    "heat_factor": heat_factor,
                }
            )
    return temp, cem43, cem43_iso, curve, float(dt_s), int(steps)


def build_pulse_schedule(prf_hz: float, duty_cycle: float, train_duration_s: float, inter_train_s: float, trains: int) -> list[dict[str, float]]:
    schedule: list[dict[str, float]] = []
    period_s = 1.0 / float(prf_hz)
    on_duration_s = period_s * float(duty_cycle)
    for train_index in range(int(trains)):
        train_start = train_index * (float(train_duration_s) + float(inter_train_s))
        pulse_index = 0
        while True:
            pulse_start = train_start + pulse_index * period_s
            if pulse_start >= train_start + float(train_duration_s):
                break
            pulse_end = min(pulse_start + on_duration_s, train_start + float(train_duration_s))
            schedule.append(
                {
                    "train_index": float(train_index),
                    "pulse_index": float(pulse_index),
                    "start_s": float(pulse_start),
                    "end_s": float(pulse_end),
                    "duration_s": float(pulse_end - pulse_start),
                }
            )
            pulse_index += 1
    return schedule


def protocol_duration_s(train_duration_s: float, inter_train_s: float, trains: int) -> float:
    return float(train_duration_s) * int(trains) + float(inter_train_s) * max(0, int(trains) - 1)


def total_pulse_on_time_s(schedule: list[dict[str, float]]) -> float:
    return float(sum(float(pulse["duration_s"]) for pulse in schedule))


def pulse_overlap_fraction(schedule: list[dict[str, float]], t0: float, t1: float) -> float:
    if t1 <= t0:
        return 0.0
    overlap = 0.0
    for pulse in schedule:
        start = float(pulse["start_s"])
        end = float(pulse["end_s"])
        if end <= t0:
            continue
        if start >= t1:
            break
        overlap += max(0.0, min(t1, end) - max(t0, start))
    return float(overlap / (t1 - t0))


def write_curve(path: Path, rows: list[dict[str, float]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_pulse_schedule(path: Path, rows: list[dict[str, float]]) -> None:
    fieldnames = ["train_index", "pulse_index", "start_s", "end_s", "duration_s"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_curve_plot(path: Path, rows: list[dict[str, float]], cooling_protocol: bool = False) -> None:
    times = [row["time_s"] for row in rows]
    target_rise = [row["target_temperature_rise_c"] for row in rows]
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 7), sharex=True, dpi=140)
    
    # Temperature subplot
    ax1.plot(times, target_rise, label="Focal/Target Rise", color="#1f77b4", linewidth=2)
    if len(rows) > 0 and "skull_max_temperature_rise_c" in rows[0]:
        skull_rise = [row["skull_max_temperature_rise_c"] for row in rows]
        ax1.plot(times, skull_rise, label="Skull Max Rise", color="#d62728", linewidth=2)
    else:
        max_rise = [row["max_temperature_rise_c"] for row in rows]
        ax1.plot(times, max_rise, label="Max Rise", color="#ff7f0e", linewidth=1.5, linestyle="--")
        
    ax1.set_ylabel("Temperature rise (°C)")
    ax1.legend(loc="upper right")
    ax1.grid(True, linestyle=":", alpha=0.6)
    
    if cooling_protocol:
        ax1.axvline(x=5.0, color="#7f7f7f", linestyle="--", alpha=0.8)
        all_rises = target_rise
        if len(rows) > 0 and "skull_max_temperature_rise_c" in rows[0]:
            all_rises = all_rises + [row["skull_max_temperature_rise_c"] for row in rows]
        max_y = max(all_rises) if len(all_rises) > 0 else 1.0
        ax1.text(2.5, max_y * 0.85, "Heating Phase\n(0-5s)", color="#2c3e50", ha="center", fontsize=9, bbox=dict(boxstyle="round", facecolor="#f8f9fa", alpha=0.8))
        ax1.text(12.5, max_y * 0.85, "Cooling Phase\n(5-20s)", color="#2c3e50", ha="center", fontsize=9, bbox=dict(boxstyle="round", facecolor="#f8f9fa", alpha=0.8))

    # Thermal Dose subplot
    if len(rows) > 0 and "max_cem43" in rows[0]:
        target_cem = [row["target_cem43"] for row in rows]
        max_cem = [row["max_cem43"] for row in rows]
        target_cem_iso = [row["target_cem43_iso"] for row in rows]
        max_cem_iso = [row["max_cem43_iso"] for row in rows]
        
        ax2.plot(times, max_cem, label="Max CEM43 (k-Wave)", color="#2ca02c", linewidth=1.5)
        ax2.plot(times, max_cem_iso, label="Max CEM43 (ISO)", color="#9467bd", linewidth=1.5, linestyle="--")
        ax2.plot(times, target_cem, label="Target CEM43 (k-Wave)", color="#bcbd22", linewidth=1.5)
        ax2.plot(times, target_cem_iso, label="Target CEM43 (ISO)", color="#17becf", linewidth=1.5, linestyle=":")
    
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Thermal Dose (min)")
    ax2.legend(loc="upper left")
    ax2.grid(True, linestyle=":", alpha=0.6)
    
    if cooling_protocol:
        ax2.axvline(x=5.0, color="#7f7f7f", linestyle="--", alpha=0.8)
        
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def run(args: argparse.Namespace) -> None:
    pressure_dir = Path(args.pressure_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pressure_mpa, pressure_summary = load_pressure(pressure_dir)
    model_path = Path(args.model or pressure_summary["config"]["model_path"])
    model = load_cropped_model(model_path, pressure_summary["crop_origin_ijk"], tuple(int(v) for v in pressure_mpa.shape))
    _one_second_rise, heat_source_w_m3, intensity_w_m2 = compute_temperature_rise(
        pressure_mpa=pressure_mpa,
        model=model,
        frequency_hz=float(pressure_summary["config"]["frequency_hz"]),
        alpha_power=float(pressure_summary["config"]["alpha_power"]),
        sonication_s=1.0,
    )

    density = np.asarray(model["density"], dtype=np.float32)
    labels = np.asarray(model["labels"], dtype=np.uint8) if "labels" in model else None
    cp, conductivity, perfusion_s = material_maps(
        labels,
        pressure_mpa.shape,
        soft_perfusion_s=float(args.soft_perfusion_s),
        skull_conductivity=float(args.skull_conductivity),
        soft_conductivity=float(args.soft_conductivity),
        skull_specific_heat=float(args.skull_specific_heat),
    )
    dx_m = float(model["dx_m"])
    target = [int(v) for v in pressure_summary["target_index_ijk"]]
    schedule = build_pulse_schedule(args.prf_hz, args.pulse_duty_cycle, args.train_duration_s, args.inter_train_s, args.trains)
    protocol_total_duration_s = protocol_duration_s(args.train_duration_s, args.inter_train_s, args.trains)
    total_on_time_s = total_pulse_on_time_s(schedule)
    protocol_effective_duty_cycle = total_on_time_s / protocol_total_duration_s if protocol_total_duration_s > 0 else 0.0
    if args.gao_cooling_protocol:
        duration_s = 20.0
        duty_cycle = float(args.duty_cycle)
        heat_source_mode_note = "Gao 2022 Cooling Protocol: 5s heating (duty_cycle={}) + 15s cooling".format(duty_cycle)
    elif args.pulse_mode == "explicit":
        duration_s = protocol_total_duration_s
        duty_cycle = args.pulse_duty_cycle
        heat_source_mode_note = "Explicit pulse schedule; each thermal step uses the pulse overlap fraction."
    elif args.pulse_mode == "protocol-averaged":
        duration_s = protocol_total_duration_s
        duty_cycle = protocol_effective_duty_cycle
        heat_source_mode_note = "Protocol-averaged heat source; constant duty equals total pulse-on time divided by protocol duration."
    else:
        duration_s = float(args.duration_s)
        duty_cycle = float(args.duty_cycle)
        heat_source_mode_note = "Constant averaged heat source; duty cycle is applied over duration_s."

    final_temp_c, cem43, cem43_iso, curve, actual_dt_s, steps = run_pennes(
        heat_source_w_m3=heat_source_w_m3,
        density=density,
        cp=cp,
        conductivity=conductivity,
        perfusion_s=perfusion_s,
        dx_m=dx_m,
        duration_s=float(duration_s),
        requested_dt_s=float(args.dt_s),
        duty_cycle=float(duty_cycle),
        pulse_mode=str(args.pulse_mode),
        pulse_schedule=schedule,
        initial_temp_c=float(args.initial_temp_c),
        blood_temp_c=float(args.blood_temp_c),
        target=target,
        labels=labels,
        cooling_protocol=bool(args.gao_cooling_protocol)
    )
    temp_rise_c = final_temp_c - float(args.initial_temp_c)
    global_index = [int(v) for v in np.unravel_index(int(np.argmax(temp_rise_c)), temp_rise_c.shape)]
    target_window_peak_c, target_window_peak_index = window_peak(temp_rise_c, target, radius=int(args.target_window_radius))

    # Region-specific metrics & safety thresholds
    soft_mask = (labels == 1) if labels is not None else np.ones_like(final_temp_c, dtype=bool)
    skull_mask = (labels == 2) if labels is not None else np.zeros_like(final_temp_c, dtype=bool)
    
    # Soft tissue (Brain)
    if np.any(soft_mask):
        brain_max_temp = float(np.max(final_temp_c[soft_mask]))
        brain_max_rise = float(np.max(temp_rise_c[soft_mask]))
        brain_max_cem43 = float(np.max(cem43[soft_mask]))
        brain_max_cem43_iso = float(np.max(cem43_iso[soft_mask]))
    else:
        brain_max_temp = float(args.initial_temp_c)
        brain_max_rise = 0.0
        brain_max_cem43 = 0.0
        brain_max_cem43_iso = 0.0

    # Skull
    if np.any(skull_mask):
        skull_max_temp = float(np.max(final_temp_c[skull_mask]))
        skull_max_rise = float(np.max(temp_rise_c[skull_mask]))
        skull_max_cem43 = float(np.max(cem43[skull_mask]))
        skull_max_cem43_iso = float(np.max(cem43_iso[skull_mask]))
    else:
        skull_max_temp = float(args.initial_temp_c)
        skull_max_rise = 0.0
        skull_max_cem43 = 0.0
        skull_max_cem43_iso = 0.0

    brain_cem43_safe = (brain_max_cem43 <= 2.0)
    brain_cem43_iso_safe = (brain_max_cem43_iso <= 2.0)
    brain_temp_safe = (brain_max_temp <= 42.0)
    
    skull_cem43_safe = (skull_max_cem43 <= 16.0)
    skull_cem43_iso_safe = (skull_max_cem43_iso <= 16.0)
    skull_temp_safe = (skull_max_temp <= 42.0)
    
    overall_safe = bool(brain_cem43_safe and brain_cem43_iso_safe and brain_temp_safe and
                        skull_cem43_safe and skull_cem43_iso_safe and skull_temp_safe)

    np.savez_compressed(
        output_dir / "pennes_temperature_c.npz",
        temperature_c=final_temp_c.astype(np.float32),
        temperature_rise_c=temp_rise_c.astype(np.float32),
        heat_source_w_m3=heat_source_w_m3.astype(np.float32),
        intensity_w_m2=intensity_w_m2.astype(np.float32),
        perfusion_s=perfusion_s.astype(np.float32),
        thermal_conductivity_w_m_k=conductivity.astype(np.float32),
        specific_heat_j_kg_k=cp.astype(np.float32),
        cem43_min=cem43.astype(np.float32),
        cem43_iso_min=cem43_iso.astype(np.float32),
    )
    write_curve(output_dir / "temperature_time_curve.csv", curve)
    write_pulse_schedule(output_dir / "pulse_schedule.csv", schedule)
    save_curve_plot(output_dir / "temperature_time_curve.png", curve, cooling_protocol=bool(args.gao_cooling_protocol))
    markers = {
        "target": target,
        "temp peak": global_index,
        "pressure peak": [int(v) for v in pressure_summary["pressure"]["target_window_peak_index_ijk"]],
    }
    save_slice(output_dir / "pennes_temperature_rise_axial.png", temp_rise_c, "axial", target[2], markers)
    save_slice(output_dir / "pennes_temperature_rise_coronal.png", temp_rise_c, "coronal", target[1], markers)
    save_slice(output_dir / "pennes_temperature_rise_sagittal.png", temp_rise_c, "sagittal", target[0], markers)

    summary = {
        "description": "Lightweight explicit Pennes bioheat estimate from quick 3D k-Wave pressure field.",
        "pressure_dir": str(pressure_dir),
        "model_path": str(model_path),
        "duration_s": float(duration_s),
        "duty_cycle": float(duty_cycle),
        "pulse_mode": str(args.pulse_mode),
        "prf_hz": float(args.prf_hz),
        "pulse_duty_cycle": float(args.pulse_duty_cycle),
        "train_duration_s": float(args.train_duration_s),
        "inter_train_s": float(args.inter_train_s),
        "trains": int(args.trains),
        "pulse_count": len(schedule),
        "protocol_total_duration_s": float(protocol_total_duration_s),
        "total_pulse_on_time_s": float(total_on_time_s),
        "protocol_effective_duty_cycle": float(protocol_effective_duty_cycle),
        "heat_source_mode_note": heat_source_mode_note,
        "requested_dt_s": float(args.dt_s),
        "actual_dt_s": actual_dt_s,
        "time_steps": steps,
        "initial_temp_c": float(args.initial_temp_c),
        "blood_temp_c": float(args.blood_temp_c),
        "material_parameters": {
            "soft_perfusion_s": float(args.soft_perfusion_s),
            "skull_conductivity_w_m_k": float(args.skull_conductivity),
            "soft_conductivity_w_m_k": float(args.soft_conductivity),
            "skull_specific_heat_j_kg_k": float(args.skull_specific_heat),
            "defaults_note": "Defaults match the previous approximate thermal material map.",
        },
        "assumptions": {
            "heat_source": "Uses Q from pressure_max_mpa with either averaged duty cycle or explicit pulse overlap per thermal step.",
            "thermal_model": "Explicit Pennes-style update with approximate material conductivity, cp, and soft-tissue perfusion.",
            "limitations": "Quick cropped domain, approximate material maps, no pulsed micro-time structure, no nonlinear acoustics.",
        },
        "max_temperature_rise_c": float(np.max(temp_rise_c)),
        "max_temperature_c": float(np.max(final_temp_c)),
        "max_temperature_index_ijk": global_index,
        "target_temperature_rise_c": float(temp_rise_c[tuple(target)]),
        "target_temperature_c": float(final_temp_c[tuple(target)]),
        "target_window_peak_temperature_rise_c": target_window_peak_c,
        "target_window_peak_temperature_index_ijk": target_window_peak_index,
        "brain_max_temperature_c": brain_max_temp,
        "brain_max_temperature_rise_c": brain_max_rise,
        "brain_max_cem43_min": brain_max_cem43,
        "brain_max_cem43_iso_min": brain_max_cem43_iso,
        "skull_max_temperature_c": skull_max_temp,
        "skull_max_temperature_rise_c": skull_max_rise,
        "skull_max_cem43_min": skull_max_cem43,
        "skull_max_cem43_iso_min": skull_max_cem43_iso,
        "thermal_dose_safety": {
            "brain_safety": {
                "max_temperature_c": brain_max_temp,
                "max_temperature_rise_c": brain_max_rise,
                "max_cem43_min": brain_max_cem43,
                "max_cem43_iso_min": brain_max_cem43_iso,
                "temp_limit_exceeded": not brain_temp_safe,
                "cem43_limit_exceeded": not brain_cem43_safe,
                "cem43_iso_limit_exceeded": not brain_cem43_iso_safe,
                "status": "SAFE" if (brain_temp_safe and brain_cem43_safe and brain_cem43_iso_safe) else "WARNING_LIMIT_EXCEEDED"
            },
            "skull_safety": {
                "max_temperature_c": skull_max_temp,
                "max_temperature_rise_c": skull_max_rise,
                "max_cem43_min": skull_max_cem43,
                "max_cem43_iso_min": skull_max_cem43_iso,
                "temp_limit_exceeded": not skull_temp_safe,
                "cem43_limit_exceeded": not skull_cem43_safe,
                "cem43_iso_limit_exceeded": not skull_cem43_iso_safe,
                "status": "SAFE" if (skull_temp_safe and skull_cem43_safe and skull_cem43_iso_safe) else "WARNING_LIMIT_EXCEEDED"
            },
            "overall_safe": overall_safe
        },
        "pressure_metrics": pressure_summary["pressure"],
        "source": pressure_summary["source"],
    }
    (output_dir / "pennes_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "pennes_summary.txt").open("w", encoding="utf-8") as handle:
        handle.write("Lightweight Pennes bioheat estimate\n")
        handle.write(f"pressure_dir={pressure_dir}\n")
        handle.write(f"duration_s={duration_s}\n")
        handle.write(f"pulse_mode={args.pulse_mode}\n")
        handle.write(f"duty_cycle={duty_cycle}\n")
        handle.write(f"prf_hz={args.prf_hz}\n")
        handle.write(f"trains={args.trains}\n")
        handle.write(f"pulse_count={len(schedule)}\n")
        handle.write(f"protocol_total_duration_s={protocol_total_duration_s}\n")
        handle.write(f"total_pulse_on_time_s={total_on_time_s}\n")
        handle.write(f"protocol_effective_duty_cycle={protocol_effective_duty_cycle}\n")
        handle.write(f"soft_perfusion_s={args.soft_perfusion_s}\n")
        handle.write(f"skull_conductivity_w_m_k={args.skull_conductivity}\n")
        handle.write(f"soft_conductivity_w_m_k={args.soft_conductivity}\n")
        handle.write(f"skull_specific_heat_j_kg_k={args.skull_specific_heat}\n")
        handle.write(f"max_temperature_rise_c={summary['max_temperature_rise_c']:.6f}\n")
        handle.write(f"target_temperature_rise_c={summary['target_temperature_rise_c']:.6f}\n")
        handle.write(f"target_window_peak_temperature_rise_c={summary['target_window_peak_temperature_rise_c']:.6f}\n")
        handle.write(f"brain_max_temperature_c={brain_max_temp:.6f}\n")
        handle.write(f"brain_max_cem43_min={brain_max_cem43:.6f}\n")
        handle.write(f"brain_max_cem43_iso_min={brain_max_cem43_iso:.6f}\n")
        handle.write(f"skull_max_temperature_c={skull_max_temp:.6f}\n")
        handle.write(f"skull_max_cem43_min={skull_max_cem43:.6f}\n")
        handle.write(f"skull_max_cem43_iso_min={skull_max_cem43_iso:.6f}\n")
        handle.write(f"overall_safe={overall_safe}\n")
        handle.write("warning=lightweight Pennes estimate; material and perfusion maps are approximate\n")
    print(
        f"max_dT_C={summary['max_temperature_rise_c']:.6f} "
        f"target_dT_C={summary['target_temperature_rise_c']:.6f} "
        f"brain_max_cem43={brain_max_cem43:.6f} "
        f"skull_max_cem43={skull_max_cem43:.6f} "
        f"overall_safe={overall_safe} output_dir={output_dir}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a lightweight Pennes bioheat estimate from a pressure field.")
    parser.add_argument(
        "--pressure-dir",
        default=str(PROJECT_ROOT / "outputs" / "ct_transducer_stability_target_020" / "ap30_r35_c8_t55"),
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "outputs" / "pennes_bioheat_target_020_best"))
    parser.add_argument(
        "--gao-cooling-protocol",
        action="store_true",
        help="Use Gao 2022 heating/cooling protocol (5s heating + 15s cooling, total 20s)."
    )
    parser.add_argument("--duration-s", type=float, default=0.067, help="Stimulus train duration in seconds.")
    parser.add_argument("--duty-cycle", type=float, default=0.06, help="Time-averaged acoustic duty cycle.")
    parser.add_argument("--pulse-mode", choices=["averaged", "protocol-averaged", "explicit"], default="averaged")
    parser.add_argument("--prf-hz", type=float, default=300.0)
    parser.add_argument("--pulse-duty-cycle", type=float, default=0.06)
    parser.add_argument("--train-duration-s", type=float, default=0.067)
    parser.add_argument("--inter-train-s", type=float, default=2.5)
    parser.add_argument("--trains", type=int, default=1)
    parser.add_argument("--dt-s", type=float, default=0.005, help="Requested thermal time step in seconds.")
    parser.add_argument("--initial-temp-c", type=float, default=37.0)
    parser.add_argument("--blood-temp-c", type=float, default=37.0)
    parser.add_argument("--target-window-radius", type=int, default=3)
    parser.add_argument("--soft-perfusion-s", type=float, default=0.003)
    parser.add_argument("--skull-conductivity", type=float, default=0.32)
    parser.add_argument("--soft-conductivity", type=float, default=0.50)
    parser.add_argument("--skull-specific-heat", type=float, default=1300.0)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
