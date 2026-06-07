from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
MODULE = "evidence_registry"
OUT_DIR = PROJECT_ROOT / "outputs" / MODULE
BRIEF_DIR = PROJECT_ROOT / "outputs" / "evidence_briefs" / MODULE
SCHEMA_PATH = PROJECT_ROOT / "governance_schemas" / "evidence_registry.schema.json"


@dataclass(frozen=True)
class ArtifactEntry:
    artifact_id: str
    title: str
    path: str
    artifact_type: str
    evidence_level: str
    maturity_level: str
    gate_status: str
    allowed_claims: list[str]
    blocked_claims: list[str]
    dependencies: list[str]
    recommended_next_action: str
    sha256: str | None
    exists: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "title": self.title,
            "path": self.path,
            "artifact_type": self.artifact_type,
            "evidence_level": self.evidence_level,
            "maturity_level": self.maturity_level,
            "gate_status": self.gate_status,
            "allowed_claims": self.allowed_claims,
            "blocked_claims": self.blocked_claims,
            "dependencies": self.dependencies,
            "recommended_next_action": self.recommended_next_action,
            "sha256": self.sha256,
            "exists": self.exists,
        }


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def file_sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nested(data: dict[str, Any] | None, keys: list[str], default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def paths() -> dict[str, Path]:
    return {
        "source_backed_alpha_stage": PROJECT_ROOT
        / "outputs/source_backed_alpha_stage_report/source_backed_alpha_stage_summary.json",
        "profile_promotion_gate": PROJECT_ROOT
        / "outputs/profile_promotion_gate/prestus_fit_alpha_power_2/profile_promotion_gate_summary.json",
        "standard_pressure_execution": PROJECT_ROOT
        / "outputs/ct_standard_pressure_authorization/079_candidate_006_dx0p75_pml12_standard/standard_pressure_execution_summary.json",
        "post_pressure_readiness": PROJECT_ROOT
        / "outputs/simple_hu300_post_pressure_readiness/079_candidate_006/post_pressure_readiness_summary.json",
        "progress_goal_gate": PROJECT_ROOT
        / "outputs/simple_hu300_progress_goal_gate/079_candidate_006/current_progress_goal_gate_summary.json",
        "standard_pressure_gap_feedback": PROJECT_ROOT
        / "outputs/evidence_briefs/simple_hu300_standard_pressure_authorization_package/gap_feedback.json",
        "profile_preset_run_contract": PROJECT_ROOT
        / "outputs/profile_preset_run_contract/profile_preset_run_contract.json",
        "profile_preset_run_conformance": PROJECT_ROOT
        / "outputs/profile_preset_run_contract/profile_preset_run_conformance.json",
        "gate_state_machine": PROJECT_ROOT / "outputs/gate_state_machine/gate_state_machine.json",
        "gate_state_machine_validation": PROJECT_ROOT / "outputs/gate_state_machine/gate_state_machine_validation.json",
        "run_ledger": PROJECT_ROOT / "outputs/run_ledger.jsonl",
        "run_ledger_summary": PROJECT_ROOT / "outputs/run_ledger_summary.json",
        "run_ledger_validation": PROJECT_ROOT / "outputs/run_ledger_validation.json",
        "maturity_model": PROJECT_ROOT / "outputs/maturity_model/maturity_model.json",
        "maturity_model_validation": PROJECT_ROOT / "outputs/maturity_model/maturity_model_validation.json",
        "claim_policy": PROJECT_ROOT / "outputs/claim_policy/claim_policy.json",
        "claim_policy_validation": PROJECT_ROOT / "outputs/claim_policy/claim_policy_validation.json",
        "module_boundary_manifest": PROJECT_ROOT / "outputs/module_boundary_manifest/module_boundary_manifest.json",
        "module_boundary_manifest_validation": PROJECT_ROOT
        / "outputs/module_boundary_manifest/module_boundary_manifest_validation.json",
        "m2_baseline_hardening_program": PROJECT_ROOT
        / "outputs/m2_baseline_hardening_program/m2_baseline_hardening_program.json",
        "m2_baseline_hardening_program_validation": PROJECT_ROOT
        / "outputs/m2_baseline_hardening_program/m2_baseline_hardening_program_validation.json",
        "cfl_environment_gate": PROJECT_ROOT / "outputs/cfl_environment_gate/cfl_environment_gate.json",
        "cfl_environment_gate_validation": PROJECT_ROOT / "outputs/cfl_environment_gate/cfl_environment_gate_validation.json",
        "simulation_presets": PROJECT_ROOT / "simulation_presets.json",
        "simple_hu300_profile": PROJECT_ROOT / "acoustic_mapping_profiles/simple_hu300.json",
    }


def load_inputs() -> dict[str, dict[str, Any] | None]:
    return {key: read_json(path) for key, path in paths().items()}


def entry(
    artifact_id: str,
    title: str,
    path: Path,
    artifact_type: str,
    evidence_level: str,
    maturity_level: str,
    gate_status: str,
    allowed_claims: list[str],
    blocked_claims: list[str],
    dependencies: list[str],
    recommended_next_action: str,
) -> ArtifactEntry:
    return ArtifactEntry(
        artifact_id=artifact_id,
        title=title,
        path=rel(path),
        artifact_type=artifact_type,
        evidence_level=evidence_level,
        maturity_level=maturity_level,
        gate_status=gate_status,
        allowed_claims=allowed_claims,
        blocked_claims=blocked_claims,
        dependencies=dependencies,
        recommended_next_action=recommended_next_action,
        sha256=file_sha256(path),
        exists=path.exists(),
    )


def build_artifacts(data: dict[str, dict[str, Any] | None]) -> list[ArtifactEntry]:
    p = paths()
    pressure_completed = nested(data["standard_pressure_execution"], ["decision", "standard_pressure_run_completed"], False)
    paper_ready = nested(data["post_pressure_readiness"], ["decision", "paper_grade_ready"], False)
    alpha_pressure_eligible = nested(data["profile_promotion_gate"], ["decision", "pressure_eligible"], False)
    profile_status = nested(data["simple_hu300_profile"], ["review_status"], "unknown")

    return [
        entry(
            "mapping.simple_hu300_profile",
            "simple_hu300 binary HU mapping profile",
            p["simple_hu300_profile"],
            "mapping_profile",
            "engineering_baseline_compatible",
            "M1_reproducible_engineering_baseline",
            "pass" if profile_status == "baseline_compatible" else "warn",
            ["current reproducible engineering baseline profile"],
            ["validated pressure baseline", "paper-grade continuous skull mapping", "medical/safety conclusion"],
            [],
            "Keep as engineering baseline; do not promote to validated pressure baseline without alpha/numerical evidence.",
        ),
        entry(
            "alpha.source_backed_stage",
            "source-backed alpha stage report",
            p["source_backed_alpha_stage"],
            "stage_report",
            "exploratory_source_backed",
            "M0_M1_exploratory_mapping_evidence",
            "block",
            ["source-backed formula audit context", "exploratory alpha route inventory"],
            ["pressure baseline", "default profile", "paper-grade or medical conclusion"],
            [],
            "Resolve alpha unit semantics and cross-check gaps before promotion.",
        ),
        entry(
            "gate.profile_promotion_prestus_fit_alpha_power_2",
            "profile promotion gate for prestus_fit_alpha_power_2",
            p["profile_promotion_gate"],
            "gate_summary",
            "promotion_gate",
            "M1_governance_gate",
            "block" if alpha_pressure_eligible is False else "warn",
            ["profile remains exploratory/blocked"],
            ["pressure-eligible source-backed alpha", "default mapping profile", "paper-grade claim"],
            ["alpha.source_backed_stage"],
            "Keep pressure/default promotion blocked until semantics and cross-check blockers resolve.",
        ),
        entry(
            "run.simple_hu300_dx075_pml12_standard_pressure",
            "user-authorized simple_hu300 dx0.75 PML12 standard pressure run",
            p["standard_pressure_execution"],
            "run_summary",
            "standard_engineering_pressure_output",
            "M2_standard_engineering_baseline_hardening",
            "pass" if pressure_completed else "block",
            [
                "one runner-gated standard pressure execution completed",
                "source mask background-only",
                "standard engineering pressure metrics available",
            ],
            [
                "validated pressure baseline",
                "paper-grade reproduction",
                "medical/safety conclusion",
                "profile/default promotion",
            ],
            ["mapping.simple_hu300_profile", "gate.profile_promotion_prestus_fit_alpha_power_2"],
            "Use as engineering pressure output only; feed readiness/gates, not paper-grade claims.",
        ),
        entry(
            "gate.simple_hu300_post_pressure_readiness",
            "post-pressure paper-grade readiness refresh",
            p["post_pressure_readiness"],
            "readiness_gate",
            "readiness_assessment",
            "M2_standard_engineering_baseline_hardening",
            "block" if paper_ready is False else "pass",
            ["standard pressure missing blocker closed", "remaining paper-grade blockers explicit"],
            ["paper-grade ready", "validated pressure baseline", "medical/safety conclusion"],
            ["run.simple_hu300_dx075_pml12_standard_pressure"],
            "Create read-only CFL/environment gate before any additional pressure comparison.",
        ),
        entry(
            "gate.current_progress_goal",
            "current progress and next-action gate",
            p["progress_goal_gate"],
            "progress_gate",
            "governance_summary",
            "M2_standard_engineering_baseline_hardening",
            "warn",
            ["current baseline and next action are explicit"],
            ["paper-grade ready", "profile promotion", "default mapping change"],
            ["gate.simple_hu300_post_pressure_readiness"],
            "Use registry plus gate status to guide the next read-only governance task.",
        ),
        entry(
            "policy.simulation_presets",
            "simulation preset policy",
            p["simulation_presets"],
            "policy",
            "governance_policy",
            "cross_cutting_policy",
            "pass",
            ["quick/standard/paper_grade separation is explicit"],
            ["using standard as paper-grade", "untracked preset escalation"],
            [],
            "Keep enforcing preset separation in every run/report.",
        ),
        entry(
            "policy.profile_preset_run_contract",
            "profile / preset / run separation contract",
            p["profile_preset_run_contract"],
            "governance_contract",
            "separation_policy",
            "cross_cutting_policy",
            "pass",
            [
                "profile status, preset level, and run claim level are separated",
                "successful standard run does not upgrade profile or paper-grade status",
            ],
            [
                "run success upgrades profile",
                "standard preset equals paper-grade",
                "profile promotion without separate gate",
            ],
            ["run.simple_hu300_dx075_pml12_standard_pressure", "policy.simulation_presets"],
            "Apply this contract to future summaries and validators.",
        ),
        entry(
            "validation.profile_preset_run_conformance",
            "profile / preset / run conformance validation",
            p["profile_preset_run_conformance"],
            "validation_report",
            "governance_validation",
            "cross_cutting_policy",
            "pass",
            ["current standard run conforms to profile/preset/run separation"],
            ["claim upgrade through run success"],
            ["policy.profile_preset_run_contract"],
            "Keep conformance passing when adding future run summaries.",
        ),
        entry(
            "policy.gate_state_machine",
            "standalone gate state machine",
            p["gate_state_machine"],
            "gate_contract",
            "gate_state_machine",
            "cross_cutting_policy",
            "pass",
            ["fixed gate names and next actions are machine-readable"],
            ["implicit gate changes", "claim upgrade without gate transition"],
            ["policy.profile_preset_run_contract"],
            "Use this state machine before choosing pressure, paper-grade, or profile-promotion tasks.",
        ),
        entry(
            "validation.gate_state_machine",
            "gate state machine validation",
            p["gate_state_machine_validation"],
            "validation_report",
            "governance_validation",
            "cross_cutting_policy",
            "pass",
            ["current gate state machine validates"],
            ["missing gate next_action", "invalid status", "unlocked prohibited claims"],
            ["policy.gate_state_machine"],
            "Keep this validation passing whenever gates are refreshed.",
        ),
        entry(
            "ledger.run_ledger",
            "real run ledger",
            p["run_ledger"],
            "run_ledger",
            "execution_governance",
            "M2_standard_engineering_baseline_hardening",
            "pass",
            ["executed standard pressure run is recorded with authorization and claim level"],
            ["untracked pressure run", "missing authorization", "missing claim boundary"],
            ["run.simple_hu300_dx075_pml12_standard_pressure"],
            "Append future real runs here and validate before registry refresh.",
        ),
        entry(
            "validation.run_ledger",
            "run ledger validation",
            p["run_ledger_validation"],
            "validation_report",
            "governance_validation",
            "M2_standard_engineering_baseline_hardening",
            "pass",
            ["run ledger validates"],
            ["unvalidated run ledger"],
            ["ledger.run_ledger"],
            "Keep ledger validation passing after every real run.",
        ),
        entry(
            "policy.maturity_model",
            "M0-M5 maturity model",
            p["maturity_model"],
            "maturity_model",
            "governance_policy",
            "cross_cutting_policy",
            "pass",
            ["current maturity is M2 and higher levels have explicit blockers"],
            ["unstated maturity upgrade", "paper-grade shortcut"],
            ["policy.gate_state_machine", "ledger.run_ledger"],
            "Use this model when deciding the next governance target.",
        ),
        entry(
            "validation.maturity_model",
            "maturity model validation",
            p["maturity_model_validation"],
            "validation_report",
            "governance_validation",
            "cross_cutting_policy",
            "pass",
            ["maturity model validates"],
            ["invalid maturity transition"],
            ["policy.maturity_model"],
            "Keep maturity validation passing after gate changes.",
        ),
        entry(
            "policy.claim_policy",
            "standalone claim policy",
            p["claim_policy"],
            "claim_policy",
            "governance_policy",
            "cross_cutting_policy",
            "pass",
            ["allowed and blocked claims are machine-readable"],
            ["paper-grade claim leakage", "medical/safety claim leakage", "profile promotion claim leakage"],
            ["policy.maturity_model", "policy.gate_state_machine", "policy.profile_preset_run_contract"],
            "Require future reports to include claim level, allowed claims, and blocked claims.",
        ),
        entry(
            "validation.claim_policy",
            "claim policy validation",
            p["claim_policy_validation"],
            "validation_report",
            "governance_validation",
            "cross_cutting_policy",
            "pass",
            ["claim policy validates"],
            ["invalid claim policy", "missing blocked claims"],
            ["policy.claim_policy"],
            "Keep claim policy validation passing after any report wording or claim-boundary changes.",
        ),
        entry(
            "manifest.module_boundary",
            "script/module boundary manifest",
            p["module_boundary_manifest"],
            "module_boundary_manifest",
            "governance_manifest",
            "cross_cutting_policy",
            "pass",
            ["root-level scripts are classified by boundary"],
            ["untracked script role", "physical file move during active physics work"],
            ["policy.claim_policy"],
            "Use this manifest before moving scripts or changing import boundaries.",
        ),
        entry(
            "validation.module_boundary",
            "module boundary manifest validation",
            p["module_boundary_manifest_validation"],
            "validation_report",
            "governance_validation",
            "cross_cutting_policy",
            "pass",
            ["module boundary manifest validates"],
            ["unclassified root script", "accidental file move"],
            ["manifest.module_boundary"],
            "Keep module boundary validation passing when adding scripts.",
        ),
        entry(
            "program.m2_baseline_hardening",
            "M2 baseline hardening program",
            p["m2_baseline_hardening_program"],
            "hardening_program",
            "governance_program",
            "M2_standard_engineering_baseline_hardening",
            "pass",
            ["governance prerequisites 1-7 are complete", "next target is read-only CFL/environment gate"],
            ["additional pressure before CFL/environment gate", "paper-grade claim", "validated baseline claim"],
            ["validation.module_boundary", "validation.claim_policy", "validation.maturity_model"],
            "Implement the read-only CFL/environment gate before any additional pressure comparison.",
        ),
        entry(
            "validation.m2_baseline_hardening",
            "M2 baseline hardening program validation",
            p["m2_baseline_hardening_program_validation"],
            "validation_report",
            "governance_validation",
            "M2_standard_engineering_baseline_hardening",
            "pass",
            ["M2 hardening program validates"],
            ["program permits pressure too early", "missing governance prerequisite"],
            ["program.m2_baseline_hardening"],
            "Keep this validation passing when changing the M2 hardening roadmap.",
        ),
        entry(
            "feedback.standard_pressure_authorization",
            "gap feedback for standard pressure authorization/execution",
            p["standard_pressure_gap_feedback"],
            "gap_feedback",
            "post_execution_feedback",
            "M2_standard_engineering_baseline_hardening",
            "pass",
            ["authorization and execution history is documented"],
            ["unattributed pressure run", "untracked authorization"],
            ["run.simple_hu300_dx075_pml12_standard_pressure"],
            "Seed run ledger from this feedback and runner status.",
        ),
        entry(
            "gate.cfl_environment",
            "read-only CFL/environment gate for current standard pressure output",
            p["cfl_environment_gate"],
            "read_only_gate",
            "m2_hardening_gate",
            "M2_standard_engineering_baseline_hardening",
            nested(data["cfl_environment_gate"], ["decision", "gate_status"], "block"),
            [
                "CFL, PML, runtime, backend, and device metadata are indexed for the current standard output",
                "current environment observation is recorded separately from historical run capture",
            ],
            [
                "paper-grade reproduction",
                "validated pressure baseline",
                "medical/safety conclusion",
                "additional pressure without explicit authorization",
            ],
            ["run.simple_hu300_dx075_pml12_standard_pressure", "policy.simulation_presets"],
            "Complete historical environment fields and numerical sensitivity evidence before any stronger claim.",
        ),
    ]


def build_gate_states(data: dict[str, dict[str, Any] | None]) -> dict[str, dict[str, Any]]:
    standard_completed = nested(data["standard_pressure_execution"], ["decision", "standard_pressure_run_completed"], False)
    paper_ready = nested(data["post_pressure_readiness"], ["decision", "paper_grade_ready"], False)
    alpha_state = nested(data["profile_promotion_gate"], ["decision", "recommended_state"], "unknown")
    blocker_count = nested(data["post_pressure_readiness"], ["decision", "paper_grade_blocker_count"], None)
    cfl_gate_status = nested(data["cfl_environment_gate"], ["decision", "gate_status"], "block")
    environment_status = nested(data["cfl_environment_gate"], ["decision", "environment_record_status"], "missing")
    return {
        "mapping_profile_gate": {
            "status": "warn",
            "reason": "simple_hu300 is reproducible baseline but not validated pressure baseline",
            "next_action": "Keep profile as engineering baseline; do not promote defaults.",
        },
        "alpha_semantics_gate": {
            "status": "block",
            "reason": f"source-backed alpha state={alpha_state}; simple_hu300 alpha semantics remain limited",
            "next_action": "Resolve alpha semantics/cross-checks before pressure-profile promotion.",
        },
        "pressure_execution_gate": {
            "status": "pass" if standard_completed else "block",
            "reason": "one user-authorized standard pressure run completed" if standard_completed else "no current standard pressure run",
            "next_action": "Do not run additional pressure until CFL/environment gate is complete.",
        },
        "numerical_quality_gate": {
            "status": "block",
            "reason": (
                "grid convergence and pressure-level PML review remain incomplete; "
                f"CFL/environment gate={cfl_gate_status}, environment_record={environment_status}"
            ),
            "next_action": "Complete environment record and plan numerical sensitivity before any additional pressure comparison.",
        },
        "cfl_environment_gate": {
            "status": cfl_gate_status,
            "reason": f"read-only gate generated; environment_record={environment_status}",
            "next_action": "Record complete environment metadata and keep pressure blocked unless explicitly authorized.",
        },
        "interpretation_gate": {
            "status": "warn",
            "reason": "pressure metrics are engineering-only and not medical/safety conclusions",
            "next_action": "Use metrics for evidence planning, not clinical claims.",
        },
        "paper_grade_gate": {
            "status": "block" if paper_ready is False else "pass",
            "reason": f"paper_grade_ready={paper_ready}; blocker_count={blocker_count}",
            "next_action": "Keep paper-grade blocked until required evidence package exists.",
        },
    }


def build_run_ledger_seed(data: dict[str, dict[str, Any] | None]) -> list[dict[str, Any]]:
    run = data["standard_pressure_execution"]
    return [
        {
            "run_id": "079_candidate_006_simple_hu300_dx075_pml12_standard_2026-06-02",
            "case_id": nested(run, ["case_id"]),
            "candidate_id": nested(run, ["candidate_id"]),
            "profile": nested(run, ["mapping_profile"]),
            "preset": nested(run, ["preset"]),
            "output_dir": nested(run, ["output_dir"]),
            "runner_status": nested(run, ["runner", "status"]),
            "runtime_s": nested(run, ["runner", "runtime_s"]),
            "pressure_generated": nested(run, ["runner", "core_output_exists", "pressure"]),
            "summary_generated": nested(run, ["runner", "core_output_exists", "summary"]),
            "claim_level": "standard_engineering_pressure_output",
            "authorization": "explicit user authorization in current Codex thread",
            "blocked_claims": [
                "validated pressure baseline",
                "paper-grade reproduction",
                "medical/safety conclusion",
            ],
        }
    ]


def build_registry() -> dict[str, Any]:
    data = load_inputs()
    artifacts = build_artifacts(data)
    gate_states = build_gate_states(data)
    run_ledger_seed = build_run_ledger_seed(data)
    missing = [name for name, payload in data.items() if payload is None]
    pressure = data["standard_pressure_execution"]
    readiness = data["post_pressure_readiness"]
    return {
        "registry_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": MODULE,
        "scope": "current evidence registry for simple_hu300 M2 baseline hardening",
        "schema": {
            "path": rel(SCHEMA_PATH),
            "schema_id": "fus-sim.evidence_registry.schema.v1",
        },
        "inputs": {
            "paths": {name: rel(path) for name, path in paths().items()},
            "missing": missing,
        },
        "project_maturity_level": {
            "current": "M2_standard_engineering_baseline_hardening",
            "rationale": "one standard engineering pressure run exists and a read-only CFL/environment gate is indexed; paper-grade and validated profile gates remain blocked",
            "next_target": "M2_environment_record_and_numerical_sensitivity_planning",
        },
        "global_claim_policy": {
            "allowed_claims": [
                "current reproducible engineering baseline uses simple_hu300",
                "one runner-gated standard pressure run completed for 079 candidate_006 dx0.75 PML12",
                "post-pressure readiness keeps paper-grade blocked",
            ],
            "blocked_claims": [
                "validated pressure baseline",
                "paper-grade reproduction",
                "medical or safety conclusion",
                "source-backed alpha pressure eligibility",
                "default profile promotion",
            ],
            "medical_or_safety_conclusion_allowed": False,
            "paper_grade_ready": nested(readiness, ["decision", "paper_grade_ready"], False),
            "profile_promotion_allowed": nested(pressure, ["decision", "profile_promotion_allowed"], False),
            "default_profile_change_allowed": nested(pressure, ["decision", "default_profile_change_allowed"], False),
        },
        "artifact_entries": [artifact.to_dict() for artifact in artifacts],
        "gate_states": gate_states,
        "run_ledger_seed": run_ledger_seed,
        "recommended_next_action": "Complete environment record and numerical sensitivity planning before any additional pressure comparison.",
        "not_executed": [
            "k-Wave simulation",
            "thermal simulation",
            "paper-grade run",
            "profile/default promotion",
        ],
    }


def build_markdown(registry: dict[str, Any]) -> str:
    lines = [
        "# Evidence Registry",
        "",
        "## Maturity",
        "",
        f"- current: `{registry['project_maturity_level']['current']}`",
        f"- rationale: {registry['project_maturity_level']['rationale']}",
        f"- next target: `{registry['project_maturity_level']['next_target']}`",
        "",
        "## Global Claim Policy",
        "",
        "Allowed claims:",
    ]
    lines.extend(f"- {item}" for item in registry["global_claim_policy"]["allowed_claims"])
    lines.append("")
    lines.append("Blocked claims:")
    lines.extend(f"- {item}" for item in registry["global_claim_policy"]["blocked_claims"])
    lines.extend(
        [
            "",
            f"- paper-grade ready: `{registry['global_claim_policy']['paper_grade_ready']}`",
            f"- medical/safety conclusion allowed: `{registry['global_claim_policy']['medical_or_safety_conclusion_allowed']}`",
            "",
            "## Gate States",
            "",
            "| Gate | Status | Reason | Next Action |",
            "|---|---:|---|---|",
        ]
    )
    for gate, payload in registry["gate_states"].items():
        lines.append(f"| `{gate}` | `{payload['status']}` | {payload['reason']} | {payload['next_action']} |")
    lines.extend(["", "## Artifact Entries", ""])
    lines.append("| Artifact | Level | Maturity | Gate | Path |")
    lines.append("|---|---|---|---:|---|")
    for item in registry["artifact_entries"]:
        lines.append(
            f"| `{item['artifact_id']}` | {item['evidence_level']} | {item['maturity_level']} | "
            f"`{item['gate_status']}` | `{item['path']}` |"
        )
    lines.extend(["", "## Run Ledger Seed", ""])
    for run in registry["run_ledger_seed"]:
        lines.append(f"- `{run['run_id']}`: status `{run['runner_status']}`, claim level `{run['claim_level']}`")
    lines.extend(["", "## Recommended Next Action", "", f"- {registry['recommended_next_action']}", "", "## Not Executed", ""])
    lines.extend(f"- {item}" for item in registry["not_executed"])
    lines.append("")
    return "\n".join(lines)


def write_outputs(registry: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    registry_json = OUT_DIR / "evidence_registry.json"
    registry_md = OUT_DIR / "evidence_registry.md"
    registry_json.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    registry_md.write_text(build_markdown(registry), encoding="utf-8")

    feedback = {
        "module": MODULE,
        "feedback_type": "post_execution_gap_feedback",
        "executed_scope": [
            "read current evidence summaries",
            "generated unified evidence registry",
            "generated gate states, claim policy, and run ledger seed",
        ],
        "outputs": {
            "registry_json": rel(registry_json),
            "registry_md": rel(registry_md),
        },
        "decision": {
            "registry_generated": True,
            "paper_grade_ready": registry["global_claim_policy"]["paper_grade_ready"],
            "medical_or_safety_conclusion_allowed": registry["global_claim_policy"][
                "medical_or_safety_conclusion_allowed"
            ],
            "project_maturity_level": registry["project_maturity_level"]["current"],
        },
        "not_executed": registry["not_executed"],
        "recommended_next_step": registry["recommended_next_action"],
    }
    (BRIEF_DIR / "gap_feedback.json").write_text(json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8")
    (BRIEF_DIR / "gap_feedback.md").write_text(
        "\n".join(
            [
                "# Gap Feedback: Evidence Registry",
                "",
                "## Actual Execution",
                "",
                "- Read current evidence summaries.",
                "- Generated unified evidence registry.",
                "- Generated gate states, claim policy, and run ledger seed.",
                "",
                "## Decision",
                "",
                f"- registry generated: `{feedback['decision']['registry_generated']}`",
                f"- paper-grade ready: `{feedback['decision']['paper_grade_ready']}`",
                f"- medical/safety conclusion allowed: `{feedback['decision']['medical_or_safety_conclusion_allowed']}`",
                f"- project maturity level: `{feedback['decision']['project_maturity_level']}`",
                "",
                "## Outputs",
                "",
                f"- `{rel(registry_json)}`",
                f"- `{rel(registry_md)}`",
                "",
                "## Not Executed",
                "",
                "- No k-Wave simulation.",
                "- No thermal simulation.",
                "- No paper-grade run.",
                "- No profile/default promotion.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    registry = build_registry()
    write_outputs(registry)
    print(f"Wrote {rel(OUT_DIR / 'evidence_registry.json')}")
    print(f"Wrote {rel(OUT_DIR / 'evidence_registry.md')}")


if __name__ == "__main__":
    main()
