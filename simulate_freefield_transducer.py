from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from simulate_kwave_3d_focus import (
    PROJECT_ROOT,
    KWave3DConfig,
    LoadedModel,
    build_source_mask,
    compute_focus_metrics,
    run_kwave,
    save_layout_image,
    save_pressure_slices,
)
from simulation_quality import build_simulation_quality, write_quality_dry_run_summary


@dataclass(frozen=True)
class FreefieldConfig:
    aperture_mm: float = 25.0
    radius_mm: float = 30.0
    frequency_khz: float = 500.0
    source_pressure_mpa: float = 1.0
    medium: str = "water"
    dx_mm: float = 1.0
    cycles: int = 6
    sim_time_us: float | None = None
    cfl: float = 0.20
    pml_size: int = 8
    preset: str = "quick"
    source_margin_mm: float = 10.0
    post_focus_mm: float = 18.0
    lateral_margin_mm: float = 12.0
    nearfield_mm: float = 10.0


def medium_properties(name: str) -> dict[str, float]:
    if name == "water":
        return {
            "sound_speed_m_s": 1480.0,
            "density_kg_m3": 1000.0,
            "alpha_coeff_db_mhz_cm": 0.0022,
            "alpha_power": 2.0,
        }
    if name == "soft":
        return {
            "sound_speed_m_s": 1540.0,
            "density_kg_m3": 1000.0,
            "alpha_coeff_db_mhz_cm": 0.5,
            "alpha_power": 1.5,
        }
    raise ValueError(f"Unsupported medium: {name}")


def odd_points(length_mm: float, dx_mm: float) -> int:
    value = int(np.ceil(length_mm / dx_mm))
    value = max(value, 3)
    return value if value % 2 == 1 else value + 1


def build_freefield_model(config: FreefieldConfig) -> tuple[LoadedModel, dict[str, object]]:
    dx_m = config.dx_mm * 1e-3
    radius_gp = int(round(config.radius_mm / config.dx_mm))
    source_margin_gp = int(round(config.source_margin_mm / config.dx_mm))
    post_focus_gp = int(round(config.post_focus_mm / config.dx_mm))
    lateral_points = odd_points(config.aperture_mm + 2.0 * config.lateral_margin_mm, config.dx_mm)
    nx = source_margin_gp + radius_gp + post_focus_gp + config.pml_size + 4
    ny = max(lateral_points, odd_points(config.aperture_mm * 1.8, config.dx_mm))
    nz = ny

    center_y = ny // 2
    center_z = nz // 2
    source_center = np.array([source_margin_gp, center_y, center_z], dtype=np.int32)
    target = np.array([source_margin_gp + radius_gp, center_y, center_z], dtype=np.int32)

    props = medium_properties(config.medium)
    shape = (int(nx), int(ny), int(nz))
    sound_speed = np.full(shape, props["sound_speed_m_s"], dtype=np.float32)
    density = np.full(shape, props["density_kg_m3"], dtype=np.float32)
    alpha_coeff = np.full(shape, props["alpha_coeff_db_mhz_cm"], dtype=np.float32)
    labels = np.zeros(shape, dtype=np.uint8)

    model = LoadedModel(
        labels=labels,
        sound_speed=sound_speed,
        density=density,
        alpha_coeff=alpha_coeff,
        dx_m=dx_m,
        target_index_ijk=target,
        source_center_index_ijk=source_center,
        entry_index_ijk=None,
        beam_axis=np.array([1, 0, 0], dtype=np.int32),
        entry_plan=None,
        crop_origin_ijk=np.zeros(3, dtype=np.int32),
        source_model_shape=shape,
    )
    metadata = {
        "medium": config.medium,
        "medium_properties": props,
        "grid_shape": list(shape),
        "dx_m": dx_m,
        "geometric_focus_index_ijk": target.astype(int).tolist(),
        "source_center_index_ijk": source_center.astype(int).tolist(),
        "geometric_focus_distance_mm": config.radius_mm,
    }
    return model, metadata


