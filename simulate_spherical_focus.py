from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


@dataclass(frozen=True)
class SimulationConfig:
    frequency_hz: float = 500_000.0
    sound_speed_m_s: float = 1540.0
    source_pressure_pa: float = 1_000_000.0
    transducer_radius_m: float = 30e-3
    aperture_diameter_m: float = 25e-3
    grid_x_m: float = 40e-3
    grid_z_m: float = 60e-3
    dx_m: float = 0.25e-3
    samples_per_axis: int = 45
    skull_layer_z_m: tuple[float, float] = (-18e-3, -12e-3)
    skull_attenuation_np_m: float = 35.0


def make_spherical_cap_sources(config: SimulationConfig) -> np.ndarray:
    half_aperture = config.aperture_diameter_m / 2.0
    axis = np.linspace(-half_aperture, half_aperture, config.samples_per_axis)
    x_src, y_src = np.meshgrid(axis, axis, indexing="xy")
    rho2 = x_src**2 + y_src**2
    aperture_mask = rho2 <= half_aperture**2

    z_src = -np.sqrt(config.transducer_radius_m**2 - rho2)
    sources = np.column_stack(
        [x_src[aperture_mask], y_src[aperture_mask], z_src[aperture_mask]]
    )
    return sources


def skull_path_length(z_grid: np.ndarray, z_src: np.ndarray, layer: tuple[float, float]) -> np.ndarray:
    layer_start, layer_end = layer
    ray_start = np.minimum(z_src, z_grid)
    ray_end = np.maximum(z_src, z_grid)
    overlap = np.minimum(ray_end, layer_end) - np.maximum(ray_start, layer_start)
    return np.clip(overlap, 0.0, None)


def compute_pressure_field(config: SimulationConfig) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.arange(-config.grid_x_m / 2.0, config.grid_x_m / 2.0 + config.dx_m, config.dx_m)
    z = np.arange(-config.grid_z_m / 2.0, config.grid_z_m / 2.0 + config.dx_m, config.dx_m)
    x_grid, z_grid = np.meshgrid(x, z, indexing="xy")
    field = np.zeros_like(x_grid, dtype=np.complex128)

    wave_number = 2.0 * np.pi * config.frequency_hz / config.sound_speed_m_s
    sources = make_spherical_cap_sources(config)

    for x_src, y_src, z_src in sources:
        distance = np.sqrt((x_grid - x_src) ** 2 + y_src**2 + (z_grid - z_src) ** 2)
        distance = np.maximum(distance, config.dx_m)
        skull_distance = skull_path_length(z_grid, z_src, config.skull_layer_z_m)
        attenuation = np.exp(-config.skull_attenuation_np_m * skull_distance)
        field += attenuation * np.exp(1j * wave_number * distance) / distance

    pressure = np.abs(field)
    pressure = pressure / pressure.max() * config.source_pressure_pa
    return x_grid, z_grid, pressure


def viridis_like(values: np.ndarray) -> np.ndarray:
    stops = np.array(
        [
            [68, 1, 84],
            [59, 82, 139],
            [33, 145, 140],
            [94, 201, 98],
            [253, 231, 37],
        ],
        dtype=float,
    )
    scaled = np.clip(values, 0.0, 1.0) * (len(stops) - 1)
    low = np.floor(scaled).astype(int)
    high = np.clip(low + 1, 0, len(stops) - 1)
    blend = scaled[..., None] - low[..., None]
    return ((1.0 - blend) * stops[low] + blend * stops[high]).astype(np.uint8)


def save_pressure_png(
    path: Path,
    x_grid: np.ndarray,
    z_grid: np.ndarray,
    pressure: np.ndarray,
    config: SimulationConfig,
    peak_index: tuple[int, int],
) -> None:
    normalized = pressure / pressure.max()
    rgb = viridis_like(normalized)

    layer_start, layer_end = config.skull_layer_z_m
    z_axis = z_grid[:, 0]
    layer_mask = (z_axis >= layer_start) & (z_axis <= layer_end)
    rgb[layer_mask, :, :] = (0.75 * rgb[layer_mask, :, :] + 0.25 * 255).astype(np.uint8)

    image = Image.fromarray(rgb, mode="RGB")
    draw = ImageDraw.Draw(image)
    peak_y, peak_x = peak_index
    draw.line((peak_x - 6, peak_y, peak_x + 6, peak_y), fill=(255, 0, 0), width=2)
    draw.line((peak_x, peak_y - 6, peak_x, peak_y + 6), fill=(255, 0, 0), width=2)
    draw.rectangle((0, 0, image.width - 1, image.height - 1), outline=(230, 230, 230), width=1)
    image = image.resize((image.width * 3, image.height * 3), Image.Resampling.NEAREST)
    image.save(path)


def save_outputs(config: SimulationConfig, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    x_grid, z_grid, pressure = compute_pressure_field(config)

    peak_index = np.unravel_index(np.argmax(pressure), pressure.shape)
    peak_x_mm = x_grid[peak_index] * 1e3
    peak_z_mm = z_grid[peak_index] * 1e3
    peak_mpa = pressure[peak_index] / 1e6

    np.savetxt(
        output_dir / "pressure_field_mpa.csv",
        pressure / 1e6,
        delimiter=",",
        fmt="%.6f",
    )

    with (output_dir / "summary.txt").open("w", encoding="utf-8") as handle:
        handle.write("Focused ultrasound lightweight simulation\n")
        handle.write(f"frequency_hz={config.frequency_hz:.0f}\n")
        handle.write(f"source_pressure_pa={config.source_pressure_pa:.0f}\n")
        handle.write(f"transducer_radius_mm={config.transducer_radius_m * 1e3:.2f}\n")
        handle.write(f"aperture_diameter_mm={config.aperture_diameter_m * 1e3:.2f}\n")
        handle.write(f"peak_pressure_mpa={peak_mpa:.4f}\n")
        handle.write(f"peak_x_mm={peak_x_mm:.3f}\n")
        handle.write(f"peak_z_mm={peak_z_mm:.3f}\n")

    save_pressure_png(output_dir / "pressure_field.png", x_grid, z_grid, pressure, config, peak_index)


if __name__ == "__main__":
    save_outputs(SimulationConfig(), Path("outputs") / "spherical_focus")
