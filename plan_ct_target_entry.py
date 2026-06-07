from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parent


LABEL_COLORS = np.array(
    [
        [31, 43, 77],
        [66, 160, 121],
        [218, 204, 137],
    ],
    dtype=np.uint8,
)


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


def load_model(model_path: Path) -> tuple[np.ndarray, float, np.ndarray]:
    if not model_path.exists():
        raise FileNotFoundError(f"Missing acoustic model: {model_path}")

    data = np.load(model_path)
    required = {"labels", "dx_m", "target_index_ijk"}
    missing = required - set(data.files)
    if missing:
        raise ValueError(f"Model is missing required fields: {sorted(missing)}")

    labels = np.asarray(data["labels"], dtype=np.uint8)
    dx_m = float(np.asarray(data["dx_m"]).item())
    target = np.asarray(data["target_index_ijk"], dtype=np.int32)
    if labels.ndim != 3:
        raise ValueError(f"labels must be 3D, got shape {labels.shape}")
    if target.shape != (3,):
        raise ValueError("target_index_ijk must contain exactly 3 entries.")
    return labels, dx_m, target


def validate_index(index: np.ndarray, shape: tuple[int, int, int], name: str) -> None:
    if np.any(index < 0) or np.any(index >= np.array(shape)):
        raise ValueError(f"{name} {index.tolist()} is outside model shape {shape}.")


def plan_left_x_entry(
    labels: np.ndarray,
    dx_m: float,
    target: np.ndarray,
    source_standoff_mm: float,
    entry_offset_mm: tuple[float, float] = (0.0, 0.0),
) -> dict[str, object]:
    validate_index(target, labels.shape, "target")
    target = target.astype(int)
    offset_gp = np.rint(np.array(entry_offset_mm, dtype=float) * 1e-3 / dx_m).astype(int)
    y_index = int(target[1] + offset_gp[0])
    z_index = int(target[2] + offset_gp[1])
    if y_index < 0 or y_index >= labels.shape[1] or z_index < 0 or z_index >= labels.shape[2]:
        raise ValueError(
            f"entry offset {entry_offset_mm} mm gives y/z index {(y_index, z_index)} outside model shape {labels.shape}."
        )
    ray = labels[: int(target[0]) + 1, y_index, z_index]
    skull_indices = np.where(ray == 2)[0]
    non_background_indices = np.where(ray != 0)[0]

    if skull_indices.size:
        entry_x = int(skull_indices[0])
        skull_exit_x = int(skull_indices[-1])
        has_skull_crossing = True
    elif non_background_indices.size:
        entry_x = int(non_background_indices[0])
        skull_exit_x = entry_x
        has_skull_crossing = False
    else:
        raise ValueError("No tissue or skull voxels were found along the left_x ray before the target.")

    standoff_gp = max(1, int(round(source_standoff_mm * 1e-3 / dx_m)))
    source_x = max(1, entry_x - standoff_gp)
    while source_x > 0 and labels[source_x, y_index, z_index] != 0:
        source_x -= 1

    source = np.array([source_x, y_index, z_index], dtype=int)
    entry = np.array([entry_x, y_index, z_index], dtype=int)
    skull_exit = np.array([skull_exit_x, y_index, z_index], dtype=int)
    beam_vector = target - source
    beam_norm = float(np.linalg.norm(beam_vector))
    if beam_norm <= 0:
        raise ValueError("source and target are identical; cannot define a beam vector.")
    source_to_target_mm = float(np.linalg.norm((target - source) * dx_m) * 1e3)
    source_to_entry_mm = float(np.linalg.norm((entry - source) * dx_m) * 1e3)
    skull_path_mm = float(max(0, skull_exit_x - entry_x + 1) * dx_m * 1e3) if has_skull_crossing else 0.0

    return {
        "description": "CT target and left_x extracranial entry plan",
        "entry_direction": "left_x",
        "entry_offset_mm": [float(entry_offset_mm[0]), float(entry_offset_mm[1])],
        "entry_offset_grid_points_yz": [int(offset_gp[0]), int(offset_gp[1])],
        "beam_axis": beam_vector.astype(int).tolist(),
        "beam_unit_vector": (beam_vector / beam_norm).astype(float).tolist(),
        "target_index_ijk": target.astype(int).tolist(),
        "entry_index_ijk": entry.astype(int).tolist(),
        "skull_exit_index_ijk": skull_exit.astype(int).tolist(),
        "source_center_index_ijk": source.astype(int).tolist(),
        "source_center_label": int(labels[tuple(source)]),
        "entry_label": int(labels[tuple(entry)]),
        "target_label": int(labels[tuple(target)]),
        "has_skull_crossing": bool(has_skull_crossing),
        "source_standoff_mm": float(source_standoff_mm),
        "source_to_entry_distance_mm": source_to_entry_mm,
        "source_to_target_distance_mm": source_to_target_mm,
        "skull_path_length_mm": skull_path_mm,
        "dx_m": float(dx_m),
        "model_shape": [int(v) for v in labels.shape],
    }


