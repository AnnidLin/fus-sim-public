from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage


def db2neper(db: np.ndarray | float, y: np.ndarray | float) -> np.ndarray | float:
    return db * (np.log(10) / 20.0) * 100.0 / ((2 * np.pi * 1e6) ** y)


def neper2db(neper: np.ndarray | float, y: np.ndarray | float) -> np.ndarray | float:
    return neper / (np.log(10) / 20.0) / 100.0 * ((2 * np.pi * 1e6) ** y)


def fit_power_law_params_multi(
    a0: np.ndarray,
    y: np.ndarray,
    c0: np.ndarray,
    f_ref: float,
    y_ref: float,
) -> np.ndarray:
    if y_ref == 1.0:
        raise ValueError("y_ref cannot be set to 1.0.")
    w = 2.0 * np.pi * f_ref
    a0_np = db2neper(a0, y)
    desired_absorption = a0_np * (w ** y)
    denom = (w ** y_ref) + desired_absorption * (y_ref + 1.0) * c0 * np.tan(np.pi * y_ref / 2.0) * (w ** (y_ref - 1.0))
    a0_fit_np = desired_absorption / denom
    a0_fit = neper2db(a0_fit_np, y_ref)
    return a0_fit


PROJECT_ROOT = Path(__file__).resolve().parent


try:
    import pydicom
except ImportError:
    pydicom = None

try:
    import nibabel as nib
except ImportError:
    nib = None


@dataclass(frozen=True)
class AcousticMaterial:
    label: int
    name: str
    sound_speed_m_s: float
    density_kg_m3: float
    alpha_db_mhz_cm: float


@dataclass(frozen=True)
class CTBuildConfig:
    dicom_dir: Path | None = None
    nifti_file: Path | None = None
    output_dir: Path = PROJECT_ROOT / "outputs" / "ct_acoustic_model_3d"
    air_threshold_hu: float = -500.0
    bone_threshold_hu: float = 300.0
    target_dx_m: float = 1.0e-3
    max_shape: int = 220
    max_preview_size: int = 420
    target_index: tuple[int, int, int] | None = None
    mapping_profile_path: Path | None = None
    mapping_profile: dict[str, object] | None = None
    materials: dict[str, AcousticMaterial] | None = None


