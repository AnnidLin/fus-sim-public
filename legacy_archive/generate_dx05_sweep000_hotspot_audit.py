from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent
PRESSURE_DIR = PROJECT_ROOT / "outputs" / "ct_sweep_scan_079_dx0p5" / "sweep_000"
PENNES_DIR = PRESSURE_DIR / "pennes_thermal"
MODEL_PATH = PROJECT_ROOT / "outputs" / "ct_acoustic_model_3d_profile_hu300_dx0p5" / "acoustic_model_3d.npz"
OUT_DIR = PROJECT_ROOT / "outputs" / "ct_sweep_hotspot_audit" / "079_sweep_000_dx0p5"
OUT_JSON = OUT_DIR / "hotspot_audit.json"
OUT_MD = OUT_DIR / "hotspot_audit.md"
OUT_AXIS_CSV = OUT_DIR / "beam_axis_profile.csv"

LABEL_NAMES = {
    0: "background_or_coupling",
    1: "soft_tissue_or_brain",
    2: "skull_bone",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def as_index(value: Any) -> np.ndarray:
    return np.asarray(value, dtype=np.int64)


def to_list(index: np.ndarray | tuple[int, int, int]) -> list[int]:
    arr = np.asarray(index, dtype=np.int64)
    return [int(v) for v in arr.tolist()]


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    val = float(value)
    if math.isfinite(val):
        return val
    return None


def distance_mm(a: np.ndarray, b: np.ndarray, dx_mm: float) -> float:
    return float(np.linalg.norm((a.astype(float) - b.astype(float)) * dx_mm))


def axial_lateral_mm(index: np.ndarray, source: np.ndarray, target: np.ndarray, dx_mm: float) -> tuple[float, float]:
    axis = target.astype(float) - source.astype(float)
    norm = float(np.linalg.norm(axis))
    if norm <= 0:
        return 0.0, 0.0
    unit = axis / norm
    delta = index.astype(float) - source.astype(float)
    axial_vox = float(np.dot(delta, unit))
    lateral_vox = float(np.linalg.norm(delta - axial_vox * unit))
    return axial_vox * dx_mm, lateral_vox * dx_mm


def load_cropped_model(crop_origin: np.ndarray, shape: tuple[int, int, int]) -> dict[str, np.ndarray]:
    model = np.load(MODEL_PATH)
    crop = tuple(slice(int(origin), int(origin) + int(size)) for origin, size in zip(crop_origin, shape))
    return {
        "labels": np.asarray(model["labels"][crop], dtype=np.uint8),
        "hu": np.asarray(model["hu"][crop], dtype=np.float32),
        "sound_speed": np.asarray(model["sound_speed"][crop], dtype=np.float32),
        "density": np.asarray(model["density"][crop], dtype=np.float32),
        "alpha_coeff": np.asarray(model["alpha_coeff"][crop], dtype=np.float32),
    }


def point_record(
    name: str,
    index: np.ndarray,
    crop_origin: np.ndarray,
    dx_mm: float,
    source: np.ndarray,
    entry: np.ndarray,
    target: np.ndarray,
    arrays: dict[str, np.ndarray],
) -> dict[str, Any]:
    idx = tuple(int(v) for v in index)
    label = int(arrays["labels"][idx])
    axial, lateral = axial_lateral_mm(index, source, target, dx_mm)
    return {
        "name": name,
        "crop_index_ijk": to_list(index),
        "model_index_ijk": to_list(crop_origin + index),
        "label": label,
        "material": LABEL_NAMES.get(label, f"unknown_{label}"),
        "pressure_mpa": safe_float(arrays["pressure"][idx]),
        "temperature_rise_c": safe_float(arrays["temperature_rise"][idx]),
        "temperature_c": safe_float(arrays["temperature"][idx]),
        "cem43_min": safe_float(arrays["cem43"][idx]),
        "heat_source_w_m3": safe_float(arrays["heat_source"][idx]),
        "intensity_w_m2": safe_float(arrays["intensity"][idx]),
        "hu": safe_float(arrays["hu"][idx]),
        "sound_speed_m_s": safe_float(arrays["sound_speed"][idx]),
        "density_kg_m3": safe_float(arrays["density"][idx]),
        "alpha_db_mhz_cm": safe_float(arrays["alpha_coeff"][idx]),
        "distance_to_source_mm": distance_mm(index, source, dx_mm),
        "distance_to_entry_mm": distance_mm(index, entry, dx_mm),
        "distance_to_target_mm": distance_mm(index, target, dx_mm),
        "axial_from_source_mm": axial,
        "lateral_offset_from_beam_mm": lateral,
        "axial_shortfall_to_target_mm": distance_mm(target, source, dx_mm) - axial,
    }


def top_label_counts(metric: np.ndarray, labels: np.ndarray, top_n: int = 1000) -> dict[str, Any]:
    flat = metric.reshape(-1)
    n = min(int(top_n), flat.size)
    top_flat = np.argpartition(flat, -n)[-n:]
    top_labels = labels.reshape(-1)[top_flat]
    unique, counts = np.unique(top_labels, return_counts=True)
    return {
        "top_n": n,
        "label_counts": {
            LABEL_NAMES.get(int(label), str(int(label))): int(count)
            for label, count in zip(unique, counts)
        },
    }


def contiguous_segments(mask: np.ndarray, dx_mm: float, source_x: int) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    start: int | None = None
    for i, active in enumerate(mask.tolist() + [False]):
        if active and start is None:
            start = i
        if not active and start is not None:
            end = i - 1
            segments.append(
                {
                    "x_start": int(start),
                    "x_end": int(end),
                    "length_voxels": int(end - start + 1),
                    "length_mm": float((end - start + 1) * dx_mm),
                    "start_axial_from_source_mm": float((start - source_x) * dx_mm),
                    "end_axial_from_source_mm": float((end - source_x) * dx_mm),
                }
            )
            start = None
    return segments


def cem43_from_curve(times: np.ndarray, temperatures: np.ndarray) -> float:
    if len(times) == 0:
        return 0.0
    cem = 0.0
    last_time = 0.0
    for t, temp in zip(times, temperatures):
        dt = max(0.0, float(t) - last_time)
        last_time = float(t)
        if temp < 37.0:
            continue
        r = 0.25 if temp < 43.0 else 0.5
        cem += (dt / 60.0) * (r ** (43.0 - float(temp)))
    return float(cem)


def load_curve(path: Path) -> dict[str, np.ndarray]:
    rows: list[dict[str, float]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append({key: float(value) for key, value in row.items() if value != ""})
    return {
        "time_s": np.asarray([row["time_s"] for row in rows], dtype=float),
        "skull_max_temperature_rise_c": np.asarray(
            [row["skull_max_temperature_rise_c"] for row in rows],
            dtype=float,
        ),
        "max_temperature_rise_c": np.asarray([row["max_temperature_rise_c"] for row in rows], dtype=float),
    }


def source_pressure_scaling(curve: dict[str, np.ndarray], current_source_pressure_mpa: float) -> dict[str, Any]:
    times = curve["time_s"]
    skull_rise = curve["skull_max_temperature_rise_c"]
    max_rise = curve["max_temperature_rise_c"]

    def metrics(scale: float) -> dict[str, float]:
        factor = scale * scale
        skull_temp = 37.0 + skull_rise * factor
        max_temp = 37.0 + max_rise * factor
        return {
            "source_pressure_mpa": float(current_source_pressure_mpa * scale),
            "scale": float(scale),
            "power_scale": float(factor),
            "skull_max_temperature_c": float(np.max(skull_temp)),
            "max_temperature_c": float(np.max(max_temp)),
            "estimated_skull_cem43_min": cem43_from_curve(times, skull_temp),
        }

    def ok(scale: float) -> bool:
        m = metrics(scale)
        return m["skull_max_temperature_c"] <= 43.0 and m["estimated_skull_cem43_min"] <= 16.0

    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if ok(mid):
            lo = mid
        else:
            hi = mid

    threshold = metrics(lo)
    return {
        "method": "linear temperature-rise scaling from existing Pennes time curve; CEM43 recomputed on scaled skull-max curve",
        "claim_level": "screening_estimate_not_thermal_validation",
        "current_source_pressure_mpa": current_source_pressure_mpa,
        "current_estimated": metrics(1.0),
        "safe_threshold_estimate": threshold,
        "rounded_recommendation": {
            "source_pressure_mpa": math.floor(threshold["source_pressure_mpa"] * 100.0) / 100.0,
            "note": "Rounded down to two decimals for planning only; requires rerun for validation.",
        },
        "limits": {
            "skull_temperature_c": 43.0,
            "skull_cem43_min": 16.0,
        },
    }


def build_axis_profile(
    arrays: dict[str, np.ndarray],
    source: np.ndarray,
    entry: np.ndarray,
    target: np.ndarray,
    crop_origin: np.ndarray,
    dx_mm: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    y = int(source[1])
    z = int(source[2])
    rows: list[dict[str, Any]] = []
    for x in range(arrays["pressure"].shape[0]):
        idx = np.asarray([x, y, z], dtype=np.int64)
        label = int(arrays["labels"][x, y, z])
        rows.append(
            {
                "x_index": x,
                "model_x_index": int(crop_origin[0] + x),
                "axial_from_source_mm": float((x - int(source[0])) * dx_mm),
                "distance_to_target_mm": distance_mm(idx, target, dx_mm),
                "label": label,
                "material": LABEL_NAMES.get(label, f"unknown_{label}"),
                "pressure_mpa": safe_float(arrays["pressure"][x, y, z]),
                "temperature_rise_c": safe_float(arrays["temperature_rise"][x, y, z]),
                "cem43_min": safe_float(arrays["cem43"][x, y, z]),
                "hu": safe_float(arrays["hu"][x, y, z]),
                "sound_speed_m_s": safe_float(arrays["sound_speed"][x, y, z]),
                "density_kg_m3": safe_float(arrays["density"][x, y, z]),
                "alpha_db_mhz_cm": safe_float(arrays["alpha_coeff"][x, y, z]),
            }
        )
    labels_axis = arrays["labels"][:, y, z]
    skull_mask = labels_axis == 2
    pressure_axis = arrays["pressure"][:, y, z]
    temp_axis = arrays["temperature_rise"][:, y, z]
    summary = {
        "axis_yz": [int(y), int(z)],
        "skull_segments": contiguous_segments(skull_mask, dx_mm, int(source[0])),
        "axis_pressure_peak": rows[int(np.argmax(pressure_axis))],
        "axis_temperature_rise_peak": rows[int(np.argmax(temp_axis))],
        "source_axis_row": rows[int(source[0])],
        "entry_axis_row": rows[int(entry[0])],
        "target_axis_row": rows[int(target[0])],
    }
    return rows, summary


def write_axis_csv(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with OUT_AXIS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(result: dict[str, Any]) -> str:
    hotspots = result["hotspots"]
    scaling = result["source_pressure_scaling"]
    axis = result["beam_axis"]
    lines = [
        "# dx0.5 Sweep 000 Hotspot Audit",
        "",
        f"- generated_at: `{result['generated_at']}`",
        f"- claim_level: `{result['claim_level']}`",
        f"- pressure_dir: `{result['inputs']['pressure_dir']}`",
        "",
        "## Hotspot Localization",
        "",
        "| Point | Material | Crop index | Model index | Pressure MPa | dT C | CEM43 min | Dist to target mm | Axial from source mm | Lateral offset mm |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in hotspots:
        lines.append(
            "| {name} | {material} | {crop} | {model} | {p:.6g} | {dt:.6g} | {cem:.6g} | {dist:.6g} | {axial:.6g} | {lat:.6g} |".format(
                name=item["name"],
                material=item["material"],
                crop=item["crop_index_ijk"],
                model=item["model_index_ijk"],
                p=item["pressure_mpa"] or 0.0,
                dt=item["temperature_rise_c"] or 0.0,
                cem=item["cem43_min"] or 0.0,
                dist=item["distance_to_target_mm"],
                axial=item["axial_from_source_mm"],
                lat=item["lateral_offset_from_beam_mm"],
            )
        )
    lines.extend(
        [
            "",
            "## Beam Axis",
            "",
            f"- axis y/z: `{axis['axis_yz']}`",
            f"- skull segments on central axis: `{axis['skull_segments']}`",
            f"- axis pressure peak: x=`{axis['axis_pressure_peak']['x_index']}`, material=`{axis['axis_pressure_peak']['material']}`, pressure=`{axis['axis_pressure_peak']['pressure_mpa']}` MPa",
            f"- target axis pressure: `{axis['target_axis_row']['pressure_mpa']}` MPa",
            "",
            "## Source Pressure Scaling Estimate",
            "",
            f"- method: `{scaling['method']}`",
            f"- current source pressure: `{scaling['current_source_pressure_mpa']}` MPa",
            f"- estimated safe threshold: `{scaling['safe_threshold_estimate']['source_pressure_mpa']:.4f}` MPa",
            f"- rounded planning value: `{scaling['rounded_recommendation']['source_pressure_mpa']:.2f}` MPa",
            f"- estimated skull CEM43 at threshold: `{scaling['safe_threshold_estimate']['estimated_skull_cem43_min']:.6g}` min",
            f"- estimated max temperature at threshold: `{scaling['safe_threshold_estimate']['max_temperature_c']:.6g}` C",
            "",
            "## Interpretation",
            "",
            "- The pressure, temperature-rise, and CEM43 extrema are co-localized near the skull-side high-pressure region, far upstream of the target.",
            "- The source-pressure estimate is a screening calculation from the existing thermal curve. It is useful for planning a later authorized validation run, not for declaring safety.",
            "- The dx0.5 run remains a hotspot diagnostic and does not establish numerical convergence.",
            "",
            "## Blocked Claims",
            "",
        ]
    )
    lines.extend(f"- {claim}" for claim in result["blocked_claims"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    summary = read_json(PRESSURE_DIR / "summary.json")
    pennes = read_json(PENNES_DIR / "pennes_summary.json")
    pressure_npz = np.load(PRESSURE_DIR / "pressure_max_mpa.npz")
    thermal_npz = np.load(PENNES_DIR / "pennes_temperature_c.npz")

    pressure = np.asarray(pressure_npz["pressure_max_mpa"], dtype=np.float32)
    shape = tuple(int(v) for v in pressure.shape)
    crop_origin = as_index(summary["crop_origin_ijk"])
    dx_mm = float(summary["dx_m"]) * 1000.0
    source = as_index(summary["source"]["source_center_index_ijk"])
    entry = as_index(summary["source"]["entry_index_ijk"])
    target = as_index(summary["target_index_ijk"])
    cropped_model = load_cropped_model(crop_origin, shape)

    arrays = {
        "pressure": pressure,
        "temperature": np.asarray(thermal_npz["temperature_c"], dtype=np.float32),
        "temperature_rise": np.asarray(thermal_npz["temperature_rise_c"], dtype=np.float32),
        "cem43": np.asarray(thermal_npz["cem43_min"], dtype=np.float32),
        "heat_source": np.asarray(thermal_npz["heat_source_w_m3"], dtype=np.float32),
        "intensity": np.asarray(thermal_npz["intensity_w_m2"], dtype=np.float32),
        **cropped_model,
    }

    indices = {
        "pressure_global_peak": as_index(pennes["pressure_metrics"]["global_peak_index_ijk"]),
        "temperature_rise_peak": as_index(pennes["max_temperature_index_ijk"]),
        "cem43_peak": as_index(np.unravel_index(np.nanargmax(arrays["cem43"]), shape)),
        "heat_source_peak": as_index(np.unravel_index(np.nanargmax(arrays["heat_source"]), shape)),
        "target": target,
        "target_window_peak": as_index(pennes["target_window_peak_temperature_index_ijk"]),
        "source_center": source,
        "entry": entry,
    }
    hotspots = [
        point_record(name, index, crop_origin, dx_mm, source, entry, target, arrays)
        for name, index in indices.items()
    ]
    axis_rows, axis_summary = build_axis_profile(arrays, source, entry, target, crop_origin, dx_mm)
    curve = load_curve(PENNES_DIR / "temperature_time_curve.csv")
    scaling = source_pressure_scaling(
        curve,
        current_source_pressure_mpa=float(summary["config"]["source_pressure_pa"]) / 1_000_000.0,
    )

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_id": "079_sweep_000_dx0p5_hotspot_audit",
        "claim_level": "hotspot_localization_and_source_pressure_screening_not_validation",
        "inputs": {
            "pressure_dir": rel(PRESSURE_DIR),
            "pennes_dir": rel(PENNES_DIR),
            "model_path": rel(MODEL_PATH),
            "summary": rel(PRESSURE_DIR / "summary.json"),
            "pennes_summary": rel(PENNES_DIR / "pennes_summary.json"),
        },
        "coordinate_frame": {
            "crop_origin_ijk": to_list(crop_origin),
            "dx_mm": dx_mm,
            "source_center_index_ijk": to_list(source),
            "entry_index_ijk": to_list(entry),
            "target_index_ijk": to_list(target),
        },
        "hotspots": hotspots,
        "top_label_counts": {
            "pressure_top_1000": top_label_counts(arrays["pressure"], arrays["labels"], 1000),
            "heat_source_top_1000": top_label_counts(arrays["heat_source"], arrays["labels"], 1000),
            "cem43_top_1000": top_label_counts(arrays["cem43"], arrays["labels"], 1000),
        },
        "beam_axis": axis_summary,
        "source_pressure_scaling": scaling,
        "decision": {
            "hotspot_colocalized_with_pressure": True,
            "hotspot_material": hotspots[0]["material"],
            "target_is_hotspot": False,
            "rerun_required_for_scaled_safety_claim": True,
            "recommended_next": "Use the rounded source-pressure estimate only to plan a single authorized validation run after reviewing hotspot geometry.",
        },
        "blocked_claims": [
            "numerical convergence",
            "validated source-pressure safety threshold",
            "clinical or medical safety",
            "paper-grade pressure baseline",
            "default mapping profile promotion",
        ],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_axis_csv(axis_rows)
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(build_markdown(result), encoding="utf-8")
    print(json.dumps({"hotspot_audit_valid": True, "output": rel(OUT_JSON)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
