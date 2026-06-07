from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / "outputs" / "mplconfig-kwave312"))
(PROJECT_ROOT / "outputs" / "mplconfig-kwave312").mkdir(parents=True, exist_ok=True)

import matplotlib.pyplot as plt
import numpy as np


def load_pressure(pressure_dir: Path) -> tuple[np.ndarray, dict[str, object]]:
    pressure_path = pressure_dir / "pressure_max_mpa.npz"
    summary_path = pressure_dir / "summary.json"
    if not pressure_path.exists():
        raise FileNotFoundError(f"Missing pressure field: {pressure_path}")
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing pressure summary: {summary_path}")
    pressure_data = np.load(pressure_path)
    if "pressure_max_mpa" not in pressure_data.files:
        raise ValueError(f"{pressure_path} does not contain pressure_max_mpa")
    return np.asarray(pressure_data["pressure_max_mpa"], dtype=np.float32), json.loads(summary_path.read_text(encoding="utf-8"))


def load_cropped_model(model_path: Path, crop_origin: list[int], shape: tuple[int, int, int]) -> dict[str, np.ndarray | float]:
    data = np.load(model_path)
    required = {"sound_speed", "density", "alpha_coeff", "dx_m"}
    missing = required - set(data.files)
    if missing:
        raise ValueError(f"Model is missing required fields: {sorted(missing)}")
    origin = np.asarray(crop_origin, dtype=int)
    slices = tuple(slice(int(origin[axis]), int(origin[axis] + shape[axis])) for axis in range(3))
    result: dict[str, np.ndarray | float] = {
        "sound_speed": np.asarray(data["sound_speed"], dtype=np.float32)[slices],
        "density": np.asarray(data["density"], dtype=np.float32)[slices],
        "alpha_coeff": np.asarray(data["alpha_coeff"], dtype=np.float32)[slices],
        "dx_m": float(np.asarray(data["dx_m"]).item()),
    }
    if "labels" in data.files:
        result["labels"] = np.asarray(data["labels"], dtype=np.uint8)[slices]
    return result


def specific_heat_map(labels: np.ndarray | None, shape: tuple[int, int, int]) -> np.ndarray:
    cp = np.full(shape, 3600.0, dtype=np.float32)
    if labels is None:
        return cp
    cp[labels == 0] = 4180.0
    cp[labels == 1] = 3600.0
    cp[labels == 2] = 1300.0
    return cp


