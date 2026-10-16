from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from kwave.data import Vector
from kwave.utils.mapgen import make_bowl

from generate_entry_plan_resolution_family import (
    angle_deg,
    sampled_ray_indices,
)
from simulate_kwave_3d_focus import odd_grid_points


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def candidate_offsets(radius: int = 1) -> list[tuple[int, int, int]]:
    offsets = list(
        itertools.product(
            range(-radius, radius + 1),
            range(-radius, radius + 1),
            range(-radius, radius + 1),
        )
    )
    return sorted(
        offsets,
        key=lambda item: (
            sum(value * value for value in item),
            item,
        ),
    )


def source_label_counts(
    labels: np.ndarray,
    source: np.ndarray,
    target: np.ndarray,
    dx_m: float,
    radius_mm: float,
    aperture_mm: float,
) -> tuple[dict[str, int], int]:
    radius_gp = int(round(radius_mm * 1e-3 / dx_m))
    diameter_gp = odd_grid_points(aperture_mm * 1e-3, dx_m)
    mask = make_bowl(
        Vector(list(labels.shape)),
        Vector((source + 1).astype(int).tolist()),
        radius_gp,
        diameter_gp,
        Vector((target + 1).astype(int).tolist()),
        binary=True,
        remove_overlap=True,
    ).astype(bool)
    if not np.any(mask):
        raise ValueError("Generated bowl source mask is empty.")
    unique, counts = np.unique(labels[mask], return_counts=True)
    return (
        {
            str(int(label)): int(count)
            for label, count in zip(unique, counts)
        },
        int(np.sum(mask)),
    )


def plan_for_source(
    base_plan: dict[str, Any],
    labels: np.ndarray,
    dx_m: float,
    source: np.ndarray,
) -> dict[str, Any]:
    target = np.asarray(base_plan["target_index_ijk"], dtype=np.int32)
    ray = sampled_ray_indices(source, target)
    ray_labels = labels[tuple(ray.T)]
    skull_positions = np.flatnonzero(ray_labels == 2)
    if not skull_positions.size:
        raise ValueError("Candidate source-target ray does not cross skull.")
    entry = ray[int(skull_positions[0])]
    skull_exit = ray[int(skull_positions[-1])]
    beam_axis = target - source
    plan = dict(base_plan)
    plan.update(
        {
            "source_center_index_ijk": source.astype(int).tolist(),
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
            "source_to_entry_distance_mm": float(
                np.linalg.norm(entry - source) * dx_m * 1e3
            ),
            "source_to_target_distance_mm": float(
                np.linalg.norm(beam_axis) * dx_m * 1e3
            ),
            "skull_path_length_mm": float(
                np.linalg.norm(skull_exit - entry) * dx_m * 1e3
                + dx_m * 1e3
            ),
            "pressure_execution_authorized": False,
        }
    )
    return plan


def rank_passing_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        (item for item in candidates if item["passed"]),
        key=lambda item: (
            item["source_physical_error_mm"],
            item["beam_angle_delta_deg"],
            tuple(item["offset_ijk"]),
        ),
    )