def fwhm_mm(profile: np.ndarray, dx_mm: float, peak_index: int) -> float | None:
    peak_value = float(profile[peak_index])
    if peak_value <= 0:
        return None
    half = peak_value * 0.5
    above = np.where(profile >= half)[0]
    if above.size < 2:
        return None
    segment = above[(above >= above[0]) & (above <= above[-1])]
    if peak_index < int(segment[0]) or peak_index > int(segment[-1]):
        return None
    return float((int(segment[-1]) - int(segment[0])) * dx_mm)


def save_profile_plot(
    output_path: Path,
    x_values: np.ndarray,
    profile: np.ndarray,
    title: str,
    xlabel: str,
    markers: list[tuple[float, str, tuple[int, int, int]]] | None = None,
) -> None:
    width, height = 900, 420
    left, right, top, bottom = 74, 24, 36, 64
    plot_w = width - left - right
    plot_h = height - top - bottom
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((left, top, left + plot_w, top + plot_h), outline=(0, 0, 0))
    draw.text((left, 10), title, fill=(0, 0, 0))
    draw.text((left, height - 34), xlabel, fill=(0, 0, 0))
    draw.text((8, top + 8), "MPa", fill=(0, 0, 0))
    y_max = max(float(np.max(profile)), 1e-9)
    x_min = float(np.min(x_values))
    x_max = float(np.max(x_values))

    points = []
    for x_value, value in zip(x_values, profile):
        x = left + int(round((float(x_value) - x_min) / max(x_max - x_min, 1e-9) * plot_w))
        y = top + plot_h - int(round(float(value) / y_max * plot_h))
        points.append((x, y))
    if len(points) > 1:
        draw.line(points, fill=(30, 105, 190), width=2)

    for frac in [0, 0.25, 0.5, 0.75, 1.0]:
        y = top + plot_h - int(round(frac * plot_h))
        draw.line((left - 5, y, left, y), fill=(0, 0, 0))
        draw.text((left - 68, y - 7), f"{frac * y_max:.2f}", fill=(0, 0, 0))
    for frac in [0, 0.25, 0.5, 0.75, 1.0]:
        x_value = x_min + frac * (x_max - x_min)
        x = left + int(round(frac * plot_w))
        draw.line((x, top + plot_h, x, top + plot_h + 5), fill=(0, 0, 0))
        draw.text((x - 18, top + plot_h + 10), f"{x_value:.0f}", fill=(0, 0, 0))

    for marker_x, label, color in markers or []:
        x = left + int(round((float(marker_x) - x_min) / max(x_max - x_min, 1e-9) * plot_w))
        draw.line((x, top, x, top + plot_h), fill=color, width=2)
        draw.text((x + 4, top + 4), label, fill=color)
    image.save(output_path)


