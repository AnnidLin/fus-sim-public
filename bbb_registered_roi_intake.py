from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from bbb_planning_contract import DEFAULT_EXAMPLE, DEFAULT_SCHEMA, load_json, validate_contract
from bbb_roi import ROIError, load_roi_mask, summarize_roi


ROOT = Path(__file__).resolve().parent


class RegisteredROIIntakeError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_project_file(relative_path: str, project_root: Path) -> Path:
    path = (project_root / relative_path).resolve()
    try:
        path.relative_to(project_root.resolve())
    except ValueError as error:
        raise RegisteredROIIntakeError(f"path escapes project root: {relative_path}") from error
    if not path.is_file():
        raise RegisteredROIIntakeError(f"required file does not exist: {relative_path}")
    return path


def validated_affine(value: Any, label: str) -> np.ndarray:
    affine = np.asarray(value, dtype=np.float64)
    if affine.shape != (4, 4) or not np.all(np.isfinite(affine)):
        raise RegisteredROIIntakeError(f"{label} must be a finite 4x4 matrix")
    if not np.allclose(affine[3], [0.0, 0.0, 0.0, 1.0], rtol=0.0, atol=1e-8):
        raise RegisteredROIIntakeError(f"{label} must have a homogeneous final row")
    if abs(float(np.linalg.det(affine[:3, :3]))) <= 1e-12:
        raise RegisteredROIIntakeError(f"{label} spatial transform must be invertible")
    return affine


def validate_registration_sidecar(
    sidecar: dict[str, Any],
    plan: dict[str, Any],
    mask_path: Path,
    project_root: Path,
) -> np.ndarray:
    if sidecar.get("registration_version") != "1.0.0":
        raise RegisteredROIIntakeError("registration_version must be 1.0.0")
    if sidecar.get("case_id") != plan["patient_model"]["case_id"]:
        raise RegisteredROIIntakeError("registration sidecar case_id mismatch")
    if sidecar.get("roi_id") != plan["target_roi"]["roi_id"]:
        raise RegisteredROIIntakeError("registration sidecar roi_id mismatch")
    if sidecar.get("interpolation") != "nearest_neighbor":
        raise RegisteredROIIntakeError("label masks require nearest_neighbor interpolation")
    if not isinstance(sidecar.get("source_image_id"), str) or not sidecar["source_image_id"].strip():
        raise RegisteredROIIntakeError("source_image_id must be recorded")
    actual_hash = sha256_file(mask_path)
    if sidecar.get("roi_mask_sha256") != actual_hash:
        raise RegisteredROIIntakeError("ROI mask SHA256 mismatch")

    plan_affine = validated_affine(
        plan["patient_model"]["world_mapping"]["affine_ijk_to_world_mm"], "patient affine"
    )
    mask_affine = validated_affine(sidecar.get("mask_affine_ijk_to_world_mm"), "mask affine")
    if not np.allclose(mask_affine, plan_affine, rtol=1e-6, atol=1e-5):
        raise RegisteredROIIntakeError("mask affine does not match the patient-model affine")

    method = sidecar.get("registration_method")
    transform = sidecar.get("transform")
    if not isinstance(transform, dict):
        raise RegisteredROIIntakeError("registration transform record is required")
    if method == "native_patient_grid":
        if transform.get("status") != "identity" or transform.get("path") is not None:
            raise RegisteredROIIntakeError("native_patient_grid requires an identity transform")
    elif method == "resampled_to_patient_grid":
        if transform.get("status") != "applied":
            raise RegisteredROIIntakeError("resampled_to_patient_grid requires an applied transform")
        transform_path = transform.get("path")
        if not isinstance(transform_path, str) or not isinstance(transform.get("sha256"), str):
            raise RegisteredROIIntakeError("applied transform path and SHA256 are required")
        resolved_transform = resolve_project_file(transform_path, project_root)
        if sha256_file(resolved_transform) != transform["sha256"]:
            raise RegisteredROIIntakeError("registration transform SHA256 mismatch")
    else:
        raise RegisteredROIIntakeError("unsupported registration_method")
    return plan_affine