MATERIALS = {
    "background": AcousticMaterial(
        label=0,
        name="air_or_coupling_background",
        sound_speed_m_s=1500.0,
        density_kg_m3=1000.0,
        alpha_db_mhz_cm=0.002,
    ),
    "soft_tissue": AcousticMaterial(
        label=1,
        name="soft_tissue_or_brain",
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


def active_materials(config: CTBuildConfig) -> dict[str, AcousticMaterial]:
    return MATERIALS if config.materials is None else config.materials


def load_mapping_profile(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Mapping profile not found: {path}")
    profile = json.loads(path.read_text(encoding="utf-8"))
    required = {"profile_id", "thresholds_hu", "materials", "evidence_source", "review_status"}
    missing = required - set(profile)
    if missing:
        raise ValueError(f"Mapping profile {path} is missing required keys: {sorted(missing)}")
    thresholds = profile["thresholds_hu"]
    if not isinstance(thresholds, dict) or "air_lt" not in thresholds or "bone_gte" not in thresholds:
        raise ValueError("Mapping profile thresholds_hu must contain air_lt and bone_gte.")
    materials_raw = profile["materials"]
    if not isinstance(materials_raw, dict):
        raise ValueError("Mapping profile materials must be an object.")
    for key in ("background", "soft_tissue", "skull"):
        if key not in materials_raw:
            raise ValueError(f"Mapping profile materials is missing {key}.")
        material = materials_raw[key]
        if not isinstance(material, dict):
            raise ValueError(f"Mapping profile material {key} must be an object.")
    mapping_type = profile.get("mapping_type")
    if mapping_type == "continuous_skull":
        cont_map = profile.get("continuous_mapping")
        if not isinstance(cont_map, dict):
            raise ValueError("Mapping profile with mapping_type 'continuous_skull' must contain a 'continuous_mapping' object.")
        for field in ("hu_min", "hu_max", "sound_speed_range_m_s", "density_range_kg_m3", "alpha_range_db_mhz_cm"):
            if field not in cont_map:
                raise ValueError(f"Mapping profile continuous_mapping is missing {field}.")
        try:
            float(cont_map["hu_min"])
            float(cont_map["hu_max"])
        except (TypeError, ValueError) as e:
            raise ValueError("continuous_mapping hu_min and hu_max must be numeric.") from e
        for range_field in ("sound_speed_range_m_s", "density_range_kg_m3", "alpha_range_db_mhz_cm"):
            r_val = cont_map[range_field]
            if not isinstance(r_val, (list, tuple)) or len(r_val) != 2:
                raise ValueError(f"continuous_mapping {range_field} must be a list/tuple of length 2.")
            try:
                float(r_val[0])
                float(r_val[1])
            except (TypeError, ValueError) as e:
                raise ValueError(f"continuous_mapping {range_field} values must be numeric.") from e
    if mapping_type in ("prestus_marsac_mueller", "prestus_fit_alpha_power_2"):
        source_map = profile.get("source_backed_mapping")
        if not isinstance(source_map, dict):
            raise ValueError(f"Mapping profile with mapping_type '{mapping_type}' must contain a 'source_backed_mapping' object.")
        for field in ("hu_min", "hu_max", "density", "sound_speed", "attenuation"):
            if field not in source_map:
                raise ValueError(f"source_backed_mapping is missing {field}.")
        float(source_map["hu_min"])
        float(source_map["hu_max"])
    return profile


def profile_materials(profile: dict[str, object]) -> dict[str, AcousticMaterial]:
    materials_raw = profile["materials"]
    assert isinstance(materials_raw, dict)
    materials: dict[str, AcousticMaterial] = {}
    for key, material_raw in materials_raw.items():
        assert isinstance(material_raw, dict)
        materials[str(key)] = AcousticMaterial(
            label=int(material_raw["label"]),
            name=str(material_raw["name"]),
            sound_speed_m_s=float(material_raw["sound_speed_m_s"]),
            density_kg_m3=float(material_raw["density_kg_m3"]),
            alpha_db_mhz_cm=float(material_raw["alpha_db_mhz_cm"]),
        )
    return materials


def apply_mapping_profile(config: CTBuildConfig, profile_path: Path | None) -> CTBuildConfig:
    if profile_path is None:
        return config
    profile = load_mapping_profile(profile_path)
    thresholds = profile["thresholds_hu"]
    assert isinstance(thresholds, dict)
    
    import sys
    # Check if CLI overrides were passed
    cli_bone = any(arg.startswith("--bone-threshold-hu") for arg in sys.argv)
    cli_air = any(arg.startswith("--air-threshold-hu") for arg in sys.argv)
    
    air_val = config.air_threshold_hu if cli_air else float(thresholds["air_lt"])
    bone_val = config.bone_threshold_hu if cli_bone else float(thresholds["bone_gte"])

    return replace(
        config,
        air_threshold_hu=air_val,
        bone_threshold_hu=bone_val,
        mapping_profile_path=profile_path,
        mapping_profile=profile,
        materials=profile_materials(profile),
    )


def discover_dicom_files(dicom_dir: Path) -> list[Path]:
    if not dicom_dir.exists():
        raise FileNotFoundError(
            f"DICOM folder not found: {dicom_dir}\n"
            "Put CT slices under D:\\AIprogram\\fus-sim\\data\\raw_ct\\case001 "
            "or pass --dicom-dir to an existing folder."
        )
    files = [path for path in dicom_dir.rglob("*") if path.is_file()]
    if not files:
        raise FileNotFoundError(f"No files found under DICOM folder: {dicom_dir}")
    return files


def read_ct_slices(dicom_dir: Path) -> tuple[np.ndarray, tuple[float, float, float], dict[str, object]]:
    if pydicom is None:
        raise ImportError(
            "pydicom is required to read DICOM CT data. Install it with:\n"
            "D:\\AIprogram\\python-envs\\kwave312\\Scripts\\python.exe -m pip install "
            "--cache-dir D:\\AIprogram\\fus-sim\\.tmp\\pip-cache pydicom==3.0.1"
        )

    slices = []
    skipped = 0
    for path in discover_dicom_files(dicom_dir):
        try:
            ds = pydicom.dcmread(str(path), force=True)
        except Exception:
            skipped += 1
            continue
        if not hasattr(ds, "PixelData"):
            skipped += 1
            continue
        if str(getattr(ds, "Modality", "CT")).upper() != "CT":
            skipped += 1
            continue
        try:
            pixel_array = ds.pixel_array.astype(np.float32)
        except Exception:
            skipped += 1
            continue

        slope = float(getattr(ds, "RescaleSlope", 1.0))
        intercept = float(getattr(ds, "RescaleIntercept", 0.0))
        hu = pixel_array * slope + intercept
        image_position = getattr(ds, "ImagePositionPatient", None)
        z_position = float(image_position[2]) if image_position is not None and len(image_position) >= 3 else None
        instance = int(getattr(ds, "InstanceNumber", len(slices)))
        slice_location = getattr(ds, "SliceLocation", None)
        sort_value = z_position if z_position is not None else float(slice_location) if slice_location is not None else float(instance)
        pixel_spacing = [float(v) for v in getattr(ds, "PixelSpacing", [1.0, 1.0])]
        slice_thickness = float(getattr(ds, "SliceThickness", 1.0))
        spacing_between = getattr(ds, "SpacingBetweenSlices", None)
        if spacing_between is not None:
            slice_thickness = abs(float(spacing_between))
        slices.append(
            {
                "hu": hu,
                "sort_value": sort_value,
                "instance": instance,
                "pixel_spacing": pixel_spacing,
                "slice_thickness": slice_thickness,
                "path": str(path),
            }
        )

    if not slices:
        raise ValueError(f"No readable CT DICOM slices found in {dicom_dir}. Skipped files: {skipped}")

    slices.sort(key=lambda item: (item["sort_value"], item["instance"]))
    rows_cols = {item["hu"].shape for item in slices}
    if len(rows_cols) != 1:
        raise ValueError(f"CT slices have inconsistent pixel dimensions: {sorted(rows_cols)}")

    volume_yxz = np.stack([item["hu"] for item in slices], axis=-1)
    volume_xyz = np.transpose(volume_yxz, (1, 0, 2)).astype(np.float32)
    spacing_y_mm, spacing_x_mm = slices[0]["pixel_spacing"]
    spacing_z_mm = estimate_z_spacing_mm(slices)
    spacing_m = (spacing_x_mm * 1e-3, spacing_y_mm * 1e-3, spacing_z_mm * 1e-3)
    metadata = {
        "source_type": "dicom",
        "source_path": str(dicom_dir),
        "dicom_dir": str(dicom_dir),
        "slice_count": len(slices),
        "skipped_file_count": skipped,
        "first_slice": slices[0]["path"],
        "last_slice": slices[-1]["path"],
        "original_shape_xyz": list(volume_xyz.shape),
        "original_spacing_mm_xyz": [spacing_x_mm, spacing_y_mm, spacing_z_mm],
        "hu_range": [float(volume_xyz.min()), float(volume_xyz.max())],
    }
    return volume_xyz, spacing_m, metadata


def read_nifti_file(nifti_file: Path) -> tuple[np.ndarray, tuple[float, float, float], dict[str, object]]:
    if nib is None:
        raise ImportError(
            "nibabel is required to read NIfTI CT data. Install it with:\n"
            "D:\\AIprogram\\python-envs\\kwave312\\Scripts\\python.exe -m pip install "
            "--cache-dir D:\\AIprogram\\fus-sim\\.tmp\\pip-cache nibabel==5.4.2"
        )
    if not nifti_file.exists():
        raise FileNotFoundError(f"NIfTI file not found: {nifti_file}")
    if nifti_file.suffix.lower() != ".nii" and not nifti_file.name.lower().endswith(".nii.gz"):
        raise ValueError(f"Unsupported NIfTI extension for {nifti_file}; expected .nii or .nii.gz")

    image = nib.as_closest_canonical(nib.load(str(nifti_file)))
    header = image.header
    zooms_mm = tuple(float(value) for value in header.get_zooms()[:3])
    if len(zooms_mm) != 3 or any(value <= 0 for value in zooms_mm):
        raise ValueError(f"Invalid NIfTI voxel spacing in {nifti_file}: {zooms_mm}")

    data = image.get_fdata(dtype=np.float32)
    if data.ndim == 4 and data.shape[3] == 1:
        data = data[:, :, :, 0]
    if data.ndim != 3:
        raise ValueError(f"NIfTI image must be 3D, got shape {data.shape}")

    slope, intercept = header.get_slope_inter()
    spacing_m = tuple(value * 1e-3 for value in zooms_mm)
    metadata = {
        "source_type": "nifti",
        "source_path": str(nifti_file),
        "nifti_file": str(nifti_file),
        "original_shape_xyz": list(data.shape),
        "original_spacing_mm_xyz": list(zooms_mm),
        "data_dtype": str(header.get_data_dtype()),
        "slope": None if slope is None else float(slope),
        "intercept": None if intercept is None else float(intercept),
        "affine": image.affine.astype(float).tolist(),
        "hu_range": [float(np.nanmin(data)), float(np.nanmax(data))],
        "slice_count": int(data.shape[2]),
    }
    return np.asarray(data, dtype=np.float32), spacing_m, metadata


def estimate_z_spacing_mm(slices: list[dict[str, object]]) -> float:
    values = np.array([float(item["sort_value"]) for item in slices], dtype=float)
    diffs = np.diff(np.sort(values))
    diffs = np.abs(diffs[diffs != 0])
    if diffs.size:
        return float(np.median(diffs))
    return float(slices[0]["slice_thickness"])


def resample_to_isotropic(
    hu_xyz: np.ndarray,
    spacing_m: tuple[float, float, float],
    target_dx_m: float,
    max_shape: int,
) -> tuple[np.ndarray, float, dict[str, object]]:
    if target_dx_m <= 0:
        raise ValueError("--target-dx-mm must be positive.")
    if max_shape <= 0:
        raise ValueError("--max-shape must be positive.")

    shape = np.array(hu_xyz.shape, dtype=float)
    spacing = np.array(spacing_m, dtype=float)
    physical_size_m = shape * spacing
    requested_shape = np.maximum(1, np.rint(physical_size_m / target_dx_m)).astype(int)
    dx_m = float(target_dx_m)
    if int(requested_shape.max()) > max_shape:
        dx_m = float(physical_size_m.max() / max_shape)

    zoom = tuple(float(value) for value in spacing / dx_m)
    estimated_shape = np.maximum(1, np.rint(shape * np.array(zoom))).astype(int)
    metadata = {
        "requested_target_dx_m": float(target_dx_m),
        "max_shape": int(max_shape),
        "zoom_xyz": [float(v) for v in zoom],
        "isotropic_dx_m": dx_m,
        "original_shape_xyz": [int(v) for v in hu_xyz.shape],
        "estimated_resampled_shape_xyz": [int(v) for v in estimated_shape],
    }

    if all(abs(factor - 1.0) < 0.05 for factor in zoom):
        metadata.update({"resampled": False, "resampled_shape_xyz": [int(v) for v in hu_xyz.shape]})
        return hu_xyz.astype(np.float32, copy=False), dx_m, metadata

    resampled = ndimage.zoom(hu_xyz, zoom=zoom, order=1).astype(np.float32)
    metadata.update(
        {
            "resampled": True,
            "resampled_shape_xyz": [int(v) for v in resampled.shape],
        }
    )
    return (
        resampled,
        dx_m,
        metadata,
    )


def labels_from_hu(hu_xyz: np.ndarray, config: CTBuildConfig) -> np.ndarray:
    materials = active_materials(config)
    labels = np.full(hu_xyz.shape, materials["soft_tissue"].label, dtype=np.uint8)
    labels[hu_xyz < config.air_threshold_hu] = materials["background"].label
    labels[hu_xyz >= config.bone_threshold_hu] = materials["skull"].label
    return labels


def material_property_volume(labels: np.ndarray, attribute: str, materials: dict[str, AcousticMaterial]) -> np.ndarray:
    values = np.zeros(labels.shape, dtype=np.float32)
    for material in materials.values():
        values[labels == material.label] = getattr(material, attribute)
    return values


def continuous_property_volume(
    hu_xyz: np.ndarray,
    labels: np.ndarray,
    attribute: str,
    config: CTBuildConfig,
) -> np.ndarray:
    materials = active_materials(config)
    values = material_property_volume(labels, attribute, materials)
    
    profile = config.mapping_profile
    if profile is None or profile.get("mapping_type") != "continuous_skull":
        return values

    cont_map = profile.get("continuous_mapping")
    if not isinstance(cont_map, dict):
        return values
        
    hu_min = float(cont_map["hu_min"])
    hu_max = float(cont_map["hu_max"])
    
    if attribute == "sound_speed_m_s":
        p_range = cont_map["sound_speed_range_m_s"]
    elif attribute == "density_kg_m3":
        p_range = cont_map["density_range_kg_m3"]
    elif attribute == "alpha_db_mhz_cm":
        p_range = cont_map["alpha_range_db_mhz_cm"]
    else:
        raise ValueError(f"Unknown acoustic property: {attribute}")
        
    p_min = float(p_range[0])
    p_max = float(p_range[1])
    
    skull_mask = (labels == materials["skull"].label)
    if not np.any(skull_mask):
        return values
        
    hu_skull = hu_xyz[skull_mask]
    hu_clipped = np.clip(hu_skull, hu_min, hu_max)
    
    if hu_max > hu_min:
        t = (hu_clipped - hu_min) / (hu_max - hu_min)
    else:
        t = np.zeros_like(hu_clipped)
        
    values[skull_mask] = p_min + t * (p_max - p_min)
    return values


def prestus_marsac_mueller_property_volume(
    hu_xyz: np.ndarray,
    labels: np.ndarray,
    attribute: str,
    config: CTBuildConfig,
) -> np.ndarray:
    materials = active_materials(config)
    values = material_property_volume(labels, attribute, materials)

    profile = config.mapping_profile
    if profile is None or profile.get("mapping_type") not in ("prestus_marsac_mueller", "prestus_fit_alpha_power_2"):
        return values
    source_map = profile.get("source_backed_mapping")
    if not isinstance(source_map, dict):
        return values

    skull_mask = labels == materials["skull"].label
    if not np.any(skull_mask):
        return values

    hu_min = float(source_map["hu_min"])
    hu_max = float(source_map["hu_max"])
    hu_clipped = np.clip(hu_xyz[skull_mask], hu_min, hu_max)
    if hu_max > hu_min:
        t = (hu_clipped - hu_min) / (hu_max - hu_min)
    else:
        t = np.zeros_like(hu_clipped)

    density_cfg = source_map["density"]
    sound_cfg = source_map["sound_speed"]
    attenuation_cfg = source_map["attenuation"]
    if not isinstance(density_cfg, dict) or not isinstance(sound_cfg, dict) or not isinstance(attenuation_cfg, dict):
        raise ValueError("source_backed_mapping density, sound_speed, and attenuation must be objects.")

    rho_water = float(density_cfg["rho_water_kg_m3"])
    rho_bone = float(density_cfg["rho_bone_kg_m3"])
    density_skull = rho_water + (rho_bone - rho_water) * t

    if attribute == "density_kg_m3":
        values[skull_mask] = density_skull
        return values

    if attribute == "sound_speed_m_s":
        c_water = float(sound_cfg["c_water_m_s"])
        c_skull = float(sound_cfg["c_skull_m_s"])
        rho_water_s = float(sound_cfg["rho_water_kg_m3"])
        rho_bone_s = float(sound_cfg["rho_bone_kg_m3"])
        if rho_bone_s > rho_water_s:
            rho_t = (density_skull - rho_water_s) / (rho_bone_s - rho_water_s)
        else:
            rho_t = np.zeros_like(density_skull)
        values[skull_mask] = c_water + (c_skull - c_water) * rho_t
        return values

    if attribute == "alpha_db_mhz_cm":
        alpha_min = float(attenuation_cfg["alpha_min_db_cm_at_500khz"])
        alpha_max = float(attenuation_cfg["alpha_max_db_cm_at_500khz"])
        alpha_power = float(attenuation_cfg.get("alpha_power", 1.0))
        alpha_at_500khz = alpha_min + (alpha_max - alpha_min) * np.sqrt(1.0 - t)
        
        if profile.get("mapping_type") == "prestus_fit_alpha_power_2":
            # Rescale the prefactor using fitPowerLawParamsMulti
            c_water = float(sound_cfg["c_water_m_s"])
            c_skull = float(sound_cfg["c_skull_m_s"])
            rho_water_s = float(sound_cfg["rho_water_kg_m3"])
            rho_bone_s = float(sound_cfg["rho_bone_kg_m3"])
            if rho_bone_s > rho_water_s:
                rho_t = (density_skull - rho_water_s) / (rho_bone_s - rho_water_s)
            else:
                rho_t = np.zeros_like(density_skull)
            c0_skull = c_water + (c_skull - c_water) * rho_t
            
            # Original prefactor a0 assuming y = alpha_power
            a0_orig = alpha_at_500khz / (0.5 ** alpha_power)
            
            y_ref = float(profile.get("alpha_semantics", {}).get("alpha_power", 2.0))
            f_ref = float(profile.get("alpha_semantics", {}).get("reference_frequency_hz", 500000.0))
            
            a0_fit = fit_power_law_params_multi(
                a0=a0_orig,
                y=np.full_like(a0_orig, alpha_power),
                c0=c0_skull,
                f_ref=f_ref,
                y_ref=y_ref
            )
            values[skull_mask] = a0_fit
        else:
            if alpha_power == 0:
                values[skull_mask] = alpha_at_500khz
            else:
                values[skull_mask] = alpha_at_500khz / (0.5 ** alpha_power)
        return values

    raise ValueError(f"Unknown acoustic property: {attribute}")


def alpha_semantics_metadata(config: CTBuildConfig) -> dict[str, object]:
    profile = config.mapping_profile
    if profile is None:
        return {
            "alpha_power": None,
            "alpha_mode": None,
            "alpha_coeff_kind": "unspecified_legacy_profile",
            "alpha_coeff_unit": "dB/MHz/cm",
            "reference_frequency_hz": None,
            "source_route": "first_pass_threshold_materials",
            "source_locator": None,
            "status": "legacy_unspecified",
            "notes": [
                "Legacy profile does not explicitly define alpha_power or whether alpha_coeff is alpha0 or alpha(f)."
            ],
        }
    semantics = profile.get("alpha_semantics")
    if isinstance(semantics, dict):
        return semantics
    return {
        "alpha_power": None,
        "alpha_mode": None,
        "alpha_coeff_kind": "unspecified_profile_alpha_coeff",
        "alpha_coeff_unit": "dB/MHz/cm",
        "reference_frequency_hz": None,
        "source_route": profile.get("profile_id"),
        "source_locator": profile.get("evidence_source"),
        "status": "missing_alpha_semantics",
        "notes": [
            "Profile does not contain an alpha_semantics block; alpha_coeff is retained for backward compatibility only."
        ],
    }


def alpha_semantics_npz_fields(config: CTBuildConfig) -> dict[str, np.ndarray]:
    semantics = alpha_semantics_metadata(config)
    def str_arr(value: object) -> np.ndarray:
        return np.array("" if value is None else str(value))
    alpha_power = semantics.get("alpha_power")
    try:
        alpha_power_value = np.nan if alpha_power is None else float(alpha_power)
    except (TypeError, ValueError):
        alpha_power_value = np.nan
    return {
        "alpha_power": np.array(alpha_power_value, dtype=np.float32),
        "alpha_mode": str_arr(semantics.get("alpha_mode")),
        "alpha_unit_semantics": str_arr(semantics.get("alpha_coeff_unit")),
        "alpha_coeff_kind": str_arr(semantics.get("alpha_coeff_kind")),
        "alpha_source_route": str_arr(semantics.get("source_route")),
        "alpha_semantics_status": str_arr(semantics.get("status")),
        "alpha_pressure_allowed": np.array(bool(semantics.get("pressure_allowed", False)), dtype=np.bool_),
    }


def choose_target_index(labels: np.ndarray, config: CTBuildConfig) -> np.ndarray:
    materials = active_materials(config)
    if config.target_index is not None:
        target = np.array(config.target_index, dtype=np.int32)
        if np.any(target < 0) or np.any(target >= np.array(labels.shape)):
            raise ValueError(f"--target-index {target.tolist()} is outside volume shape {labels.shape}.")
        return target

    soft = np.argwhere(labels == materials["soft_tissue"].label)
    if soft.size:
        return np.rint(np.mean(soft, axis=0)).astype(np.int32)
    return np.array([(size - 1) // 2 for size in labels.shape], dtype=np.int32)


def normalize_to_uint8(values: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    scaled = (np.clip(values, vmin, vmax) - vmin) / max(vmax - vmin, 1e-12)
    return (scaled * 255).astype(np.uint8)


def label_to_rgb(slice_2d: np.ndarray) -> Image.Image:
    colors = np.array(
        [
            [31, 43, 77],
            [66, 160, 121],
            [218, 204, 137],
        ],
        dtype=np.uint8,
    )
    return Image.fromarray(colors[np.clip(slice_2d, 0, len(colors) - 1)], mode="RGB")


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


def annotate(image: Image.Image, title: str, target_xy: tuple[int, int] | None = None, max_size: int = 420) -> Image.Image:
    scale = max(1, min(4, max_size // max(image.width, image.height)))
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


def save_slice_previews(output_dir: Path, hu: np.ndarray, labels: np.ndarray, sound_speed: np.ndarray, target: np.ndarray, config: CTBuildConfig) -> None:
    tx, ty, tz = [int(v) for v in target]

    hu_images = [
        annotate(Image.fromarray(normalize_to_uint8(hu[:, :, tz].T, -1000, 2000), mode="L").convert("RGB"), "Axial CT HU", (tx, ty), config.max_preview_size),
        annotate(Image.fromarray(normalize_to_uint8(hu[:, ty, :].T, -1000, 2000), mode="L").convert("RGB"), "Coronal CT HU", (tx, tz), config.max_preview_size),
        annotate(Image.fromarray(normalize_to_uint8(hu[tx, :, :].T, -1000, 2000), mode="L").convert("RGB"), "Sagittal CT HU", (ty, tz), config.max_preview_size),
    ]
    make_contact_sheet(hu_images).save(output_dir / "ct_hu_slices.png")

    label_images = [
        annotate(label_to_rgb(labels[:, :, tz].T), "Axial labels", (tx, ty), config.max_preview_size),
        annotate(label_to_rgb(labels[:, ty, :].T), "Coronal labels", (tx, tz), config.max_preview_size),
        annotate(label_to_rgb(labels[tx, :, :].T), "Sagittal labels", (ty, tz), config.max_preview_size),
    ]
    make_contact_sheet(label_images).save(output_dir / "label_slices.png")

    speed_images = [
        annotate(scalar_to_rgb(sound_speed[:, :, tz].T), "Axial sound speed", (tx, ty), config.max_preview_size),
        annotate(scalar_to_rgb(sound_speed[:, ty, :].T), "Coronal sound speed", (tx, tz), config.max_preview_size),
        annotate(scalar_to_rgb(sound_speed[tx, :, :].T), "Sagittal sound speed", (ty, tz), config.max_preview_size),
    ]
    make_contact_sheet(speed_images).save(output_dir / "sound_speed_slices.png")


def save_summary(
    output_dir: Path,
    config: CTBuildConfig,
    metadata: dict[str, object],
    resample_metadata: dict[str, object],
    labels: np.ndarray,
    hu: np.ndarray,
    sound_speed: np.ndarray,
    density: np.ndarray,
    alpha_coeff: np.ndarray,
    dx_m: float,
    target: np.ndarray,
) -> None:
    materials = active_materials(config)
    counts = {material.name: int(np.sum(labels == material.label)) for material in materials.values()}
    profile_summary = None
    if config.mapping_profile is not None:
        profile_summary = {
            "path": None if config.mapping_profile_path is None else str(config.mapping_profile_path),
            "profile_id": config.mapping_profile.get("profile_id"),
            "mapping_type": config.mapping_profile.get("mapping_type"),
            "evidence_source": config.mapping_profile.get("evidence_source"),
            "review_status": config.mapping_profile.get("review_status"),
            "notes": config.mapping_profile.get("notes", []),
            "alpha_semantics": alpha_semantics_metadata(config),
        }
    summary = {
        "description": "CT-derived 3D acoustic model using HU acoustic mapping profile" if profile_summary else "CT-derived 3D acoustic model using first-pass HU thresholds",
        "source": metadata,
        "resampling": resample_metadata,
        "mapping_profile": profile_summary,
        "thresholds_hu": {
            "air_background_lt": config.air_threshold_hu,
            "bone_gte": config.bone_threshold_hu,
        },
        "grid_shape": list(labels.shape),
        "dx_m": dx_m,
        "target_index_ijk": target.astype(int).tolist(),
        "materials": {key: asdict(value) for key, value in materials.items()},
        "voxel_counts": counts,
        "hu_range": [float(hu.min()), float(hu.max())],
        "sound_speed_range_m_s": [float(sound_speed.min()), float(sound_speed.max())],
        "density_range_kg_m3": [float(density.min()), float(density.max())],
        "alpha_range_db_mhz_cm": [float(alpha_coeff.min()), float(alpha_coeff.max())],
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    with (output_dir / "summary.txt").open("w", encoding="utf-8") as handle:
        handle.write("CT-derived 3D acoustic model\n")
        handle.write(f"source_type={metadata.get('source_type', 'unknown')}\n")
        handle.write(f"source_path={metadata.get('source_path', '')}\n")
        handle.write(f"slice_count={metadata.get('slice_count', labels.shape[2])}\n")
        handle.write(f"original_shape_xyz={metadata.get('original_shape_xyz')}\n")
        handle.write(f"original_spacing_mm_xyz={metadata.get('original_spacing_mm_xyz')}\n")
        handle.write(f"target_dx_mm={config.target_dx_m * 1e3:.3f}\n")
        handle.write(f"max_shape={config.max_shape}\n")
        if profile_summary is not None:
            handle.write(f"mapping_profile_path={profile_summary['path']}\n")
            handle.write(f"mapping_profile_id={profile_summary['profile_id']}\n")
            handle.write(f"mapping_profile_evidence_source={profile_summary['evidence_source']}\n")
            handle.write(f"mapping_profile_review_status={profile_summary['review_status']}\n")
            handle.write(f"alpha_semantics={json.dumps(profile_summary['alpha_semantics'], ensure_ascii=False)}\n")
        handle.write(f"grid_shape={labels.shape}\n")
        handle.write(f"dx_mm={dx_m * 1e3:.3f}\n")
        handle.write(f"target_index_ijk={tuple(int(v) for v in target)}\n")
        handle.write(f"hu_range={float(hu.min()):.1f},{float(hu.max()):.1f}\n")
        handle.write(f"resampled={resample_metadata['resampled']}\n")
        handle.write(f"zoom_xyz={resample_metadata['zoom_xyz']}\n")
        for material in materials.values():
            handle.write(
                f"material={material.label},{material.name},"
                f"c={material.sound_speed_m_s:.1f},rho={material.density_kg_m3:.1f},"
                f"alpha={material.alpha_db_mhz_cm:.3f}\n"
            )
        for name, count in counts.items():
            handle.write(f"voxel_count_{name}={count}\n")


def save_model(config: CTBuildConfig) -> None:
    if (config.dicom_dir is None) == (config.nifti_file is None):
        raise ValueError("Pass exactly one input source: --dicom-dir or --nifti-file.")

    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    if config.nifti_file is not None:
        hu_raw, spacing_m, metadata = read_nifti_file(config.nifti_file)
    elif config.dicom_dir is not None:
        hu_raw, spacing_m, metadata = read_ct_slices(config.dicom_dir)
    else:
        raise ValueError("No CT input source was provided.")

    hu, dx_m, resample_metadata = resample_to_isotropic(
        hu_raw,
        spacing_m,
        target_dx_m=config.target_dx_m,
        max_shape=config.max_shape,
    )
    labels = labels_from_hu(hu, config)
    target = choose_target_index(labels, config)
    materials = active_materials(config)
    profile = config.mapping_profile
    if profile is not None and profile.get("mapping_type") == "continuous_skull":
        sound_speed = continuous_property_volume(hu, labels, "sound_speed_m_s", config)
        density = continuous_property_volume(hu, labels, "density_kg_m3", config)
        alpha_coeff = continuous_property_volume(hu, labels, "alpha_db_mhz_cm", config)
    elif profile is not None and profile.get("mapping_type") in ("prestus_marsac_mueller", "prestus_fit_alpha_power_2"):
        sound_speed = prestus_marsac_mueller_property_volume(hu, labels, "sound_speed_m_s", config)
        density = prestus_marsac_mueller_property_volume(hu, labels, "density_kg_m3", config)
        alpha_coeff = prestus_marsac_mueller_property_volume(hu, labels, "alpha_db_mhz_cm", config)
    else:
        sound_speed = material_property_volume(labels, "sound_speed_m_s", materials)
        density = material_property_volume(labels, "density_kg_m3", materials)
        alpha_coeff = material_property_volume(labels, "alpha_db_mhz_cm", materials)

    if not np.any(labels == materials["soft_tissue"].label):
        raise ValueError("CT thresholding found no soft tissue voxels. Adjust thresholds.")
    if not np.any(labels == materials["skull"].label):
        raise ValueError("CT thresholding found no skull voxels. Adjust --bone-threshold-hu.")

    alpha_fields = alpha_semantics_npz_fields(config)
    np.savez_compressed(
        output_dir / "acoustic_model_3d.npz",
        labels=labels,
        hu=hu.astype(np.float32),
        sound_speed=sound_speed,
        density=density,
        alpha_coeff=alpha_coeff,
        **alpha_fields,
        dx_m=np.array(dx_m, dtype=np.float32),
        target_index_ijk=target.astype(np.int32),
        original_spacing_m_xyz=np.array(spacing_m, dtype=np.float32),
    )
    save_slice_previews(output_dir, hu, labels, sound_speed, target, config)
    save_summary(output_dir, config, metadata, resample_metadata, labels, hu, sound_speed, density, alpha_coeff, dx_m, target)


def parse_target_index(value: str) -> tuple[int, int, int]:
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("--target-index must be formatted as i,j,k")
    return tuple(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert CT DICOM or NIfTI data into a k-Wave-compatible 3D acoustic model.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--dicom-dir", default=None, help="Folder containing CT DICOM slices.")
    input_group.add_argument("--nifti-file", default=None, help="Path to a CT NIfTI file (.nii or .nii.gz).")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs" / "ct_acoustic_model_3d"),
        help="Output directory for the acoustic model and preview images.",
    )
    parser.add_argument("--air-threshold-hu", type=float, default=-500.0, help="HU threshold below which voxels are background/coupling.")
    parser.add_argument("--bone-threshold-hu", type=float, default=300.0, help="HU threshold at or above which voxels are skull bone.")
    parser.add_argument("--mapping-profile", default=None, help="Optional acoustic mapping profile JSON. Overrides threshold and material defaults.")
    parser.add_argument("--target-dx-mm", type=float, default=1.0, help="Requested isotropic output voxel size in millimeters.")
    parser.add_argument("--max-shape", type=int, default=220, help="Maximum dimension after isotropic resampling; voxel size is increased if needed.")
    parser.add_argument("--target-index", type=parse_target_index, default=None, help="Optional target index formatted as i,j,k.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        config = CTBuildConfig(
            dicom_dir=None if args.dicom_dir is None else Path(args.dicom_dir),
            nifti_file=None if args.nifti_file is None else Path(args.nifti_file),
            output_dir=Path(args.output_dir),
            air_threshold_hu=args.air_threshold_hu,
            bone_threshold_hu=args.bone_threshold_hu,
            target_dx_m=args.target_dx_mm * 1e-3,
            max_shape=args.max_shape,
            target_index=args.target_index,
        )
        save_model(apply_mapping_profile(config, None if args.mapping_profile is None else Path(args.mapping_profile)))
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
