from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class AcousticMaterial:
    label: int
    name: str
    sound_speed_m_s: float
    density_kg_m3: float
    alpha_db_mhz_cm: float


@dataclass(frozen=True)
class SkullModel3DConfig:
    dx_m: float = 1.0e-3
    nx: int = 96
    ny: int = 96
    nz: int = 72
    skull_thickness_m: float = 4.0e-3
    outer_radius_x_m: float = 42.0e-3
    outer_radius_y_m: float = 36.0e-3
    outer_radius_z_m: float = 30.0e-3
    target_x_m: float = -16.0e-3
    target_y_m: float = 0.0
    target_z_m: float = 0.0


MATERIALS = {
    "water": AcousticMaterial(
        label=0,
        name="water_or_coupling_medium",
        sound_speed_m_s=1500.0,
        density_kg_m3=1000.0,
        alpha_db_mhz_cm=0.002,
    ),
    "brain": AcousticMaterial(
        label=1,
        name="brain_soft_tissue",
        sound_speed_m_s=1540.0,
        density_kg_m3=1040.0,
        alpha_db_mhz_cm=0.60,
    ),
    "skull": AcousticMaterial(
        label=2,
        name="skull_bone",
        sound_speed_m_s=2800.0,
        density_kg_m3=1900.0,
        alpha_db_mhz_cm=8.00,
    ),
}


def coordinate_grid(config: SkullModel3DConfig) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = (np.arange(config.nx) - (config.nx - 1) / 2.0) * config.dx_m
    y = (np.arange(config.ny) - (config.ny - 1) / 2.0) * config.dx_m
    z = (np.arange(config.nz) - (config.nz - 1) / 2.0) * config.dx_m
    return np.meshgrid(x, y, z, indexing="ij")


def ellipsoid_mask(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    radius_x_m: float,
    radius_y_m: float,
    radius_z_m: float,
) -> np.ndarray:
    return (x / radius_x_m) ** 2 + (y / radius_y_m) ** 2 + (z / radius_z_m) ** 2 <= 1.0


def build_label_volume(config: SkullModel3DConfig) -> np.ndarray:
    x, y, z = coordinate_grid(config)
    outer = ellipsoid_mask(
        x,
        y,
        z,
        config.outer_radius_x_m,
        config.outer_radius_y_m,
        config.outer_radius_z_m,
    )
    inner = ellipsoid_mask(
        x,
        y,
        z,
        config.outer_radius_x_m - config.skull_thickness_m,
        config.outer_radius_y_m - config.skull_thickness_m,
        config.outer_radius_z_m - config.skull_thickness_m,
    )

    labels = np.full((config.nx, config.ny, config.nz), MATERIALS["water"].label, dtype=np.uint8)
    labels[inner] = MATERIALS["brain"].label
    labels[outer & ~inner] = MATERIALS["skull"].label
    return labels


def material_property_volume(labels: np.ndarray, attribute: str) -> np.ndarray:
    values = np.zeros(labels.shape, dtype=np.float32)
    for material in MATERIALS.values():
        values[labels == material.label] = getattr(material, attribute)
    return values


def target_index(config: SkullModel3DConfig) -> tuple[int, int, int]:
    center = np.array([(config.nx - 1) / 2.0, (config.ny - 1) / 2.0, (config.nz - 1) / 2.0])
    offset = np.array([config.target_x_m, config.target_y_m, config.target_z_m]) / config.dx_m
    index = np.rint(center + offset).astype(int)
    index = np.clip(index, [0, 0, 0], [config.nx - 1, config.ny - 1, config.nz - 1])
    return tuple(int(v) for v in index)


def label_to_rgb(slice_2d: np.ndarray) -> Image.Image:
    colors = np.array(
        [
            [31, 43, 77],
            [66, 160, 121],
            [218, 204, 137],
        ],
        dtype=np.uint8,
    )
    return Image.fromarray(colors[slice_2d], mode="RGB")


def scalar_to_rgb(slice_2d: np.ndarray) -> Image.Image:
    values = slice_2d.astype(float)
    scaled = (values - values.min()) / max(values.max() - values.min(), 1e-12)
    stops = np.array(
        [
            [68, 1, 84],
            [59, 82, 139],
            [33, 145, 140],
            [94, 201, 98],
            [253, 231, 37],
        ],
        dtype=float,
    )
    idx = np.clip(scaled * (len(stops) - 1), 0, len(stops) - 1)
    low = np.floor(idx).astype(int)
    high = np.clip(low + 1, 0, len(stops) - 1)
    blend = idx[..., None] - low[..., None]
    rgb = ((1.0 - blend) * stops[low] + blend * stops[high]).astype(np.uint8)
    return Image.fromarray(rgb, mode="RGB")


