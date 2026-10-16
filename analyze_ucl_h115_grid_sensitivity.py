"""Align H115 water fields by physical source coordinates and compare grids."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates


def load_field(run_dir: Path) -> dict[str, np.ndarray | float]:
    with np.load(run_dir / "pressure_max_mpa.npz") as archive:
        return {
            "pressure": np.asarray(archive["pressure_max_mpa"], dtype=np.float32),
            "dx_m": float(np.asarray(archive["dx_m"]).item()),
            "source": np.asarray(archive["source_center_index_ijk"], dtype=float),
            "target": np.asarray(archive["target_index_ijk"], dtype=float),
            "nearfield_m": float(np.asarray(archive["nearfield_exclusion_m"]).item()),
        }


def sample_candidate_on_reference(reference: dict, candidate: dict) -> tuple[np.ndarray, np.ndarray]:
    reference_pressure = np.asarray(reference["pressure"])
    candidate_pressure = np.asarray(candidate["pressure"])
    ratio = float(reference["dx_m"]) / float(candidate["dx_m"])
    mapped = np.full(reference_pressure.shape, np.nan, dtype=np.float32)
    valid = np.zeros(reference_pressure.shape, dtype=bool)
    y_index = candidate["source"][1] + (np.arange(reference_pressure.shape[1]) - reference["source"][1]) * ratio
    z_index = candidate["source"][2] + (np.arange(reference_pressure.shape[2]) - reference["source"][2]) * ratio
    yy, zz = np.meshgrid(y_index, z_index, indexing="ij")
    yz_valid = (yy >= 0) & (yy <= candidate_pressure.shape[1] - 1) & (zz >= 0) & (zz <= candidate_pressure.shape[2] - 1)
    for x in range(reference_pressure.shape[0]):
        xx_value = candidate["source"][0] + (x - reference["source"][0]) * ratio
        if not 0 <= xx_value <= candidate_pressure.shape[0] - 1:
            continue
        xx = np.full_like(yy, xx_value)
        mapped[x] = map_coordinates(candidate_pressure, np.stack((xx, yy, zz)), order=1, mode="constant", cval=np.nan)
        valid[x] = yz_valid & np.isfinite(mapped[x])
    return mapped, valid


def comparison_metrics(reference: np.ndarray, candidate: np.ndarray, valid: np.ndarray) -> dict[str, float | int]:
    left = np.asarray(reference[valid], dtype=float)
    right = np.asarray(candidate[valid], dtype=float)
    if left.size == 0 or not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        raise ValueError("common-domain fields are empty or non-finite")
    scale = float(np.dot(left, right) / np.dot(right, right))
    residual = right * scale - left
    norm = float(np.linalg.norm(left))
    return {
        "common_voxels": int(left.size),
        "candidate_to_reference_least_squares_scale": scale,
        "scaled_relative_l2_percent": 100.0 * float(np.linalg.norm(residual)) / norm,
        "scaled_relative_linf_percent_of_reference_peak": 100.0 * float(np.max(np.abs(residual))) / float(np.max(left)),
        "normalized_correlation": float(np.corrcoef(left / np.max(left), right / np.max(right))[0, 1]),
        "reference_peak_mpa": float(np.max(left)),
        "candidate_peak_mpa": float(np.max(right)),
        "peak_magnitude_change_percent": 100.0 * (float(np.max(right)) - float(np.max(left))) / float(np.max(left)),
    }


def axial_peak_distance_mm(field: dict) -> float:
    pressure = np.asarray(field["pressure"])
    source = np.asarray(field["source"], dtype=int)
    line = pressure[:, source[1], source[2]]
    distances = (np.arange(line.size) - source[0]) * float(field["dx_m"])
    eligible = distances >= float(field["nearfield_m"])
    index = np.flatnonzero(eligible)[int(np.argmax(line[eligible]))]
    return float(distances[index] * 1e3)


def run(reference_dir: Path, candidate_dir: Path) -> dict:
    reference = load_field(reference_dir)
    candidate = load_field(candidate_dir)
    mapped, common = sample_candidate_on_reference(reference, candidate)
    x_distance = (np.arange(np.asarray(reference["pressure"]).shape[0]) - reference["source"][0]) * float(reference["dx_m"])
    analysis_mask = common & (x_distance[:, None, None] >= float(reference["nearfield_m"]))
    reference_peak = axial_peak_distance_mm(reference)
    candidate_peak = axial_peak_distance_mm(candidate)
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed_grid_sensitivity_observation",
        "reference": {"run_dir": str(reference_dir), "dx_mm": float(reference["dx_m"]) * 1e3},
        "candidate": {"run_dir": str(candidate_dir), "dx_mm": float(candidate["dx_m"]) * 1e3},
        "alignment": "trilinear interpolation of candidate onto reference indices using coordinates relative to each stored source centre",
        "nearfield_excluded_metrics": comparison_metrics(np.asarray(reference["pressure"]), mapped, analysis_mask),
        "axial_peak": {
            "reference_distance_mm": reference_peak,
            "candidate_distance_mm": candidate_peak,
            "candidate_minus_reference_mm": candidate_peak - reference_peak,
        },
        "interpretation": "A two-grid observation cannot establish asymptotic convergence. It only tests whether refinement materially changes this result.",
        "claim_boundary": "Homogeneous-water numerical sensitivity only; not source-model validation, skull/Case079, thermal, safety, efficacy or clinical evidence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.reference_dir, args.candidate_dir)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
