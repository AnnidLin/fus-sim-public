from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
MODULE = "gate_state_machine"
OUT_DIR = PROJECT_ROOT / "outputs" / MODULE

REQUIRED_GATES = [
    "mapping_profile_gate",
    "alpha_semantics_gate",
    "pressure_execution_gate",
    "numerical_quality_gate",
    "interpretation_gate",
    "paper_grade_gate",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def nested(data: dict[str, Any] | None, keys: list[str], default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def paths() -> dict[str, Path]:
    return {
        "registry": PROJECT_ROOT / "outputs/evidence_registry/evidence_registry.json",
        "post_pressure_readiness": PROJECT_ROOT
        / "outputs/simple_hu300_post_pressure_readiness/079_candidate_006/post_pressure_readiness_summary.json",
        "profile_preset_run_contract": PROJECT_ROOT / "outputs/profile_preset_run_contract/profile_preset_run_contract.json",
        "profile_promotion_gate": PROJECT_ROOT
        / "outputs/profile_promotion_gate/prestus_fit_alpha_power_2/profile_promotion_gate_summary.json",
    }


def build_state_machine() -> dict[str, Any]:
    p = paths()
    registry = read_json(p["registry"])
    readiness = read_json(p["post_pressure_readiness"])
    separation = read_json(p["profile_preset_run_contract"])
    alpha_gate = read_json(p["profile_promotion_gate"])

    registry_gates = nested(registry, ["gate_states"], {})
    gates: dict[str, dict[str, Any]] = {}
    for gate in REQUIRED_GATES:
        payload = registry_gates.get(gate, {})
        gates[gate] = {
            "status": payload.get("status", "block"),
            "reason": payload.get("reason", "missing registry gate payload"),
            "next_action": payload.get("next_action", "restore registry gate payload"),
            "source": rel(p["registry"]),
            "blocks": [],
            "unlocks": [],
        }

    gates["mapping_profile_gate"]["blocks"] = ["validated_pressure_baseline", "default_profile_promotion"]
    gates["mapping_profile_gate"]["unlocks"] = ["engineering_baseline_reference"]
    gates["alpha_semantics_gate"]["blocks"] = ["source_backed_alpha_pressure", "profile_promotion", "validated_pressure_baseline"]
    gates["pressure_execution_gate"]["unlocks"] = ["standard_engineering_pressure_output"]
    gates["numerical_quality_gate"]["blocks"] = ["paper_grade_candidate", "additional_pressure_without_gate"]
    gates["interpretation_gate"]["blocks"] = ["medical_or_safety_conclusion"]
    gates["paper_grade_gate"]["blocks"] = ["paper_grade_reproduction_claim"]

    return {
        "state_machine_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": MODULE,
        "inputs": {name: rel(path) for name, path in p.items()},
        "required_gates": REQUIRED_GATES,
        "gates": gates,
        "transition_policy": {
            "allowed_statuses": ["pass", "warn", "block"],
            "one_next_action_per_gate": True,
            "pressure_requires_user_authorization_and_runner_gate": True,
            "paper_grade_requires_all_gates_pass": True,
            "profile_promotion_requires_alpha_semantics_gate_pass": True,
            "run_success_cannot_upgrade_profile": nested(
                separation, ["separation_policy", "run_success_does_not_upgrade_profile"], True
            ),
            "run_success_cannot_upgrade_paper_grade": nested(
                separation, ["separation_policy", "run_success_does_not_upgrade_paper_grade"], True
            ),
        },
        "global_locks": {
            "paper_grade_ready": nested(readiness, ["decision", "paper_grade_ready"], False),
            "medical_or_safety_conclusion_allowed": False,
            "profile_promotion_allowed": nested(alpha_gate, ["decision", "default_profile_eligible"], False),
            "default_profile_change_allowed": nested(alpha_gate, ["decision", "default_profile_eligible"], False),
        },
        "recommended_next_gate": "cfl_environment_gate",
    }


def write_outputs(machine: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "gate_state_machine.json"
    md_path = OUT_DIR / "gate_state_machine.md"
    json_path.write_text(json.dumps(machine, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Gate State Machine",
        "",
        f"- version: `{machine['state_machine_version']}`",
        f"- recommended next gate: `{machine['recommended_next_gate']}`",
        "",
        "| Gate | Status | Blocks | Next Action |",
        "|---|---:|---|---|",
    ]
    for gate, payload in machine["gates"].items():
        lines.append(
            f"| `{gate}` | `{payload['status']}` | {', '.join(payload['blocks'])} | {payload['next_action']} |"
        )
    lines.extend(["", "## Global Locks", ""])
    for key, value in machine["global_locks"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    machine = build_state_machine()
    write_outputs(machine)
    print(f"Wrote {rel(OUT_DIR / 'gate_state_machine.json')}")
    print(f"Wrote {rel(OUT_DIR / 'gate_state_machine.md')}")


if __name__ == "__main__":
    main()
