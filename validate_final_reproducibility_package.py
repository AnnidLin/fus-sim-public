from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
PACKAGE_DIR = PROJECT_ROOT / "outputs/reproducibility_package"
INDEX_PATH = PACKAGE_DIR / "data_index.json"
REPORT_PATH = PACKAGE_DIR / "final_report.md"
OUT_JSON = PACKAGE_DIR / "validation.json"
OUT_MD = PACKAGE_DIR / "validation.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: Any) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": str(evidence)})


def main() -> None:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8-sig"))
    report = REPORT_PATH.read_text(encoding="utf-8-sig")
    checks: list[dict[str, Any]] = []
    artifacts = index.get("artifacts", [])
    missing = [item.get("path") for item in artifacts if item.get("required") and not item.get("exists")]
    unsafe_paths = [item.get("path") for item in artifacts if PurePosixPath(str(item.get("path", ""))).is_absolute() or ":" in str(item.get("path", ""))]
    hash_mismatches = []
    for item in artifacts:
        path = PROJECT_ROOT / str(item.get("path", ""))
        if path.is_file() and sha256(path) != item.get("sha256"):
            hash_mismatches.append(item.get("path"))

    add(checks, "package.case", index.get("case_id") == "079", index.get("case_id"))
    add(checks, "package.claim_level", index.get("claim_level") == "auditable_research_dataset_candidate_not_numerical_convergence", index.get("claim_level"))
    add(checks, "artifacts.present", len(artifacts) >= 15 and not missing, missing)
    add(checks, "artifacts.relative_paths", not unsafe_paths, unsafe_paths)
    add(checks, "artifacts.hashes_match", not hash_mismatches, hash_mismatches)
    add(checks, "commands.complete", set(index.get("commands", {})) == {"regenerate_manifest", "validate_manifest", "generate_package", "validate_package"}, sorted(index.get("commands", {})))
    add(checks, "git.commit_recorded", len(index.get("git", {}).get("commit", "")) == 40, index.get("git", {}).get("commit"))
    sensitivity = index.get("key_results", {}).get("sensitivity", {})
    add(checks, "p3.dx05_chain_valid", sensitivity.get("dx05_coordinate_chain_valid") is True, sensitivity)
    add(
        checks,
        "p3.no_false_convergence",
        sensitivity.get("numerical_convergence_demonstrated") is False
        and sensitivity.get("dx05_sweep000_pressure_executed") is True,
        sensitivity,
    )
    add(
        checks,
        "hotspot.screening_not_validation",
        sensitivity.get("dx05_sweep000_hotspot_material") == "skull_bone"
        and sensitivity.get("dx05_sweep000_scaled_source_pressure_validated") is True
        and sensitivity.get("dx05_sweep000_scaled_clinical_safety_allowed") is False,
        sensitivity,
    )
    blocked = set(index.get("blocked_claims", []))
    required_blocked = {"numerical convergence", "paper-grade validated pressure baseline", "tuned focus", "clinical or medical safety", "medical efficacy"}
    add(checks, "claims.boundaries", required_blocked.issubset(blocked), sorted(blocked))
    add(checks, "report.exists_and_bounded", REPORT_PATH.is_file() and "not evidence of numerical convergence or clinical safety" in report, REPORT_PATH)

    failed = [item for item in checks if item["status"] == "fail"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "package_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(f"# Final Package Validation\n\n- package valid: `{result['package_valid']}`\n- failed check count: `{len(failed)}`\n", encoding="utf-8")
    print(json.dumps({"package_valid": result["package_valid"], "failed_check_count": len(failed)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