def annotate(image: Image.Image, title: str, target_xy: tuple[int, int] | None = None) -> Image.Image:
    scale = 4
    image = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (image.width, image.height + 30), "white")
    canvas.paste(image, (0, 30))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 8), title, fill=(0, 0, 0))
    if target_xy is not None:
        x, y = target_xy
        x *= scale
        y = y * scale + 30
        draw.line((x - 8, y, x + 8, y), fill=(255, 0, 0), width=2)
        draw.line((x, y - 8, x, y + 8), fill=(255, 0, 0), width=2)
    return canvas


def make_contact_sheet(images: list[Image.Image]) -> Image.Image:
    width = sum(image.width for image in images)
    height = max(image.height for image in images)
    sheet = Image.new("RGB", (width, height), "white")
    x = 0
    for image in images:
        sheet.paste(image, (x, 0))
        x += image.width
    return sheet


def save_slice_previews(output_dir: Path, labels: np.ndarray, sound_speed: np.ndarray, config: SkullModel3DConfig) -> None:
    tx, ty, tz = target_index(config)

    label_images = [
        annotate(label_to_rgb(labels[:, :, tz].T), "Axial label", (tx, ty)),
        annotate(label_to_rgb(labels[:, ty, :].T), "Coronal label", (tx, tz)),
        annotate(label_to_rgb(labels[tx, :, :].T), "Sagittal label", (ty, tz)),
    ]
    make_contact_sheet(label_images).save(output_dir / "label_slices.png")

    speed_images = [
        annotate(scalar_to_rgb(sound_speed[:, :, tz].T), "Axial sound speed", (tx, ty)),
        annotate(scalar_to_rgb(sound_speed[:, ty, :].T), "Coronal sound speed", (tx, tz)),
        annotate(scalar_to_rgb(sound_speed[tx, :, :].T), "Sagittal sound speed", (ty, tz)),
    ]
    make_contact_sheet(speed_images).save(output_dir / "sound_speed_slices.png")


def save_summary(
    output_dir: Path,
    config: SkullModel3DConfig,
    labels: np.ndarray,
    sound_speed: np.ndarray,
    density: np.ndarray,
    alpha_coeff: np.ndarray,
) -> None:
    counts = {material.name: int(np.sum(labels == material.label)) for material in MATERIALS.values()}
    summary = {
        "description": "Procedural 3D acoustic skull model for k-Wave pipeline validation",
        "grid_shape": [config.nx, config.ny, config.nz],
        "dx_m": config.dx_m,
        "target_index_ijk": list(target_index(config)),
        "target_position_m": [config.target_x_m, config.target_y_m, config.target_z_m],
        "materials": {key: asdict(value) for key, value in MATERIALS.items()},
        "voxel_counts": counts,
        "sound_speed_range_m_s": [float(sound_speed.min()), float(sound_speed.max())],
        "density_range_kg_m3": [float(density.min()), float(density.max())],
        "alpha_range_db_mhz_cm": [float(alpha_coeff.min()), float(alpha_coeff.max())],
        "next_step": "Replace the procedural labels with CT-derived labels, then feed arrays into kspaceFirstOrder3D.",
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    with (output_dir / "summary.txt").open("w", encoding="utf-8") as handle:
        handle.write("3D acoustic skull model\n")
        handle.write(f"grid_shape={config.nx}x{config.ny}x{config.nz}\n")
        handle.write(f"dx_mm={config.dx_m * 1e3:.3f}\n")
        handle.write(f"target_index_ijk={target_index(config)}\n")
        for material in MATERIALS.values():
            handle.write(
                f"material={material.label},{material.name},"
                f"c={material.sound_speed_m_s:.1f},rho={material.density_kg_m3:.1f},"
                f"alpha={material.alpha_db_mhz_cm:.3f}\n"
            )
        for name, count in counts.items():
            handle.write(f"voxel_count_{name}={count}\n")


def save_model(config: SkullModel3DConfig, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    labels = build_label_volume(config)
    sound_speed = material_property_volume(labels, "sound_speed_m_s")
    density = material_property_volume(labels, "density_kg_m3")
    alpha_coeff = material_property_volume(labels, "alpha_db_mhz_cm")

    np.savez_compressed(
        output_dir / "acoustic_model_3d.npz",
        labels=labels,
        sound_speed=sound_speed,
        density=density,
        alpha_coeff=alpha_coeff,
        dx_m=np.array(config.dx_m, dtype=np.float32),
        target_index_ijk=np.array(target_index(config), dtype=np.int32),
    )
    save_slice_previews(output_dir, labels, sound_speed, config)
    save_summary(output_dir, config, labels, sound_speed, density, alpha_coeff)


if __name__ == "__main__":
    save_model(SkullModel3DConfig(), PROJECT_ROOT / "outputs" / "skull_model_3d")
