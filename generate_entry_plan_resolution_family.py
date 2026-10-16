from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_model(path: Path) -> tuple[np.ndarray, float, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        labels = np.asarray(archive["labels"], dtype=np.uint8)
        dx_m = float(np.asarray(archive["dx_m"]).item())
        target = np.asarray(archive["target_index_ijk"], dtype=np.int32)
    if labels.ndim != 3 or target.shape != (3,):
        raise ValueError("Model labels must be 3-D and target_index_ijk length 3.")
    return labels, dx_m, target


def scaled_index(
    index: np.ndarray,
    reference_dx_m: float,
    candidate_dx_m: float,
    shape: tuple[int, int, int],
) -> np.ndarray:
    mapped = np.rint(
        np.asarray(index, dtype=np.float64)
        * reference_dx_m
        / candidate_dx_m
    ).astype(np.int32)
    if np.any(mapped < 0) or np.any(mapped >= np.asarray(shape)):
        raise ValueError(
            f"Mapped index {mapped.tolist()} is outside candidate shape {shape}."
        )
    return mapped


def sampled_ray_indices(
    source: np.ndarray,
    target: np.ndarray,
    *,
    samples_per_voxel: int = 8,
) -> np.ndarray:
    delta = target.astype(np.float64) - source.astype(np.float64)
    samples = max(2, int(np.max(np.abs(delta))) * samples_per_voxel + 1)
    points = np.rint(
        source[None, :] + np.linspace(0.0, 1.0, samples)[:, None] * delta[None, :]
    ).astype(np.int32)
    keep = np.ones(points.shape[0], dtype=bool)
    keep[1:] = np.any(points[1:] != points[:-1], axis=1)
    return points[keep]


def angle_deg(left: np.ndarray, right: np.ndarray) -> float:
    left = left.astype(np.float64)
    right = right.astype(np.float64)
    cosine = float(
        np.dot(left, right)
        / (np.linalg.norm(left) * np.linalg.norm(right))
    )
    return math.degrees(math.acos(float(np.clip(cosine, -1.0, 1.0))))


def transform_plan(
    reference_plan: dict[str, Any],
    labels: np.ndarray,
    candidate_dx_m: float,
    model_target: np.ndarray,
) -> tuple[dict[str, Any], dict[str, Any]]:
    reference_dx_m = float(reference_plan["dx_m"])
    shape = tuple(int(value) for value in labels.shape)
    reference_target = np.asarray(
        reference_plan["target_index_ijk"], dtype=np.int32
    )
    reference_source = np.asarray(
        reference_plan["source_center_index_ijk"], dtype=np.int32
    )
    target = scaled_index(
        reference_target, reference_dx_m, candidate_dx_m, shape
    )
    source = scaled_index(
        reference_source, reference_dx_m, candidate_dx_m, shape
    )
    ray = sampled_ray_indices(source, target)
    ray_labels = labels[tuple(ray.T)]
    skull_positions = np.flatnonzero(ray_labels == 2)
    if not skull_positions.size:
        raise ValueError("Mapped source-target ray does not cross skull label 2.")
    entry = ray[int(skull_positions[0])]
    skull_exit = ray[int(skull_positions[-1])]
    beam_axis = target - source
    source_to_target_mm = (
        float(np.linalg.norm(beam_axis) * candidate_dx_m * 1e3)
    )
    source_to_entry_mm = (
        float(np.linalg.norm(entry - source) * candidate_dx_m * 1e3)
    )
    if skull_positions.size == 1:
        skull_path_mm = candidate_dx_m * 1e3
    else:
        skull_path_mm = float(
            np.sum(
                np.linalg.norm(
                    np.diff(ray[skull_positions], axis=0), axis=1
                )
            )
            * candidate_dx_m
            * 1e3
            + candidate_dx_m * 1e3
        )
    reference_beam = reference_target - reference_source
    source_error_mm = float(
        np.linalg.norm(
            source * candidate_dx_m - reference_source * reference_dx_m
        )
        * 1e3
    )
    target_error_mm = float(
        np.linalg.norm(
            target * candidate_dx_m - reference_target * reference_dx_m
        )
        * 1e3
    )
    distance_delta_mm = abs(
        source_to_target_mm
        - float(reference_plan["source_to_target_distance_mm"])
    )
    angular_delta_deg = angle_deg(reference_beam, beam_axis)
    tolerance_mm = candidate_dx_m * 1e3
    checks = {
        "model_target_matches_mapped_reference": bool(
            np.array_equal(model_target, target)
        ),
        "source_center_background": int(labels[tuple(source)]) == 0,
        "target_is_soft_tissue": int(labels[tuple(target)]) == 1,
        "ray_crosses_skull": bool(skull_positions.size),
        "source_physical_error_within_one_voxel": (
            source_error_mm <= tolerance_mm
        ),
        "target_physical_error_within_one_voxel": (
            target_error_mm <= tolerance_mm
        ),
        "source_target_distance_within_two_voxels": (
            distance_delta_mm <= 2.0 * tolerance_mm
        ),
        "beam_angle_within_one_degree": angular_delta_deg <= 1.0,
    }
    plan = {
        "description": (
            "Resolution-mapped Case079 entry plan derived from a frozen "
            "reference source-target ray"
        ),
        "entry_direction": reference_plan.get(
            "entry_direction", "mapped_reference_ray"
        ),
        "entry_offset_mm": reference_plan.get("entry_offset_mm"),
        "target_index_ijk": target.tolist(),
        "source_center_index_ijk": source.tolist(),
        "entry_index_ijk": entry.astype(int).tolist(),
        "skull_exit_index_ijk": skull_exit.astype(int).tolist(),
        "beam_axis": beam_axis.astype(int).tolist(),
        "beam_unit_vector": (
            beam_axis.astype(float) / np.linalg.norm(beam_axis)
        ).tolist(),
        "source_center_label": int(labels[tuple(source)]),
        "entry_label": int(labels[tuple(entry)]),
        "target_label": int(labels[tuple(target)]),
        "has_skull_crossing": True,
        "source_to_entry_distance_mm": source_to_entry_mm,
        "source_to_target_distance_mm": source_to_target_mm,
        "skull_path_length_mm": skull_path_mm,
        "dx_m": candidate_dx_m,
        "model_shape": list(shape),
        "pressure_execution_authorized": False,
    }
    diagnostics = {
        "checks": checks,
        "passed": all(checks.values()),
        "source_physical_error_mm": source_error_mm,
        "target_physical_error_mm": target_error_mm,
        "source_target_distance_delta_mm": distance_delta_mm,
        "beam_angle_delta_deg": angular_delta_deg,
        "ray_voxels": int(ray.shape[0]),
        "skull_ray_voxels": int(skull_positions.size),
        "pressure_execution_authorized": False,
    }
    return plan, diagnostics


def parse_candidate(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            "candidate must be formatted as id=path"
        )
    identifier, raw_path = value.split("=", 1)
    if not identifier.strip() or not raw_path.strip():
        raise argparse.ArgumentTypeError(
            "candidate must contain a non-empty id and path"
        )
    return identifier.strip(), Path(raw_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Map one frozen entry plan to one or more acoustic-model "
            "resolutions without authorizing pressure execution."
        )
    )
    parser.add_argument("--reference-plan", type=Path, required=True)
    parser.add_argument(
        "--candidate",
        type=parse_candidate,
        action="append",
        required=True,
        help="Repeatable id=path acoustic-model candidate.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    reference_plan_path = args.reference_plan.resolve()
    reference_plan = json.loads(
        reference_plan_path.read_text(encoding="utf-8")
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    candidates: list[dict[str, Any]] = []
    for identifier, model_path in args.candidate:
        model_path = model_path.resolve()
        labels, dx_m, model_target = load_model(model_path)
        plan, diagnostics = transform_plan(
            reference_plan, labels, dx_m, model_target
        )
        candidate_dir = args.output_dir / identifier
        candidate_dir.mkdir(parents=True, exist_ok=True)
        plan_path = candidate_dir / "entry_plan.json"
        plan_path.write_text(
            json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        candidates.append(
            {
                "candidate_id": identifier,
                "model_path": str(model_path),
                "model_sha256": sha256_file(model_path),
                "entry_plan_path": str(plan_path.resolve()),
                "entry_plan_sha256": sha256_file(plan_path),
                "dx_m": dx_m,
                "model_shape": list(labels.shape),
                "diagnostics": diagnostics,
            }
        )
    report = {
        "schema_version": "1.0",
        "status": (
            "passed"
            if all(item["diagnostics"]["passed"] for item in candidates)
            else "failed"
        ),
        "claim_level": "coordinate_resolution_mapping_only_no_pressure",
        "reference_plan": {
            "path": str(reference_plan_path),
            "sha256": sha256_file(reference_plan_path),
        },
        "candidates": candidates,
        "pressure_execution_authorized": False,
        "claim_boundary": (
            "Passing establishes bounded voxel/world-coordinate and skull-ray "
            "parity only. Dry-run quality remains mandatory before pressure."
        ),
    }
    report_path = args.output_dir / "entry_plan_resolution_family.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": str(report_path.resolve()),
                "candidates": len(candidates),
                "pressure_execution_authorized": False,
            }
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