def save_profiles(output_dir: Path, pressure_mpa: np.ndarray, model: LoadedModel, metrics: dict[str, object]) -> dict[str, object]:
    target = model.target_index_ijk.astype(int)
    dx_mm = model.dx_m * 1e3
    axial = pressure_mpa[:, target[1], target[2]]
    x_mm = (np.arange(pressure_mpa.shape[0]) - target[0]) * dx_mm
    effective_peak = np.array(metrics["effective_peak_index_ijk"], dtype=int)
    global_peak = np.array(metrics["global_peak_index_ijk"], dtype=int)

    np.savetxt(
        output_dir / "axial_profile.csv",
        np.column_stack([np.arange(pressure_mpa.shape[0]), x_mm, axial]),
        delimiter=",",
        header="x_index,x_relative_to_geometric_focus_mm,pressure_mpa",
        comments="",
        fmt=["%d", "%.6f", "%.6f"],
    )
    save_profile_plot(
        output_dir / "axial_profile.png",
        x_mm,
        axial,
        "Free-field axial pressure profile",
        "x relative to geometric focus [mm]",
        [(0.0, "geom", (255, 0, 0)), (x_mm[effective_peak[0]], "effective", (230, 150, 0))],
    )

    lateral = pressure_mpa[effective_peak[0], :, target[2]]
    y_mm = (np.arange(pressure_mpa.shape[1]) - target[1]) * dx_mm
    np.savetxt(
        output_dir / "lateral_profile.csv",
        np.column_stack([np.arange(pressure_mpa.shape[1]), y_mm, lateral]),
        delimiter=",",
        header="y_index,y_relative_to_axis_mm,pressure_mpa",
        comments="",
        fmt=["%d", "%.6f", "%.6f"],
    )
    save_profile_plot(
        output_dir / "lateral_profile.png",
        y_mm,
        lateral,
        "Free-field lateral pressure profile at effective focus",
        "y relative to beam axis [mm]",
        [(0.0, "axis", (255, 0, 0)), (y_mm[effective_peak[1]], "effective", (230, 150, 0))],
    )

    axial_width = fwhm_mm(axial, dx_mm, int(effective_peak[0]))
    lateral_width = fwhm_mm(lateral, dx_mm, int(effective_peak[1]))
    return {
        "axial_fwhm_mm": axial_width,
        "lateral_fwhm_mm": lateral_width,
        "global_peak_relative_to_focus_mm": ((global_peak - target) * dx_mm).astype(float).tolist(),
        "effective_peak_relative_to_focus_mm": ((effective_peak - target) * dx_mm).astype(float).tolist(),
    }


