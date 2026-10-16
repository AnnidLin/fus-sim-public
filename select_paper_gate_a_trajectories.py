from __future__ import annotations

import argparse
import csv
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

from simulate_source_array_focus import (
    SourceArrayConfig,
    build_source_array_mask,
    load_model,
)


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = PROJECT_ROOT / "outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/acoustic_model_3d.npz"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs/paper_gate_a_trajectory_selection_079"


def candidate_source_index(
    target: np.ndarray,
    offset_yz_mm: tuple[float, float],
    radius_mm: float,
    dx_m: float,
) -> np.ndarray | None:
    dy_gp, dz_gp = np.rint(np.asarray(offset_yz_mm) / (dx_m * 1e3)).astype(int)
    lateral_gp_sq = int(dy_gp**2 + dz_gp**2)
    radius_gp = radius_mm / (dx_m * 1e3)
    if lateral_gp_sq >= radius_gp**2:
        return None
    dx_gp = int(round(np.sqrt(radius_gp**2 - lateral_gp_sq)))
    return target + np.array([-dx_gp, dy_gp, dz_gp], dtype=int)


def sampled_ray_indices(source: np.ndarray, target: np.ndarray, shape: tuple[int, ...]) -> np.ndarray:
    length_gp = float(np.linalg.norm(target - source))
    points = np.linspace(source, target, max(2, int(np.ceil(length_gp * 2.0)) + 1))
    indices = np.rint(points).astype(int)
    indices = np.unique(indices, axis=0)
    valid = np.all(indices >= 0, axis=1) & np.all(indices < np.asarray(shape), axis=1)
    return indices[valid]


def contiguous_segments(mask: np.ndarray) -> int:
    if not np.any(mask):
        return 0
    starts = mask & np.concatenate(([True], ~mask[:-1]))
    return int(np.count_nonzero(starts))


def incidence_angle_deg(beam_unit: np.ndarray, normal_field: tuple[np.ndarray, ...], entry: np.ndarray) -> float | None:
    normal = np.array([field[tuple(entry)] for field in normal_field], dtype=float)
    norm = float(np.linalg.norm(normal))
    if norm < 1e-8:
        return None
    normal /= norm
    cosine = float(np.clip(abs(np.dot(beam_unit, normal)), 0.0, 1.0))
    return float(np.degrees(np.arccos(cosine)))


def trace_metrics(
    source: np.ndarray,
    target: np.ndarray,
    labels: np.ndarray,
    hu: np.ndarray,
    alpha: np.ndarray,
    dx_m: float,
    normal_field: tuple[np.ndarray, ...],
) -> dict[str, object]:
    ray = sampled_ray_indices(source, target, labels.shape)
    ray_labels = labels[tuple(ray.T)]
    skull_mask = ray_labels == 2
    result: dict[str, object] = {
        "ray_samples": int(len(ray)),
        "skull_samples": int(np.count_nonzero(skull_mask)),
        "skull_segments": contiguous_segments(skull_mask),
        "post_skull_background_gap": False,
    }
    if not np.any(skull_mask):
        return result

    skull_positions = np.flatnonzero(skull_mask)
    first, last = int(skull_positions[0]), int(skull_positions[-1])
    entry = ray[first]
    skull_ray = ray[skull_mask]
    beam = target.astype(float) - source.astype(float)
    beam_unit = beam / np.linalg.norm(beam)
    post_labels = ray_labels[last + 1 : -1]
    result.update(
        {
            "entry_index_ijk": entry.tolist(),
            "skull_exit_index_ijk": ray[last].tolist(),
            "skull_crossing_mm": float(np.count_nonzero(skull_mask) * dx_m * 1e3),
            "source_to_entry_mm": float(np.linalg.norm(entry - source) * dx_m * 1e3),
            "max_hu": float(np.max(hu[tuple(skull_ray.T)])),
            "mean_alpha_db_mhz_cm": float(np.mean(alpha[tuple(skull_ray.T)])),
            "incidence_angle_deg": incidence_angle_deg(beam_unit, normal_field, entry),
            "post_skull_background_gap": bool(np.any(post_labels == 0)),
        }
    )
    return result


def normalized(values: np.ndarray) -> np.ndarray:
    span = float(np.max(values) - np.min(values))
    return np.zeros_like(values, dtype=float) if span <= 0 else (values - np.min(values)) / span


def angular_separation_deg(a: np.ndarray, b: np.ndarray) -> float:
    cosine = float(np.clip(np.dot(a, b), -1.0, 1.0))
    return float(np.degrees(np.arccos(cosine)))