def audit_registered_roi(
    plan: dict[str, Any],
    schema: dict[str, Any],
    project_root: Path = ROOT,
    sidecar: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_contract(plan, schema, verify_file_hashes=False)
    patient = plan["patient_model"]
    roi = plan["target_roi"]
    blockers = []
    if roi["anatomical_status"] != "registered_anatomical":
        blockers.append("roi_contract_is_not_registered_anatomy")
    if roi["generation"]["method"] != "loaded_mask" or not roi["generation"]["mask_path"]:
        blockers.append("registered_mask_path_not_declared")
    if patient["world_mapping"]["status"] != "available":
        blockers.append("authoritative_patient_affine_unavailable")
    if blockers:
        return {
            "status": "registered_roi_intake_blocked",
            "case_id": patient["case_id"],
            "plan_id": plan["plan_id"],
            "roi_id": roi["roi_id"],
            "registration_ready": False,
            "blockers": blockers,
            "pressure_executed": False,
            "clinical_safety_claim": False,
            "claim_boundary": "anatomical_input_provenance_only",
        }
    if sidecar is None:
        raise RegisteredROIIntakeError("registered anatomy requires a registration sidecar")

    mask_relative = roi["generation"]["mask_path"]
    if sidecar.get("roi_mask_path") != mask_relative:
        raise RegisteredROIIntakeError("registration sidecar ROI mask path mismatch")
    mask_path = resolve_project_file(mask_relative, project_root)
    expected_affine = validate_registration_sidecar(sidecar, plan, mask_path, project_root)
    try:
        loaded = load_roi_mask(mask_path, tuple(patient["shape_ijk"]), expected_affine)
    except (ROIError, ImportError) as error:
        raise RegisteredROIIntakeError(str(error)) from error
    summary = summarize_roi(loaded.mask, tuple(patient["spacing_m_ijk"]))
    if summary["voxel_count"] != roi["voxel_count"]:
        raise RegisteredROIIntakeError("ROI voxel count differs from the planning contract")
    center = tuple(roi["center_full_ijk"])
    if not bool(loaded.mask[center]):
        raise RegisteredROIIntakeError("target ROI center is outside the registered mask")

    return {
        "status": "registered_roi_intake_ready",
        "case_id": patient["case_id"],
        "plan_id": plan["plan_id"],
        "roi_id": roi["roi_id"],
        "registration_ready": True,
        "source_format": loaded.source_format,
        "roi_mask_path": mask_relative,
        "roi_mask_sha256": sha256_file(mask_path),
        "registration_method": sidecar["registration_method"],
        "source_image_id": sidecar["source_image_id"],
        "mask_affine_ijk_to_world_mm": expected_affine.tolist(),
        "roi_summary": summary,
        "center_inside_mask": True,
        "blockers": [],
        "pressure_executed": False,
        "clinical_safety_claim": False,
        "claim_boundary": "registered_anatomical_input_ready_for_research_simulation",
    }


def write_report(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "registered_roi_intake.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    lines = [
        "# Registered ROI Intake Audit",
        "",
        f"- Status: `{result['status']}`",
        f"- Case: `{result['case_id']}`",
        f"- ROI: `{result['roi_id']}`",
        f"- Registration ready: `{str(result['registration_ready']).lower()}`",
        "- Claim boundary: anatomical input provenance only; no pressure or clinical-safety claim.",
    ]
    if result["blockers"]:
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- `{blocker}`" for blocker in result["blockers"])
    (output_dir / "registered_roi_intake.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit registered anatomical ROI intake without simulation.")
    parser.add_argument("--plan", type=Path, default=DEFAULT_EXAMPLE)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--registration-sidecar", type=Path)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "outputs" / "bbb_registered_roi_intake_20260722"
    )
    args = parser.parse_args()
    plan = load_json(args.plan)
    schema = load_json(args.schema)
    sidecar = load_json(args.registration_sidecar) if args.registration_sidecar else None
    result = audit_registered_roi(plan, schema, sidecar=sidecar)
    write_report(result, args.output_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
