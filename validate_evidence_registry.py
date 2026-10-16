from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_REGISTRY = PROJECT_ROOT / "outputs" / "evidence_registry" / "evidence_registry.json"
DEFAULT_SCHEMA = PROJECT_ROOT / "governance_schemas" / "evidence_registry.schema.json"
OUT_DIR = PROJECT_ROOT / "outputs" / "evidence_registry"

ALLOWED_GATE_STATUSES = {"pass", "warn", "block"}
REQUIRED_GLOBAL_BLOCKS = {
    "validated pressure baseline",
    "paper-grade reproduction",
    "medical or safety conclusion",
    "source-backed alpha pressure eligibility",
    "default profile promotion",
}
REQUIRED_TOP_LEVEL = {
    "registry_version",
    "generated_at",
    "module",
    "scope",
    "inputs",
    "project_maturity_level",
    "global_claim_policy",
    "artifact_entries",
    "gate_states",
    "run_ledger_seed",
    "recommended_next_action",
    "not_executed",
}
REQUIRED_ARTIFACT_FIELDS = {
    "artifact_id",
    "title",
    "path",
    "artifact_type",
    "evidence_level",
    "maturity_level",
    "gate_status",
    "allowed_claims",
    "blocked_claims",
    "dependencies",
    "recommended_next_action",
    "sha256",
    "exists",
}
REQUIRED_GATES = {
    "mapping_profile_gate",
    "alpha_semantics_gate",
    "pressure_execution_gate",
    "numerical_quality_gate",
    "cfl_environment_gate",
    "interpretation_gate",
    "paper_grade_gate",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def add_check(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: str) -> None:
    checks.append(
        {
            "check_id": check_id,
            "status": "pass" if passed else "fail",
            "evidence": evidence,
        }
    )


def validate(registry: dict[str, Any], schema: dict[str, Any], registry_path: Path, schema_path: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    missing_top = sorted(REQUIRED_TOP_LEVEL - set(registry))
    add_check(checks, "top_level.required_keys", not missing_top, f"missing={missing_top}")
    add_check(checks, "schema.parsed", bool(schema), f"schema_path={rel(schema_path)}")
    add_check(checks, "registry.version", registry.get("registry_version") == "1.0.0", f"registry_version={registry.get('registry_version')}")
    add_check(checks, "registry.module", registry.get("module") == "evidence_registry", f"module={registry.get('module')}")

    artifacts = registry.get("artifact_entries", [])
    artifact_ids = [item.get("artifact_id") for item in artifacts if isinstance(item, dict)]
    duplicate_ids = sorted({item for item in artifact_ids if artifact_ids.count(item) > 1})
    add_check(checks, "artifacts.unique_ids", not duplicate_ids, f"duplicates={duplicate_ids}; count={len(artifact_ids)}")

    artifact_missing_fields = {}
    bad_gate_status = {}
    missing_files = []
    missing_hashes = []
    known_ids = set(artifact_ids)
    unresolved_deps: dict[str, list[str]] = {}
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        artifact_id = str(item.get("artifact_id"))
        missing = sorted(REQUIRED_ARTIFACT_FIELDS - set(item))
        if missing:
            artifact_missing_fields[artifact_id] = missing
        if item.get("gate_status") not in ALLOWED_GATE_STATUSES:
            bad_gate_status[artifact_id] = item.get("gate_status")
        if item.get("exists") is not True:
            missing_files.append(artifact_id)
        if not item.get("sha256"):
            missing_hashes.append(artifact_id)
        deps = [dep for dep in item.get("dependencies", []) if dep not in known_ids]
        if deps:
            unresolved_deps[artifact_id] = deps

    add_check(checks, "artifacts.required_fields", not artifact_missing_fields, f"missing_fields={artifact_missing_fields}")
    add_check(checks, "artifacts.gate_status_values", not bad_gate_status, f"bad_gate_status={bad_gate_status}")
    add_check(checks, "artifacts.files_exist", not missing_files, f"missing_files={missing_files}")
    add_check(checks, "artifacts.sha256_present", not missing_hashes, f"missing_hashes={missing_hashes}")
    add_check(checks, "artifacts.dependencies_resolve", not unresolved_deps, f"unresolved_deps={unresolved_deps}")

    gate_states = registry.get("gate_states", {})
    missing_gates = sorted(REQUIRED_GATES - set(gate_states))
    gate_bad_status = {
        gate: payload.get("status")
        for gate, payload in gate_states.items()
        if isinstance(payload, dict) and payload.get("status") not in ALLOWED_GATE_STATUSES
    }
    gate_missing_next = [
        gate
        for gate, payload in gate_states.items()
        if not isinstance(payload, dict) or not payload.get("next_action")
    ]
    add_check(checks, "gates.required", not missing_gates, f"missing_gates={missing_gates}")
    add_check(checks, "gates.status_values", not gate_bad_status, f"bad_status={gate_bad_status}")
    add_check(checks, "gates.next_action", not gate_missing_next, f"missing_next_action={gate_missing_next}")

    policy = registry.get("global_claim_policy", {})
    blocked = set(policy.get("blocked_claims", []))
    missing_required_blocks = sorted(REQUIRED_GLOBAL_BLOCKS - blocked)
    add_check(checks, "claim_policy.required_blocks", not missing_required_blocks, f"missing_required_blocks={missing_required_blocks}")
    add_check(checks, "claim_policy.paper_grade_false", policy.get("paper_grade_ready") is False, f"paper_grade_ready={policy.get('paper_grade_ready')}")
    add_check(
        checks,
        "claim_policy.medical_false",
        policy.get("medical_or_safety_conclusion_allowed") is False,
        f"medical_or_safety_conclusion_allowed={policy.get('medical_or_safety_conclusion_allowed')}",
    )
    add_check(
        checks,
        "claim_policy.profile_false",
        policy.get("profile_promotion_allowed") is False and policy.get("default_profile_change_allowed") is False,
        f"profile_promotion_allowed={policy.get('profile_promotion_allowed')}; default_profile_change_allowed={policy.get('default_profile_change_allowed')}",
    )

    ledger = registry.get("run_ledger_seed", [])
    ledger_has_standard = any(
        item.get("claim_level") == "standard_engineering_pressure_output" and item.get("pressure_generated") is True
        for item in ledger
        if isinstance(item, dict)
    )
    add_check(checks, "run_ledger.standard_pressure_seed", ledger_has_standard, f"ledger_entries={len(ledger)}")

    failed = [check for check in checks if check["status"] != "pass"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registry_path": rel(registry_path),
        "schema_path": rel(schema_path),
        "registry_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }


def write_report(result: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "evidence_registry_validation.json"
    md_path = OUT_DIR / "evidence_registry_validation.md"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Evidence Registry Validation",
        "",
        f"- registry valid: `{result['registry_valid']}`",
        f"- failed check count: `{result['failed_check_count']}`",
        f"- registry: `{result['registry_path']}`",
        f"- schema: `{result['schema_path']}`",
        "",
        "## Checks",
        "",
        "| Status | Check | Evidence |",
        "|---|---|---|",
    ]
    for check in result["checks"]:
        evidence = str(check["evidence"]).replace("\n", " ")
        if len(evidence) > 180:
            evidence = evidence[:177] + "..."
        lines.append(f"| `{check['status']}` | `{check['check_id']}` | {evidence} |")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the fus-sim evidence registry without external packages.")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    args = parser.parse_args()

    registry_path = Path(args.registry)
    schema_path = Path(args.schema)
    result = validate(read_json(registry_path), read_json(schema_path), registry_path, schema_path)
    write_report(result)
    print(json.dumps({"registry_valid": result["registry_valid"], "failed_check_count": result["failed_check_count"]}))
    if not result["registry_valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
