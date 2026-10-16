from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from plan_ct_target_entry import PROJECT_ROOT, plan_left_x_entry
from simulate_kwave_3d_focus import KWave3DConfig, build_source_mask, load_model


def parse_index(value: str) -> tuple[int, int, int]:
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("index must be formatted as i,j,k")
    return tuple(parts)


def parse_offset_mm(value: str) -> tuple[float, float]:
    parts = [float(part.strip()) for part in value.split(",")]
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("offset must be formatted as y,z in millimeters")
    return tuple(parts)


def parse_float_list(value: str) -> list[float]:
    try:
        values = [float(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("standoff list must be comma-separated numbers") from exc
    if not values:
        raise argparse.ArgumentTypeError("at least one standoff value is required")
    return values


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_labels_dx_target(model_path: Path, target_index: tuple[int, int, int] | None) -> tuple[np.ndarray, float, np.ndarray]:
    data = np.load(model_path)
    required = {"labels", "dx_m", "target_index_ijk"}
    missing = required - set(data.files)
    if missing:
        raise ValueError(f"Model is missing required fields: {sorted(missing)}")
    labels = np.asarray(data["labels"], dtype=np.uint8)
    dx_m = float(np.asarray(data["dx_m"]).item())
    target = np.asarray(target_index if target_index is not None else data["target_index_ijk"], dtype=np.int32)
    return labels, dx_m, target


def label_count(metadata: dict[str, object], label: int) -> int:
    counts = metadata.get("source_label_counts", {})
    if not isinstance(counts, dict):
        return 0
    return int(counts.get(str(label), 0))


def evaluate_standoff(
    model_path: Path,
    output_dir: Path,
    labels: np.ndarray,
    dx_m: float,
    target: np.ndarray,
    entry_offset_mm: tuple[float, float],
    standoff_mm: float,
    aperture_mm: float,
    radius_mm: float,
    quick_lateral_mm: float,
    quick_post_target_mm: float,
) -> dict[str, object]:
    plan = plan_left_x_entry(labels, dx_m, target, standoff_mm, entry_offset_mm)
    plan_path = output_dir / f"entry_plan_standoff_{standoff_mm:g}mm_ap{aperture_mm:g}_r{radius_mm:g}.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    config = KWave3DConfig(
        model_path=model_path,
        entry_plan_path=plan_path,
        quick_mode=True,
        quick_lateral_half_width_m=quick_lateral_mm * 1e-3,
        quick_post_target_margin_m=quick_post_target_mm * 1e-3,
        aperture_diameter_m=aperture_mm * 1e-3,
        transducer_radius_m=radius_mm * 1e-3,
    )
    loaded = load_model(config)
    _source_mask, source_metadata = build_source_mask(loaded, config)
    label0 = label_count(source_metadata, 0)
    label1 = label_count(source_metadata, 1)
    label2 = label_count(source_metadata, 2)
    total = int(source_metadata["source_points"])
    unsafe_points = label1 + label2
    return {
        "standoff_mm": float(standoff_mm),
        "aperture_mm": float(aperture_mm),
        "radius_mm": float(radius_mm),
        "status": "valid",
        "entry_plan": str(plan_path),
        "source_center_index_ijk": plan["source_center_index_ijk"],
        "entry_index_ijk": plan["entry_index_ijk"],
        "target_index_ijk": plan["target_index_ijk"],
        "source_to_target_distance_mm": plan["source_to_target_distance_mm"],
        "source_to_entry_distance_mm": plan["source_to_entry_distance_mm"],
        "skull_path_length_mm": plan["skull_path_length_mm"],
        "source_points": total,
        "source_label_0_count": label0,
        "source_label_1_count": label1,
        "source_label_2_count": label2,
        "unsafe_source_points": unsafe_points,
        "unsafe_source_fraction": float(unsafe_points / total) if total else 1.0,
        "source_label_counts": source_metadata.get("source_label_counts", {}),
        "crop_origin_ijk": loaded.crop_origin_ijk.astype(int).tolist(),
        "crop_shape": [int(v) for v in loaded.sound_speed.shape],
        "voxel_count": int(np.prod(loaded.sound_speed.shape)),
        "bowl_index_ijk": source_metadata["bowl_index_ijk"],
        "radius_grid_points": source_metadata["radius_grid_points"],
        "diameter_grid_points": source_metadata["diameter_grid_points"],
    }


def rank_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    valid = [row for row in rows if row.get("status") == "valid"]
    valid.sort(
        key=lambda row: (
            int(row["source_label_2_count"]),
            int(row["source_label_1_count"]),
            float(row["unsafe_source_fraction"]),
            int(row["voxel_count"]),
            -int(row["source_points"]),
            float(row["aperture_mm"]),
            float(row["radius_mm"]),
            float(row["standoff_mm"]),
        )
    )
    for rank, row in enumerate(valid, start=1):
        row["safety_rank"] = rank
        row["recommended"] = rank == 1
        row["source_mask_is_background_only"] = int(row["unsafe_source_points"]) == 0
    failures = [row for row in rows if row.get("status") != "valid"]
    for row in failures:
        row["safety_rank"] = ""
        row["recommended"] = False
        row["source_mask_is_background_only"] = False
    return valid + failures


def write_summary(output_dir: Path, args: argparse.Namespace, rows: list[dict[str, object]]) -> None:
    best = next((row for row in rows if row.get("recommended")), None)
    summary = {
        "model_path": str(args.model),
        "target_index_ijk": list(args.target_index) if args.target_index is not None else None,
        "entry_offset_mm": list(args.entry_offset_mm),
        "standoff_candidates_mm": args.standoff_mm,
        "aperture_candidates_mm": args.aperture_mm,
        "radius_candidates_mm": args.radius_mm,
        "quick_lateral_mm": args.quick_lateral_mm,
        "quick_post_target_mm": args.quick_post_target_mm,
        "valid_count": sum(1 for row in rows if row.get("status") == "valid"),
        "failure_count": sum(1 for row in rows if row.get("status") != "valid"),
        "recommended": best,
        "warning": None
        if best and int(best.get("unsafe_source_points", 1)) == 0
        else "No background-only source mask was found; recommended standoff minimizes overlap.",
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "summary.txt").open("w", encoding="utf-8") as handle:
        handle.write("Source standoff safety check\n")
        handle.write(f"model={args.model}\n")
        handle.write(f"target_index_ijk={summary['target_index_ijk']}\n")
        handle.write(f"entry_offset_mm={summary['entry_offset_mm']}\n")
        handle.write(f"valid_count={summary['valid_count']}\n")
        if best:
            handle.write(f"recommended_standoff_mm={best['standoff_mm']}\n")
            handle.write(f"recommended_aperture_mm={best['aperture_mm']}\n")
            handle.write(f"recommended_radius_mm={best['radius_mm']}\n")
            handle.write(f"recommended_entry_plan={best['entry_plan']}\n")
            handle.write(f"source_label_counts={best['source_label_counts']}\n")
            handle.write(f"unsafe_source_points={best['unsafe_source_points']}\n")
            handle.write(f"voxel_count={best['voxel_count']}\n")
        if summary["warning"]:
            handle.write(f"warning={summary['warning']}\n")


def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    model_path = Path(args.model)
    output_dir.mkdir(parents=True, exist_ok=True)
    labels, dx_m, target = load_labels_dx_target(model_path, args.target_index)
    rows: list[dict[str, object]] = []
    for standoff_mm in args.standoff_mm:
        for aperture_mm in args.aperture_mm:
            for radius_mm in args.radius_mm:
                try:
                    rows.append(
                        evaluate_standoff(
                            model_path=model_path,
                            output_dir=output_dir,
                            labels=labels,
                            dx_m=dx_m,
                            target=target,
                            entry_offset_mm=args.entry_offset_mm,
                            standoff_mm=standoff_mm,
                            aperture_mm=aperture_mm,
                            radius_mm=radius_mm,
                            quick_lateral_mm=args.quick_lateral_mm,
                            quick_post_target_mm=args.quick_post_target_mm,
                        )
                    )
                except Exception as exc:
                    rows.append(
                        {
                            "standoff_mm": float(standoff_mm),
                            "aperture_mm": float(aperture_mm),
                            "radius_mm": float(radius_mm),
                            "status": "failed",
                            "error": str(exc),
                        }
                    )
    ranked = rank_rows(rows)
    write_csv(output_dir / "source_safety_candidates.csv", ranked)
    write_summary(output_dir, args, ranked)
    best = next((row for row in ranked if row.get("recommended")), None)
    best_text = "none" if best is None else f"standoff={best['standoff_mm']}mm aperture={best['aperture_mm']}mm radius={best['radius_mm']}mm"
    print(f"checked={len(rows)} recommended={best_text} output_dir={output_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check whether a CT entry-plan bowl source overlaps tissue/skull.")
    parser.add_argument(
        "--model",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "ct_acoustic_model_3d" / "acoustic_model_3d.npz",
    )
    parser.add_argument("--target-index", type=parse_index, default=None)
    parser.add_argument("--entry-offset-mm", type=parse_offset_mm, default=(0.0, 0.0))
    parser.add_argument("--standoff-mm", type=parse_float_list, default=[8.0, 12.0, 16.0, 20.0, 24.0, 28.0, 32.0])
    parser.add_argument("--aperture-mm", type=parse_float_list, default=[25.0])
    parser.add_argument("--radius-mm", type=parse_float_list, default=[30.0])
    parser.add_argument("--quick-lateral-mm", type=float, default=17.0)
    parser.add_argument("--quick-post-target-mm", type=float, default=8.0)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "ct_source_safety_target_020",
    )
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
