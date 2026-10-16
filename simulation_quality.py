from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_PRESETS_PATH = PROJECT_ROOT / "simulation_presets.json"


def load_presets(path: Path | None = None) -> dict[str, Any]:
    presets_path = path or DEFAULT_PRESETS_PATH
    with presets_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_preset(preset_name: str, presets_path: Path | None = None) -> dict[str, Any]:
    data = load_presets(presets_path)
    presets = data.get("presets", {})
    if preset_name not in presets:
        raise ValueError(f"Unknown simulation preset {preset_name!r}. Available presets: {', '.join(sorted(presets))}")
    preset = dict(presets[preset_name])
    preset["preset"] = preset_name
    preset["schema_version"] = data.get("schema_version")
    preset["source_evidence_brief"] = data.get("source_evidence_brief")
    return preset


def estimate_runtime_grid(sound_speed: np.ndarray, dx_m: float, cfl: float, simulation_time_s: float) -> dict[str, Any]:
    c_max = float(np.max(sound_speed))
    dt_s = float(cfl * dx_m / c_max)
    nt = int(math.ceil(simulation_time_s / dt_s))
    return {
        "dt_s": dt_s,
        "nt": nt,
        "c_max_m_s": c_max,
    }


def estimate_memory_bytes(shape: tuple[int, ...], nt: int) -> dict[str, Any]:
    voxel_count = int(np.prod(shape))
    # Conservative lightweight estimate for core Python arrays kept around this platform.
    float32_arrays = 6
    uint8_or_bool_arrays = 3
    time_series_factor = min(max(nt, 1), 2048)
    estimated_bytes = voxel_count * (float32_arrays * 4 + uint8_or_bool_arrays)
    estimated_bytes += time_series_factor * 8
    return {
        "voxel_count": voxel_count,
        "estimated_bytes": int(estimated_bytes),
        "estimated_mb": float(estimated_bytes / (1024**2)),
        "method": "approx_core_arrays_float32x6_uint8x3_plus_small_time_series",
    }


def build_simulation_quality(
    *,
    preset_name: str,
    sound_speed: np.ndarray,
    dx_m: float,
    frequency_hz: float,
    cfl: float,
    pml_size: int,
    simulation_time_s: float,
    backend: str,
    device: str,
    runtime_s: float | None = None,
    output_completeness: dict[str, bool] | None = None,
) -> dict[str, Any]:
    preset = get_preset(preset_name)
    runtime_grid = estimate_runtime_grid(sound_speed, dx_m, cfl, simulation_time_s)
    shape = tuple(int(v) for v in sound_speed.shape)
    c_min = float(np.min(sound_speed))
    wavelength_min_m = c_min / float(frequency_hz)
    ppw_min = wavelength_min_m / float(dx_m)
    memory = estimate_memory_bytes(shape, int(runtime_grid["nt"]))
    paper_grade_blockers: list[str] = []
    if preset_name == "paper_grade":
        paper_grade_blockers.extend(
            [
                "grid_convergence_report_missing",
                "pml_boundary_review_missing",
                "environment_record_missing",
            ]
        )
    else:
        paper_grade_blockers.append("preset_is_not_paper_grade")
    return {
        "preset": preset_name,
        "quality_level": preset.get("quality_level", preset_name),
        "intended_use": preset.get("intended_use"),
        "evidence_level": preset.get("evidence_level"),
        "screening_only": bool(preset.get("screening_only", True)),
        "is_paper_grade": preset_name == "paper_grade" and not paper_grade_blockers,
        "paper_grade_blockers": paper_grade_blockers,
        "dx_m": float(dx_m),
        "dx_mm": float(dx_m * 1e3),
        "frequency_hz": float(frequency_hz),
        "sound_speed_min_m_s": c_min,
        "sound_speed_max_m_s": float(np.max(sound_speed)),
        "wavelength_min_m": float(wavelength_min_m),
        "ppw_min_sound_speed": float(ppw_min),
        "cfl": float(cfl),
        "pml_size": int(pml_size),
        "grid_size": list(shape),
        "voxel_count": memory["voxel_count"],
        "dt_s": runtime_grid["dt_s"],
        "nt": runtime_grid["nt"],
        "simulation_time_s": float(simulation_time_s),
        "backend": backend,
        "device": device,
        "runtime_s": None if runtime_s is None else float(runtime_s),
        "memory_estimate": memory,
        "required_summary_fields": preset.get("required_summary_fields", []),
        "quality_requirements": preset.get("quality_requirements", {}),
        "runtime_policy": preset.get("runtime_policy", {}),
        "output_completeness": output_completeness or {},
        "source_evidence_brief": preset.get("source_evidence_brief"),
    }


def write_quality_dry_run_summary(
    output_dir: Path,
    *,
    description: str,
    config: dict[str, Any],
    model: dict[str, Any],
    source: dict[str, Any],
    simulation_quality: dict[str, Any],
    environment_record: dict[str, Any] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "description": description,
        "dry_run_quality_only": True,
        "note": "This dry run did not call k-Wave and did not generate a pressure field.",
        "config": config,
        "model": model,
        "source": source,
        "simulation_quality": simulation_quality,
    }
    if environment_record is not None:
        summary["environment_record"] = environment_record
    (output_dir / "quality_dry_run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
