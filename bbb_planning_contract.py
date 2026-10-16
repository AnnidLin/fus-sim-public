from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_SCHEMA = ROOT / "planning_contracts" / "bbb_simulation_plan.schema.json"
DEFAULT_EXAMPLE = ROOT / "planning_contracts" / "examples" / "case079_h1_bbb_simulation_plan.json"


class ContractError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError(f"{path}: root must be an object")
    return value


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    raise ContractError(f"unsupported schema type: {expected}")


def validate_schema_subset(value: Any, schema: dict[str, Any], root: dict[str, Any], location: str = "$") -> None:
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            raise ContractError(f"{location}: unsupported reference {ref}")
        definition = root["$defs"][ref.split("/")[-1]]
        validate_schema_subset(value, definition, root, location)
        return

    if "const" in schema and value != schema["const"]:
        raise ContractError(f"{location}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise ContractError(f"{location}: {value!r} is outside allowed values")

    expected = schema.get("type")
    if expected is not None:
        options = expected if isinstance(expected, list) else [expected]
        if not any(_matches_type(value, option) for option in options):
            raise ContractError(f"{location}: expected type {options}, got {type(value).__name__}")
        if value is None:
            return

    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = [key for key in required if key not in value]
        if missing:
            raise ContractError(f"{location}: missing required fields {missing}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise ContractError(f"{location}: unexpected fields {extra}")
        for key, child in value.items():
            if key in properties:
                validate_schema_subset(child, properties[key], root, f"{location}.{key}")

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ContractError(f"{location}: too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ContractError(f"{location}: too many items")
        if "items" in schema:
            for index, child in enumerate(value):
                validate_schema_subset(child, schema["items"], root, f"{location}[{index}]")

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise ContractError(f"{location}: string is too short")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            raise ContractError(f"{location}: string does not match {schema['pattern']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ContractError(f"{location}: value is below minimum")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            raise ContractError(f"{location}: value is not above exclusive minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise ContractError(f"{location}: value is above maximum")


def _sphere_voxel_count(radius_m: float, spacing_m_ijk: list[float]) -> int:
    extents = [math.ceil(radius_m / spacing) for spacing in spacing_m_ijk]
    count = 0
    for i in range(-extents[0], extents[0] + 1):
        for j in range(-extents[1], extents[1] + 1):
            for k in range(-extents[2], extents[2] + 1):
                distance_sq = sum(
                    (offset * spacing) ** 2
                    for offset, spacing in zip((i, j, k), spacing_m_ijk, strict=True)
                )
                if distance_sq <= radius_m**2 + 1e-18:
                    count += 1
    return count


def _require_index_in_bounds(index: list[int], shape: list[int], name: str) -> None:
    if any(size <= 0 for size in shape):
        raise ContractError("patient_model.shape_ijk values must be positive")
    if any(position < 0 or position >= size for position, size in zip(index, shape, strict=True)):
        raise ContractError(f"{name} is outside patient_model.shape_ijk")


def validate_semantics(plan: dict[str, Any]) -> None:
    patient = plan["patient_model"]
    roi = plan["target_roi"]
    transducer = plan["transducer_plan"]
    exposure = plan["exposure_protocol"]
    metrics = plan["plan_metrics"]

    shape = patient["shape_ijk"]
    crop = patient["crop_origin_ijk"]
    expected_full = [local + origin for local, origin in zip(roi["center_local_ijk"], crop, strict=True)]
    if expected_full != roi["center_full_ijk"]:
        raise ContractError("target ROI coordinate mismatch: full must equal local + crop_origin")

    for name, index in (
        ("target_roi.center_full_ijk", roi["center_full_ijk"]),
        ("transducer_plan.target_full_ijk", transducer["target_full_ijk"]),
        ("transducer_plan.source_center_full_ijk", transducer["source_center_full_ijk"]),
        ("transducer_plan.entry_full_ijk", transducer["entry_full_ijk"]),
    ):
        _require_index_in_bounds(index, shape, name)

    if transducer["target_full_ijk"] != roi["center_full_ijk"]:
        raise ContractError("transducer target must equal ROI center for this single-focus v1 contract")

    world = patient["world_mapping"]
    affine = world.get("affine_ijk_to_world_mm")
    if world["status"] == "unavailable" and affine is not None:
        raise ContractError("unavailable world mapping cannot contain an affine")
    if world["status"] == "available" and affine is None:
        raise ContractError("available world mapping requires a 4x4 affine")

    generation = roi["generation"]
    if roi["roi_kind"] == "synthetic_sphere_proxy":
        if roi["anatomical_status"] != "synthetic_not_anatomical":
            raise ContractError("synthetic ROI cannot be marked as anatomical")
        if generation["method"] != "sphere_from_center" or generation["radius_m"] is None:
            raise ContractError("synthetic sphere requires sphere_from_center and radius_m")
        if generation["mask_path"] is not None:
            raise ContractError("generated synthetic sphere must not claim a source mask path")
        expected_voxels = _sphere_voxel_count(generation["radius_m"], patient["spacing_m_ijk"])
        if roi["voxel_count"] != expected_voxels:
            raise ContractError(f"synthetic sphere voxel_count must be {expected_voxels}")
    elif generation["method"] == "loaded_mask" and not generation["mask_path"]:
        raise ContractError("loaded ROI requires mask_path")

    protocol_fields = ("prf_hz", "duty_cycle_fraction", "total_sonication_time_s")
    if exposure["status"] == "calibration_reference_only":
        if exposure["pressure_semantics"] != "source_excitation_not_insitu_dose":
            raise ContractError("calibration reference must use source-excitation pressure semantics")
        if any(exposure[field] is not None for field in protocol_fields):
            raise ContractError("calibration reference must not invent BBB pulse-train fields")
    if exposure["microbubble"]["status"] == "not_specified":
        if any(exposure["microbubble"][field] is not None for field in ("product", "dose", "timing")):
            raise ContractError("unspecified microbubble protocol must use null details")

    metric_names = [key for key in metrics if key not in ("status", "clinical_safety_claim")]
    if metrics["status"] == "not_computed" and any(metrics[key] is not None for key in metric_names):
        raise ContractError("not_computed metrics must all be null")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_files(plan: dict[str, Any], project_root: Path) -> None:
    checks = (
        (plan["patient_model"]["model_path"], plan["patient_model"]["model_sha256"], "patient model"),
        (plan["transducer_plan"]["entry_plan_path"], plan["transducer_plan"]["entry_plan_sha256"], "entry plan"),
    )
    for relative, expected_hash, label in checks:
        path = project_root / relative
        if not path.is_file():
            raise ContractError(f"{label} file does not exist: {relative}")
        if _sha256(path) != expected_hash:
            raise ContractError(f"{label} SHA256 mismatch: {relative}")


def validate_contract(plan: dict[str, Any], schema: dict[str, Any], verify_file_hashes: bool = False) -> None:
    validate_schema_subset(plan, schema, schema)
    validate_semantics(plan)
    if verify_file_hashes:
        verify_files(plan, ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a fus-sim BBB planning contract.")
    parser.add_argument("--plan", type=Path, default=DEFAULT_EXAMPLE)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--verify-files", action="store_true")
    args = parser.parse_args()

    plan = load_json(args.plan)
    schema = load_json(args.schema)
    validate_contract(plan, schema, verify_file_hashes=args.verify_files)
    print(json.dumps({
        "status": "pass",
        "plan_id": plan["plan_id"],
        "schema_version": plan["schema_version"],
        "file_hashes_verified": args.verify_files,
        "pressure_executed": False,
        "claim_boundary": "interface_consistency_only",
    }, indent=2))


if __name__ == "__main__":
    main()
