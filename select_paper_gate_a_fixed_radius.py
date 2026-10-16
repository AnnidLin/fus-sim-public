from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from kwave.data import Vector
from kwave.utils.mapgen import make_bowl
from scipy.ndimage import distance_transform_edt, gaussian_filter

from select_paper_gate_a_trajectories import (
    candidate_source_index,
    choose_three,
    normalized,
    trace_metrics,
    write_outputs,
)
from simulate_source_array_focus import odd_grid_points


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = PROJECT_ROOT / "outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/acoustic_model_3d.npz"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs/paper_gate_a_trajectory_selection_079"


def bowl_source_labels(
    labels: np.ndarray,
    source: np.ndarray,
    target: np.ndarray,
    radius_mm: float,
    aperture_mm: float,
    dx_m: float,
) -> tuple[dict[str, int], int]:
    source_mask = make_bowl(
        Vector(list(labels.shape)),
        Vector((source + 1).tolist()),
        int(round(radius_mm * 1e-3 / dx_m)),
        odd_grid_points(aperture_mm * 1e-3, dx_m),
        Vector((target + 1).tolist()),
        binary=True,
        remove_overlap=True,
    ).astype(bool)
    values, counts = np.unique(labels[source_mask], return_counts=True)
    return {str(int(value)): int(count) for value, count in zip(values, counts)}, int(source_mask.sum())