def refine_source_center(
    model_path: Path,
    initial_plan_path: Path,
    reference_plan_path: Path,
    *,
    radius_mm: float = 74.435,
    aperture_mm: float = 60.0,
    search_radius: int = 1,
) -> dict[str, Any]:
    with np.load(model_path, allow_pickle=False) as archive:
        labels = np.asarray(archive["labels"], dtype=np.uint8)
        dx_m = float(np.asarray(archive["dx_m"]).item())
    initial_plan = json.loads(initial_plan_path.read_text(encoding="utf-8"))
    reference_plan = json.loads(
        reference_plan_path.read_text(encoding="utf-8")
    )
    initial_source = np.asarray(
        initial_plan["source_center_index_ijk"], dtype=np.int32
    )
    target = np.asarray(initial_plan["target_index_ijk"], dtype=np.int32)
    reference_source = np.asarray(
        reference_plan["source_center_index_ijk"], dtype=np.int32
    )
    reference_target = np.asarray(
        reference_plan["target_index_ijk"], dtype=np.int32
    )
    reference_dx_m = float(reference_plan["dx_m"])
    reference_source_mm = reference_source * reference_dx_m * 1e3
    reference_distance_mm = float(
        reference_plan["source_to_target_distance_mm"]
    )
    reference_beam = reference_target - reference_source
    candidates: list[dict[str, Any]] = []
    for offset in candidate_offsets(search_radius):
        source = initial_source + np.asarray(offset, dtype=np.int32)
        in_bounds = bool(
            np.all(source >= 0) and np.all(source < np.asarray(labels.shape))
        )
        if not in_bounds:
            candidates.append(
                {
                    "offset_ijk": list(offset),
                    "source_center_index_ijk": source.tolist(),
                    "passed": False,
                    "failure": "source_out_of_bounds",
                }
            )
            continue
        try:
            plan = plan_for_source(initial_plan, labels, dx_m, source)
            counts, points = source_label_counts(
                labels,
                source,
                target,
                dx_m,
                radius_mm,
                aperture_mm,
            )
        except ValueError as exc:
            candidates.append(
                {
                    "offset_ijk": list(offset),
                    "source_center_index_ijk": source.tolist(),
                    "passed": False,
                    "failure": str(exc),
                }
            )
            continue
        physical_error_mm = float(
            np.linalg.norm(source * dx_m * 1e3 - reference_source_mm)
        )
        beam_axis = target - source
        angular_delta = angle_deg(reference_beam, beam_axis)
        distance_delta = abs(
            float(plan["source_to_target_distance_mm"])
            - reference_distance_mm
        )
        checks = {
            "source_center_background": int(labels[tuple(source)]) == 0,
            "bowl_background_only": set(counts) == {"0"},
            "ray_crosses_skull": bool(plan["has_skull_crossing"]),
            "source_error_within_1p5_voxels": (
                physical_error_mm <= 1.5 * dx_m * 1e3
            ),
            "beam_angle_within_one_degree": angular_delta <= 1.0,
            "distance_within_two_voxels": (
                distance_delta <= 2.0 * dx_m * 1e3
            ),
        }
        candidates.append(
            {
                "offset_ijk": list(offset),
                "source_center_index_ijk": source.tolist(),
                "source_points": points,
                "source_label_counts": counts,
                "source_physical_error_mm": physical_error_mm,
                "beam_angle_delta_deg": angular_delta,
                "source_target_distance_delta_mm": distance_delta,
                "checks": checks,
                "passed": all(checks.values()),
                "plan": plan,
            }
        )
    passing = rank_passing_candidates(candidates)
    selected = passing[0] if passing else None
    return {
        "schema_version": "1.0",
        "status": "passed" if selected is not None else "failed",
        "claim_level": "source_center_coordinate_refinement_only_no_pressure",
        "model": {
            "path": str(model_path.resolve()),
            "sha256": sha256_file(model_path),
            "dx_m": dx_m,
            "shape": list(labels.shape),
        },
        "initial_plan": {
            "path": str(initial_plan_path.resolve()),
            "sha256": sha256_file(initial_plan_path),
        },
        "reference_plan": {
            "path": str(reference_plan_path.resolve()),
            "sha256": sha256_file(reference_plan_path),
        },
        "fixed_geometry": {
            "target_index_ijk": target.tolist(),
            "radius_mm": radius_mm,
            "aperture_mm": aperture_mm,
        },
        "search_radius_voxels": search_radius,
        "candidates": candidates,
        "passing_candidate_count": len(passing),
        "selected_offset_ijk": (
            selected["offset_ijk"] if selected is not None else None
        ),
        "selected_plan": (
            selected["plan"] if selected is not None else None
        ),
        "pressure_execution_authorized": False,
        "claim_boundary": (
            "Selection is based only on fixed geometry, material labels and "
            "coordinate error. Dry-run quality remains mandatory."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Select the nearest background-only discretized bowl center "
            "without pressure execution."
        )
    )
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--initial-plan", type=Path, required=True)
    parser.add_argument("--reference-plan", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--radius-mm", type=float, default=74.435)
    parser.add_argument("--aperture-mm", type=float, default=60.0)
    parser.add_argument("--search-radius", type=int, default=1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = refine_source_center(
        args.model,
        args.initial_plan,
        args.reference_plan,
        radius_mm=args.radius_mm,
        aperture_mm=args.aperture_mm,
        search_radius=args.search_radius,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / "source_center_refinement.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if report["selected_plan"] is not None:
        (args.output_dir / "entry_plan.json").write_text(
            json.dumps(
                report["selected_plan"], indent=2, ensure_ascii=False
            )
            + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "status": report["status"],
                "passing_candidates": report["passing_candidate_count"],
                "selected_offset_ijk": report["selected_offset_ijk"],
                "pressure_execution_authorized": False,
            }
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
