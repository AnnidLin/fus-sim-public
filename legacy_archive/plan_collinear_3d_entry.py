from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/acoustic_model_3d.npz"
OUT_DIR = PROJECT_ROOT / "outputs/collinear_entry_planning/079_candidate_006_dx0p75"

LABEL_COLORS = np.array(
    [
        [31, 43, 77],     # 0: Air/Background (dark blue)
        [66, 160, 121],    # 1: Tissue (green)
        [218, 204, 137],   # 2: Skull (yellow)
    ],
    dtype=np.uint8,
)

def load_model(path: Path) -> tuple[np.ndarray, np.ndarray, float, np.ndarray]:
    data = np.load(path)
    return (
        np.asarray(data["labels"], dtype=np.uint8),
        np.asarray(data["hu"], dtype=np.float32),
        float(np.asarray(data["dx_m"]).item()),
        np.asarray(data["target_index_ijk"], dtype=np.int32)
    )

def trace_line(start: np.ndarray, end: np.ndarray) -> np.ndarray:
    dist = np.linalg.norm(end - start)
    num_points = int(max(10, round(dist * 5)))
    t = np.linspace(0, 1, num_points)
    pts = np.outer(1 - t, start) + np.outer(t, end)
    coords = np.round(pts).astype(int)
    _, idx = np.unique(coords, axis=0, return_index=True)
    return coords[sorted(idx)]

def label_image(slice_2d: np.ndarray) -> Image.Image:
    return Image.fromarray(LABEL_COLORS[np.clip(slice_2d, 0, len(LABEL_COLORS) - 1)], mode="RGB")