def choose_three(candidates: list[dict[str, object]], min_separation_deg: float) -> list[dict[str, object]]:
    if len(candidates) < 3:
        return []
    scores = np.array([float(item["difficulty_score"]) for item in candidates])
    targets = [float(np.min(scores)), float(np.median(scores)), float(np.max(scores))]
    selected: list[dict[str, object]] = []
    for target_score in targets:
        ranked = sorted(candidates, key=lambda item: abs(float(item["difficulty_score"]) - target_score))
        choice = next(
            (
                item
                for item in ranked
                if item not in selected
                and all(
                    angular_separation_deg(np.asarray(item["beam_unit"]), np.asarray(other["beam_unit"]))
                    >= min_separation_deg
                    for other in selected
                )
            ),
            None,
        )
        if choice is None:
            return []
        selected.append(choice)
    return selected


def write_outputs(output_dir: Path, summary: dict[str, object]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "gate_a_trajectory_selection.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    fields = [
        "candidate_id", "offset_y_mm", "offset_z_mm", "source_to_target_mm", "source_to_entry_mm",
        "skull_crossing_mm", "skull_segments", "max_hu", "mean_alpha_db_mhz_cm",
        "incidence_angle_deg", "post_skull_background_gap", "source_label_counts",
        "active_patches", "difficulty_score", "hard_gate_pass", "failure_reasons",
    ]
    with (output_dir / "candidate_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in summary["candidates"]:
            writer.writerow({field: item.get(field) for field in fields})

    selected_ids = {item["candidate_id"] for item in summary["selected"]}
    lines = [
        "# Paper Gate A Fixed-Radius Trajectory Selection",
        "",
        f"- Status: `{summary['status']}`",
        f"- Fixed radius: `{summary['fixed']['radius_mm']} mm`",
        f"- Passing candidates: `{summary['passing_candidate_count']}`",
        "- Pressure execution: not authorized",
        "",
        "| Selected | Candidate | Offset y,z (mm) | Skull (mm) | Incidence (deg) | Max HU | Mean alpha | Standoff (mm) | Score |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in summary["candidates"]:
        if item["candidate_id"] not in selected_ids and not item["hard_gate_pass"]:
            continue
        lines.append(
            f"| {'yes' if item['candidate_id'] in selected_ids else ''} | `{item['candidate_id']}` | "
            f"({item['offset_y_mm']:.1f}, {item['offset_z_mm']:.1f}) | {item.get('skull_crossing_mm', 0):.2f} | "
            f"{item.get('incidence_angle_deg', float('nan')):.2f} | {item.get('max_hu', 0):.1f} | "
            f"{item.get('mean_alpha_db_mhz_cm', 0):.3f} | {item.get('source_to_entry_mm', 0):.2f} | "
            f"{item.get('difficulty_score', 0):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "The label model does not identify eyes or sinuses separately. Post-skull background gaps are rejected, but selected slices still require manual anatomical review before Gate A closure.",
        ]
    )
    (output_dir / "gate_a_trajectory_selection.md").write_text("\n".join(lines), encoding="utf-8")

    for rank, item in enumerate(summary["selected"], start=1):
        plan = item["entry_plan"]
        plan["paper_gate_a_rank"] = rank
        plan["paper_gate_a_difficulty"] = ["low", "medium", "high"][rank - 1]
        candidate_dir = output_dir / item["candidate_id"]
        candidate_dir.mkdir(exist_ok=True)
        (candidate_dir / "entry_plan.json").write_text(
            json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Select fixed-radius Case 079 paper trajectories without pressure simulation.")
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

    config = SourceArrayConfig(
        model_path=args.model,
        transducer_radius_m=args.radius_mm * 1e-3,
        aperture_diameter_m=args.aperture_mm * 1e-3,
        array_elements_y=15,
        array_elements_z=15,
    )
    model = load_model(config)
    if model.labels is None:
        raise ValueError("Gate A requires material labels.")
    data = np.load(args.model)
    hu = np.asarray(data["hu"], dtype=np.float32)
    alpha = np.asarray(data["alpha_coeff"], dtype=np.float32)
    skull = model.labels == 2
    signed_distance = distance_transform_edt(~skull) - distance_transform_edt(skull)
    normal_field = tuple(np.gradient(gaussian_filter(signed_distance.astype(np.float32), sigma=1.0)))

    offsets = np.arange(-args.offset_limit_mm, args.offset_limit_mm + args.offset_step_mm * 0.5, args.offset_step_mm)
    candidates: list[dict[str, object]] = []
    for offset_y in offsets:
        for offset_z in offsets:
            source = candidate_source_index(model.target_index_ijk, (float(offset_y), float(offset_z)), args.radius_mm, model.dx_m)
            if source is None or np.any(source < 0) or np.any(source >= np.asarray(model.labels.shape)):
                continue
            metrics = trace_metrics(source, model.target_index_ijk, model.labels, hu, alpha, model.dx_m, normal_field)
            source_to_target_mm = float(np.linalg.norm(model.target_index_ijk - source) * model.dx_m * 1e3)
            failure_reasons: list[str] = []
            if int(model.labels[tuple(source)]) != 0:
                failure_reasons.append("source_center_not_background")
            if metrics["skull_samples"] == 0:
                failure_reasons.append("no_skull_crossing")
            if bool(metrics.get("post_skull_background_gap", False)):
                failure_reasons.append("post_skull_background_gap")
            if float(metrics.get("source_to_entry_mm", 0.0)) < args.min_standoff_mm:
                failure_reasons.append("standoff_below_minimum")
            incidence = metrics.get("incidence_angle_deg")
            if incidence is None or float(incidence) > args.max_incidence_deg:
                failure_reasons.append("incidence_angle_failed")
            if abs(source_to_target_mm - args.radius_mm) > model.dx_m * 1e3 * 0.5:
                failure_reasons.append("fixed_radius_tolerance_failed")

            source_labels: dict[str, int] = {}
            active_patches = 0
            if not failure_reasons:
                candidate_model = replace(
                    model,
                    source_center_index_ijk=source.astype(np.int32),
                    beam_axis=(model.target_index_ijk - source).astype(np.int32),
                )
                _, _, metadata, _ = build_source_array_mask(candidate_model, config)
                source_labels = metadata.get("source_label_counts", {})
                active_patches = sum(int(size) > 0 for size in metadata["patch_sizes"])
                if source_labels != {"0": int(metadata["source_points"])}:
                    failure_reasons.append("bowl_mask_not_background_only")

            beam = model.target_index_ijk.astype(float) - source.astype(float)
            beam /= np.linalg.norm(beam)
            candidate_id = f"offset_y{offset_y:+05.1f}_z{offset_z:+05.1f}".replace(".", "p")
            entry = metrics.get("entry_index_ijk")
            entry_plan = {
                "description": "Paper Gate A fixed-radius Case 079 entry plan",
                "entry_direction": "fixed_radius_left_hemisphere",
                "entry_offset_mm": [float(offset_y), float(offset_z)],
                "target_index_ijk": model.target_index_ijk.astype(int).tolist(),
                "source_center_index_ijk": source.astype(int).tolist(),
                "entry_index_ijk": entry,
                "skull_exit_index_ijk": metrics.get("skull_exit_index_ijk"),
                "beam_axis": (model.target_index_ijk - source).astype(int).tolist(),
                "source_center_label": int(model.labels[tuple(source)]),
                "target_label": int(model.labels[tuple(model.target_index_ijk)]),
                "has_skull_crossing": bool(metrics["skull_samples"]),
                "source_standoff_mm": metrics.get("source_to_entry_mm"),
                "source_to_entry_distance_mm": metrics.get("source_to_entry_mm"),
                "source_to_target_distance_mm": source_to_target_mm,
                "skull_path_length_mm": metrics.get("skull_crossing_mm"),
                "incidence_angle_deg": incidence,
                "dx_m": model.dx_m,
                "model_shape": list(model.source_model_shape),
            }
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "offset_y_mm": float(offset_y),
                    "offset_z_mm": float(offset_z),
                    "source_index_ijk": source.tolist(),
                    "beam_unit": beam.tolist(),
                    "source_to_target_mm": source_to_target_mm,
                    "source_label_counts": source_labels,
                    "active_patches": active_patches,
                    "failure_reasons": failure_reasons,
                    "hard_gate_pass": not failure_reasons,
                    "entry_plan": entry_plan,
                    **metrics,
                }
            )

    passing = [item for item in candidates if item["hard_gate_pass"]]
    if passing:
        crossing = normalized(np.array([item["skull_crossing_mm"] for item in passing], dtype=float))
        attenuation = normalized(np.array([item["mean_alpha_db_mhz_cm"] for item in passing], dtype=float))
        hu_values = normalized(np.array([item["max_hu"] for item in passing], dtype=float))
        incidence = normalized(np.array([item["incidence_angle_deg"] for item in passing], dtype=float))
        scores = 0.4 * crossing + 0.25 * attenuation + 0.2 * hu_values + 0.15 * incidence
        for item, score in zip(passing, scores):
            item["difficulty_score"] = float(score)
    for item in candidates:
        item.setdefault("difficulty_score", None)

    selected = choose_three(passing, args.min_separation_deg)
    selected.sort(key=lambda item: float(item["difficulty_score"]))
    status = "gate_a_candidates_selected_manual_review_pending" if len(selected) == 3 else "gate_a_blocked"
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "case_id": "079",
        "fixed": {
            "model": str(args.model),
            "radius_mm": args.radius_mm,
            "aperture_mm": args.aperture_mm,
            "frequency_khz": 500.0,
            "dx_mm": model.dx_m * 1e3,
            "target_index_ijk": model.target_index_ijk.astype(int).tolist(),
        },
        "candidate_count": len(candidates),
        "passing_candidate_count": len(passing),
        "selected": selected,
        "candidates": candidates,
        "pressure_execution_authorized": False,
        "manual_review_required": ["eye_orbit_avoidance", "sinus_and_air_cavity_review", "selected_slice_review"],
    }
    write_outputs(args.output_dir, summary)
    print(json.dumps({"status": status, "passing": len(passing), "selected": [item["candidate_id"] for item in selected]}))


if __name__ == "__main__":
    main()
