from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "outputs/claim_policy"
BRIEF_DIR = PROJECT_ROOT / "outputs/evidence_briefs/claim_policy"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def nested(data: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def build_policy() -> dict[str, Any]:
    registry = read_json(PROJECT_ROOT / "outputs/evidence_registry/evidence_registry.json")
    gates = read_json(PROJECT_ROOT / "outputs/gate_state_machine/gate_state_machine.json")
    contract = read_json(PROJECT_ROOT / "outputs/profile_preset_run_contract/profile_preset_run_contract.json")
    maturity = read_json(PROJECT_ROOT / "outputs/maturity_model/maturity_model.json")
    readiness = read_json(
        PROJECT_ROOT / "outputs/simple_hu300_post_pressure_readiness/079_candidate_006/post_pressure_readiness_summary.json"
    )

    registry_policy = registry.get("global_claim_policy", {})
    blocked = list(
        dict.fromkeys(
            registry_policy.get("blocked_claims", [])
            + [
                "validated pressure baseline",
                "paper-grade reproduction",
                "medical or safety conclusion",
                "source-backed alpha pressure eligibility",
                "default profile promotion",
                "thermal safety conclusion",
                "clinical efficacy conclusion",
            ]
        )
    )
    allowed = list(
        dict.fromkeys(
            registry_policy.get("allowed_claims", [])
            + [
                "simple_hu300 is the current reproducible engineering baseline",
                "the completed pressure run is standard engineering evidence only",
                "current maturity is M2_standard_engineering_baseline_hardening",
            ]
        )
    )
    flags = {
        "paper_grade_ready": False,
        "medical_or_safety_conclusion_allowed": False,
        "profile_promotion_allowed": False,
        "default_profile_change_allowed": False,
        "source_backed_alpha_pressure_eligible": False,
        "thermal_safety_claim_allowed": False,
        "validated_pressure_baseline_allowed": False,
    }
    return {
        "policy_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": "claim_policy",
        "scope": "claim boundaries for current simple_hu300 M2 baseline hardening",
        "current_claim_level": nested(contract, ["current_run", "run_claim_level"], "standard_engineering_pressure_output"),
        "current_maturity_level": maturity.get("current_level"),
        "source_inputs": {
            "registry": "outputs/evidence_registry/evidence_registry.json",
            "gate_state_machine": "outputs/gate_state_machine/gate_state_machine.json",
            "profile_preset_run_contract": "outputs/profile_preset_run_contract/profile_preset_run_contract.json",
            "maturity_model": "outputs/maturity_model/maturity_model.json",
            "post_pressure_readiness": "outputs/simple_hu300_post_pressure_readiness/079_candidate_006/post_pressure_readiness_summary.json",
        },
        "allowed_claims": allowed,
        "blocked_claims": blocked,
        "claim_flags": flags,
        "gate_snapshot": {
            "alpha_semantics_gate": nested(gates, ["gates", "alpha_semantics_gate", "status"], nested(registry, ["gate_states", "alpha_semantics_gate", "status"])),
            "numerical_quality_gate": nested(gates, ["gates", "numerical_quality_gate", "status"], nested(registry, ["gate_states", "numerical_quality_gate", "status"])),
            "paper_grade_gate": nested(gates, ["gates", "paper_grade_gate", "status"], nested(registry, ["gate_states", "paper_grade_gate", "status"])),
        },
        "readiness_snapshot": {
            "paper_grade_ready": nested(readiness, ["decision", "paper_grade_ready"], False),
            "blockers": nested(readiness, ["blockers"], []),
        },
        "required_report_fields": [
            "preset",
            "claim_level",
            "mapping_profile",
            "profile_status",
            "paper_grade_ready",
            "medical_or_safety_conclusion_allowed",
            "allowed_claims",
            "blocked_claims",
        ],
        "enforcement_rules": [
            "A standard run may support engineering evidence but must not upgrade a profile.",
            "Paper-grade language is blocked while paper_grade_gate is block.",
            "Medical or safety conclusions are blocked in the current baseline.",
            "Source-backed alpha pressure eligibility is blocked while alpha semantics are unresolved.",
            "Future reports must include allowed_claims and blocked_claims.",
        ],
        "recommended_next_action": "Use this policy in future reports, then proceed to module boundary manifest.",
        "not_executed": [
            "k-Wave simulation",
            "thermal simulation",
            "paper-grade run",
            "profile/default promotion",
        ],
    }


def write_markdown(policy: dict[str, Any]) -> str:
    lines = [
        "# Claim Policy",
        "",
        f"- policy version: `{policy['policy_version']}`",
        f"- current claim level: `{policy['current_claim_level']}`",
        f"- current maturity: `{policy['current_maturity_level']}`",
        "",
        "## Allowed Claims",
        "",
    ]
    lines.extend(f"- {item}" for item in policy["allowed_claims"])
    lines.extend(["", "## Blocked Claims", ""])
    lines.extend(f"- {item}" for item in policy["blocked_claims"])
    lines.extend(["", "## Claim Flags", ""])
    for key, value in policy["claim_flags"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Enforcement Rules", ""])
    lines.extend(f"- {item}" for item in policy["enforcement_rules"])
    lines.extend(["", "## Not Executed", ""])
    lines.extend(f"- {item}" for item in policy["not_executed"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    policy = build_policy()
    policy_path = OUT_DIR / "claim_policy.json"
    report_path = OUT_DIR / "claim_policy.md"
    policy_path.write_text(json.dumps(policy, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(write_markdown(policy), encoding="utf-8")
    feedback = {
        "module": "claim_policy",
        "feedback_type": "post_execution_gap_feedback",
        "executed_scope": [
            "generated standalone claim policy",
            "kept paper-grade/medical/profile-promotion claims blocked",
            "prepared policy for registry integration",
        ],
        "outputs": {
            "policy": rel(policy_path),
            "report": rel(report_path),
        },
        "decision": {
            "claim_policy_status": "v1_complete",
            "paper_grade_ready": False,
            "medical_or_safety_conclusion_allowed": False,
            "profile_promotion_allowed": False,
            "source_backed_alpha_pressure_eligible": False,
        },
        "not_executed": policy["not_executed"],
        "recommended_next_step": "Proceed to item 7: script/module boundary manifest.",
    }
    (BRIEF_DIR / "gap_feedback.json").write_text(json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8")
    (BRIEF_DIR / "gap_feedback.md").write_text(
        "# Gap Feedback: Claim Policy\n\n"
        "## Decision\n\n"
        "- claim policy status: `v1_complete`\n"
        "- paper-grade ready: `False`\n"
        "- medical/safety conclusion allowed: `False`\n"
        "- profile promotion allowed: `False`\n"
        "- source-backed alpha pressure eligible: `False`\n\n"
        "## Outputs\n\n"
        f"- `{rel(policy_path)}`\n"
        f"- `{rel(report_path)}`\n\n"
        "## Not Executed\n\n"
        "- No k-Wave simulation.\n"
        "- No thermal simulation.\n"
        "- No paper-grade run.\n"
        "- No profile/default promotion.\n",
        encoding="utf-8",
    )
    print(f"Wrote {rel(policy_path)}")


if __name__ == "__main__":
    main()
