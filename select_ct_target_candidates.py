from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from plan_ct_target_entry import LABEL_COLORS, PROJECT_ROOT, load_model, plan_left_x_entry
from scan_ct_entry_positions import estimate_quick_crop, geometry_metrics


DEFAULT_X_OFFSETS_MM = [-20.0, -10.0, 0.0, 10.0, 20.0]
DEFAULT_Y_OFFSETS_MM = [-20.0, -10.0, 0.0, 10.0, 20.0]
DEFAULT_Z_OFFSETS_MM = [-15.0, -5.0, 0.0, 5.0, 15.0]
DEFAULT_ENTRY_PROBE_OFFSETS_MM = [(0.0, -10.0), (0.0, 0.0), (-10.0, 0.0), (10.0, 0.0), (0.0, 10.0)]


def parse_float_list(value: str) -> list[float]:
    try:
        return [float(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a comma-separated number list") from exc


def parse_index(value: str) -> tuple[int, int, int]:
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("index must be formatted as i,j,k")
    return tuple(parts)


def parse_entry_probe_offsets(value: str) -> list[tuple[float, float]]:
    offsets: list[tuple[float, float]] = []
    for item in value.split(";"):
        if not item.strip():
            continue
        parts = [float(part.strip()) for part in item.split(",")]
        if len(parts) != 2:
            raise argparse.ArgumentTypeError("entry probe offsets must use 'y,z;y,z' format")
        offsets.append((parts[0], parts[1]))
    if not offsets:
        raise argparse.ArgumentTypeError("at least one entry probe offset is required")
    return offsets


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


def target_from_offsets(base_target: np.ndarray, dx_m: float, offsets_mm: tuple[float, float, float]) -> np.ndarray:
    offset_grid = np.rint(np.array(offsets_mm, dtype=float) * 1e-3 / dx_m).astype(int)
    return base_target.astype(int) + offset_grid


def local_soft_tissue_fraction(labels: np.ndarray, target: np.ndarray, radius_gp: int) -> float:
    lo = np.maximum(target - radius_gp, 0)
    hi = np.minimum(target + radius_gp + 1, np.array(labels.shape))
    window = labels[lo[0] : hi[0], lo[1] : hi[1], lo[2] : hi[2]]
    if window.size == 0:
        return 0.0
    return float(np.mean(window == 1))


def edge_margin_mm(target: np.ndarray, shape: tuple[int, int, int], dx_m: float) -> float:
    margin_gp = min(
        int(target[0]),
        int(target[1]),
        int(target[2]),
        int(shape[0] - 1 - target[0]),
        int(shape[1] - 1 - target[1]),
        int(shape[2] - 1 - target[2]),
    )
    return float(margin_gp * dx_m * 1e3)


def pick_best_entry_probe(
    labels: np.ndarray,
    dx_m: float,
    target: np.ndarray,
    source_standoff_mm: float,
    entry_probe_offsets_mm: list[tuple[float, float]],
) -> tuple[dict[str, object], dict[str, object]]:
    best_plan: dict[str, object] | None = None
    best_metrics: dict[str, object] | None = None
    failures: list[str] = []
    for entry_offset in entry_probe_offsets_mm:
        try:
            plan = plan_left_x_entry(labels, dx_m, target, source_standoff_mm, entry_offset)
            if not plan["has_skull_crossing"]:
                raise ValueError("no skull crossing")
            if int(plan["source_center_label"]) != 0:
                raise ValueError(f"source label {plan['source_center_label']}")
            if int(plan["entry_label"]) != 2:
                raise ValueError(f"entry label {plan['entry_label']}")
            estimates = estimate_quick_crop(plan, labels.shape, True, None)
            geom = geometry_metrics(plan)
            merged = {**estimates, **geom}
            score = (
                float(merged["voxel_count"]) / 100_000.0
                + 0.20 * float(plan["skull_path_length_mm"])
                + 0.05 * float(merged["angle_from_left_x_deg"])
            )
            merged["entry_probe_score"] = score
            if best_metrics is None or score < float(best_metrics["entry_probe_score"]):
                best_plan = plan
                best_metrics = merged
        except Exception as exc:
            failures.append(f"{entry_offset}: {exc}")
    if best_plan is None or best_metrics is None:
        raise ValueError("; ".join(failures) if failures else "no valid entry probe")
    return best_plan, best_metrics


def build_target_candidates(
    model_path: Path,
    target_override: tuple[int, int, int] | None,
    x_offsets_mm: list[float],
    y_offsets_mm: list[float],
    z_offsets_mm: list[float],
    source_standoff_mm: float,
    entry_probe_offsets_mm: list[tuple[float, float]],
    min_edge_margin_mm: float,
    soft_radius_mm: float,
    min_soft_fraction: float,
) -> tuple[np.ndarray, float, np.ndarray, list[dict[str, object]], list[dict[str, object]]]:
    labels, dx_m, model_target = load_model(model_path)
    base_target = np.array(target_override if target_override is not None else model_target, dtype=int)
    soft_radius_gp = max(1, int(round(soft_radius_mm * 1e-3 / dx_m)))
    valid_rows: list[dict[str, object]] = []
    rejected_rows: list[dict[str, object]] = []
    candidate_index = 0

    for x_offset in x_offsets_mm:
        for y_offset in y_offsets_mm:
            for z_offset in z_offsets_mm:
                offsets = (x_offset, y_offset, z_offset)
                target = target_from_offsets(base_target, dx_m, offsets)
                row_base: dict[str, object] = {
                    "target_offset_x_mm": x_offset,
                    "target_offset_y_mm": y_offset,
                    "target_offset_z_mm": z_offset,
                    "target_index_ijk": target.astype(int).tolist(),
                }
                try:
                    if np.any(target < 0) or np.any(target >= np.array(labels.shape)):
                        raise ValueError("target outside model")
                    label = int(labels[tuple(target)])
                    if label != 1:
                        raise ValueError(f"target label is {label}, expected soft tissue label 1")
                    margin_mm = edge_margin_mm(target, labels.shape, dx_m)
                    if margin_mm < min_edge_margin_mm:
                        raise ValueError(f"edge margin {margin_mm:.1f} mm below {min_edge_margin_mm:.1f} mm")
                    soft_fraction = local_soft_tissue_fraction(labels, target, soft_radius_gp)
                    if soft_fraction < min_soft_fraction:
                        raise ValueError(
                            f"local soft-tissue fraction {soft_fraction:.3f} below {min_soft_fraction:.3f}"
                        )

                    best_plan, best_probe = pick_best_entry_probe(
                        labels, dx_m, target, source_standoff_mm, entry_probe_offsets_mm
                    )
                    distance_from_base_mm = float(np.linalg.norm((target - base_target) * dx_m) * 1e3)
                    target_score = (
                        float(best_probe["voxel_count"]) / 100_000.0
                        + 0.20 * float(best_plan["skull_path_length_mm"])
                        + 0.05 * float(best_probe["angle_from_left_x_deg"])
                        + 0.50 * (1.0 - soft_fraction)
                        + 0.01 * distance_from_base_mm
                    )
                    valid_rows.append(
                        {
                            "target_candidate_id": f"target_{candidate_index:03d}",
                            "status": "valid",
                            **row_base,
                            "target_label": label,
                            "local_soft_tissue_fraction": soft_fraction,
                            "edge_margin_mm": margin_mm,
                            "distance_from_base_target_mm": distance_from_base_mm,
                            "recommended_entry_offset_y_mm": best_plan["entry_offset_mm"][0],
                            "recommended_entry_offset_z_mm": best_plan["entry_offset_mm"][1],
                            "source_center_index_ijk": best_plan["source_center_index_ijk"],
                            "entry_index_ijk": best_plan["entry_index_ijk"],
                            "source_to_target_distance_mm": best_plan["source_to_target_distance_mm"],
                            "skull_path_length_mm": best_plan["skull_path_length_mm"],
                            "angle_from_left_x_deg": best_probe["angle_from_left_x_deg"],
                            "crop_shape": best_probe["crop_shape"],
                            "voxel_count": best_probe["voxel_count"],
                            "arrival_time_us_estimate": best_probe["arrival_time_us_estimate"],
                            "sim_time_us_estimate": best_probe["sim_time_us_estimate"],
                            "nt_estimate": best_probe["nt_estimate"],
                            "work_estimate": best_probe["work_estimate"],
                            "target_score": target_score,
                        }
                    )
                    candidate_index += 1
                except Exception as exc:
                    rejected_rows.append({**row_base, "status": "rejected", "error": str(exc)})

    valid_rows.sort(
        key=lambda row: (
            float(row["target_score"]),
            int(row["voxel_count"]),
            float(row["source_to_target_distance_mm"]),
        )
    )
    for rank, row in enumerate(valid_rows, start=1):
        row["target_rank"] = rank
        row["recommended_top3"] = rank <= 3
    return labels, dx_m, base_target, valid_rows, rejected_rows


def label_image(slice_2d: np.ndarray) -> Image.Image:
    return Image.fromarray(LABEL_COLORS[np.clip(slice_2d, 0, len(LABEL_COLORS) - 1)], mode="RGB")


def draw_markers(
    image: Image.Image,
    title: str,
    markers: list[tuple[int, int, tuple[int, int, int], str]],
) -> Image.Image:
    scale = max(2, min(5, 820 // max(image.width, image.height)))
    image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (image.width, image.height + 38), "white")
    canvas.paste(image, (0, 38))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 12), title, fill=(0, 0, 0))
    for x, y, color, label in markers:
        xs = int(x) * scale
        ys = int(y) * scale + 38
        draw.line((xs - 9, ys, xs + 9, ys), fill=color, width=2)
        draw.line((xs, ys - 9, xs, ys + 9), fill=color, width=2)
        draw.text((xs + 10, ys - 8), label, fill=color)
    return canvas


def save_preview_images(output_dir: Path, labels: np.ndarray, base_target: np.ndarray, rows: list[dict[str, object]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    top_rows = rows[:3]
    marker_targets = [(np.array(row["target_index_ijk"], dtype=int), f"T{row['target_rank']}") for row in top_rows]
    axial_z = int(base_target[2])
    coronal_y = int(base_target[1])
    sagittal_x = int(base_target[0])

    axial_markers = [(int(base_target[0]), int(base_target[1]), (255, 0, 0), "base")]
    axial_markers.extend(
        (int(target[0]), int(target[1]), (255, 180, 0), label)
        for target, label in marker_targets
        if int(target[2]) == axial_z
    )
    draw_markers(label_image(labels[:, :, axial_z].T), "Target candidates axial", axial_markers).save(
        output_dir / "target_candidates_axial.png"
    )

    coronal_markers = [(int(base_target[0]), int(base_target[2]), (255, 0, 0), "base")]
    coronal_markers.extend(
        (int(target[0]), int(target[2]), (255, 180, 0), label)
        for target, label in marker_targets
        if int(target[1]) == coronal_y
    )
    draw_markers(label_image(labels[:, coronal_y, :].T), "Target candidates coronal", coronal_markers).save(
        output_dir / "target_candidates_coronal.png"
    )

    sagittal_markers = [(int(base_target[1]), int(base_target[2]), (255, 0, 0), "base")]
    sagittal_markers.extend(
        (int(target[1]), int(target[2]), (255, 180, 0), label)
        for target, label in marker_targets
        if int(target[0]) == sagittal_x
    )
    draw_markers(label_image(labels[sagittal_x, :, :].T), "Target candidates sagittal", sagittal_markers).save(
        output_dir / "target_candidates_sagittal.png"
    )


def write_summary(
    output_dir: Path,
    model_path: Path,
    base_target: np.ndarray,
    valid_rows: list[dict[str, object]],
    rejected_rows: list[dict[str, object]],
    args: argparse.Namespace,
) -> None:
    best = valid_rows[0] if valid_rows else None
    summary = {
        "model_path": str(model_path),
        "base_target_index_ijk": base_target.astype(int).tolist(),
        "valid_target_count": len(valid_rows),
        "rejected_target_count": len(rejected_rows),
        "search_offsets_mm": {
            "x": args.x_offsets_mm,
            "y": args.y_offsets_mm,
            "z": args.z_offsets_mm,
        },
        "filters": {
            "min_edge_margin_mm": args.min_edge_margin_mm,
            "soft_radius_mm": args.soft_radius_mm,
            "min_soft_fraction": args.min_soft_fraction,
        },
        "entry_probe_offsets_mm": args.entry_probe_offsets_mm,
        "recommended_top3": valid_rows[:3],
        "best_target": best,
        "time_budget": {
            "target_generation_expected_s": "10-30",
            "single_geometry_scan_expected_s": "10-30",
            "single_kwave_fast_expected_min": "4-8",
            "first_kwave_checkpoint_min": 2,
            "reassess_kwave_after_min": 10,
        },
        "note": "Targets are CT-label geometric candidates, not anatomical treatment targets.",
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "summary.txt").open("w", encoding="utf-8") as handle:
        handle.write("CT target candidate selection\n")
        handle.write(f"model={model_path}\n")
        handle.write(f"base_target_index_ijk={base_target.astype(int).tolist()}\n")
        handle.write(f"valid_target_count={len(valid_rows)}\n")
        handle.write(f"rejected_target_count={len(rejected_rows)}\n")
        if best:
            handle.write(f"best_target_candidate_id={best['target_candidate_id']}\n")
            handle.write(f"best_target_index_ijk={best['target_index_ijk']}\n")
            handle.write(f"best_target_score={best['target_score']}\n")
            handle.write(
                "recommended_scan_command="
                f"python scan_ct_entry_positions.py --model {model_path} "
                f"--target-index {','.join(str(v) for v in best['target_index_ijk'])} "
                f"--output-dir {output_dir.parent / ('ct_entry_scan_079_' + best['target_candidate_id'])}\n"
            )


def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    model_path = Path(args.model)
    output_dir.mkdir(parents=True, exist_ok=True)
    labels, _dx_m, base_target, valid_rows, rejected_rows = build_target_candidates(
        model_path=model_path,
        target_override=args.target_index,
        x_offsets_mm=args.x_offsets_mm,
        y_offsets_mm=args.y_offsets_mm,
        z_offsets_mm=args.z_offsets_mm,
        source_standoff_mm=args.source_standoff_mm,
        entry_probe_offsets_mm=args.entry_probe_offsets_mm,
        min_edge_margin_mm=args.min_edge_margin_mm,
        soft_radius_mm=args.soft_radius_mm,
        min_soft_fraction=args.min_soft_fraction,
    )
    write_csv(output_dir / "target_candidates.csv", valid_rows)
    write_csv(output_dir / "rejected_target_candidates.csv", rejected_rows)
    save_preview_images(output_dir, labels, base_target, valid_rows)
    write_summary(output_dir, model_path, base_target, valid_rows, rejected_rows, args)
    best = valid_rows[0]["target_candidate_id"] if valid_rows else "none"
    print(f"valid_targets={len(valid_rows)} rejected_targets={len(rejected_rows)} recommended_first={best} output_dir={output_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select CT-label geometric target candidates for 079 tFUS scans.")
    parser.add_argument(
        "--model",
        default=str(PROJECT_ROOT / "outputs" / "ct_acoustic_model_3d" / "acoustic_model_3d.npz"),
        help="Path to a CT-derived acoustic model .npz file.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs" / "ct_target_candidates_079"),
        help="Output directory for target candidate reports.",
    )
    parser.add_argument("--target-index", type=parse_index, default=None, help="Optional base target index formatted as i,j,k.")
    parser.add_argument("--x-offsets-mm", type=parse_float_list, default=DEFAULT_X_OFFSETS_MM)
    parser.add_argument("--y-offsets-mm", type=parse_float_list, default=DEFAULT_Y_OFFSETS_MM)
    parser.add_argument("--z-offsets-mm", type=parse_float_list, default=DEFAULT_Z_OFFSETS_MM)
    parser.add_argument(
        "--entry-probe-offsets-mm",
        type=parse_entry_probe_offsets,
        default=DEFAULT_ENTRY_PROBE_OFFSETS_MM,
        help="Semicolon-separated entry probe offsets, formatted as 'y,z;y,z'.",
    )
    parser.add_argument("--source-standoff-mm", type=float, default=8.0)
    parser.add_argument("--min-edge-margin-mm", type=float, default=20.0)
    parser.add_argument("--soft-radius-mm", type=float, default=3.0)
    parser.add_argument("--min-soft-fraction", type=float, default=0.65)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
