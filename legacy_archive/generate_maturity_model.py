from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "outputs/maturity_model"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def nested(data: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def build_model() -> dict[str, Any]:
    registry = read_json(PROJECT_ROOT / "outputs/evidence_registry/evidence_registry.json")
    gates = read_json(PROJECT_ROOT / "outputs/gate_state_machine/gate_state_machine.json")
    readiness = read_json(PROJECT_ROOT / "outputs/simple_hu300_post_pressure_readiness/079_candidate_006/post_pressure_readiness_summary.json")
    ledger = read_json(PROJECT_ROOT / "outputs/run_ledger_summary.json")
    current = nested(registry, ["project_maturity_level", "current"], "M2_standard_engineering_baseline_hardening")
    return {
        "model_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": "maturity_model",
        "current_level": current,
        "levels": {
            "M0_plumbing_smoke": "scripts and I/O work only",
            "M1_reproducible_engineering_baseline": "reproducible baseline profile and dry-run metadata",
            "M2_standard_engineering_baseline_hardening": "one standard engineering pressure output plus governance gates",
            "M3_numerical_sensitivity_package": "grid/PML/CFL sensitivity package exists",
            "M4_source_backed_profile_cross_checked": "source-backed profile semantics and cross-checks pass",
            "M5_paper_grade_candidate": "paper-grade candidate with convergence, environment, reporting, and comparison evidence"
        },
        "transition_requirements": {
            "M2_to_M3": ["ct.grid_convergence", "ct.pml_boundary_review", "ct.cfl_review", "environment.record"],
            "M3_to_M4": ["alpha.semantics", "MATLAB/source-backed cross-check"],
            "M4_to_M5": ["paper_grade.required_fields", "paper_grade preset plan", "external comparison package"]
        },
        "evidence": {
            "pressure_run_count": nested(ledger, ["pressure_run_count"], 0),
            "paper_grade_ready": nested(readiness, ["decision", "paper_grade_ready"], False),
            "gate_statuses": {name: payload.get("status") for name, payload in gates.get("gates", {}).items()}
        },
        "blocked_upgrades": [
            {"target": "M3_numerical_sensitivity_package", "status": "block", "reason": "grid/PML/CFL/environment evidence incomplete"},
            {"target": "M4_source_backed_profile_cross_checked", "status": "block", "reason": "alpha semantics and cross-check gaps remain"},
            {"target": "M5_paper_grade_candidate", "status": "block", "reason": "paper_grade_gate is blocked"}
        ],
        "recommended_next_action": "Create read-only CFL/environment gate as the next M2 hardening artifact."
    }


def main() -> None:
    model = build_model()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "maturity_model.json").write_text(json.dumps(model, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Maturity Model", "", f"- current level: `{model['current_level']}`", "", "## Blocked Upgrades", ""]
    for item in model["blocked_upgrades"]:
        lines.append(f"- `{item['target']}`: {item['reason']}")
    (OUT_DIR / "maturity_model.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote outputs/maturity_model/maturity_model.json")


if __name__ == "__main__":
    main()