def save_freefield_summary(
    output_dir: Path,
    config: FreefieldConfig,
    model_metadata: dict[str, object],
    source_metadata: dict[str, object],
    runtime_metadata: dict[str, object],
    metrics: dict[str, object],
    profile_metrics: dict[str, object],
    runtime_s: float,
    simulation_quality: dict[str, object],
) -> None:
    summary = {
        "description": "Free-field/water-tank style single-bowl transducer calibration run.",
        "calibration_level": "quick_freefield_sanity_check",
        "parameter_boundary_note": (
            "source_pressure_mpa is the prescribed source/excitation pressure; "
            "free-field pressure is not transcranial in-situ pressure."
        ),
        "config": asdict(config),
        "model": model_metadata,
        "source": source_metadata,
        "runtime": {**runtime_metadata, "runtime_s": runtime_s},
        "simulation_quality": simulation_quality,
        "pressure": metrics,
        "profile_metrics": profile_metrics,
    }
    (output_dir / "freefield_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "freefield_summary.txt").open("w", encoding="utf-8") as handle:
        handle.write("Free-field/water-tank transducer calibration\n")
        handle.write("calibration_level=quick_freefield_sanity_check\n")
        handle.write(f"medium={config.medium}\n")
        handle.write(f"aperture_mm={config.aperture_mm:.3f}\n")
        handle.write(f"radius_mm={config.radius_mm:.3f}\n")
        handle.write(f"frequency_khz={config.frequency_khz:.3f}\n")
        handle.write(f"source_pressure_mpa={config.source_pressure_mpa:.3f}\n")
        handle.write(f"grid_shape={tuple(model_metadata['grid_shape'])}\n")
        handle.write(f"dx_mm={config.dx_mm:.3f}\n")
        handle.write(f"dt_ns={runtime_metadata['dt_s'] * 1e9:.3f}\n")
        handle.write(f"nt={runtime_metadata['nt']}\n")
        handle.write(f"preset={simulation_quality['preset']}\n")
        handle.write(f"quality_level={simulation_quality['quality_level']}\n")
        handle.write(f"is_paper_grade={simulation_quality['is_paper_grade']}\n")
        handle.write(f"ppw_min_sound_speed={simulation_quality['ppw_min_sound_speed']:.3f}\n")
        handle.write(f"pml_size={simulation_quality['pml_size']}\n")
        handle.write(f"cfl={simulation_quality['cfl']}\n")
        handle.write(f"backend={simulation_quality['backend']}\n")
        handle.write(f"device={simulation_quality['device']}\n")
        handle.write(f"memory_estimate_mb={simulation_quality['memory_estimate']['estimated_mb']:.3f}\n")
        handle.write(f"source_points={source_metadata['source_points']}\n")
        handle.write(f"global_peak_mpa={metrics['global_peak_mpa']:.6f}\n")
        handle.write(f"effective_peak_mpa={metrics['effective_peak_mpa']:.6f}\n")
        handle.write(f"effective_peak_to_geometric_focus_distance_mm={metrics['effective_peak_to_target_distance_mm']:.3f}\n")
        handle.write(f"target_pressure_mpa={metrics['target_pressure_mpa']:.6f}\n")
        handle.write(f"target_window_peak_mpa={metrics['target_window_peak_mpa']:.6f}\n")
        handle.write(f"axial_fwhm_mm={profile_metrics['axial_fwhm_mm']}\n")
        handle.write(f"lateral_fwhm_mm={profile_metrics['lateral_fwhm_mm']}\n")
        handle.write(f"runtime_s={runtime_s:.3f}\n")
        handle.write("note=source pressure, free-field pressure, and transcranial in-situ pressure are distinct quantities.\n")


def quality_metadata(
    model: LoadedModel,
    config: FreefieldConfig,
    simulation_time_s: float,
    runtime_s: float | None = None,
    output_completeness: dict[str, bool] | None = None,
) -> dict[str, object]:
    return build_simulation_quality(
        preset_name=config.preset,
        sound_speed=model.sound_speed,
        dx_m=model.dx_m,
        frequency_hz=config.frequency_khz * 1e3,
        cfl=config.cfl,
        pml_size=config.pml_size,
        simulation_time_s=simulation_time_s,
        backend="python",
        device="cpu",
        runtime_s=runtime_s,
        output_completeness=output_completeness,
    )


def run(config: FreefieldConfig, output_dir: Path, dry_run_quality: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    model, model_metadata = build_freefield_model(config)
    source_mask, source_metadata = build_source_mask(
        model,
        KWave3DConfig(
            frequency_hz=config.frequency_khz * 1e3,
            source_pressure_pa=config.source_pressure_mpa * 1e6,
            transducer_radius_m=config.radius_mm * 1e-3,
            aperture_diameter_m=config.aperture_mm * 1e-3,
            tone_burst_cycles=config.cycles,
            cfl=config.cfl,
            pml_size=config.pml_size,
            preset=config.preset,
            alpha_power=medium_properties(config.medium)["alpha_power"],
            nearfield_exclusion_m=config.nearfield_mm * 1e-3,
        ),
    )
    props = medium_properties(config.medium)
    auto_time_s = ((config.radius_mm + config.post_focus_mm) * 1e-3 / props["sound_speed_m_s"]) + config.cycles / (config.frequency_khz * 1e3) + 8e-6
    simulation_time_s = config.sim_time_us * 1e-6 if config.sim_time_us is not None else auto_time_s
    kwave_config = KWave3DConfig(
        frequency_hz=config.frequency_khz * 1e3,
        source_pressure_pa=config.source_pressure_mpa * 1e6,
        transducer_radius_m=config.radius_mm * 1e-3,
        aperture_diameter_m=config.aperture_mm * 1e-3,
        tone_burst_cycles=config.cycles,
        cfl=config.cfl,
        simulation_time_s=simulation_time_s,
        pml_size=config.pml_size,
        preset=config.preset,
        alpha_power=props["alpha_power"],
        nearfield_exclusion_m=config.nearfield_mm * 1e-3,
    )
    if dry_run_quality:
        write_quality_dry_run_summary(
            output_dir,
            description="Free-field k-Wave quality dry run for single-bowl transducer calibration.",
            config=asdict(config),
            model=model_metadata,
            source=source_metadata,
            simulation_quality=quality_metadata(model, config, simulation_time_s),
        )
        return

    start = time.perf_counter()
    pressure_mpa, runtime_s, runtime_metadata, _ = run_kwave(model, source_mask, kwave_config)
    runtime_s = time.perf_counter() - start if runtime_s <= 0 else runtime_s
    if not np.all(np.isfinite(pressure_mpa)):
        raise ValueError("Free-field pressure field contains NaN or infinite values.")
    if float(np.max(pressure_mpa)) <= 0:
        raise ValueError("Free-field pressure field is all zero.")

    metrics = compute_focus_metrics(pressure_mpa, source_mask, model.target_index_ijk, model.dx_m, config.nearfield_mm * 1e-3)
    profile_metrics = save_profiles(output_dir, pressure_mpa, model, metrics)
    save_pressure_slices(output_dir, pressure_mpa, source_mask, model, metrics)
    save_layout_image(output_dir, source_mask, model, source_metadata)
    np.savez_compressed(
        output_dir / "pressure_max_mpa.npz",
        pressure_max_mpa=pressure_mpa,
        dx_m=np.array(model.dx_m, dtype=np.float32),
        target_index_ijk=model.target_index_ijk.astype(np.int32),
        crop_origin_ijk=model.crop_origin_ijk.astype(np.int32),
        source_mask=source_mask.astype(np.uint8),
        labels=model.labels.astype(np.uint8),
        nearfield_exclusion_m=np.array(config.nearfield_mm * 1e-3, dtype=np.float32),
    )
    simulation_quality = quality_metadata(
        model,
        config,
        simulation_time_s,
        runtime_s=runtime_s,
        output_completeness={
            "pressure_max_mpa_npz": True,
            "freefield_summary_json": True,
            "axial_profile_png": True,
            "lateral_profile_png": True,
            "pressure_slices": True,
        },
    )
    save_freefield_summary(output_dir, config, model_metadata, source_metadata, runtime_metadata, metrics, profile_metrics, runtime_s, simulation_quality)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a free-field/water-tank style single-bowl transducer calibration.")
    parser.add_argument("--aperture-mm", type=float, default=25.0)
    parser.add_argument("--radius-mm", type=float, default=30.0)
    parser.add_argument("--frequency-khz", type=float, default=500.0)
    parser.add_argument("--source-pressure-mpa", type=float, default=1.0)
    parser.add_argument("--medium", choices=["water", "soft"], default="water")
    parser.add_argument("--dx-mm", type=float, default=1.0)
    parser.add_argument("--cycles", type=int, default=6)
    parser.add_argument("--sim-time-us", type=float, default=None)
    parser.add_argument("--cfl", type=float, default=0.20)
    parser.add_argument("--pml-size", type=int, default=8)
    parser.add_argument("--source-margin-mm", type=float, default=10.0)
    parser.add_argument("--post-focus-mm", type=float, default=18.0)
    parser.add_argument("--lateral-margin-mm", type=float, default=12.0)
    parser.add_argument("--nearfield-mm", type=float, default=10.0)
    parser.add_argument("--preset", choices=["smoke", "quick", "standard", "paper_grade"], default="quick")
    parser.add_argument("--dry-run-quality", action="store_true", help="Write quality metadata without running k-Wave.")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "outputs" / "freefield_calibration" / "ap25_r30_f500"))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        FreefieldConfig(
            aperture_mm=args.aperture_mm,
            radius_mm=args.radius_mm,
            frequency_khz=args.frequency_khz,
            source_pressure_mpa=args.source_pressure_mpa,
            medium=args.medium,
            dx_mm=args.dx_mm,
            cycles=args.cycles,
            sim_time_us=args.sim_time_us,
            cfl=args.cfl,
            pml_size=args.pml_size,
            preset=args.preset,
            source_margin_mm=args.source_margin_mm,
            post_focus_mm=args.post_focus_mm,
            lateral_margin_mm=args.lateral_margin_mm,
            nearfield_mm=args.nearfield_mm,
        ),
        Path(args.output_dir),
        dry_run_quality=args.dry_run_quality,
    )
