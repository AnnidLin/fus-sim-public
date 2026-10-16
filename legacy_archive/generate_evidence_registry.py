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
    if path.suffix.lower() == ".jsonl":
        entries = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        ]
        return {"entries": entries, "entry_count": len(entries)}
    if path.suffix.lower() != ".json":
        return {"path": rel(path), "exists": True, "size_bytes": path.stat().st_size}
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
        "grid_dx0p5_run": PROJECT_ROOT / "outputs/corrected_pressure_runs/079_candidate_006_dx0p5_pml12_cfl0p2_standard/runner_status.json",
        "grid_convergence_analysis": PROJECT_ROOT
        / "outputs/ct_grid_convergence_analysis/079_candidate_006/ct_grid_convergence_analysis.json",
        "corrected_dx0p75_run": PROJECT_ROOT
        / "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard/runner_status.json",
        "corrected_dx0p75_summary": PROJECT_ROOT
        / "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard/summary.json",
        "corrected_dx0p75_focus_metrics": PROJECT_ROOT
        / "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard/focus_metrics.json",
        "corrected_dx0p75_gap_feedback": PROJECT_ROOT
        / "outputs/evidence_briefs/corrected_dx0p75_standard_pressure/gap_feedback.json",
        "p3_numerical_sensitivity_plan": PROJECT_ROOT
        / "outputs/p3_numerical_sensitivity_plan/079_candidate_006_dx0p75/p3_numerical_sensitivity_plan.json",
        "p3_numerical_sensitivity_plan_validation": PROJECT_ROOT
        / "outputs/p3_numerical_sensitivity_plan/079_candidate_006_dx0p75/p3_numerical_sensitivity_plan_validation.json",
        "p3_numerical_sensitivity_gap_feedback": PROJECT_ROOT
        / "outputs/evidence_briefs/p3_numerical_sensitivity_plan/gap_feedback.json",
        "p3a_pml16_sensitivity_report": PROJECT_ROOT
        / "outputs/p3a_pml16_sensitivity_analysis/079_candidate_006_dx0p75/p3a_pml16_sensitivity_report.json",
        "p3a_pml16_sensitivity_report_validation": PROJECT_ROOT
        / "outputs/p3a_pml16_sensitivity_analysis/079_candidate_006_dx0p75/p3a_pml16_sensitivity_report_validation.json",
        "p3a_pml16_gap_feedback": PROJECT_ROOT
        / "outputs/evidence_briefs/p3a_pml16_boundary_sensitivity/gap_feedback.json",
        "p3b_cfl0p1_sensitivity_report": PROJECT_ROOT
        / "outputs/p3b_cfl0p1_sensitivity_analysis/079_candidate_006_dx0p75/p3b_cfl0p1_sensitivity_report.json",
        "p3b_cfl0p1_sensitivity_report_validation": PROJECT_ROOT
        / "outputs/p3b_cfl0p1_sensitivity_analysis/079_candidate_006_dx0p75/p3b_cfl0p1_sensitivity_report_validation.json",
        "p3b_cfl0p1_gap_feedback": PROJECT_ROOT
        / "outputs/evidence_briefs/p3b_cfl0p1_timestep_sensitivity/gap_feedback.json",
        "p4_corrected_pennes_summary": PROJECT_ROOT / "outputs/corrected_pennes_thermal/pennes_summary.json",
        "p6a_focus_metric_audit": PROJECT_ROOT
        / "outputs/p6a_focus_metric_semantics_audit/079_candidate_006_dx0p75/focus_metric_semantics_audit.json",
        "p6a_focus_metric_audit_validation": PROJECT_ROOT
        / "outputs/p6a_focus_metric_semantics_audit/079_candidate_006_dx0p75/focus_metric_semantics_audit_validation.json",
        "dx05_sweep000_hotspot_audit": PROJECT_ROOT
        / "outputs/ct_sweep_hotspot_audit/079_sweep_000_dx0p5/hotspot_audit.json",
        "dx05_sweep000_hotspot_axis_profile": PROJECT_ROOT
        / "outputs/ct_sweep_hotspot_audit/079_sweep_000_dx0p5/beam_axis_profile.csv",
       "dx05_sweep000_p038_scaled_validation": PROJECT_ROOT
       / "outputs/ct_sweep_scaled_pressure_validation/079_sweep_000_dx0p5_p038/scaled_pressure_validation.json",
       "dx05_sweep000_p038_scaled_validation_check": PROJECT_ROOT
       / "outputs/ct_sweep_scaled_pressure_validation/079_sweep_000_dx0p5_p038/scaled_pressure_validation_check.json",
        "sweep_005_p500_pressure": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p500/pressure_max_mpa.npz",
        "sweep_005_p500_summary": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p500/summary.json",
        "sweep_005_p500_focus_metrics": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p500/focus_metrics.json",
        "sweep_005_p500_runner_status": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p500/runner_status.json",
        "sweep_005_p500_pennes": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p500/pennes_thermal/pennes_summary.json",
        "sweep_005_p600_pressure": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p600/pressure_max_mpa.npz",
        "sweep_005_p600_summary": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p600/summary.json",
        "sweep_005_p600_focus_metrics": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p600/focus_metrics.json",
        "sweep_005_p600_runner_status": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p600/runner_status.json",
        "sweep_005_p600_pennes": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p600/pennes_thermal/pennes_summary.json",
        "sweep_005_p700_pressure": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p700/pressure_max_mpa.npz",
        "sweep_005_p700_summary": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p700/summary.json",
        "sweep_005_p700_focus_metrics": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p700/focus_metrics.json",
        "sweep_005_p700_runner_status": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p700/runner_status.json",
        "sweep_005_p700_pennes": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p700/pennes_thermal/pennes_summary.json",
        "sweep_005_p800_pressure": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p800/pressure_max_mpa.npz",
        "sweep_005_p800_summary": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p800/summary.json",
        "sweep_005_p800_focus_metrics": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p800/focus_metrics.json",
        "sweep_005_p800_runner_status": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p800/runner_status.json",
        "sweep_005_p800_pennes": PROJECT_ROOT
        / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p800/pennes_thermal/pennes_summary.json",
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
    grid_run_completed = data["grid_dx0p5_run"] is not None and nested(data["grid_dx0p5_run"], ["status"]) == "kwave_ok"
    corrected_run_completed = (
        data["corrected_dx0p75_run"] is not None
        and nested(data["corrected_dx0p75_run"], ["status"]) == "kwave_ok"
    )
    p3_plan_ready = nested(data["p3_numerical_sensitivity_plan_validation"], ["plan_valid"], False) is True
    p3a_report_valid = nested(data["p3a_pml16_sensitivity_report_validation"], ["report_valid"], False) is True
    p3a_stable = nested(data["p3a_pml16_sensitivity_report"], ["decision", "p3a_stable_within_thresholds"], False) is True
    p3b_report_valid = nested(data["p3b_cfl0p1_sensitivity_report_validation"], ["report_valid"], False) is True
    p3b_stable = nested(data["p3b_cfl0p1_sensitivity_report"], ["decision", "p3b_stable_within_thresholds"], False) is True
    p6a_valid = nested(data["p6a_focus_metric_audit_validation"], ["audit_valid"], False) is True
    dx05_hotspot_audit_exists = data["dx05_sweep000_hotspot_audit"] is not None
    dx05_p038_validation_passed = (
        nested(data["dx05_sweep000_p038_scaled_validation"], ["decision", "scaled_validation_passed_local_thermal_gates"], False)
        is True
    )
    sweep_005_p500_exists = data["sweep_005_p500_pressure"] is not None
    sweep_005_p500_runner_ok = data["sweep_005_p500_runner_status"] is not None and nested(data["sweep_005_p500_runner_status"], ["status"]) == "kwave_ok"
    sweep_005_p600_runner_ok = data["sweep_005_p600_runner_status"] is not None and nested(data["sweep_005_p600_runner_status"], ["status"]) == "kwave_ok"
    sweep_005_p700_runner_ok = data["sweep_005_p700_runner_status"] is not None and nested(data["sweep_005_p700_runner_status"], ["status"]) == "kwave_ok"
    sweep_005_p800_runner_ok = data["sweep_005_p800_runner_status"] is not None and nested(data["sweep_005_p800_runner_status"], ["status"]) == "kwave_ok"
    grid_analysis_exists = data["grid_convergence_analysis"] is not None
    grid_analysis_claim_level = nested(
        data["grid_convergence_analysis"],
        ["claim_level"],
        "engineering_grid_convergence_observation",
    )
    grid_resolution_compatible = nested(
        data["grid_convergence_analysis"],
        ["entry_plan_resolution_gate", "compatible"],
        True,
    )

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
            "run.simple_hu300_dx075_pml12_cfl02_corrected_standard_pressure",
            "user-authorized corrected simple_hu300 dx0.75 PML12 CFL0.2 standard pressure run",
            p["corrected_dx0p75_run"],
            "run_summary",
            "corrected_standard_pressure_research_dataset_candidate",
            "M2_standard_engineering_baseline_hardening",
            "warn" if corrected_run_completed else "block",
            [
                "one runner-gated corrected standard pressure execution completed",
                "corrected entry plan matches the dx0.75 acoustic model",
                "target pressure metrics are available for sensitivity planning",
            ],
            [
                "validated pressure baseline",
                "paper-grade reproduction",
                "medical/safety conclusion",
                "profile/default promotion",
                "tuned focus baseline",
                "numerical convergence claim",
            ],
            ["mapping.simple_hu300_profile", "policy.simulation_presets"],
            "Use as the P2 corrected research dataset candidate; plan P3 sensitivity before stronger interpretation.",
        ),
        entry(
            "feedback.corrected_dx0p75_standard_pressure",
            "gap feedback for corrected dx0.75 standard pressure run",
            p["corrected_dx0p75_gap_feedback"],
            "gap_feedback",
            "post_execution_feedback",
            "M2_standard_engineering_baseline_hardening",
            "pass" if p["corrected_dx0p75_gap_feedback"].exists() else "block",
            ["P2 execution details and residual tuning gaps are documented"],
            ["untracked corrected pressure run", "unbounded interpretation"],
            ["run.simple_hu300_dx075_pml12_cfl02_corrected_standard_pressure"],
            "Keep this feedback linked to ledger and manifest updates.",
        ),
        entry(
            "plan.p3_numerical_sensitivity_079_candidate_006_dx0p75",
            "P3 numerical sensitivity one-run authorization packet plan",
            p["p3_numerical_sensitivity_plan"],
            "execution_plan",
            "planning_only_no_execution",
            "M2_standard_engineering_baseline_hardening",
            "pass" if p3_plan_ready else "block",
            [
                "P3a PML16 and P3b CFL0.1 are planned as separate one-run authorization packets",
                "no additional pressure execution is authorized by the plan itself",
            ],
            [
                "additional pressure authorized by planning",
                "pressure batch execution",
                "thermal simulation",
                "numerical convergence claim",
                "paper-grade reproduction",
            ],
            ["run.simple_hu300_dx075_pml12_cfl02_corrected_standard_pressure"],
            "Request explicit authorization for P3a PML16 boundary sensitivity only.",
        ),
        entry(
            "validation.p3_numerical_sensitivity_plan",
            "P3 numerical sensitivity plan validation",
            p["p3_numerical_sensitivity_plan_validation"],
            "validation_report",
            "planning_validation",
            "M2_standard_engineering_baseline_hardening",
            "pass" if p3_plan_ready else "block",
            ["P3 plan validates and contains no --execute command"],
            ["unvalidated P3 planning", "hidden execution authorization"],
            ["plan.p3_numerical_sensitivity_079_candidate_006_dx0p75"],
            "Keep validation passing before any P3 authorization request.",
        ),
        entry(
            "analysis.p3a_pml16_boundary_sensitivity",
            "P3a PML16 boundary sensitivity comparison against corrected P2 baseline",
            p["p3a_pml16_sensitivity_report"],
            "analysis_report",
            "pml_boundary_sensitivity_observation_not_convergence",
            "M2_standard_engineering_baseline_hardening",
            "pass" if p3a_report_valid and p3a_stable else "warn" if p3a_report_valid else "block",
            [
                "P3a PML16 pressure run completed and compared against P2 baseline",
                "PML16 deltas are within predeclared thresholds"
                if p3a_stable
                else "PML16 deltas require review",
            ],
            [
                "validated pressure baseline",
                "paper-grade reproduction",
                "medical/safety conclusion",
                "tuned focus baseline",
                "numerical convergence claim",
            ],
            ["plan.p3_numerical_sensitivity_079_candidate_006_dx0p75"],
            "Request explicit authorization for P3b CFL0.1 timestep sensitivity only."
            if p3a_report_valid and p3a_stable
            else "Pause for P3a boundary analysis before any further pressure run.",
        ),
        entry(
            "validation.p3a_pml16_boundary_sensitivity",
            "P3a PML16 boundary sensitivity report validation",
            p["p3a_pml16_sensitivity_report_validation"],
            "validation_report",
            "analysis_validation",
            "M2_standard_engineering_baseline_hardening",
            "pass" if p3a_report_valid else "block",
            ["P3a report validates and threshold checks pass"],
            ["unvalidated P3a analysis", "hidden convergence claim"],
            ["analysis.p3a_pml16_boundary_sensitivity"],
            "Keep validation passing before P3b authorization request.",
        ),
        entry(
            "analysis.p3b_cfl0p1_timestep_sensitivity",
            "P3b CFL0.1 timestep sensitivity comparison against corrected P2 baseline",
            p["p3b_cfl0p1_sensitivity_report"],
            "analysis_report",
            "cfl_timestep_sensitivity_observation_not_convergence",
            "M2_standard_engineering_baseline_hardening",
            "pass" if p3b_report_valid and p3b_stable else "warn" if p3b_report_valid else "block",
            [
                "P3b CFL0.1 pressure run completed and compared against P2 baseline",
                "CFL0.1 deltas are within predeclared thresholds"
                if p3b_stable
                else "CFL0.1 deltas require review",
            ],
            [
                "validated pressure baseline",
                "paper-grade reproduction",
                "medical/safety conclusion",
                "tuned focus baseline",
                "numerical convergence claim",
            ],
            ["analysis.p3a_pml16_boundary_sensitivity"],
            "Proceed to P3c corrected dx0.5 coordinate-chain prerequisite before any dx0.5 pressure."
            if p3b_report_valid and p3b_stable
            else "Pause for P3b timestep analysis before any further pressure run.",
        ),
        entry(
            "validation.p3b_cfl0p1_timestep_sensitivity",
            "P3b CFL0.1 timestep sensitivity report validation",
            p["p3b_cfl0p1_sensitivity_report_validation"],
            "validation_report",
            "analysis_validation",
            "M2_standard_engineering_baseline_hardening",
            "pass" if p3b_report_valid else "block",
            ["P3b report validates and threshold checks pass"],
            ["unvalidated P3b analysis", "hidden convergence claim"],
            ["analysis.p3b_cfl0p1_timestep_sensitivity"],
            "Keep validation passing before P3c prerequisite work.",
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
            ["executed pressure runs are recorded with authorization and claim level"],
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
        entry(
            "run.simple_hu300_dx05_pml12_cfl02_grid_convergence",
            "user-authorized simple_hu300 dx0.5 PML12 CFL0.2 standard pressure run",
            p["grid_dx0p5_run"],
            "run_summary",
            grid_analysis_claim_level,
            "M2_standard_engineering_baseline_hardening",
            "warn" if grid_run_completed and not grid_resolution_compatible else "pass" if grid_run_completed else "block",
            [
                "one runner-gated dx0.5 standard pressure execution completed",
                "coordinate-mapping diagnostic input available"
                if not grid_resolution_compatible
                else "grid-convergence comparison input available",
            ],
            [
                "validated pressure baseline",
                "paper-grade reproduction",
                "medical/safety conclusion",
                "profile/default promotion",
            ],
            ["run.simple_hu300_dx075_pml12_standard_pressure", "gate.cfl_environment"],
            "Treat as coordinate-mapping diagnostic only until entry_plan resolution is compatible."
            if not grid_resolution_compatible
            else "Treat as engineering grid-convergence observation only; review material deltas before further runs.",
        ),
        entry(
            "analysis.ct_grid_convergence_079_candidate_006",
            "CT grid convergence analysis for 079 candidate_006 dx0.75 vs dx0.5",
            p["grid_convergence_analysis"],
            "analysis_report",
            grid_analysis_claim_level,
            "M2_standard_engineering_baseline_hardening",
            "block" if grid_analysis_exists and not grid_resolution_compatible else "warn" if grid_analysis_exists else "block",
            [
                "entry-plan resolution mismatch is diagnosed"
                if not grid_resolution_compatible
                else "dx0.75 and dx0.5 standard engineering pressure metrics are compared"
            ],
            [
                "validated convergence",
                "paper-grade reproduction",
                "medical/safety conclusion",
                "profile/default promotion",
            ],
            [
                "run.simple_hu300_dx075_pml12_standard_pressure",
                "run.simple_hu300_dx05_pml12_cfl02_grid_convergence",
            ],
            "Regenerate or transform entry_plan for the target acoustic model resolution before another pressure run."
            if not grid_resolution_compatible
            else "Review material grid deltas before deciding another grid point or paper-grade plan.",
        ),
        entry(
            "analysis.p6a_focus_metric_semantics_audit",
            "P6a beam-axis focus metric and nearfield semantics audit",
            p["p6a_focus_metric_audit"],
            "analysis_report",
            "read_only_metric_semantics_audit",
            "M2_standard_engineering_baseline_hardening",
            "pass" if p6a_valid else "block",
            ["legacy focus fields preserved", "beam-axis and post-entry peaks are explicitly separated"],
            ["prefocal root cause fully established", "tuned focus", "numerical convergence", "medical/safety conclusion"],
            ["run.simple_hu300_dx075_pml12_cfl02_corrected_standard_pressure"],
            "Proceed to P6b post-skull beam-axis profile and interface audit; do not run pressure.",
        ),
        entry(
            "validation.p6a_focus_metric_semantics_audit",
            "P6a focus metric semantics audit validation",
            p["p6a_focus_metric_audit_validation"],
            "validation_report",
            "read_only_analysis_validation",
            "M2_standard_engineering_baseline_hardening",
            "pass" if p6a_valid else "block",
            ["P6a audit validation checks pass"],
            ["unvalidated focus reinterpretation"],
            ["analysis.p6a_focus_metric_semantics_audit"],
            "Keep validation passing before P6b interpretation.",
        ),
        entry(
            "analysis.dx05_sweep000_hotspot_audit",
            "dx0.5 sweep_000 hotspot localization and source-pressure screening audit",
            p["dx05_sweep000_hotspot_audit"],
            "analysis_report",
            "hotspot_localization_and_source_pressure_screening_not_validation",
            "M2_standard_engineering_baseline_hardening",
            "warn" if dx05_hotspot_audit_exists else "block",
            [
                "dx0.5 pressure, heat-source, and CEM43 hotspots are localized against material labels",
                "source-pressure screening estimate is available for planning",
            ],
            [
                "validated source-pressure safety threshold",
                "numerical convergence",
                "paper-grade pressure baseline",
                "medical/safety conclusion",
            ],
            ["analysis.ct_grid_convergence_079_candidate_006"],
            "Review hotspot geometry before requesting exactly one scaled-pressure validation run.",
        ),
        entry(
            "data.dx05_sweep000_hotspot_axis_profile",
            "dx0.5 sweep_000 central beam-axis material and pressure profile",
            p["dx05_sweep000_hotspot_axis_profile"],
            "tabular_profile",
            "read_only_hotspot_supporting_data",
            "M2_standard_engineering_baseline_hardening",
            "warn" if dx05_hotspot_audit_exists else "block",
            ["central beam-axis labels, pressure, temperature rise, and CEM43 are tabulated"],
            ["validated source-pressure safety threshold", "medical/safety conclusion"],
            ["analysis.dx05_sweep000_hotspot_audit"],
            "Use as supporting evidence for hotspot geometry review only.",
        ),
        entry(
            "analysis.dx05_sweep000_p038_scaled_validation",
            "dx0.5 sweep_000 0.38 MPa scaled-pressure validation",
            p["dx05_sweep000_p038_scaled_validation"],
            "analysis_report",
            "scaled_pressure_engineering_validation_not_clinical_safety",
            "M2_standard_engineering_baseline_hardening",
            "warn" if dx05_p038_validation_passed else "block",
            ["0.38 MPa passes local engineering thermal-dose gates in the approximate Pennes model"],
            [
                "clinical or medical safety",
                "paper-grade pressure baseline",
                "numerical convergence",
                "tuned focus",
            ],
            ["analysis.dx05_sweep000_hotspot_audit"],
            "Use as an engineering validation point only; improve focus or validate assumptions before stronger claims.",
        ),
        entry(
            "validation.dx05_sweep000_p038_scaled_validation",
            "dx0.5 sweep_000 0.38 MPa scaled validation boundary check",
            p["dx05_sweep000_p038_scaled_validation_check"],
            "validation_report",
            "engineering_validation_boundary_check",
            "M2_standard_engineering_baseline_hardening",
            "pass" if dx05_p038_validation_passed else "block",
            ["scaled validation checks pass and claim boundaries are explicit"],
            ["unbounded thermal safety interpretation"],
            ["analysis.dx05_sweep000_p038_scaled_validation"],
           "Keep this validation passing before citing the scaled run.",
       ),
        entry(
            "data.sweep_005_p500_pressure",
            "sweep_005 p500 pressure maximum field",
            p["sweep_005_p500_pressure"],
            "data_array",
            "sweep_scan_pressure_field",
            "M2_standard_engineering_baseline_hardening",
            "pass" if sweep_005_p500_runner_ok else "block",
            ["sweep_005 p500 maximum pressure field is available"],
            ["validated pressure baseline", "paper-grade reproduction", "medical/safety conclusion", "tuned focus baseline"],
            ["execution.sweep_005_p500_runner_status"],
            "Use as a sweep-scan data point; do not promote to baseline without further validation.",
        ),
        entry(
            "data.sweep_005_p500_summary",
            "sweep_005 p500 run summary",
            p["sweep_005_p500_summary"],
            "run_summary",
            "sweep_scan_pressure_summary",
            "M2_standard_engineering_baseline_hardening",
            "pass" if sweep_005_p500_runner_ok else "block",
            ["sweep_005 p500 configuration and pressure metrics are documented"],
            ["validated pressure baseline", "paper-grade reproduction", "medical/safety conclusion"],
            ["execution.sweep_005_p500_runner_status"],
            "Use as a sweep-scan summary only; keep stronger claims blocked.",
        ),
        entry(
            "data.sweep_005_p500_focus_metrics",
            "sweep_005 p500 focus metrics",
            p["sweep_005_p500_focus_metrics"],
            "metrics_summary",
            "sweep_scan_focus_metrics",
            "M2_standard_engineering_baseline_hardening",
            "pass" if sweep_005_p500_runner_ok else "block",
            ["sweep_005 p500 focal gain and target pressure metrics are documented"],
            ["tuned focus baseline", "validated focus", "paper-grade reproduction", "medical/safety conclusion"],
            ["data.sweep_005_p500_summary", "execution.sweep_005_p500_runner_status"],
            "Use as a sweep-scan focus observation only; do not claim tuned focus.",
        ),
        entry(
            "data.sweep_005_p500_pennes",
            "sweep_005 p500 Pennes thermal summary",
            p["sweep_005_p500_pennes"],
            "thermal_summary",
            "sweep_scan_pennes_thermal_summary",
            "M2_standard_engineering_baseline_hardening",
            "pass" if data["sweep_005_p500_pennes"] is not None else "block",
            ["sweep_005 p500 approximate Pennes thermal dose summary is documented"],
            ["clinical or medical safety", "validated thermal dose", "paper-grade reproduction", "medical/safety conclusion"],
            ["data.sweep_005_p500_pressure", "execution.sweep_005_p500_runner_status"],
            "Use as a sweep-scan thermal observation only; do not claim clinical safety.",
        ),
        entry(
            "execution.sweep_005_p500_runner_status",
            "sweep_005 p500 runner status",
            p["sweep_005_p500_runner_status"],
            "execution_status",
            "sweep_scan_execution_status",
            "M2_standard_engineering_baseline_hardening",
            "pass" if sweep_005_p500_runner_ok else "block",
            ["sweep_005 p500 pressure run was executed and reported"],
            ["validated pressure baseline", "paper-grade reproduction", "medical/safety conclusion"],
            [],
            "Verify dry-run and execution logs before citing the sweep-scan data.",
        ),
        entry(
            "data.sweep_005_p600_pressure",
            "sweep_005 p600 pressure maximum field",
            p["sweep_005_p600_pressure"],
            "data_array",
            "sweep_scan_pressure_field",
            "M2_standard_engineering_baseline_hardening",
            "pass" if sweep_005_p600_runner_ok else "block",
            ["sweep_005 p600 maximum pressure field is available"],
            ["validated pressure baseline", "paper-grade reproduction", "medical/safety conclusion", "tuned focus baseline"],
            ["execution.sweep_005_p600_runner_status"],
            "Use as a sweep-scan data point; do not promote to baseline without further validation.",
        ),
        entry(
            "data.sweep_005_p600_summary",
            "sweep_005 p600 run summary",
            p["sweep_005_p600_summary"],
            "run_summary",
            "sweep_scan_pressure_summary",
            "M2_standard_engineering_baseline_hardening",
            "pass" if sweep_005_p600_runner_ok else "block",
            ["sweep_005 p600 configuration and pressure metrics are documented"],
            ["validated pressure baseline", "paper-grade reproduction", "medical/safety conclusion"],
            ["execution.sweep_005_p600_runner_status"],
            "Use as a sweep-scan summary only; keep stronger claims blocked.",
        ),
        entry(
            "data.sweep_005_p600_focus_metrics",
            "sweep_005 p600 focus metrics",
            p["sweep_005_p600_focus_metrics"],
            "metrics_summary",
            "sweep_scan_focus_metrics",
            "M2_standard_engineering_baseline_hardening",
            "pass" if sweep_005_p600_runner_ok else "block",
            ["sweep_005 p600 focal gain and target pressure metrics are documented"],
            ["tuned focus baseline", "validated focus", "paper-grade reproduction", "medical/safety conclusion"],
            ["data.sweep_005_p600_summary", "execution.sweep_005_p600_runner_status"],
            "Use as a sweep-scan focus observation only; do not claim tuned focus.",
        ),
        entry(
            "data.sweep_005_p600_pennes",
            "sweep_005 p600 Pennes thermal summary",
            p["sweep_005_p600_pennes"],
            "thermal_summary",
            "sweep_scan_pennes_thermal_summary",
            "M2_standard_engineering_baseline_hardening",
            "pass" if data["sweep_005_p600_pennes"] is not None else "block",
            ["sweep_005 p600 approximate Pennes thermal dose summary is documented"],
            ["clinical or medical safety", "validated thermal dose", "paper-grade reproduction", "medical/safety conclusion"],
            ["data.sweep_005_p600_pressure", "execution.sweep_005_p600_runner_status"],
            "Use as a sweep-scan thermal observation only; do not claim clinical safety.",
        ),
        entry(
            "execution.sweep_005_p600_runner_status",
            "sweep_005 p600 runner status",
            p["sweep_005_p600_runner_status"],
            "execution_status",
            "sweep_scan_execution_status",
            "M2_standard_engineering_baseline_hardening",
            "pass" if sweep_005_p600_runner_ok else "block",
            ["sweep_005 p600 pressure run was executed and reported"],
            ["validated pressure baseline", "paper-grade reproduction", "medical/safety conclusion"],
            [],
            "Verify dry-run and execution logs before citing the sweep-scan data.",
        ),
        entry(
            "data.sweep_005_p700_pressure",
            "sweep_005 p700 pressure maximum field",
            p["sweep_005_p700_pressure"],
            "data_array",
            "sweep_scan_pressure_field",
            "M2_standard_engineering_baseline_hardening",
            "pass" if sweep_005_p700_runner_ok else "block",
            ["sweep_005 p700 maximum pressure field is available"],
            ["validated pressure baseline", "paper-grade reproduction", "medical/safety conclusion", "tuned focus baseline"],
            ["execution.sweep_005_p700_runner_status"],
            "Use as a sweep-scan data point; do not promote to baseline without further validation.",
        ),
        entry(
            "data.sweep_005_p700_summary",
            "sweep_005 p700 run summary",
            p["sweep_005_p700_summary"],
            "run_summary",
            "sweep_scan_pressure_summary",
            "M2_standard_engineering_baseline_hardening",
            "pass" if sweep_005_p700_runner_ok else "block",
            ["sweep_005 p700 configuration and pressure metrics are documented"],
            ["validated pressure baseline", "paper-grade reproduction", "medical/safety conclusion"],
            ["execution.sweep_005_p700_runner_status"],
            "Use as a sweep-scan summary only; keep stronger claims blocked.",
        ),
        entry(
            "data.sweep_005_p700_focus_metrics",
            "sweep_005 p700 focus metrics",
            p["sweep_005_p700_focus_metrics"],
            "metrics_summary",
            "sweep_scan_focus_metrics",
            "M2_standard_engineering_baseline_hardening",
            "pass" if sweep_005_p700_runner_ok else "block",
            ["sweep_005 p700 focal gain and target pressure metrics are documented"],
            ["tuned focus baseline", "validated focus", "paper-grade reproduction", "medical/safety conclusion"],
            ["data.sweep_005_p700_summary", "execution.sweep_005_p700_runner_status"],
            "Use as a sweep-scan focus observation only; do not claim tuned focus.",
        ),
        entry(
            "data.sweep_005_p700_pennes",
            "sweep_005 p700 Pennes thermal summary",
            p["sweep_005_p700_pennes"],
            "thermal_summary",
            "sweep_scan_pennes_thermal_summary",
            "M2_standard_engineering_baseline_hardening",
            "pass" if data["sweep_005_p700_pennes"] is not None else "block",
            ["sweep_005 p700 approximate Pennes thermal dose summary is documented"],
            ["clinical or medical safety", "validated thermal dose", "paper-grade reproduction", "medical/safety conclusion"],
            ["data.sweep_005_p700_pressure", "execution.sweep_005_p700_runner_status"],
            "Use as a sweep-scan thermal observation only; do not claim clinical safety.",
        ),
        entry(
            "execution.sweep_005_p700_runner_status",
            "sweep_005 p700 runner status",
            p["sweep_005_p700_runner_status"],
            "execution_status",
            "sweep_scan_execution_status",
            "M2_standard_engineering_baseline_hardening",
            "pass" if sweep_005_p700_runner_ok else "block",
            ["sweep_005 p700 pressure run was executed and reported"],
            ["validated pressure baseline", "paper-grade reproduction", "medical/safety conclusion"],
            [],
            "Verify dry-run and execution logs before citing the sweep-scan data.",
        ),
        entry(
            "data.sweep_005_p800_pressure",
            "sweep_005 p800 pressure maximum field",
            p["sweep_005_p800_pressure"],
            "data_array",
            "sweep_scan_pressure_field",
            "M2_standard_engineering_baseline_hardening",
            "pass" if sweep_005_p800_runner_ok else "block",
            ["sweep_005 p800 maximum pressure field is available"],
            ["validated pressure baseline", "paper-grade reproduction", "medical/safety conclusion", "tuned focus baseline"],
            ["execution.sweep_005_p800_runner_status"],
            "Use as a sweep-scan data point; do not promote to baseline without further validation.",
        ),
        entry(
            "data.sweep_005_p800_summary",
            "sweep_005 p800 run summary",
            p["sweep_005_p800_summary"],
            "run_summary",
            "sweep_scan_pressure_summary",
            "M2_standard_engineering_baseline_hardening",
            "pass" if sweep_005_p800_runner_ok else "block",
            ["sweep_005 p800 configuration and pressure metrics are documented"],
            ["validated pressure baseline", "paper-grade reproduction", "medical/safety conclusion"],
            ["execution.sweep_005_p800_runner_status"],
            "Use as a sweep-scan summary only; keep stronger claims blocked.",
        ),
        entry(
            "data.sweep_005_p800_focus_metrics",
            "sweep_005 p800 focus metrics",
            p["sweep_005_p800_focus_metrics"],
            "metrics_summary",
            "sweep_scan_focus_metrics",
            "M2_standard_engineering_baseline_hardening",
            "pass" if sweep_005_p800_runner_ok else "block",
            ["sweep_005 p800 focal gain and target pressure metrics are documented"],
            ["tuned focus baseline", "validated focus", "paper-grade reproduction", "medical/safety conclusion"],
            ["data.sweep_005_p800_summary", "execution.sweep_005_p800_runner_status"],
            "Use as a sweep-scan focus observation only; do not claim tuned focus.",
        ),
        entry(
            "data.sweep_005_p800_pennes",
            "sweep_005 p800 Pennes thermal summary",
            p["sweep_005_p800_pennes"],
            "thermal_summary",
            "sweep_scan_pennes_thermal_summary",
            "M2_standard_engineering_baseline_hardening",
            "pass" if data["sweep_005_p800_pennes"] is not None else "block",
            ["sweep_005 p800 approximate Pennes thermal dose summary is documented"],
            ["clinical or medical safety", "validated thermal dose", "paper-grade reproduction", "medical/safety conclusion"],
            ["data.sweep_005_p800_pressure", "execution.sweep_005_p800_runner_status"],
            "Use as a sweep-scan thermal observation only; do not claim clinical safety.",
        ),
        entry(
            "execution.sweep_005_p800_runner_status",
            "sweep_005 p800 runner status",
            p["sweep_005_p800_runner_status"],
            "execution_status",
            "sweep_scan_execution_status",
            "M2_standard_engineering_baseline_hardening",
            "pass" if sweep_005_p800_runner_ok else "block",
            ["sweep_005 p800 pressure run was executed and reported"],
            ["validated pressure baseline", "paper-grade reproduction", "medical/safety conclusion"],
            [],
            "Verify dry-run and execution logs before citing the sweep-scan data.",
        ),
   ]


