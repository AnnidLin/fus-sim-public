from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from build_ct_acoustic_model import read_nifti_file, resample_to_isotropic
from plan_ct_target_entry import LABEL_COLORS, parse_index


PROJECT_ROOT = Path(__file__).resolve().parent


def parse_float_list(value: str) -> list[float]:
    try:
        values = [float(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Expected comma-separated numbers.") from exc
    if not values:
        raise argparse.ArgumentTypeError("Expected at least one numeric threshold.")
    return values


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
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


def load_hu_volume(args: argparse.Namespace) -> tuple[np.ndarray, float, dict[str, Any]]:
    model_path = Path(args.model)
    if model_path.exists():
        data = np.load(model_path)
        if "hu" in data.files and "dx_m" in data.files:
            return (
                np.asarray(data["hu"], dtype=np.float32),
                float(np.asarray(data["dx_m"]).item()),
                {"source_type": "existing_acoustic_model", "source_path": str(model_path), "fields": sorted(data.files)},
            )

    nifti_file = Path(args.nifti_file)
    hu_raw, spacing_m, metadata = read_nifti_file(nifti_file)
    hu, dx_m, resample_metadata = resample_to_isotropic(
        hu_raw,
        spacing_m,
        target_dx_m=float(args.target_dx_mm) * 1e-3,
        max_shape=int(args.max_shape),
    )
    metadata["resampling"] = resample_metadata
    return hu, dx_m, metadata


def labels_from_thresholds(hu: np.ndarray, air_threshold_hu: float, bone_threshold_hu: float) -> np.ndarray:
    labels = np.ones(hu.shape, dtype=np.uint8)
    labels[hu < float(air_threshold_hu)] = 0
    labels[hu >= float(bone_threshold_hu)] = 2
    return labels


def largest_component_fraction(mask: np.ndarray) -> tuple[float, int, int]:
    total = int(np.sum(mask))
    if total == 0:
        return 0.0, 0, 0
    structure = ndimage.generate_binary_structure(3, 1)
    labeled, count = ndimage.label(mask, structure=structure)
    if count == 0:
        return 0.0, 0, 0
    sizes = np.bincount(labeled.ravel())
    sizes[0] = 0
    largest = int(np.max(sizes))
    return float(largest / total), largest, int(count)


def keep_largest_component(mask: np.ndarray) -> np.ndarray:
    if not np.any(mask):
        return np.zeros(mask.shape, dtype=bool)
    structure = ndimage.generate_binary_structure(3, 1)
    labeled, count = ndimage.label(mask, structure=structure)
    if count == 0:
        return np.zeros(mask.shape, dtype=bool)
    sizes = np.bincount(labeled.ravel())
    sizes[0] = 0
    largest_label = int(np.argmax(sizes))
    return labeled == largest_label


def line_indices(start: np.ndarray, end: np.ndarray) -> np.ndarray:
    distance = float(np.linalg.norm(end - start))
    steps = max(1, int(np.ceil(distance))) + 1
    points = np.rint(np.linspace(start, end, steps)).astype(int)
    _, unique_indices = np.unique(points, axis=0, return_index=True)
    return points[np.sort(unique_indices)]


def sample_path(labels: np.ndarray, start: np.ndarray, end: np.ndarray, dx_m: float) -> dict[str, Any]:
    indices = line_indices(start.astype(float), end.astype(float))
    valid = np.all((indices >= 0) & (indices < np.array(labels.shape)), axis=1)
    indices = indices[valid]
    values = labels[indices[:, 0], indices[:, 1], indices[:, 2]] if len(indices) else np.array([], dtype=np.uint8)
    bone_mask = values == 2
    non_background_mask = values != 0
    return {
        "sample_count": int(len(indices)),
        "bone_sample_count": int(np.sum(bone_mask)),
        "bone_path_length_mm": float(np.sum(bone_mask) * dx_m * 1e3),
        "non_background_sample_count": int(np.sum(non_background_mask)),
        "has_bone_crossing": bool(np.any(bone_mask)),
        "has_tissue_crossing": bool(np.any(non_background_mask)),
        "start_label": int(values[0]) if values.size else None,
        "end_label": int(values[-1]) if values.size else None,
    }


def label_to_rgb(slice_2d: np.ndarray) -> Image.Image:
    return Image.fromarray(LABEL_COLORS[np.clip(slice_2d, 0, len(LABEL_COLORS) - 1)], mode="RGB")


def annotate(image: Image.Image, title: str, markers: list[tuple[int, int, tuple[int, int, int], str]]) -> Image.Image:
    scale = max(2, min(5, 780 // max(image.width, image.height)))
    image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (image.width, image.height + 34), "white")
    canvas.paste(image, (0, 34))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 10), title, fill=(0, 0, 0))
    for x, y, color, label in markers:
        xs = int(x) * scale
        ys = int(y) * scale + 34
        draw.line((xs - 9, ys, xs + 9, ys), fill=color, width=2)
        draw.line((xs, ys - 9, xs, ys + 9), fill=color, width=2)
        draw.text((xs + 10, ys - 8), label, fill=color)
    return canvas


def contact_sheet(images: list[Image.Image]) -> Image.Image:
    width = max(image.width for image in images)
    height = sum(image.height for image in images)
    sheet = Image.new("RGB", (width, height), "white")
    y = 0
    for image in images:
        sheet.paste(image, (0, y))
        y += image.height
    return sheet


def save_label_preview(path: Path, labels: np.ndarray, target: np.ndarray, entry: np.ndarray) -> None:
    axial_z = int(target[2])
    coronal_y = int(target[1])
    sagittal_x = int(target[0])
    images = [
        annotate(
            label_to_rgb(labels[:, :, axial_z].T),
            f"Axial labels z={axial_z}",
            [
                (target[0], target[1], (255, 0, 0), "target"),
                (entry[0], entry[1], (255, 180, 0), "entry"),
            ],
        ),
        annotate(
            label_to_rgb(labels[:, coronal_y, :].T),
            f"Coronal labels y={coronal_y}",
            [
                (target[0], target[2], (255, 0, 0), "target"),
                (entry[0], entry[2], (255, 180, 0), "entry"),
            ],
        ),
        annotate(
            label_to_rgb(labels[sagittal_x, :, :].T),
            f"Sagittal labels x={sagittal_x}",
            [
                (target[1], target[2], (255, 0, 0), "target"),
                (entry[1], entry[2], (255, 180, 0), "entry"),
            ],
        ),
    ]
    contact_sheet(images).save(path)


def evaluate_threshold(
    hu: np.ndarray,
    dx_m: float,
    air_threshold_hu: float,
    bone_threshold_hu: float,
    target: np.ndarray,
    entry: np.ndarray,
    source: np.ndarray | None,
    output_dir: Path,
) -> dict[str, Any]:
    labels = labels_from_thresholds(hu, air_threshold_hu, bone_threshold_hu)
    bone_mask = labels == 2
    largest_fraction, largest_size, component_count = largest_component_fraction(bone_mask)
    largest_bone_mask = keep_largest_component(bone_mask)
    cleaned_labels = labels.copy()
    cleaned_labels[(labels == 2) & ~largest_bone_mask] = 1
    counts = {
        "background": int(np.sum(labels == 0)),
        "soft_tissue": int(np.sum(labels == 1)),
        "skull": int(np.sum(labels == 2)),
    }
    target_label = int(labels[tuple(target)])
    entry_label = int(labels[tuple(entry)])
    source_label = int(labels[tuple(source)]) if source is not None else None
    beam_path = sample_path(labels, entry, target, dx_m)
    left_x_start = np.array([0, entry[1], entry[2]], dtype=int)
    left_x_end = np.array([target[0], entry[1], entry[2]], dtype=int)
    left_x_path = sample_path(labels, left_x_start, left_x_end, dx_m)
    cleaned_beam_path = sample_path(cleaned_labels, entry, target, dx_m)
    cleaned_left_x_path = sample_path(cleaned_labels, left_x_start, left_x_end, dx_m)

    threshold_dir = output_dir / f"threshold_{int(round(bone_threshold_hu))}"
    threshold_dir.mkdir(parents=True, exist_ok=True)
    save_label_preview(threshold_dir / "label_slices.png", labels, target, entry)
    path_summary = {
        "bone_threshold_hu": float(bone_threshold_hu),
        "target_index_ijk": target.astype(int).tolist(),
        "entry_index_ijk": entry.astype(int).tolist(),
        "source_index_ijk": None if source is None else source.astype(int).tolist(),
        "target_label": target_label,
        "entry_label": entry_label,
        "source_label": source_label,
        "beam_path_entry_to_target": beam_path,
        "left_x_path_entry_yz_to_target_x": left_x_path,
        "cleaned_keep_largest_bone_component": {
            "removed_bone_voxels": int(np.sum(bone_mask & ~largest_bone_mask)),
            "beam_path_entry_to_target": cleaned_beam_path,
            "left_x_path_entry_yz_to_target_x": cleaned_left_x_path,
        },
    }
    (threshold_dir / "entry_path_summary.json").write_text(
        json.dumps(path_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "bone_threshold_hu": float(bone_threshold_hu),
        "air_threshold_hu": float(air_threshold_hu),
        "background_voxels": counts["background"],
        "soft_tissue_voxels": counts["soft_tissue"],
        "skull_voxels": counts["skull"],
        "skull_fraction": float(counts["skull"] / labels.size),
        "bone_component_count": int(component_count),
        "largest_bone_component_voxels": int(largest_size),
        "largest_bone_component_fraction": float(largest_fraction),
        "cleaned_removed_bone_voxels": int(np.sum(bone_mask & ~largest_bone_mask)),
        "cleaned_skull_voxels": int(np.sum(largest_bone_mask)),
        "target_label": target_label,
        "entry_label": entry_label,
        "source_label": source_label,
        "beam_bone_path_length_mm": beam_path["bone_path_length_mm"],
        "beam_has_bone_crossing": beam_path["has_bone_crossing"],
        "left_x_bone_path_length_mm": left_x_path["bone_path_length_mm"],
        "left_x_has_bone_crossing": left_x_path["has_bone_crossing"],
        "cleaned_beam_bone_path_length_mm": cleaned_beam_path["bone_path_length_mm"],
        "cleaned_beam_has_bone_crossing": cleaned_beam_path["has_bone_crossing"],
        "cleaned_left_x_bone_path_length_mm": cleaned_left_x_path["bone_path_length_mm"],
        "cleaned_left_x_has_bone_crossing": cleaned_left_x_path["has_bone_crossing"],
        "label_preview": str(threshold_dir / "label_slices.png"),
        "entry_path_summary": str(threshold_dir / "entry_path_summary.json"),
    }


def choose_recommendation(rows: list[dict[str, Any]], baseline_threshold: float) -> dict[str, Any] | None:
    valid = [
        row
        for row in rows
        if int(row["target_label"]) == 1
        and int(row["entry_label"]) == 2
        and bool(row["beam_has_bone_crossing"])
        and bool(row["cleaned_beam_has_bone_crossing"])
        and float(row["largest_bone_component_fraction"]) >= 0.80
    ]
    if not valid:
        return None
    baseline = next((row for row in valid if abs(float(row["bone_threshold_hu"]) - baseline_threshold) < 1e-6), None)
    if baseline is None:
        baseline = min(valid, key=lambda row: abs(float(row["bone_threshold_hu"]) - baseline_threshold))
    baseline_components = int(baseline["bone_component_count"])
    candidates = [
        row
        for row in valid
        if int(row["bone_component_count"]) <= baseline_components
        and float(row["cleaned_left_x_bone_path_length_mm"]) > 0.0
    ]
    if not candidates:
        candidates = valid
    return min(
        candidates,
        key=lambda row: (
            int(row["bone_component_count"]),
            -float(row["largest_bone_component_fraction"]),
            abs(float(row["bone_threshold_hu"]) - baseline_threshold),
        ),
    )


def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = np.array(parse_index(args.target_index), dtype=int)
    entry = np.array(parse_index(args.entry_index), dtype=int)
    source = np.array(parse_index(args.source_index), dtype=int) if args.source_index else None
    thresholds = parse_float_list(args.bone_thresholds_hu)
    hu, dx_m, source_metadata = load_hu_volume(args)
    for name, index in [("target", target), ("entry", entry), ("source", source)]:
        if index is not None and (np.any(index < 0) or np.any(index >= np.array(hu.shape))):
            raise ValueError(f"{name} index {index.tolist()} outside HU volume shape {hu.shape}")

    rows = [
        evaluate_threshold(
            hu=hu,
            dx_m=dx_m,
            air_threshold_hu=float(args.air_threshold_hu),
            bone_threshold_hu=threshold,
            target=target,
            entry=entry,
            source=source,
            output_dir=output_dir,
        )
        for threshold in thresholds
    ]
    write_csv(output_dir / "segmentation_eval.csv", rows)
    recommended = choose_recommendation(rows, baseline_threshold=float(args.baseline_bone_threshold_hu))
    summary = {
        "description": "CT skull threshold sensitivity evaluation; no k-Wave simulation is run.",
        "source": source_metadata,
        "hu_shape": [int(v) for v in hu.shape],
        "dx_m": float(dx_m),
        "air_threshold_hu": float(args.air_threshold_hu),
        "bone_thresholds_hu": thresholds,
        "target_index_ijk": target.astype(int).tolist(),
        "entry_index_ijk": entry.astype(int).tolist(),
        "source_index_ijk": None if source is None else source.astype(int).tolist(),
        "rows": rows,
        "recommended_for_rebuild": recommended,
        "recommendation_note": (
            "Use the recommended threshold for a separate rebuild output directory only; do not overwrite current best results."
            if recommended
            else "No threshold met the conservative recommendation criteria; thresholding alone may not be the main bottleneck."
        ),
        "limitations": [
            "Threshold evaluation is geometric only and does not predict acoustic focus quality.",
            "The target and entry indices are current modeling candidates, not verified anatomical treatment points.",
            "Morphology is summarized by connected components; no cleaned label volume is written in this step.",
        ],
    }
    (output_dir / "segmentation_eval_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (output_dir / "segmentation_eval_summary.txt").open("w", encoding="utf-8") as handle:
        handle.write("CT segmentation threshold evaluation\n")
        handle.write(f"hu_shape={hu.shape}\n")
        handle.write(f"dx_mm={dx_m * 1e3:.3f}\n")
        handle.write(f"thresholds={thresholds}\n")
        if recommended:
            handle.write(f"recommended_bone_threshold_hu={recommended['bone_threshold_hu']}\n")
            handle.write(f"recommended_component_count={recommended['bone_component_count']}\n")
            handle.write(f"recommended_left_x_bone_path_length_mm={recommended['left_x_bone_path_length_mm']:.3f}\n")
        else:
            handle.write("recommended_bone_threshold_hu=None\n")
    print(f"segmentation_eval={output_dir / 'segmentation_eval.csv'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate CT skull segmentation thresholds without running k-Wave.")
    parser.add_argument("--nifti-file", default=str(PROJECT_ROOT / "data" / "raw_ct" / "079.nii"))
    parser.add_argument("--model", default=str(PROJECT_ROOT / "outputs" / "ct_acoustic_model_3d" / "acoustic_model_3d.npz"))
    parser.add_argument("--target-index", required=True)
    parser.add_argument("--entry-index", required=True)
    parser.add_argument("--source-index", default="47,131,63")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "outputs" / "ct_segmentation_eval_079"))
    parser.add_argument("--air-threshold-hu", type=float, default=-500.0)
    parser.add_argument("--bone-thresholds-hu", default="250,300,400,500,700")
    parser.add_argument("--baseline-bone-threshold-hu", type=float, default=300.0)
    parser.add_argument("--target-dx-mm", type=float, default=1.0)
    parser.add_argument("--max-shape", type=int, default=220)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