def annotate_layout(image: Image.Image, title: str, markers: list[tuple[float, float, tuple[int, int, int], str]]) -> Image.Image:
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

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("Loading acoustic model...")
    labels, hu, dx_m, default_target = load_model(MODEL_PATH)
    dx_mm = dx_m * 1e3
    
    # Load target index from candidate_006's selected entry plan JSON
    plan_path = PROJECT_ROOT / "outputs/corrected_entry_plan_resolution_chain/079_candidate_006_dx0p75/selected_entry_plan.json"
    with open(plan_path, "r", encoding="utf-8") as f:
        plan_ref = json.load(f)
    target = np.array(plan_ref["target_index_ijk"], dtype=np.int32)
    
    # Stand-off config: 16 mm
    source_standoff_mm = 16.0

    standoff_gp = source_standoff_mm / dx_mm
    
    print(f"Target index (source coordinates): {target.tolist()}")
    
    best_candidate = None
    best_score = -999999.0
    
    # Search range for y-z offsets around target
    # 079_candidate_006 had an entry offset of [10.0, 0.0] mm
    # We search offset y from -15 to 15 mm and offset z from -10 to 10 mm
    y_offsets_mm = np.arange(-15.0, 16.0, 1.0)
    z_offsets_mm = np.arange(-10.0, 11.0, 1.0)
    
    print("Searching for collinear entry candidates...")
    for dy_mm in y_offsets_mm:
        dy_gp = int(round(dy_mm / dx_mm))
        y_entry = target[1] + dy_gp
        if y_entry < 0 or y_entry >= labels.shape[1]:
            continue
            
        for dz_mm in z_offsets_mm:
            dz_gp = int(round(dz_mm / dx_mm))
            z_entry = target[2] + dz_gp
            if z_entry < 0 or z_entry >= labels.shape[2]:
                continue
                
            # Ray parallel to x-axis to find the candidate skull entry
            ray_labels = labels[:target[0] + 1, y_entry, z_entry]
            skull_indices = np.where(ray_labels == 2)[0]
            if len(skull_indices) == 0:
                continue
                
            entry_x = skull_indices[0]
            candidate_entry = np.array([entry_x, y_entry, z_entry])
            
            # Form collinear beam unit vector
            beam_vec = target - candidate_entry
            beam_norm = np.linalg.norm(beam_vec)
            if beam_norm <= 0:
                continue
            beam_unit = beam_vec / beam_norm
            
            # Position source center strictly along the collinear axis
            source_center = candidate_entry - standoff_gp * beam_unit
            source_center_idx = np.round(source_center).astype(int)
            
            # Check bounds for source center
            if np.any(source_center_idx < 0) or np.any(source_center_idx >= labels.shape):
                continue
                
            # Safety check: source center must be in label 0 (air/coupling)
            if labels[tuple(source_center_idx)] != 0:
                continue
                
            # Trace the actual collinear beam axis
            path_coords = trace_line(source_center_idx, target)
            
            # Count skull crossing voxels along the actual path
            crossed_skull_indices = []
            hu_values = []
            for coord in path_coords:
                lbl = labels[tuple(coord)]
                hu_val = hu[tuple(coord)]
                if lbl == 2:
                    crossed_skull_indices.append(coord.tolist())
                    hu_values.append(hu_val)
                    
            skull_voxels_crossed = len(crossed_skull_indices)
            actual_skull_thickness_mm = skull_voxels_crossed * dx_mm
            
            if skull_voxels_crossed > 0:
                avg_hu = float(np.mean(hu_values))
                # Score function: prefers high bone density and penalizes large offsets
                score = avg_hu - 15.0 * (dy_mm**2 + dz_mm**2)
                
                if score > best_score:
                    best_score = score
                    # Find entry_x and skull_exit_x along the path
                    crossed_x = [c[0] for c in crossed_skull_indices]
                    best_candidate = {
                        "entry_offset_mm": [float(dy_mm), float(dz_mm)],
                        "entry_offset_grid_points_yz": [dy_gp, dz_gp],
                        "beam_axis": (target - source_center_idx).tolist(),
                        "beam_unit_vector": beam_unit.tolist(),
                        "target_index_ijk": target.tolist(),
                        "entry_index_ijk": crossed_skull_indices[0],
                        "skull_exit_index_ijk": crossed_skull_indices[-1],
                        "source_center_index_ijk": source_center_idx.tolist(),
                        "source_center_label": int(labels[tuple(source_center_idx)]),
                        "entry_label": 2,
                        "target_label": int(labels[tuple(target)]),
                        "has_skull_crossing": True,
                        "source_standoff_mm": source_standoff_mm,
                        "source_to_entry_distance_mm": float(np.linalg.norm((crossed_skull_indices[0] - source_center_idx) * dx_mm)),
                        "source_to_target_distance_mm": float(np.linalg.norm((target - source_center_idx) * dx_mm)),
                        "skull_path_length_mm": actual_skull_thickness_mm,
                        "average_hu_along_crossing": avg_hu,
                        "dx_m": dx_m,
                        "model_shape": list(labels.shape)
                    }

    if best_candidate is None:
        print("No valid collinear entry plan found!")
        return
        
    print(f"Best collinear candidate found!")
    print(f"  Entry Offset: {best_candidate['entry_offset_mm']} mm")
    print(f"  Source Center: {best_candidate['source_center_index_ijk']}")
    print(f"  Skull Entry: {best_candidate['entry_index_ijk']}")
    print(f"  Skull Exit: {best_candidate['skull_exit_index_ijk']}")
    print(f"  Skull Path Length: {best_candidate['skull_path_length_mm']:.2f} mm")
    print(f"  Average HU: {best_candidate['average_hu_along_crossing']:.1f}")
    
    # Save json report
    with open(OUT_DIR / "collinear_entry_plan.json", "w", encoding="utf-8") as f:
        json.dump(best_candidate, f, indent=2, ensure_ascii=False)
    
    # Generate layout images
    source = np.array(best_candidate["source_center_index_ijk"])
    entry = np.array(best_candidate["entry_index_ijk"])
    skull_exit = np.array(best_candidate["skull_exit_index_ijk"])
    
    # Axial Slice Layout
    axial = label_image(labels[:, :, target[2]].T)
    axial_annotated = annotate_layout(
        axial,
        "Collinear Entry Plan Axial Slice (z=" + str(target[2]) + ")",
        [
            (float(source[0]), float(source[1]), (255, 255, 255), "source"),
            (float(entry[0]), float(entry[1]), (255, 160, 0), "entry"),
            (float(skull_exit[0]), float(skull_exit[1]), (255, 255, 0), "exit"),
            (float(target[0]), float(target[1]), (255, 0, 0), "target"),
        ]
    )
    axial_annotated.save(OUT_DIR / "entry_layout_axial.png")
    
    # Coronal Slice Layout
    coronal = label_image(labels[:, target[1], :].T)
    coronal_annotated = annotate_layout(
        coronal,
        "Collinear Entry Plan Coronal Slice (y=" + str(target[1]) + ")",
        [
            (float(source[0]), float(source[2]), (255, 255, 255), "source"),
            (float(entry[0]), float(entry[2]), (255, 160, 0), "entry"),
            (float(skull_exit[0]), float(skull_exit[2]), (255, 255, 0), "exit"),
            (float(target[0]), float(target[2]), (255, 0, 0), "target"),
        ]
    )
    coronal_annotated.save(OUT_DIR / "entry_layout_coronal.png")
    
    print("Generated layout images.")

if __name__ == "__main__":
    main()