def main() -> None:
    parser = argparse.ArgumentParser(description="Select fixed-radius Case 079 paper trajectories without pressure.")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--radius-mm", type=float, default=74.4353753)
    parser.add_argument("--aperture-mm", type=float, default=30.0)
    parser.add_argument("--offset-limit-mm", type=float, default=22.5)
    parser.add_argument("--offset-step-mm", type=float, default=2.5)
    parser.add_argument("--min-standoff-mm", type=float, default=10.0)
    parser.add_argument("--max-incidence-deg", type=float, default=30.0)
    parser.add_argument("--min-separation-deg", type=float, default=6.0)
    args = parser.parse_args()

    data = np.load(args.model)
    labels = np.asarray(data["labels"], dtype=np.uint8)
    hu = np.asarray(data["hu"], dtype=np.float32)
    alpha = np.asarray(data["alpha_coeff"], dtype=np.float32)
    dx_m = float(np.asarray(data["dx_m"]).item())
    target = np.asarray(data["target_index_ijk"], dtype=np.int32)
    signed_distance = distance_transform_edt(labels != 2) - distance_transform_edt(labels == 2)
    normal_field = tuple(np.gradient(gaussian_filter(signed_distance.astype(np.float32), sigma=1.0)))

    offsets = np.arange(-args.offset_limit_mm, args.offset_limit_mm + 0.5 * args.offset_step_mm, args.offset_step_mm)
    candidates: list[dict[str, object]] = []
    for offset_y in offsets:
        for offset_z in offsets:
            source = candidate_source_index(target, (float(offset_y), float(offset_z)), args.radius_mm, dx_m)
            if source is None or np.any(source < 0) or np.any(source >= np.asarray(labels.shape)):
                continue
            metrics = trace_metrics(source, target, labels, hu, alpha, dx_m, normal_field)
            distance_mm = float(np.linalg.norm(target - source) * dx_m * 1e3)
            failures: list[str] = []
            if int(labels[tuple(source)]) != 0:
                failures.append("source_center_not_background")
            if int(metrics["skull_samples"]) == 0:
                failures.append("no_skull_crossing")
            if bool(metrics.get("post_skull_background_gap", False)):
                failures.append("post_skull_background_gap")
            if float(metrics.get("source_to_entry_mm", 0.0)) < args.min_standoff_mm:
                failures.append("standoff_below_minimum")
            incidence = metrics.get("incidence_angle_deg")
            if incidence is None or float(incidence) > args.max_incidence_deg:
                failures.append("incidence_angle_failed")
            if abs(distance_mm - args.radius_mm) > dx_m * 1e3 * 0.5:
                failures.append("fixed_radius_tolerance_failed")

            beam = target.astype(float) - source.astype(float)
            beam /= np.linalg.norm(beam)
            candidate_id = f"offset_y{offset_y:+05.1f}_z{offset_z:+05.1f}".replace(".", "p")
            plan = {
                "description": "Paper Gate A fixed-radius Case 079 entry plan",
                "entry_direction": "fixed_radius_left_hemisphere",
                "entry_offset_mm": [float(offset_y), float(offset_z)],
                "target_index_ijk": target.tolist(),
                "source_center_index_ijk": source.tolist(),
                "entry_index_ijk": metrics.get("entry_index_ijk"),
                "skull_exit_index_ijk": metrics.get("skull_exit_index_ijk"),
                "beam_axis": (target - source).tolist(),
                "source_center_label": int(labels[tuple(source)]),
                "target_label": int(labels[tuple(target)]),
                "has_skull_crossing": bool(metrics["skull_samples"]),
                "source_standoff_mm": metrics.get("source_to_entry_mm"),
                "source_to_entry_distance_mm": metrics.get("source_to_entry_mm"),
                "source_to_target_distance_mm": distance_mm,
                "skull_path_length_mm": metrics.get("skull_crossing_mm"),
                "incidence_angle_deg": incidence,
                "dx_m": dx_m,
                "model_shape": list(labels.shape),
            }
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "offset_y_mm": float(offset_y),
                    "offset_z_mm": float(offset_z),
                    "source_index_ijk": source.tolist(),
                    "beam_unit": beam.tolist(),
                    "source_to_target_mm": distance_mm,
                    "source_label_counts": {},
                    "active_patches": None,
                    "failure_reasons": failures,
                    "geometry_gate_pass": not failures,
                    "hard_gate_pass": False,
                    "entry_plan": plan,
                    **metrics,
                }
            )

    geometry_passing = [item for item in candidates if item["geometry_gate_pass"]]
    if geometry_passing:
        crossing = normalized(np.array([item["skull_crossing_mm"] for item in geometry_passing]))
        attenuation = normalized(np.array([item["mean_alpha_db_mhz_cm"] for item in geometry_passing]))
        max_hu = normalized(np.array([item["max_hu"] for item in geometry_passing]))
        incidence = normalized(np.array([item["incidence_angle_deg"] for item in geometry_passing]))
        for item, score in zip(geometry_passing, 0.4 * crossing + 0.25 * attenuation + 0.2 * max_hu + 0.15 * incidence):
            item["difficulty_score"] = float(score)
    for item in candidates:
        item.setdefault("difficulty_score", None)

    selected = choose_three(geometry_passing, args.min_separation_deg)
    selected.sort(key=lambda item: float(item["difficulty_score"]))
    for item in selected:
        label_counts, source_points = bowl_source_labels(
            labels, np.asarray(item["source_index_ijk"]), target, args.radius_mm, args.aperture_mm, dx_m
        )
        item["source_label_counts"] = label_counts
        item["source_points"] = source_points
        item["hard_gate_pass"] = label_counts == {"0": source_points}
        if not item["hard_gate_pass"]:
            item["failure_reasons"].append("bowl_mask_not_background_only")

    status = (
        "gate_a_candidates_selected_manual_review_pending"
        if len(selected) == 3 and all(item["hard_gate_pass"] for item in selected)
        else "gate_a_blocked"
    )
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "case_id": "079",
        "fixed": {
            "model": str(args.model), "radius_mm": args.radius_mm, "aperture_mm": args.aperture_mm,
            "frequency_khz": 500.0, "dx_mm": dx_m * 1e3, "target_index_ijk": target.tolist(),
        },
        "candidate_count": len(candidates),
        "geometry_passing_candidate_count": len(geometry_passing),
        "passing_candidate_count": sum(bool(item["hard_gate_pass"]) for item in selected),
        "selected": selected,
        "candidates": candidates,
        "pressure_execution_authorized": False,
        "manual_review_required": ["eye_orbit_avoidance", "sinus_and_air_cavity_review", "selected_slice_review"],
    }
    write_outputs(args.output_dir, summary)
    print(json.dumps({"status": status, "geometry_passing": len(geometry_passing), "selected": [x["candidate_id"] for x in selected]}))


if __name__ == "__main__":
    main()
