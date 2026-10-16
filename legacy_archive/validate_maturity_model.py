from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "outputs/maturity_model/maturity_model.json"
OUT_JSON = PROJECT_ROOT / "outputs/maturity_model/maturity_model_validation.json"
OUT_MD = PROJECT_ROOT / "outputs/maturity_model/maturity_model_validation.md"


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: str) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": evidence})


def main() -> None:
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []
    add(checks, "model.version", model.get("model_version") == "1.0.0", str(model.get("model_version")))
    add(checks, "current.is_m2", model.get("current_level") == "M2_standard_engineering_baseline_hardening", str(model.get("current_level")))
    gates = model.get("evidence", {}).get("gate_statuses", {})
    add(checks, "gates.block_m3", gates.get("numerical_quality_gate") == "block", str(gates))
    add(checks, "gates.block_m4", gates.get("alpha_semantics_gate") == "block", str(gates))
    add(checks, "gates.block_m5", gates.get("paper_grade_gate") == "block", str(gates))
    blocked = {item.get("target") for item in model.get("blocked_upgrades", [])}
    add(checks, "blocked.targets", {"M3_numerical_sensitivity_package", "M4_source_backed_profile_cross_checked", "M5_paper_grade_candidate"}.issubset(blocked), str(blocked))
    failed = [item for item in checks if item["status"] != "pass"]
    result = {"generated_at": datetime.now(timezone.utc).isoformat(), "maturity_model_valid": not failed, "failed_check_count": len(failed), "checks": checks, "failed_checks": failed}
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(f"# Maturity Model Validation\n\n- valid: `{result['maturity_model_valid']}`\n- failed check count: `{len(failed)}`\n", encoding="utf-8")
    print(json.dumps({"maturity_model_valid": result["maturity_model_valid"], "failed_check_count": len(failed)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
