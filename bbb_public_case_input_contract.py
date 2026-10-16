from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from bbb_planning_contract import ContractError, load_json, validate_schema_subset
from public_case_source_policy import MIXED_MEDIUM, classify_source_materials


ROOT = Path(__file__).resolve().parent
DEFAULT_SCHEMA = ROOT / "planning_contracts" / "bbb_public_case_input_v1_2.schema.json"
DEFAULT_EXAMPLE = (
    ROOT
    / "planning_contracts"
    / "examples"
    / "nlm_public_postmortem_proxy_input_v1_2.json"
)

REQUIRED_ENGINEERING_BLOCKERS = {
    "hardware_geometry_missing",
    "mixed_medium_source_not_external_hardware",
    "standard_or_paper_grade_execution_not_permitted",
}
REQUIRED_ANATOMICAL_BLOCKERS = {
    "expert_human_registration_qc_missing",
    "registered_anatomical_roi_missing",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_in_bounds(index: list[int], shape: list[int], name: str) -> None:
    if any(size <= 0 for size in shape):
        raise ContractError("acoustic_model.shape_ijk values must be positive")
    if any(position >= size for position, size in zip(index, shape, strict=True)):
        raise ContractError(f"{name} is outside acoustic_model.shape_ijk")


def validate_semantics(contract: dict[str, Any]) -> None:
    model = contract["acoustic_model"]
    target = contract["target_roi"]
    trajectory = contract["trajectory_screening"]
    gates = contract["readiness_gates"]

    for name, index in (
        ("target_roi.center_ijk", target["center_ijk"]),
        ("trajectory_screening.target_ijk", trajectory["target_ijk"]),
        ("trajectory_screening.entry_ijk", trajectory["entry_ijk"]),
        ("trajectory_screening.source_center_ijk", trajectory["source_center_ijk"]),
    ):
        _require_in_bounds(index, model["shape_ijk"], name)

    if target["center_ijk"] != trajectory["target_ijk"]:
        raise ContractError("trajectory target must equal proxy ROI center")

    source_counts = trajectory["source_label_counts"]
    label_counts = {
        "0": source_counts["background"],
        "1": source_counts["soft_tissue"],
        "2": source_counts["skull"],
    }
    if classify_source_materials(label_counts) != MIXED_MEDIUM:
        raise ContractError("contract source counts must classify as mixed_medium_idealized_source")

    required_sets = (
        ("engineering_blockers", REQUIRED_ENGINEERING_BLOCKERS),
        ("anatomical_or_clinical_blockers", REQUIRED_ANATOMICAL_BLOCKERS),
    )
    for field, required in required_sets:
        missing = sorted(required - set(gates[field]))
        if missing:
            raise ContractError(f"readiness_gates.{field} missing required safety gates: {missing}")

    affine = model["affine_ijk_to_world_mm"]
    if affine[3] != [0.0, 0.0, 0.0, 1.0]:
        raise ContractError("affine_ijk_to_world_mm must use a homogeneous final row")


def _verify_hash(path: Path, expected_hash: str, label: str, relative: str) -> None:
    if not path.is_file():
        raise ContractError(f"{label} file does not exist: {relative}")
    if _sha256(path) != expected_hash:
        raise ContractError(f"{label} SHA256 mismatch: {relative}")


def verify_files(contract: dict[str, Any], project_root: Path = ROOT) -> None:
    trajectory = contract["trajectory_screening"]
    checks = (
        (
            contract["acoustic_model"]["model_path"],
            contract["acoustic_model"]["model_sha256"],
            "acoustic model",
        ),
        (
            contract["target_roi"]["mask_path"],
            contract["target_roi"]["mask_sha256"],
            "proxy ROI mask",
        ),
        (
            trajectory["entry_plan_path"],
            trajectory["entry_plan_sha256"],
            "entry plan",
        ),
        (
            trajectory["dry_run_path"],
            trajectory["dry_run_sha256"],
            "source-material dry run",
        ),
    )
    for relative, expected_hash, label in checks:
        _verify_hash(project_root / relative, expected_hash, label, relative)

    readiness_path = project_root / contract["provenance"]["readiness_report_path"]
    if not readiness_path.is_file():
        raise ContractError(f"readiness report file does not exist: {readiness_path}")
    readiness = load_json(readiness_path)
    if readiness.get("engineering_sandbox_input_ready") is not True:
        raise ContractError("readiness report does not authorize engineering sandbox input")
    if readiness.get("expert_required_for_engineering_sandbox") is not False:
        raise ContractError("readiness report incorrectly requires an expert for engineering sandbox input")
    if readiness.get("simulation_execution_ready") is not False:
        raise ContractError("readiness report must keep new simulation execution blocked")

    dry_run = load_json(project_root / trajectory["dry_run_path"])
    dry_counts = dry_run["source"]["label_composition"]
    contract_counts = trajectory["source_label_counts"]
    normalized_dry_counts = {
        "background": int(dry_counts.get("0", 0)),
        "soft_tissue": int(dry_counts.get("1", 0)),
        "skull": int(dry_counts.get("2", 0)),
    }
    if normalized_dry_counts != contract_counts:
        raise ContractError("source-material dry-run counts do not match the contract")


def validate_contract(
    contract: dict[str, Any],
    schema: dict[str, Any],
    verify_file_hashes: bool = False,
) -> None:
    validate_schema_subset(contract, schema, schema)
    validate_semantics(contract)
    if verify_file_hashes:
        verify_files(contract)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the current public postmortem proxy input contract.")
    parser.add_argument("--contract", type=Path, default=DEFAULT_EXAMPLE)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--verify-files", action="store_true")
    args = parser.parse_args()

    contract = load_json(args.contract)
    schema = load_json(args.schema)
    validate_contract(contract, schema, verify_file_hashes=args.verify_files)
    print(json.dumps({
        "status": "pass",
        "contract_id": contract["contract_id"],
        "schema_version": contract["schema_version"],
        "file_hashes_verified": args.verify_files,
        "engineering_sandbox_input_ready": True,
        "expert_required_for_engineering_sandbox": False,
        "source_material_semantics": contract["trajectory_screening"]["source_material_semantics"],
        "new_simulation_execution_permitted": False,
        "historical_quick_pressure_outputs_exist": True,
        "clinical_safety_claim": False,
        "claim_boundary": contract["provenance"]["claim_boundary"],
    }, indent=2))


if __name__ == "__main__":
    main()
