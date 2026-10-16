"""Scan source-safe left-x entry candidates for Visible Human public CT cases.

This script only performs geometry and source-mask safety checks. It does not
run k-Wave. The output is intended to select one safe candidate for a later
direct quick-smoke simulation.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from plan_ct_target_entry import plan_left_x_entry
from simulate_kwave_3d_focus import KWave3DConfig, build_source_mask, load_model


DEFAULT_CASES = [
    "visible_human_female_head_1mm",
    "visible_human_male_head_1mm",
]
DEFAULT_STANDOFFS_MM = [16.0, 20.0, 24.0, 28.0, 32.0]
DEFAULT_OFFSETS_MM = [-10.0, 0.0, 10.0]


def parse_float_list(value: str) -> list[float]:
    values = [float(part.strip()) for part in value.split(",") if part.strip()]
    if not values:
        raise argparse.ArgumentTypeError("list cannot be empty")
    return values


def load_labels_dx_target(model_path: Path) -> tuple[np.ndarray, float, np.ndarray]:
    data = np.load(model_path)
    required = {"labels", "dx_m", "target_index_ijk"}
    missing = required - set(data.files)
    if missing:
        raise ValueError(f"Model is missing required fields: {sorted(missing)}")
    labels = np.asarray(data["labels"], dtype=np.uint8)
    dx_m = float(np.asarray(data["dx_m"]).item())
    target = np.asarray(data["target_index_ijk"], dtype=np.int32)
    return labels, dx_m, target


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def count_label(counts: dict[str, Any], label: int) -> int:
    return int(counts.get(str(label), 0))


def estimate_crop(plan: dict[str, Any], model_shape: tuple[int, int, int], dx_m: float) -> dict[str, Any]:
    target = np.asarray(plan["target_index_ijk"], dtype=int)
    source = np.asarray(plan["source_center_index_ijk"], dtype=int)
    lateral_half = max(8, int(round(17e-3 / dx_m)))
    post_target = max(4, int(round(8e-3 / dx_m)))
    pml_size = 8
    anchor_min = np.minimum(target, source)
    anchor_max = np.maximum(target, source)
    x0 = max(0, int(anchor_min[0]) - pml_size - 4)
    x1 = min(model_shape[0], int(anchor_max[0]) + post_target)
    y0 = max(0, int(anchor_min[1]) - lateral_half)
    y1 = min(model_shape[1], int(anchor_max[1]) + lateral_half + 1)
    z0 = max(0, int(anchor_min[2]) - lateral_half)
    z1 = min(model_shape[2], int(anchor_max[2]) + lateral_half + 1)
    shape = [int(x1 - x0), int(y1 - y0), int(z1 - z0)]
    return {
        "quick_crop_origin_ijk": [int(x0), int(y0), int(z0)],
        "quick_crop_shape": shape,
        "quick_voxel_count": int(np.prod(shape)),
    }


def evaluate_candidate(
    case_id: str,
    model_path: Path,
    case_dir: Path,
    labels: np.ndarray,
    dx_m: float,
    target: np.ndarray,
    standoff_mm: float,
    y_offset_mm: float,
    z_offset_mm: float,
    candidate_index: int,
) -> dict[str, Any]:
    candidate_id = f"candidate_{candidate_index:03d}"
    candidate_dir = case_dir / candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    plan = plan_left_x_entry(labels, dx_m, target, standoff_mm, (y_offset_mm, z_offset_mm))
    entry_plan_path = candidate_dir / "entry_plan.json"
    entry_plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")

    config = KWave3DConfig(
        model_path=model_path,
        entry_plan_path=entry_plan_path,
        quick_mode=True,
        quick_lateral_half_width_m=17e-3,
        quick_post_target_margin_m=8e-3,
        aperture_diameter_m=25e-3,
        transducer_radius_m=30e-3,
    )
    loaded = load_model(config)
    _mask, metadata = build_source_mask(loaded, config)
    counts = metadata.get("source_label_counts", {})
    if not isinstance(counts, dict):
        counts = {}
    label0 = count_label(counts, 0)
    label1 = count_label(counts, 1)
    label2 = count_label(counts, 2)
    source_points = int(metadata["source_points"])
    unsafe_points = label1 + label2
    crop = estimate_crop(plan, tuple(int(v) for v in labels.shape), dx_m)

    return {
        "case_id": case_id,
        "candidate_id": candidate_id,
        "status": "valid",
        "entry_plan_path": str(entry_plan_path),
        "model_path": str(model_path),
        "standoff_mm": standoff_mm,
        "entry_offset_y_mm": y_offset_mm,
        "entry_offset_z_mm": z_offset_mm,
        "target_index_ijk": ",".join(str(v) for v in plan["target_index_ijk"]),
        "entry_index_ijk": ",".join(str(v) for v in plan["entry_index_ijk"]),
        "source_center_index_ijk": ",".join(str(v) for v in plan["source_center_index_ijk"]),
        "has_skull_crossing": bool(plan["has_skull_crossing"]),
        "entry_label": int(plan["entry_label"]),
        "source_center_label": int(plan["source_center_label"]),
        "source_points": source_points,
        "source_label_counts": json.dumps(counts, ensure_ascii=False),
        "source_label_0_count": label0,
        "source_label_1_count": label1,
        "source_label_2_count": label2,
        "unsafe_source_points": unsafe_points,
        "source_mask_background_only": unsafe_points == 0,
        "source_to_target_distance_mm": float(plan["source_to_target_distance_mm"]),
        "source_to_entry_distance_mm": float(plan["source_to_entry_distance_mm"]),
        "skull_path_length_mm": float(plan["skull_path_length_mm"]),
        "quick_crop_shape": ",".join(str(v) for v in crop["quick_crop_shape"]),
        "quick_voxel_count": int(crop["quick_voxel_count"]),
        "aperture_mm": 25.0,
        "radius_mm": 30.0,
        "cycles": 6,
        "sim_time_us": 45.0,
    }


def rank_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows.sort(
        key=lambda row: (
            int(row.get("source_label_2_count", 999999)),
            int(row.get("source_label_1_count", 999999)),
            int(row.get("quick_voxel_count", 999999999)),
            float(row.get("source_to_target_distance_mm", 999999.0)),
            float(row.get("standoff_mm", 999999.0)),
            abs(float(row.get("entry_offset_y_mm", 999999.0))),
            abs(float(row.get("entry_offset_z_mm", 999999.0))),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["safety_rank"] = index
        row["recommended"] = index == 1 and bool(row.get("source_mask_background_only"))
    return rows


def write_summary(output_dir: Path, rows: list[dict[str, Any]], cases: list[str]) -> None:
    ranked = rank_rows(list(rows))
    safe = [row for row in ranked if row.get("source_mask_background_only")]
    best = safe[0] if safe else None
    summary = {
        "description": "Visible Human source-safe entry scan. No k-Wave simulation was run.",
        "cases": cases,
        "candidate_count": len(rows),
        "background_only_count": len(safe),
        "recommended": best,
        "warning": None if best else "No background-only source mask candidate found.",
    }
    (output_dir / "scan_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8-sig",
    )
    write_csv(output_dir / "ranked_safe_candidates.csv", ranked)


def write_recommended_command(output_dir: Path, recommended: dict[str, Any] | None) -> None:
    if not recommended:
        (output_dir / "recommended_smoke_command.ps1").write_text(
            "# 没有完全安全的 source mask 候选，本轮不建议运行 k-Wave。\n",
            encoding="utf-8-sig",
        )
        return
    python_exe = r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe"
    case_id = recommended["case_id"]
    output_run = f"outputs\\visible_human_quick_smoke_runs\\{case_id}_best_safe"
    command = (
        f"{python_exe} simulate_kwave_3d_focus.py "
        f"--model {recommended['model_path']} "
        f"--entry-plan {recommended['entry_plan_path']} "
        f"--output-dir {output_run} --sim-time-us 45 --cycles 6 "
        f"--quick-lateral-mm 17 --quick-post-target-mm 8 --aperture-mm 25 --radius-mm 30"
    )
    analyze = f"{python_exe} analyze_kwave_3d_focus.py --input-dir {output_run}"
    (output_dir / "recommended_smoke_command.ps1").write_text(
        "# 只运行排名第一的完全安全候选。\n" + command + "\n" + analyze + "\n",
        encoding="utf-8-sig",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-root", default="outputs/ct_acoustic_models_public")
    parser.add_argument("--output-dir", default="outputs/visible_human_source_safety_scan")
    parser.add_argument("--cases", default=",".join(DEFAULT_CASES))
    parser.add_argument("--standoff-mm", type=parse_float_list, default=DEFAULT_STANDOFFS_MM)
    parser.add_argument("--y-offsets-mm", type=parse_float_list, default=DEFAULT_OFFSETS_MM)
    parser.add_argument("--z-offsets-mm", type=parse_float_list, default=DEFAULT_OFFSETS_MM)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    models_root = Path(args.models_root)
    cases = [case.strip() for case in args.cases.split(",") if case.strip()]
    all_rows: list[dict[str, Any]] = []
    for case_id in cases:
        model_path = models_root / f"{case_id}_bone300_dx1" / "acoustic_model_3d.npz"
        labels, dx_m, target = load_labels_dx_target(model_path)
        case_dir = output_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        rows: list[dict[str, Any]] = []
        candidate_index = 0
        for standoff_mm in args.standoff_mm:
            for y_offset_mm in args.y_offsets_mm:
                for z_offset_mm in args.z_offsets_mm:
                    try:
                        row = evaluate_candidate(
                            case_id=case_id,
                            model_path=model_path,
                            case_dir=case_dir,
                            labels=labels,
                            dx_m=dx_m,
                            target=target,
                            standoff_mm=standoff_mm,
                            y_offset_mm=y_offset_mm,
                            z_offset_mm=z_offset_mm,
                            candidate_index=candidate_index,
                        )
                    except Exception as exc:
                        row = {
                            "case_id": case_id,
                            "candidate_id": f"candidate_{candidate_index:03d}",
                            "status": "failed",
                            "error": str(exc),
                            "standoff_mm": standoff_mm,
                            "entry_offset_y_mm": y_offset_mm,
                            "entry_offset_z_mm": z_offset_mm,
                        }
                    rows.append(row)
                    all_rows.append(row)
                    candidate_index += 1
        ranked = rank_rows(rows)
        write_csv(case_dir / "ranked_safe_candidates.csv", ranked)
        safe = [row for row in ranked if row.get("source_mask_background_only")]
        (case_dir / "scan_summary.json").write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "candidate_count": len(rows),
                    "background_only_count": len(safe),
                    "recommended": safe[0] if safe else None,
                    "warning": None if safe else "No background-only source mask candidate found.",
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8-sig",
        )

    write_summary(output_dir, all_rows, cases)
    overall = json.loads((output_dir / "scan_summary.json").read_text(encoding="utf-8-sig"))
    write_recommended_command(output_dir, overall.get("recommended"))
    print(
        f"scanned_cases={len(cases)} candidates={len(all_rows)} "
        f"background_only={overall['background_only_count']} output_dir={output_dir}"
    )


if __name__ == "__main__":
    main()