def build_gate_states(data: dict[str, dict[str, Any] | None]) -> dict[str, dict[str, Any]]:
    standard_completed = nested(data["standard_pressure_execution"], ["decision", "standard_pressure_run_completed"], False)
    paper_ready = nested(data["post_pressure_readiness"], ["decision", "paper_grade_ready"], False)
    alpha_state = nested(data["profile_promotion_gate"], ["decision", "recommended_state"], "unknown")
    blocker_count = nested(data["post_pressure_readiness"], ["decision", "paper_grade_blocker_count"], None)
    cfl_gate_status = nested(data["cfl_environment_gate"], ["decision", "gate_status"], "block")
    environment_status = nested(data["cfl_environment_gate"], ["decision", "environment_record_status"], "missing")
    grid_run_completed = data["grid_dx0p5_run"] is not None and nested(data["grid_dx0p5_run"], ["status"]) == "kwave_ok"
    corrected_run_completed = (
        data["corrected_dx0p75_run"] is not None
        and nested(data["corrected_dx0p75_run"], ["status"]) == "kwave_ok"
    )
    p3_plan_ready = nested(data["p3_numerical_sensitivity_plan_validation"], ["plan_valid"], False) is True
    p3a_report_valid = nested(data["p3a_pml16_sensitivity_report_validation"], ["report_valid"], False) is True
    p3a_stable = nested(data["p3a_pml16_sensitivity_report"], ["decision", "p3a_stable_within_thresholds"], False) is True
    p3b_report_valid = nested(data["p3b_cfl0p1_sensitivity_report_validation"], ["report_valid"], False) is True
    p3b_stable = nested(data["p3b_cfl0p1_sensitivity_report"], ["decision", "p3b_stable_within_thresholds"], False) is True
    p6a_valid = nested(data["p6a_focus_metric_audit_validation"], ["audit_valid"], False) is True
    corrected_tuning_note = nested(data["corrected_dx0p75_summary"], ["tuning_note"], "missing corrected tuning note")
    corrected_target_ratio = nested(data["corrected_dx0p75_focus_metrics"], ["target_to_global_peak_ratio"], None)
    grid_resolution_compatible = nested(
        data["grid_convergence_analysis"],
        ["entry_plan_resolution_gate", "compatible"],
        True,
    )
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
            "status": "pass" if standard_completed or corrected_run_completed else "block",
            "reason": (
                "corrected dx0.75 standard pressure run completed after P1 resolution-chain gate"
                if corrected_run_completed
                else
                "user-authorized standard pressure run and one dx0.5 grid-convergence pressure run completed"
                if standard_completed and grid_run_completed
                else "one user-authorized standard pressure run completed"
                if standard_completed
                else "no current standard pressure run"
            ),
            "next_action": "Do not run additional pressure unless separately authorized and evidence-briefed.",
        },
        "numerical_quality_gate": {
            "status": "warn" if corrected_run_completed else "block" if grid_run_completed and not grid_resolution_compatible else "warn" if grid_run_completed else "block",
            "reason": (
                "P6a preserved legacy fields and showed prefocal dominance persists under beam-axis and post-entry semantics"
                if p6a_valid
                else "P3a PML16 and P3b CFL0.1 are complete and stable within thresholds; corrected dx0.5 coordinate-chain prerequisite is next"
                if p3b_report_valid and p3b_stable
                else
                "P3a PML16 completed and stable within thresholds; P3b CFL0.1 is the next authorized-choice candidate"
                if p3a_report_valid and p3a_stable
                else
                f"corrected P2 exists but still needs sensitivity; tuning_note={corrected_tuning_note}; "
                f"target_to_global_peak_ratio={corrected_target_ratio}"
                if corrected_run_completed
                else (
                "entry_plan/model dx mismatch blocks grid-convergence interpretation; "
                if grid_run_completed and not grid_resolution_compatible
                else ""
            )
            + (
                "CFL0.1/CFL0.3, PML16, and one dx0.5 grid-convergence observation exist, "
                "but material grid deltas keep paper-grade and validated convergence blocked; "
                f"CFL/environment gate={cfl_gate_status}, environment_record={environment_status}"
            )),
            "next_action": (
                "Proceed to P6b post-skull beam-axis profile and interface audit; do not run pressure."
                if p6a_valid
                else "Proceed to P3c corrected dx0.5 coordinate-chain prerequisite; do not run dx0.5 pressure yet."
                if p3b_report_valid and p3b_stable
                else
                "Request explicit authorization for P3b CFL0.1 timestep sensitivity only."
                if p3a_report_valid and p3a_stable
                else
                "Request explicit authorization for P3a PML16 boundary sensitivity only."
                if p3_plan_ready
                else "Plan P3 one-run sensitivity packets for corrected dx0.75; do not claim tuned or validated focus yet."
                if corrected_run_completed
                else "Regenerate or transform entry_plan for the target acoustic model resolution before any further pressure run."
                if grid_run_completed and not grid_resolution_compatible
                else "Review grid-convergence deltas before deciding another grid point or paper-grade plan."
            ),
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
    entries = [
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
    grid = data["grid_dx0p5_run"]
    if grid is not None:
        grid_claim_level = nested(
            data["grid_convergence_analysis"],
            ["claim_level"],
            "coordinate_mapping_diagnostic_not_grid_convergence",
        )
        entries.append(
            {
                "run_id": "079_candidate_006_simple_hu300_dx05_pml12_cfl02_standard_2026-06-13",
                "case_id": "079",
                "candidate_id": "candidate_006",
                "profile": "simple_hu300",
                "preset": "standard",
                "output_dir": "outputs/ct_grid_convergence_runs/079_candidate_006_dx0p5_standard",
                "runner_status": nested(grid, ["status"]),
                "runtime_s": nested(grid, ["execution", "runtime_s"]),
                "pressure_generated": nested(grid, ["execution", "core_output_exists", "pressure"]),
                "summary_generated": nested(grid, ["execution", "core_output_exists", "summary"]),
                "claim_level": grid_claim_level,
                "authorization": "explicit user authorization in Codex thread: continue after dx0.5 dry-run gate",
                "blocked_claims": [
                    "validated pressure baseline",
                    "paper-grade reproduction",
                    "medical/safety conclusion",
                    "profile/default promotion",
                ],
            }
        )
    corrected = data["corrected_dx0p75_run"]
    corrected_summary = data["corrected_dx0p75_summary"]
    if corrected is not None:
        entries.append(
            {
                "run_id": "079_candidate_006_simple_hu300_dx075_pml12_cfl02_corrected_standard_2026-06-18",
                "case_id": "079",
                "candidate_id": "candidate_006",
                "profile": "simple_hu300",
                "preset": nested(corrected_summary, ["config", "preset"], "standard"),
                "output_dir": "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard",
                "runner_status": nested(corrected, ["status"]),
                "runtime_s": nested(corrected, ["execution", "runtime_s"]),
                "pressure_generated": nested(corrected, ["execution", "core_output_exists", "pressure"]),
                "summary_generated": nested(corrected, ["execution", "core_output_exists", "summary"]),
                "claim_level": "corrected_standard_pressure_research_dataset_candidate",
                "authorization": "explicit user authorization in Codex thread: continue P2 corrected dx0.75 standard pressure baseline",
                "blocked_claims": [
                    "validated pressure baseline",
                    "paper-grade reproduction",
                    "medical/safety conclusion",
                    "profile/default promotion",
                    "tuned focus baseline",
                    "numerical convergence claim",
                ],
            }
        )
    return entries


def build_registry() -> dict[str, Any]:
    data = load_inputs()
    artifacts = build_artifacts(data)
    gate_states = build_gate_states(data)
    run_ledger_seed = build_run_ledger_seed(data)
    missing = [name for name, payload in data.items() if payload is None]
    pressure = data["standard_pressure_execution"]
    readiness = data["post_pressure_readiness"]
    corrected_run_completed = (
        data["corrected_dx0p75_run"] is not None
        and nested(data["corrected_dx0p75_run"], ["status"]) == "kwave_ok"
    )
    p3_plan_ready = nested(data["p3_numerical_sensitivity_plan_validation"], ["plan_valid"], False) is True
    p3a_report_valid = nested(data["p3a_pml16_sensitivity_report_validation"], ["report_valid"], False) is True
    p3a_stable = nested(data["p3a_pml16_sensitivity_report"], ["decision", "p3a_stable_within_thresholds"], False) is True
    p3b_report_valid = nested(data["p3b_cfl0p1_sensitivity_report_validation"], ["report_valid"], False) is True
    p3b_stable = nested(data["p3b_cfl0p1_sensitivity_report"], ["decision", "p3b_stable_within_thresholds"], False) is True
    p6a_valid = nested(data["p6a_focus_metric_audit_validation"], ["audit_valid"], False) is True
    p4_completed = data["p4_corrected_pennes_summary"] is not None
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
            "rationale": (
                "corrected dx0.75 standard pressure run is indexed as a research dataset candidate; "
                "tuning and numerical sensitivity blockers remain before stronger interpretation"
                if corrected_run_completed
                else "one standard engineering pressure run, one dx0.5 grid-convergence observation, and a read-only CFL/environment gate are indexed; paper-grade and validated profile gates remain blocked"
            ),
            "next_target": "M2_corrected_pressure_numerical_sensitivity_planning"
            if corrected_run_completed
            else "M2_grid_delta_review_and_numerical_sensitivity_planning",
        },
        "global_claim_policy": {
            "allowed_claims": [
                "current reproducible engineering baseline uses simple_hu300",
                "one runner-gated standard pressure run completed for 079 candidate_006 dx0.75 PML12",
                "one runner-gated dx0.5 grid-convergence observation completed for 079 candidate_006",
                "one corrected dx0.75 standard pressure research dataset candidate exists"
                if corrected_run_completed
                else "corrected dx0.75 standard pressure is not yet executed",
                "P3 numerical sensitivity one-run authorization packets are ready"
                if p3_plan_ready
                else "P3 numerical sensitivity one-run authorization packets are not yet ready",
                "P3a PML16 boundary sensitivity is complete and stable within thresholds"
                if p3a_report_valid and p3a_stable
                else "P3a PML16 boundary sensitivity is not yet complete or stable",
                "P3b CFL0.1 timestep sensitivity is complete and stable within thresholds"
                if p3b_report_valid and p3b_stable
                else "P3b CFL0.1 timestep sensitivity is not yet complete or stable",
                "P6a focus metric semantics audit is complete and validated"
                if p6a_valid
                else "P6a focus metric semantics audit is not yet complete",
                "P4 corrected Pennes research dataset exists"
                if p4_completed
                else "P4 corrected Pennes dataset is not yet generated",
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
        "recommended_next_action": (
            "Proceed to P6b post-skull beam-axis profile and interface audit; do not run pressure, thermal, or batch."
            if p6a_valid
            else "Proceed to P3c corrected dx0.5 coordinate-chain prerequisite; no dx0.5 pressure without a corrected dry-run gate and explicit authorization."
            if p3b_report_valid and p3b_stable
            else
            "Request explicit authorization for P3b CFL0.1 timestep sensitivity only; do not run thermal or dx0.5 pressure."
            if p3a_report_valid and p3a_stable
            else
            "Request explicit authorization for P3a PML16 boundary sensitivity only; do not run P3b or thermal."
            if p3_plan_ready
            else
            "Plan P3 one-run sensitivity packets for the corrected dx0.75 dataset; keep tuned-focus and paper-grade claims blocked."
            if corrected_run_completed
            else "Review material dx0.5 grid-convergence deltas and decide whether another grid point or paper-grade plan is justified."
        ),
        "not_executed": (["paper-grade run", "profile/default promotion"] if p4_completed else ["thermal simulation", "paper-grade run", "profile/default promotion"]),
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
