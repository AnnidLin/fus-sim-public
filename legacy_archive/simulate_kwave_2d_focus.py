from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
RUNTIME_TMP = PROJECT_ROOT / ".tmp"
MPLCONFIGDIR = RUNTIME_TMP / f"mplconfig-kwave312-runtime-{os.getpid()}"
RUNTIME_TMP.mkdir(parents=True, exist_ok=True)
MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(RUNTIME_TMP)
os.environ["TMP"] = str(RUNTIME_TMP)
os.environ["MPLCONFIGDIR"] = str(MPLCONFIGDIR)
logging.getLogger("matplotlib").setLevel(logging.ERROR)

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from kwave.data import Vector
from kwave.kgrid import kWaveGrid
from kwave.kmedium import kWaveMedium
from kwave.ksensor import kSensor
from kwave.ksource import kSource
from kwave.kspaceFirstOrder import kspaceFirstOrder, reshape_to_grid
from kwave.utils.mapgen import make_arc
from kwave.utils.signals import tone_burst


@dataclass(frozen=True)
class KWave2DConfig:
    frequency_hz: float = 500_000.0
    source_pressure_pa: float = 1_000_000.0
    sound_speed_m_s: float = 1540.0
    density_kg_m3: float = 1000.0
    transducer_radius_m: float = 30e-3
    aperture_diameter_m: float = 25e-3
    dx_m: float = 0.5e-3
    grid_depth_m: float = 64e-3
    grid_lateral_m: float = 48.5e-3
    source_depth_m: float = 4e-3
    cfl: float = 0.30
    simulation_time_s: float = 55e-6
    tone_burst_cycles: int = 5
    pml_size: int = 12

    @property
    def nx(self) -> int:
        return int(round(self.grid_depth_m / self.dx_m))

    @property
    def ny(self) -> int:
        return int(round(self.grid_lateral_m / self.dx_m))

    @property
    def dt_s(self) -> float:
        return self.cfl * self.dx_m / self.sound_speed_m_s

    @property
    def nt(self) -> int:
        return int(np.ceil(self.simulation_time_s / self.dt_s))

    @property
    def source_depth_index(self) -> int:
        return max(2, int(round(self.source_depth_m / self.dx_m)) + 1)

    @property
    def focus_depth_index(self) -> int:
        return self.source_depth_index + int(round(self.transducer_radius_m / self.dx_m))

    @property
    def center_lateral_index(self) -> int:
        return self.ny // 2 + 1

    @property
    def aperture_grid_points(self) -> int:
        points = int(round(self.aperture_diameter_m / self.dx_m))
        return points if points % 2 == 1 else points + 1

    @property
    def radius_grid_points(self) -> int:
        return int(round(self.transducer_radius_m / self.dx_m))


def build_source_mask(config: KWave2DConfig) -> np.ndarray:
    if config.focus_depth_index >= config.nx:
        raise ValueError("The focus is outside the grid; increase grid_depth_m.")

    return make_arc(
        Vector([config.nx, config.ny]),
        Vector([config.source_depth_index, config.center_lateral_index]),
        config.radius_grid_points,
        config.aperture_grid_points,
        Vector([config.focus_depth_index, config.center_lateral_index]),
    ).astype(bool)


def run_simulation(config: KWave2DConfig) -> tuple[dict[str, np.ndarray], np.ndarray, float]:
    kgrid = kWaveGrid([config.nx, config.ny], [config.dx_m, config.dx_m])
    kgrid.setTime(config.nt, config.dt_s)

    medium = kWaveMedium(
        sound_speed=np.array(config.sound_speed_m_s),
        density=np.array(config.density_kg_m3),
    )

    source = kSource()
    source.p_mask = build_source_mask(config)
    source.p = config.source_pressure_pa * tone_burst(
        1.0 / config.dt_s,
        config.frequency_hz,
        config.tone_burst_cycles,
        signal_length=config.nt,
    )
    source.p_mode = "dirichlet"

    sensor = kSensor(
        mask=np.ones((config.nx, config.ny), dtype=bool),
        record=["p_max", "p_min", "p_final"],
    )

    start = time.perf_counter()
    result = kspaceFirstOrder(
        kgrid,
        medium,
        source,
        sensor,
        backend="python",
        device="cpu",
        pml_size=config.pml_size,
        pml_inside=False,
        quiet=True,
    )
    elapsed_s = time.perf_counter() - start
    return result, source.p_mask, elapsed_s


def pressure_abs_max_mpa(result: dict[str, np.ndarray], config: KWave2DConfig) -> np.ndarray:
    p_max = reshape_to_grid(result["p_max"], (config.nx, config.ny))
    p_min = reshape_to_grid(result["p_min"], (config.nx, config.ny))
    return np.maximum(np.abs(p_max), np.abs(p_min)) / 1e6