def label_image(slice_2d: np.ndarray) -> Image.Image:
    return Image.fromarray(LABEL_COLORS[np.clip(slice_2d, 0, len(LABEL_COLORS) - 1)], mode="RGB")


def annotate_layout(image: Image.Image, title: str, markers: list[tuple[int, int, tuple[int, int, int], str]]) -> Image.Image:
    scale = max(2, min(5, 780 // max(image.width, image.height)))
    image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (image.width, image.height + 34), "white")
    canvas.paste(image, (0, 34))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 10), title, fill=(0, 0, 0))
    for x, y, color, label in markers:
        x_scaled = int(x) * scale
        y_scaled = int(y) * scale + 34
        draw.line((x_scaled - 9, y_scaled, x_scaled + 9, y_scaled), fill=color, width=2)
        draw.line((x_scaled, y_scaled - 9, x_scaled, y_scaled + 9), fill=color, width=2)
        draw.text((x_scaled + 10, y_scaled - 8), label, fill=color)
    return canvas


def save_layout_images(output_dir: Path, labels: np.ndarray, plan: dict[str, object]) -> None:
    target = np.array(plan["target_index_ijk"], dtype=int)
    entry = np.array(plan["entry_index_ijk"], dtype=int)
    source = np.array(plan["source_center_index_ijk"], dtype=int)

    axial = label_image(labels[:, :, target[2]].T)
    annotate_layout(
        axial,
        "CT entry plan axial slice",
        [
            (source[0], source[1], (255, 255, 255), "source"),
            (entry[0], entry[1], (255, 160, 0), "entry"),
            (target[0], target[1], (255, 0, 0), "target"),
        ],
    ).save(output_dir / "entry_layout_axial.png")

    coronal = label_image(labels[:, target[1], :].T)
    annotate_layout(
        coronal,
        "CT entry plan coronal slice",
        [
            (source[0], source[2], (255, 255, 255), "source"),
            (entry[0], entry[2], (255, 160, 0), "entry"),
            (target[0], target[2], (255, 0, 0), "target"),
        ],
    ).save(output_dir / "entry_layout_coronal.png")


def write_summary(output_dir: Path, model_path: Path, plan: dict[str, object]) -> None:
    (output_dir / "entry_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "summary.txt").open("w", encoding="utf-8") as handle:
        handle.write("CT target and extracranial entry plan\n")
        handle.write(f"model={model_path}\n")
        for key, value in plan.items():
            handle.write(f"{key}={value}\n")
        if not plan["has_skull_crossing"]:
            handle.write("warning=no skull voxel was found along the selected entry ray\n")
        if plan["source_center_label"] != 0:
            handle.write("warning=source center is not in background/coupling label 0\n")


def run(
    model_path: Path,
    output_dir: Path,
    target_override: tuple[int, int, int] | None,
    source_standoff_mm: float,
    entry_offset_mm: tuple[float, float],
) -> None:
    labels, dx_m, model_target = load_model(model_path)
    target = np.array(target_override if target_override is not None else model_target, dtype=np.int32)
    plan = plan_left_x_entry(labels, dx_m, target, source_standoff_mm, entry_offset_mm)
    output_dir.mkdir(parents=True, exist_ok=True)
    save_layout_images(output_dir, labels, plan)
    write_summary(output_dir, model_path, plan)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan a CT target and extracranial left_x tFUS entry path.")
    parser.add_argument(
        "--model",
        default=str(PROJECT_ROOT / "outputs" / "ct_acoustic_model_3d" / "acoustic_model_3d.npz"),
        help="Path to a CT-derived acoustic model .npz file.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs" / "ct_entry_plan_079"),
        help="Directory for entry plan outputs.",
    )
    parser.add_argument("--target-index", type=parse_index, default=None, help="Optional target index formatted as i,j,k.")
    parser.add_argument("--entry-offset-mm", type=parse_offset_mm, default=(0.0, 0.0), help="Entry y,z offset from the target ray in millimeters.")
    parser.add_argument("--source-standoff-mm", type=float, default=8.0, help="Distance from the outer skull entry point to the source center.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run(
            Path(args.model),
            Path(args.output_dir),
            args.target_index,
            args.source_standoff_mm,
            args.entry_offset_mm,
        )
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