def compute_temperature_rise(
    pressure_mpa: np.ndarray,
    model: dict[str, np.ndarray | float],
    frequency_hz: float,
    alpha_power: float,
    sonication_s: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pressure_pa_peak = pressure_mpa.astype(np.float32) * 1e6
    pressure_pa_rms = pressure_pa_peak / np.sqrt(2.0)
    sound_speed = np.asarray(model["sound_speed"], dtype=np.float32)
    density = np.asarray(model["density"], dtype=np.float32)
    alpha_coeff = np.asarray(model["alpha_coeff"], dtype=np.float32)
    labels = np.asarray(model["labels"], dtype=np.uint8) if "labels" in model else None
    cp = specific_heat_map(labels, pressure_mpa.shape)

    intensity_w_m2 = np.square(pressure_pa_rms) / np.maximum(density * sound_speed, 1.0)
    frequency_mhz = frequency_hz * 1e-6
    alpha_db_per_cm = alpha_coeff * (frequency_mhz**alpha_power)
    alpha_np_per_m = alpha_db_per_cm * 100.0 / 8.686
    heat_source_w_m3 = 2.0 * alpha_np_per_m * intensity_w_m2
    temperature_rise_c = heat_source_w_m3 * sonication_s / np.maximum(density * cp, 1.0)
    return temperature_rise_c.astype(np.float32), heat_source_w_m3.astype(np.float32), intensity_w_m2.astype(np.float32)


def window_peak(array: np.ndarray, center: list[int], radius: int = 3) -> tuple[float, list[int]]:
    slices = tuple(slice(max(0, int(center[axis]) - radius), min(array.shape[axis], int(center[axis]) + radius + 1)) for axis in range(3))
    window = array[slices]
    local_index = np.unravel_index(int(np.argmax(window)), window.shape)
    origin = [sl.start for sl in slices]
    index = [int(origin[axis] + local_index[axis]) for axis in range(3)]
    return float(window[local_index]), index


def save_slice(path: Path, volume: np.ndarray, plane: str, index: int, markers: dict[str, list[int]]) -> None:
    if plane == "axial":
        image = volume[:, :, index].T
        marker_xy = {name: (pt[0], pt[1]) for name, pt in markers.items() if int(pt[2]) == index}
    elif plane == "coronal":
        image = volume[:, index, :].T
        marker_xy = {name: (pt[0], pt[2]) for name, pt in markers.items() if int(pt[1]) == index}
    elif plane == "sagittal":
        image = volume[index, :, :].T
        marker_xy = {name: (pt[1], pt[2]) for name, pt in markers.items() if int(pt[0]) == index}
    else:
        raise ValueError(f"Unknown plane: {plane}")

    plt.figure(figsize=(7, 5), dpi=140)
    plt.imshow(image, origin="lower", cmap="inferno")
    plt.colorbar(label="Temperature rise (C)")
    for name, (x, y) in marker_xy.items():
        plt.scatter([x], [y], s=28, label=name)
    if marker_xy:
        plt.legend(loc="upper right")
    plt.title(f"{plane} temperature rise")
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
    temperature_rise_c, heat_source_w_m3, intensity_w_m2 = compute_temperature_rise(
        pressure_mpa=pressure_mpa,
        model=model,
        frequency_hz=float(pressure_summary["config"]["frequency_hz"]),
        alpha_power=float(pressure_summary["config"]["alpha_power"]),
        sonication_s=float(args.sonication_s),
    )

    target = [int(v) for v in pressure_summary["target_index_ijk"]]
    global_temp_index = [int(v) for v in np.unravel_index(int(np.argmax(temperature_rise_c)), temperature_rise_c.shape)]
    target_window_peak_c, target_window_peak_index = window_peak(temperature_rise_c, target, radius=int(args.target_window_radius))

    np.savez_compressed(
        output_dir / "temperature_rise_c.npz",
        temperature_rise_c=temperature_rise_c,
        heat_source_w_m3=heat_source_w_m3,
        intensity_w_m2=intensity_w_m2,
    )
    markers = {
        "target": target,
        "temp peak": global_temp_index,
        "pressure peak": [int(v) for v in pressure_summary["pressure"]["target_window_peak_index_ijk"]],
    }
    save_slice(output_dir / "temperature_rise_axial.png", temperature_rise_c, "axial", target[2], markers)
    save_slice(output_dir / "temperature_rise_coronal.png", temperature_rise_c, "coronal", target[1], markers)
    save_slice(output_dir / "temperature_rise_sagittal.png", temperature_rise_c, "sagittal", target[0], markers)

    summary = {
        "description": "First-order temperature rise estimate from peak pressure field; no perfusion or thermal diffusion.",
        "pressure_dir": str(pressure_dir),
        "model_path": str(model_path),
        "sonication_s": float(args.sonication_s),
        "frequency_hz": float(pressure_summary["config"]["frequency_hz"]),
        "alpha_power": float(pressure_summary["config"]["alpha_power"]),
        "assumptions": {
            "pressure_to_intensity": "I = (p_peak/sqrt(2))^2 / (rho*c)",
            "heat_source": "Q = 2 * alpha_np_per_m * I",
            "temperature": "dT = Q * sonication_s / (rho * cp)",
            "limitations": "Uses pressure_max_mpa as a steady peak proxy; ignores perfusion, conduction, pulsing duty cycle, and nonlinear effects.",
        },
        "max_temperature_rise_c": float(np.max(temperature_rise_c)),
        "max_temperature_index_ijk": global_temp_index,
        "target_temperature_rise_c": float(temperature_rise_c[tuple(target)]),
        "target_window_peak_temperature_rise_c": target_window_peak_c,
        "target_window_peak_temperature_index_ijk": target_window_peak_index,
        "max_heat_source_w_m3": float(np.max(heat_source_w_m3)),
        "max_intensity_w_m2": float(np.max(intensity_w_m2)),
        "pressure_metrics": pressure_summary["pressure"],
        "source": pressure_summary["source"],
    }
    (output_dir / "thermal_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "thermal_summary.txt").open("w", encoding="utf-8") as handle:
        handle.write("First-order tFUS temperature rise estimate\n")
        handle.write(f"pressure_dir={pressure_dir}\n")
        handle.write(f"sonication_s={args.sonication_s}\n")
        handle.write(f"max_temperature_rise_c={summary['max_temperature_rise_c']:.6f}\n")
        handle.write(f"max_temperature_index_ijk={summary['max_temperature_index_ijk']}\n")
        handle.write(f"target_temperature_rise_c={summary['target_temperature_rise_c']:.6f}\n")
        handle.write(f"target_window_peak_temperature_rise_c={summary['target_window_peak_temperature_rise_c']:.6f}\n")
        handle.write("warning=first-order estimate only; not a full bioheat simulation\n")
    print(
        f"max_dT_C={summary['max_temperature_rise_c']:.6f} "
        f"target_dT_C={summary['target_temperature_rise_c']:.6f} output_dir={output_dir}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Estimate first-order temperature rise from a 3D k-Wave pressure result.")
    parser.add_argument(
        "--pressure-dir",
        default=str(PROJECT_ROOT / "outputs" / "ct_transducer_stability_target_020" / "ap30_r35_c8_t55"),
    )
    parser.add_argument("--model", default=None, help="Optional acoustic model .npz path; defaults to pressure summary config.")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "outputs" / "thermal_estimate_target_020_best"))
    parser.add_argument("--sonication-s", type=float, default=1.0, help="Equivalent continuous sonication duration in seconds.")
    parser.add_argument("--target-window-radius", type=int, default=3)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