def save_pressure_image(path: Path, pressure_mpa: np.ndarray, source_mask: np.ndarray, config: KWave2DConfig) -> None:
    peak_index = np.unravel_index(np.argmax(pressure_mpa), pressure_mpa.shape)
    center_lateral_zero_index = config.center_lateral_index - 1
    lateral_mm = (np.arange(config.ny) - center_lateral_zero_index) * config.dx_m * 1e3
    depth_mm = np.arange(config.nx) * config.dx_m * 1e3
    peak_lateral_mm = lateral_mm[peak_index[1]]
    peak_depth_mm = depth_mm[peak_index[0]]

    fig, ax = plt.subplots(figsize=(7.0, 6.5), dpi=150)
    im = ax.imshow(
        pressure_mpa,
        cmap="viridis",
        origin="upper",
        extent=[lateral_mm[0], lateral_mm[-1], depth_mm[-1], depth_mm[0]],
        aspect="equal",
    )
    source_y, source_x = np.where(source_mask)
    ax.scatter(
        lateral_mm[source_x],
        depth_mm[source_y],
        s=6,
        c="white",
        marker="s",
        linewidths=0,
        label="source arc",
    )
    ax.plot(peak_lateral_mm, peak_depth_mm, marker="+", color="red", markersize=14, markeredgewidth=2.0)
    ax.plot(
        0.0,
        (config.focus_depth_index - 1) * config.dx_m * 1e3,
        marker="x",
        color="white",
        markersize=8,
        markeredgewidth=1.6,
        label="geometric focus",
    )
    ax.set_xlabel("Lateral position [mm]")
    ax.set_ylabel("Depth [mm]")
    ax.set_title("2D k-Wave focused ultrasound pressure maximum")
    ax.legend(loc="lower right", fontsize=8, framealpha=0.85)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Absolute peak pressure [MPa]")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def save_layout_image(path: Path, source_mask: np.ndarray, config: KWave2DConfig) -> None:
    layout = np.zeros((config.nx, config.ny), dtype=float)
    layout[source_mask] = 1.0
    layout[config.focus_depth_index - 1, config.center_lateral_index - 1] = 0.65

    lateral_mm = (np.arange(config.ny) - (config.center_lateral_index - 1)) * config.dx_m * 1e3
    depth_mm = np.arange(config.nx) * config.dx_m * 1e3

    fig, ax = plt.subplots(figsize=(7.0, 6.5), dpi=150)
    ax.imshow(
        layout,
        cmap="magma",
        origin="upper",
        extent=[lateral_mm[0], lateral_mm[-1], depth_mm[-1], depth_mm[0]],
        aspect="equal",
        vmin=0,
        vmax=1,
    )
    ax.set_xlabel("Lateral position [mm]")
    ax.set_ylabel("Depth [mm]")
    ax.set_title("2D k-Wave source and geometric focus layout")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def save_summary(path: Path, pressure_mpa: np.ndarray, source_mask: np.ndarray, elapsed_s: float, config: KWave2DConfig) -> None:
    peak_index = np.unravel_index(np.argmax(pressure_mpa), pressure_mpa.shape)
    peak_depth_mm = peak_index[0] * config.dx_m * 1e3
    peak_lateral_mm = (peak_index[1] - (config.center_lateral_index - 1)) * config.dx_m * 1e3
    focus_depth_mm = (config.focus_depth_index - 1) * config.dx_m * 1e3

    with path.open("w", encoding="utf-8") as handle:
        handle.write("2D k-Wave focused ultrasound baseline\n")
        handle.write("backend=python_cpu\n")
        handle.write(f"frequency_hz={config.frequency_hz:.0f}\n")
        handle.write(f"source_pressure_pa={config.source_pressure_pa:.0f}\n")
        handle.write(f"tone_burst_cycles={config.tone_burst_cycles}\n")
        handle.write(f"sound_speed_m_s={config.sound_speed_m_s:.1f}\n")
        handle.write(f"density_kg_m3={config.density_kg_m3:.1f}\n")
        handle.write(f"transducer_radius_mm={config.transducer_radius_m * 1e3:.2f}\n")
        handle.write(f"aperture_diameter_mm={config.aperture_diameter_m * 1e3:.2f}\n")
        handle.write(f"grid_points={config.nx}x{config.ny}\n")
        handle.write(f"dx_mm={config.dx_m * 1e3:.3f}\n")
        handle.write(f"dt_ns={config.dt_s * 1e9:.3f}\n")
        handle.write(f"nt={config.nt}\n")
        handle.write(f"pml_size={config.pml_size}\n")
        handle.write(f"source_points={int(np.sum(source_mask))}\n")
        handle.write(f"geometric_focus_depth_mm={focus_depth_mm:.3f}\n")
        handle.write(f"peak_pressure_mpa={float(np.max(pressure_mpa)):.6f}\n")
        handle.write(f"peak_lateral_mm={peak_lateral_mm:.3f}\n")
        handle.write(f"peak_depth_mm={peak_depth_mm:.3f}\n")
        handle.write(f"runtime_s={elapsed_s:.3f}\n")


def save_outputs(config: KWave2DConfig, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    result, source_mask, elapsed_s = run_simulation(config)
    pressure_mpa = pressure_abs_max_mpa(result, config)

    if not np.all(np.isfinite(pressure_mpa)):
        raise ValueError("Pressure field contains NaN or infinite values.")
    if np.max(pressure_mpa) <= 0:
        raise ValueError("Pressure field is all zero.")

    np.savetxt(output_dir / "pressure_max_mpa.csv", pressure_mpa, delimiter=",", fmt="%.6f")
    save_pressure_image(output_dir / "pressure_max.png", pressure_mpa, source_mask, config)
    save_layout_image(output_dir / "source_layout.png", source_mask, config)
    save_summary(output_dir / "summary.txt", pressure_mpa, source_mask, elapsed_s, config)


if __name__ == "__main__":
    save_outputs(KWave2DConfig(), PROJECT_ROOT / "outputs" / "kwave_2d_focus")
