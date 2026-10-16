from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from governance_recent_evidence import RECENT_ARTIFACT_SPECS


PROJECT_ROOT = Path(__file__).resolve().parent
REGISTRY_DIR = PROJECT_ROOT / "outputs" / "evidence_registry"
REGISTRY_JSON = REGISTRY_DIR / "evidence_registry.json"
REGISTRY_MD = REGISTRY_DIR / "evidence_registry.md"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact(
    artifact_id: str,
    title: str,
    path: str,
    artifact_type: str,
    evidence_level: str,
    maturity_level: str,
    gate_status: str,
    allowed_claims: list[str],
    blocked_claims: list[str],
    dependencies: list[str],
    recommended_next_action: str,
) -> dict[str, Any]:
    full_path = PROJECT_ROOT / path
    return {
        "artifact_id": artifact_id,
        "title": title,
        "path": path,
        "artifact_type": artifact_type,
        "evidence_level": evidence_level,
        "maturity_level": maturity_level,
        "gate_status": gate_status,
        "allowed_claims": allowed_claims,
        "blocked_claims": blocked_claims,
        "dependencies": dependencies,
        "recommended_next_action": recommended_next_action,
        "sha256": file_sha256(full_path),
        "exists": full_path.exists(),
    }


def upsert_artifacts(registry: dict[str, Any], new_items: list[dict[str, Any]]) -> None:
    by_id = {
        item.get("artifact_id"): item
        for item in registry.get("artifact_entries", [])
        if isinstance(item, dict)
    }
    for item in new_items:
        by_id[item["artifact_id"]] = item
    registry["artifact_entries"] = list(by_id.values())


def write_markdown(registry: dict[str, Any]) -> None:
    lines = [
        "# Evidence Registry",
        "",
        "## Maturity",
        "",
        f"- current: `{registry['project_maturity_level']['current']}`",
        f"- rationale: {registry['project_maturity_level']['rationale']}",
        f"- next target: `{registry['project_maturity_level']['next_target']}`",
        "",
        "## Gate States",
        "",
        "| Gate | Status | Reason | Next Action |",
        "|---|---:|---|---|",
    ]
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
    lines.extend(["", "## Recommended Next Action", "", f"- {registry['recommended_next_action']}", ""])
    REGISTRY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    registry = json.loads(REGISTRY_JSON.read_text(encoding="utf-8-sig"))
    registry["generated_at"] = datetime.now(timezone.utc).isoformat()
    registry["scope"] = "current acoustic-field-first evidence registry for fus-sim M2 baseline hardening"
    registry["project_maturity_level"]["next_target"] = "P0A_diagnose_D60_grid_focus_nonconvergence"
    registry["recommended_next_action"] = (
        "Keep pressure execution stopped. Diagnose D60 source discretization, cross-grid target-distance rounding, and sensor recording architecture without pressure; "
        "create a new Evidence Brief before any source correction or additional simulation."
    )
    paths = registry.setdefault("inputs", {}).setdefault("paths", {})
    paths.update(
        {
            "next_phase_execution_plan": "NEXT_PHASE_EXECUTION_PLAN.md",
            "acoustic_paper_grade_plan": "ACOUSTIC_PAPER_GRADE_EXECUTION_PLAN.md",
            "acoustic_paper_grade_brief": "outputs/evidence_briefs/acoustic_paper_grade_route/evidence_brief.json",
            "acoustic_paper_grade_matrix": "outputs/acoustic_paper_grade_plan_20260711/experiment_matrix.csv",
            "paper_gate_a_brief": "outputs/evidence_briefs/paper_gate_a_trajectory_selection/evidence_brief.json",
            "paper_gate_a_feedback": "outputs/evidence_briefs/paper_gate_a_trajectory_selection/gap_feedback.json",
            "paper_gate_a_selection": "outputs/paper_gate_a_trajectory_selection_079/gate_a_trajectory_selection.json",
            "paper_gate_b_brief": "outputs/evidence_briefs/paper_gate_b_freefield_closure/evidence_brief.json",
            "paper_gate_b_feedback": "outputs/evidence_briefs/paper_gate_b_freefield_closure/gap_feedback.json",
            "paper_gate_b_dry_run_report": "outputs/paper_gate_b_freefield_closure/gate_b_dry_run_report.json",
            "paper_gate_b_dx075_result": "outputs/paper_gate_b_freefield_closure/dx0p75_freefield_result.json",
            "freefield_curvature_report": "outputs/freefield_curvature_calibration/curvature_calibration_report.json",
            "freefield_curvature_feedback": "outputs/evidence_briefs/freefield_curvature_calibration/gap_feedback.md",
            "freefield_aperture_feedback": "outputs/evidence_briefs/freefield_aperture_calibration/gap_feedback.json",
            "acoustic_stage_closeout": "outputs/stage_closeout_20260712.md",
            "d60_resume_brief": "outputs/evidence_briefs/freefield_aperture_calibration_resume_20260713/evidence_brief.json",
            "d60_resume_feedback": "outputs/evidence_briefs/freefield_aperture_calibration_resume_20260713/gap_feedback.json",
            "d60_closure_report": "outputs/freefield_aperture_calibration/d60_dx0p75_resume_20260713/d60_freefield_closure_report.json",
            "d60_gate_a_brief": "outputs/evidence_briefs/paper_gate_a_d60_trajectory_selection/evidence_brief.json",
            "d60_gate_a_feedback": "outputs/evidence_briefs/paper_gate_a_d60_trajectory_selection/gap_feedback.json",
            "d60_gate_a_selection": "outputs/paper_gate_a_d60_trajectory_selection_079/gate_a_d60_trajectory_selection.json",
            "d60_dx0p5_brief": "outputs/evidence_briefs/freefield_d60_dx0p5_convergence/evidence_brief.json",
            "d60_dx0p5_feedback": "outputs/evidence_briefs/freefield_d60_dx0p5_convergence/gap_feedback.json",
            "d60_dx0p5_recovery_brief": "outputs/evidence_briefs/freefield_d60_dx0p5_fieldonly_recovery/evidence_brief.json",
            "d60_dx0p5_recovery_feedback": "outputs/evidence_briefs/freefield_d60_dx0p5_fieldonly_recovery/gap_feedback.json",
            "d60_dx0p5_summary": "outputs/freefield_aperture_calibration/d60_dx0p5_fieldonly_20260713/run/summary.json",
            "d60_grid_convergence_report": "outputs/freefield_aperture_calibration/d60_grid_convergence_20260713/d60_grid_convergence_report.json",
            "alpha_semantics_gap_closure_brief": "outputs/evidence_briefs/alpha_semantics_gap_closure/evidence_brief.json",
            "alpha_semantics_gap_closure_feedback": "outputs/evidence_briefs/alpha_semantics_gap_closure/gap_feedback.json",
            "alpha_semantics_legacy_dry_run": "outputs/evidence_briefs/alpha_semantics_gap_closure/legacy_hu300_dx0p75_dry_run/quality_dry_run_summary.json",
            "alpha_semantics_smoke_model_summary": "outputs/evidence_briefs/alpha_semantics_gap_closure/hu300_max80_model_smoke/summary.json",
            "alpha_semantics_smoke_dry_run": "outputs/evidence_briefs/alpha_semantics_gap_closure/hu300_max80_model_smoke_dry_run/quality_dry_run_summary.json",
            "freefield_current_tuned_summary": "outputs/freefield_current_tuned_calibration/ap30_r35_f500_dx0p75_pml12_standard/free_field_calibration_summary.json",
            "freefield_calibration_feedback": "outputs/evidence_briefs/freefield_calibration/gap_feedback.json",
            "source_freefield_insitu_boundary_brief": "outputs/evidence_briefs/source_freefield_insitu_boundary/evidence_brief.json",
            "source_freefield_insitu_boundary_feedback": "outputs/evidence_briefs/source_freefield_insitu_boundary/gap_feedback.json",
            "source_freefield_insitu_boundary_report": "outputs/source_freefield_insitu_boundary_079/source_freefield_insitu_boundary.json",
            "focus_apodization_brief": "outputs/evidence_briefs/focus_apodization/evidence_brief.json",
            "focus_apodization_feedback": "outputs/evidence_briefs/focus_apodization/gap_feedback.json",
            "focus_apodization_report": "outputs/focus_apodization_review_20260710/apodization_screening_report.json",
            "thick_skull_external_validity_brief": "outputs/evidence_briefs/thick_skull_external_validity/evidence_brief.json",
            "thick_skull_external_validity_feedback": "outputs/evidence_briefs/thick_skull_external_validity/gap_feedback.json",
            "thick_skull_plus5_standard_dry_run": "outputs/thick_skull_candidate_runs/079_offset_y+005_z+000_ap30_r35_dx0p75_pml12_standard_dryrun_v2/dry_run_gate.json",
            "thick_skull_plus5_standard_summary": "outputs/thick_skull_candidate_runs/079_offset_y+005_z+000_ap30_r35_dx0p75_pml12_standard_pressure_20260710/summary.json",
            "thick_skull_plus5_runner_status": "outputs/thick_skull_candidate_runs/079_offset_y+005_z+000_ap30_r35_dx0p75_pml12_standard_pressure_20260710/runner_status.json",
            "thick_skull_external_validity_report": "outputs/thick_skull_external_validity_079/thick_skull_external_validity_report.json",
            "phase_delay_correction_feedback": "outputs/evidence_briefs/source_array_phase_delay_correction/gap_feedback.json",
            "hotspot_mitigation_report": "outputs/hotspot_mitigation_screening_079/hotspot_mitigation_screening_report.json",
            "radius_matched_brief": "outputs/evidence_briefs/radius_matched_geometry_079/evidence_brief.json",
            "radius_matched_feedback": "outputs/evidence_briefs/radius_matched_geometry_079/gap_feedback.json",
            "radius_matched_report": "outputs/radius_matched_geometry_079/radius_matched_geometry_report.json",
            "radius_matched_summary": "outputs/radius_matched_geometry_079/ap30_r74p435_single_bowl_quick_post8/summary.json",
            "radius_matched_phase_brief": "outputs/evidence_briefs/radius_matched_phase_control_079/evidence_brief.json",
            "radius_matched_phase_feedback": "outputs/evidence_briefs/radius_matched_phase_control_079/gap_feedback.json",
            "radius_matched_phase_report": "outputs/radius_matched_phase_control_079/radius_matched_phase_control_report.json",
            "radius_matched_phase_summary": "outputs/radius_matched_phase_control_079/ap30_r74p435_15x15_pathintegral_quick_v2/summary.json",
            "tr_a3_brief": "outputs/evidence_briefs/time_reversal_a3/evidence_brief.json",
            "tr_a3_feedback": "outputs/evidence_briefs/time_reversal_a3/gap_feedback.json",
            "tr_calibrate_summary": "outputs/time_reversal_079_y+5_z0/summary_calibrate.json",
            "tr_refocus_summary": "outputs/time_reversal_079_y+5_z0/summary.json",
            "tr_runner_status": "outputs/time_reversal_079_y+5_z0/runner_status.json",
            "tr_comparison_report": "outputs/time_reversal_comparison_20260717/time_reversal_comparison.json",
            "d60_sensitivity_brief": "outputs/evidence_briefs/d60_pml16_cfl0p1_sensitivity/evidence_brief.json",
        }
    )
    sensitivity_optional_paths = {
        "d60_sensitivity_feedback": "outputs/evidence_briefs/d60_pml16_cfl0p1_sensitivity/gap_feedback.json",
        "d60_pml16_summary": "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pml16_pointwave_20260717/run/summary.json",
        "d60_pml16_runner": "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pml16_pointwave_20260717/run/runner_status.json",
        "d60_cfl0p1_summary": "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_cfl0p1_pointwave_20260717/run/summary.json",
        "d60_cfl0p1_runner": "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_cfl0p1_pointwave_20260717/run/runner_status.json",
    }
    paths.update({key: value for key, value in sensitivity_optional_paths.items() if (PROJECT_ROOT / value).exists()})
    # 2026-07-18 night session (standing delegation): dx0.375 Gate-B residual run is
    # registered once its summary lands; A.4 quick-screen report/feedback likewise.
    night_20260718_optional_paths = {
        "d60_dx0p375_summary": "outputs/freefield_aperture_calibration/d60_r78p330_dx0p375_pointwave_20260718/run/summary.json",
        "d60_dx0p375_runner": "outputs/freefield_aperture_calibration/d60_r78p330_dx0p375_pointwave_20260718/run/runner_status.json",
        "a4_quick_screen_report": "outputs/a4_quick_screen_20260718/a4_quick_screen_report.json",
        "a4_quick_screen_feedback": "outputs/evidence_briefs/a4_quick_screen_tr_gated_trajectories/gap_feedback.json",
    }
    for traj in ("offset_y+00p0_z-20p0", "offset_y+17p5_z-02p5", "offset_y+17p5_z+10p0"):
        safe = traj.replace("+", "p").replace("-", "m")
        night_20260718_optional_paths[f"a4_{safe}_baseline_summary"] = (
            f"outputs/a4_quick_screen_20260718/{traj}/baseline/summary.json"
        )
        night_20260718_optional_paths[f"a4_{safe}_tr_summary"] = (
            f"outputs/a4_quick_screen_20260718/{traj}/tr/summary.json"
        )
    night_20260718_optional_paths.update({
        "a5_selection_brief": "outputs/evidence_briefs/a5_heldout_trajectory_selection/evidence_brief.json",
        "a5_heldout_selection": "outputs/a5_heldout_d60_trajectory_selection_20260719/heldout_selection.json",
        "a5_tr_brief": "outputs/evidence_briefs/a5_heldout_tr_confirmation/evidence_brief.json",
        "a5_tr_report": "outputs/a5_heldout_tr_confirmation_20260719/heldout_tr_report.json",
        "a5_tr_feedback": "outputs/evidence_briefs/a5_heldout_tr_confirmation/gap_feedback.json",
        "tr_generalization_audit": "outputs/tr_generalization_audit_20260719/generalization_audit.json",
    })
    for traj in ("offset_y-10p0_z-02p5", "offset_y+05p0_z+05p0", "offset_y+12p5_z-15p0"):
        safe = traj.replace("+", "p").replace("-", "m")
        night_20260718_optional_paths[f"a5_{safe}_tr_summary"] = (
            f"outputs/a5_heldout_tr_confirmation_20260719/{traj}/tr/summary.json"
        )
        night_20260718_optional_paths[f"a5_{safe}_tr_runner"] = (
            f"outputs/a5_heldout_tr_confirmation_20260719/{traj}/tr/runner_status.json"
        )
    night_20260718_optional_paths.update({
        "a5_hamming_brief": "outputs/evidence_briefs/a5_hotspot_suppression_hamming/evidence_brief.json",
        "a5_hamming_preparation": "outputs/a5_hotspot_suppression_hamming_20260720/offset_y-10p0_z-02p5/tr/hamming_replay_preparation.json",
        "a5_hamming_summary": "outputs/a5_hotspot_suppression_hamming_20260720/offset_y-10p0_z-02p5/tr/summary.json",
        "a5_hamming_runner": "outputs/a5_hotspot_suppression_hamming_20260720/offset_y-10p0_z-02p5/tr/runner_status.json",
        "a5_hamming_report": "outputs/a5_hamming_hotspot_report_20260720/hamming_hotspot_report.json",
        "a5_hamming_feedback": "outputs/evidence_briefs/a5_hotspot_suppression_hamming/gap_feedback.json",
        "dual_point_tr_brief": "outputs/evidence_briefs/dual_point_hotspot_constrained_tr/evidence_brief.json",
        "dual_point_tr_feedback": "outputs/evidence_briefs/dual_point_hotspot_constrained_tr/gap_feedback.json",
        "dual_point_tr_design": "outputs/dual_point_hotspot_constrained_tr_20260720/hotspot_calibration_request.json",
        "dual_point_tr_dryrun": "outputs/dual_point_hotspot_constrained_tr_20260720/hotspot_calibration_dryrun/quality_dry_run_summary.json",
        "dual_point_tr_validation": "outputs/dual_point_hotspot_constrained_tr_20260720/validation.json",
        "bbb_personalized_route_brief": "outputs/evidence_briefs/bbb_personalized_drug_delivery_route/evidence_brief.json",
        "bbb_planning_contract": "planning_contracts/examples/case079_h1_bbb_simulation_plan.json",
        "bbb_hotspot_final_result": "outputs/dual_point_constrained_refocus_20260721/result/four_gate_result.json",
        "bbb_plan_report": "outputs/bbb_simulation_plan_report_20260721/plan_report.json",
        "bbb_plan_report_feedback": "outputs/evidence_briefs/bbb_plan_report/gap_feedback.json",
        "bbb_blend_final_result": "outputs/target_preserving_blend_validation_20260722/result/four_gate_result.json",
        "bbb_second_hotspot_feedback": "outputs/evidence_briefs/second_skull_hotspot_calibration_20260722/gap_feedback.json",
        "bbb_three_vector_feedback": "outputs/evidence_briefs/three_vector_skull_region_optimization_20260722/gap_feedback.json",
        "bbb_skull_region_next_plan": "SKULL_REGION_OPTIMIZATION_PLAN_20260722.md",
    })
    paths.update({key: value for key, value in night_20260718_optional_paths.items() if (PROJECT_ROOT / value).exists()})
    registry["inputs"]["missing"] = [key for key, value in paths.items() if not (PROJECT_ROOT / value).exists()]
    registry["gate_states"]["alpha_semantics_gate"] = {
        "status": "warn",
        "reason": "simple_hu300 missing-metadata fallback is patched and smoke-validated; profile-default promotion remains blocked.",
        "next_action": "Use inferred metadata for new binary-profile models; keep source-backed alpha routes gated until cross-checks close.",
    }
    corrected_gate_b_path = PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_grid_convergence_corrected_20260716/d60_grid_convergence_report.json"
    if corrected_gate_b_path.exists():
        corrected_gate_b = json.loads(corrected_gate_b_path.read_text(encoding="utf-8"))
        gate_b_status = str(corrected_gate_b.get("status", "unknown"))
        dx05_err = corrected_gate_b.get("dx0p5", {}).get("refined_focus_error_percent")
        if gate_b_status == "gate_b_dx075_dx05_pass":
            gate_b_reason = (
                f"D60 Gate A passed and Gate B passed at engineering level (dx0.5 refined focus error "
                f"{dx05_err:.3f}% with complete target waveform); CT pressure still requires separate "
                f"explicit authorization."
            )
        elif gate_b_status == "field_metrics_pass_dx0p5_waveform_gap":
            gate_b_reason = (
                "D60 Gate A passed; Gate B field metrics pass but the dx0.5 target waveform gap "
                "remains (field_metrics_pass_dx0p5_waveform_gap)."
            )
        else:
            gate_b_reason = (
                f"D60 Gate A passed, but Gate B failed ({gate_b_status}; dx0.5 refined focus error "
                f"{dx05_err}%)."
            )
    else:
        gate_b_reason = (
            "D60 Gate A passed, but Gate B failed: dx0.5 refined focus error is 5.472% and the "
            "complete dx0.5 target waveform is missing."
        )
    registry["gate_states"]["pressure_execution_gate"] = {
        "status": "block",
        "reason": gate_b_reason
        + " The gate remains formally blocked for claim-level purposes, but execution is currently "
        "authorized: the user's 2026-07-18 22:50 standing delegation ('全部运行，全部你判断'; no "
        "per-run adjudication requests) supersedes the 2026-07-17 one-shot blanket delegation, "
        "under which the dx0.375 Gate-B residual run (in flight at registration time) and the A.4 "
        "three-trajectory quick screen were launched.",
        "next_action": "Under the 2026-07-18 standing delegation the orchestrator may launch "
        "engineering-level pressure runs directly (dx0.375 in flight; A.4 quick screen in flight; "
        "A.5 unlocked only if the A.4 quick gates pass). The delegation covers execution "
        "authorization only; it does not relax claim-level wording discipline (engineering "
        "evidence, no clinical/paper-grade claims).",
    }
    upsert_artifacts(
        registry,
        [
            artifact(
                "plan.acoustic_paper_grade",
                "canonical acoustic-field-first paper-grade execution plan",
                "ACOUSTIC_PAPER_GRADE_EXECUTION_PLAN.md",
                "execution_plan",
                "project_governance_plan",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["adaptive acoustic manuscript route and stop gates are documented"],
                ["paper-grade result", "clinical or medical safety conclusion"],
                ["brief.acoustic_paper_grade_route"],
                "Execute Gate A geometry-only selection, then Gate B free-field closure.",
            ),
            artifact(
                "brief.acoustic_paper_grade_route",
                "acoustic paper-grade route evidence brief",
                "outputs/evidence_briefs/acoustic_paper_grade_route/evidence_brief.json",
                "evidence_brief",
                "pre_execution_evidence",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["scope, evidence boundaries, and non-authorized execution state are documented"],
                ["pressure execution", "paper-grade result", "clinical safety"],
                [],
                "Use with the canonical plan; create run-specific briefs before execution.",
            ),            artifact(
                "plan.next_phase_execution",
                "near-term P0-P4 execution plan",
                "NEXT_PHASE_EXECUTION_PLAN.md",
                "execution_plan",
                "project_governance_plan",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["near-term execution route is documented"],
                ["paper-grade claim", "clinical or medical safety conclusion"],
                [],
                "Use as the current plan before older M5-first roadmaps.",
            ),
            artifact(
                "brief.freefield_calibration",
                "free-field calibration evidence brief",
                "outputs/evidence_briefs/freefield_calibration/evidence_brief.json",
                "evidence_brief",
                "pre_execution_evidence",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["source/free-field/in-situ pressure boundary requirements are defined"],
                ["execution result", "paper-grade calibration", "transcranial pressure claim"],
                [],
                "Keep execution results in freefield calibration gap feedback.",
            ),            artifact(
                "summary.freefield_current_tuned_standard",
                "P1 current tuned standard free-field calibration summary",
                "outputs/freefield_current_tuned_calibration/ap30_r35_f500_dx0p75_pml12_standard/free_field_calibration_summary.json",
                "free_field_calibration_summary",
                "standard_engineering_validation_not_paper_grade",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["source/free-field pressure boundary for ap30/r35 current tuned geometry"],
                ["transcranial in-situ pressure", "clinical safety", "paper-grade convergence"],
                ["brief.freefield_calibration"],
                "Use for MItc/source-free-field-in-situ boundary documentation.",
            ),
            artifact(
                "feedback.freefield_calibration",
                "free-field calibration gap feedback",
                "outputs/evidence_briefs/freefield_calibration/gap_feedback.json",
                "gap_feedback",
                "post_execution_feedback",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["P1 free-field execution and deviations are documented"],
                ["paper-grade calibration", "hydrophone validation", "transcranial pressure claim"],
                ["summary.freefield_current_tuned_standard"],
                "Select a phase-correction-sensitive skull-crossing geometry next.",
            ),
            artifact(
                "brief.source_freefield_insitu_boundary",
                "source/free-field/in-situ definition evidence brief",
                "outputs/evidence_briefs/source_freefield_insitu_boundary/evidence_brief.json",
                "evidence_brief",
                "pre_execution_evidence",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["matched pressure-chain and MItc definition requirements are documented"],
                ["compliant MItc", "medical or safety conclusion"],
                ["summary.freefield_current_tuned_standard"],
                "Use with the boundary report; pressure magnitude is not PNPtc.",
            ),
            artifact(
                "report.source_freefield_insitu_boundary",
                "Case 079 source/free-field/in-situ boundary report",
                "outputs/source_freefield_insitu_boundary_079/source_freefield_insitu_boundary.json",
                "pressure_definition_boundary_report",
                "engineering_boundary_not_mitc",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["matched corrected/free-field ratios", "MItc calculation boundary"],
                ["thick-skull transmission", "compliant MItc", "clinical safety"],
                ["brief.source_freefield_insitu_boundary"],
                "Matched target-window ratio is 32.335%; keep the edge-skimming interpretation.",
            ),
            artifact(
                "feedback.source_freefield_insitu_boundary",
                "source/free-field/in-situ boundary gap feedback",
                "outputs/evidence_briefs/source_freefield_insitu_boundary/gap_feedback.json",
                "gap_feedback",
                "post_execution_feedback",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["P1.3 boundary closure and remaining waveform gap are recorded"],
                ["MItc or safety claim"],
                ["report.source_freefield_insitu_boundary"],
                "Obtain waveform-derived PNPtc on an interpretable skull-crossing run.",
            ),
            artifact(
                "brief.focus_apodization",
                "radial focus apodization correction brief",
                "outputs/evidence_briefs/focus_apodization/evidence_brief.json",
                "evidence_brief",
                "pre_execution_evidence",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["Tukey radial semantics and regression criteria are defined"],
                ["pressure result", "real-skull confirmation"],
                ["plan.next_phase_execution"],
                "Use only for the scoped radial Tukey correction.",
            ),
            artifact(
                "report.focus_apodization",
                "overnight source-array apodization recovery report",
                "outputs/focus_apodization_review_20260710/apodization_screening_report.json",
                "diagnostic_report",
                "quick_synthetic_functional_trend_only",
                "M2_standard_engineering_baseline_hardening",
                "warn",
                ["Hann/Hamming screening trend", "Tukey defect diagnosis"],
                ["source-safe pressure validation", "standard confirmation", "clinical safety"],
                ["brief.focus_apodization"],
                "Synthetic source mask intersects soft tissue; do not promote the pressure result.",
            ),
            artifact(
                "feedback.focus_apodization",
                "focus apodization correction gap feedback",
                "outputs/evidence_briefs/focus_apodization/gap_feedback.json",
                "gap_feedback",
                "post_execution_feedback",
                "M2_standard_engineering_baseline_hardening",
                "warn",
                ["code correction and source-safety stop are documented"],
                ["corrected Tukey pressure effect", "real-skull validation"],
                ["report.focus_apodization"],
                "Resume apodization only on a source-safe geometry.",
            ),
            artifact(
                "brief.thick_skull_external_validity",
                "Case 079 (+5,0) thick-skull validation brief",
                "outputs/evidence_briefs/thick_skull_external_validity/evidence_brief.json",
                "evidence_brief",
                "pre_execution_evidence",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["matched ap30/r35 standard dry-run and pressure acceptance gates"],
                ["pressure result", "paper-grade or safety claim"],
                ["report.source_freefield_insitu_boundary"],
                "Pressure execution remains separately authorized.",
            ),
            artifact(
                "validation.thick_skull_plus5_standard_dry_run",
                "Case 079 (+5,0) ap30/r35 standard dry-run gate",
                "outputs/thick_skull_candidate_runs/079_offset_y+005_z+000_ap30_r35_dx0p75_pml12_standard_dryrun_v2/dry_run_gate.json",
                "dry_run_quality_summary",
                "standard_pressure_readiness_not_execution",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["PPW/PML/CFL/source-safety readiness"],
                ["pressure field", "thick-skull external validity", "safety claim"],
                ["brief.thick_skull_external_validity"],
                "Ready for exactly one explicitly authorized pressure run.",
            ),
            artifact(
                "summary.thick_skull_plus5_standard_pressure",
                "Case 079 (+5,0) ap30/r35 standard pressure summary",
                "outputs/thick_skull_candidate_runs/079_offset_y+005_z+000_ap30_r35_dx0p75_pml12_standard_pressure_20260710/summary.json",
                "pressure_summary",
                "standard_engineering_external_validity_failure_observation",
                "M2_standard_engineering_baseline_hardening",
                "warn",
                ["matched standard pressure execution", "target waveform at the target", "skull-entry hotspot observation"],
                ["tuned focus", "compliant MItc", "clinical safety", "paper-grade convergence"],
                ["validation.thick_skull_plus5_standard_dry_run"],
                "Use as failure evidence: target-window 0.596 MPa and global skull peak 9.698 MPa.",
            ),
            artifact(
                "report.thick_skull_external_validity",
                "Case 079 thick-skull external-validity report",
                "outputs/thick_skull_external_validity_079/thick_skull_external_validity_report.json",
                "external_validity_report",
                "standard_engineering_external_validity_failure_observation",
                "M2_standard_engineering_baseline_hardening",
                "warn",
                ["matched free-field ratios", "hotspot location", "target-site PNP boundary"],
                ["tuned focus", "compliant MItc", "thermal safety", "paper-grade validity"],
                ["summary.thick_skull_plus5_standard_pressure"],
                "Do not start thermal work or another pressure batch before acoustic mitigation.",
            ),
            artifact(
                "feedback.thick_skull_external_validity",
                "Case 079 (+5,0) standard execution gap feedback",
                "outputs/evidence_briefs/thick_skull_external_validity/gap_feedback.json",
                "gap_feedback",
                "post_execution_feedback",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["dry-run history, standard execution, focus failure, and remaining gaps are recorded"],
                ["tuned focus", "MItc", "medical safety"],
                ["report.thick_skull_external_validity"],
                "Return to source-safe quick hotspot-mitigation screening.",
            ),
            artifact(
                "brief.alpha_semantics_gap_closure",
                "alpha semantics gap closure evidence brief",
                "outputs/evidence_briefs/alpha_semantics_gap_closure/evidence_brief.json",
                "evidence_brief",
                "pre_execution_evidence",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["P0 metadata closure criteria are documented"],
                ["execution result", "profile-default promotion"],
                ["plan.next_phase_execution"],
                "Keep execution results in gap_feedback.",
            ),
            artifact(
                "feedback.alpha_semantics_gap_closure",
                "alpha semantics gap closure gap feedback",
                "outputs/evidence_briefs/alpha_semantics_gap_closure/gap_feedback.json",
                "gap_feedback",
                "post_execution_feedback",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["P0 metadata closure execution and verification are documented"],
                ["profile-default promotion", "new pressure field"],
                ["brief.alpha_semantics_gap_closure"],
                "Use this feedback to decide P1 free-field calibration readiness.",
            ),
            artifact(
                "validation.alpha_semantics_legacy_dry_run",
                "legacy hu300 dry-run alpha semantics compatibility check",
                "outputs/evidence_briefs/alpha_semantics_gap_closure/legacy_hu300_dx0p75_dry_run/quality_dry_run_summary.json",
                "dry_run_quality_summary",
                "metadata_compatibility_validation",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["legacy missing alpha metadata no longer implies explicit pressure rejection"],
                ["new pressure field", "paper-grade claim"],
                ["brief.alpha_semantics_gap_closure"],
                "Use as solver fallback evidence only.",
            ),
            artifact(
                "validation.alpha_semantics_smoke_model",
                "new hu300 smoke model alpha semantics metadata check",
                "outputs/evidence_briefs/alpha_semantics_gap_closure/hu300_max80_model_smoke/summary.json",
                "model_summary",
                "builder_metadata_validation",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["new binary profile model writes inferred alpha semantics"],
                ["production model replacement", "new pressure field"],
                ["brief.alpha_semantics_gap_closure"],
                "Use as builder metadata smoke evidence only.",
            ),
            artifact(
                "validation.alpha_semantics_smoke_dry_run",
                "new hu300 smoke model dry-run alpha semantics check",
                "outputs/evidence_briefs/alpha_semantics_gap_closure/hu300_max80_model_smoke_dry_run/quality_dry_run_summary.json",
                "dry_run_quality_summary",
                "solver_metadata_validation",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["new inferred alpha semantics are pressure-eligible at the alpha metadata layer"],
                ["production model replacement", "new pressure field"],
                ["validation.alpha_semantics_smoke_model"],
                "Use as dry-run metadata evidence only.",
            ),
            artifact(
                "report.reference_paper_gap_matrix_20260715",
                "Reference paper gap matrix for acoustic-field-first manuscript",
                "outputs/reference_paper_gap_matrix_20260715/reference_paper_gap_matrix.json",
                "planning_report",
                "literature_alignment_gap_assessment",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["reference paper parameters aligned with current project state", "gap levels classified as satisfied/fillable/requires_new_computation/currently_unachievable"],
                ["new pressure field", "experimental validation", "paper-grade convergence claim"],
                [],
                "Proceed to paper skeleton and results package using only satisfied/fillable items.",
            ),
            artifact(
                "report.paper_skeleton_20260715",
                "Manuscript skeleton and Figure 1 package for D60 free-field source calibration",
                "outputs/paper_skeleton_20260715/paper_skeleton.json",
                "planning_report",
                "manuscript_skeleton_and_figure_package",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["manuscript skeleton generated from existing free-field data", "figure 1 and tables traceable to JSON/CSV"],
                ["clinical safety", "paper-grade convergence", "transcranial efficacy", "hydrophone-equivalent accuracy"],
                ["report.reference_paper_gap_matrix_20260715"],
                "Proceed to P3 fine-grid resumption decision gate or refine skeleton into full draft.",
            ),
            artifact(
                "report.fine_grid_decision_gate_20260715",
                "Fine-grid resumption decision gate for D60 source calibration",
                "outputs/fine_grid_decision_gate_20260715/fine_grid_decision_gate.json",
                "planning_report",
                "decision_gate_analysis",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["resumption criteria evaluated against current plan", "options A/B/C documented with time and memory estimates"],
                ["new pressure field", "automatic simulation restart", "paper-grade convergence claim"],
                ["report.paper_skeleton_20260715"],
                "Default is Option C (declare non-convergence); Option A or B requires explicit user authorization.",
            ),
            artifact(
                "brief.time_reversal_a3",
                "A.3 full-wave time-reversal evidence brief",
                "outputs/evidence_briefs/time_reversal_a3/evidence_brief.json",
                "evidence_brief",
                "pre_execution_evidence",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["protocol-verified two-stage TR design", "resource plan aligned with measured 079 (+5,0) runtime"],
                ["pressure result", "reference-method conclusion"],
                ["summary.thick_skull_plus5_standard_pressure"],
                "Source freeze satisfied by Gate B pass; TR executed under 2026-07-17 delegation.",
            ),
            artifact(
                "summary.tr_refocus_y+5_z0",
                "TR refocus pressure summary for 079 (+5,0) dx0.75",
                "outputs/time_reversal_079_y+5_z0/summary.json",
                "pressure_summary",
                "time_reversal_reference_engineering_observation",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["two-stage TR execution with finite field", "target/global 0.364 vs baseline 0.055 (6.61x)", "global peak moved out of skull material"],
                ["tuned focus", "compliant MItc", "clinical safety", "paper-grade convergence"],
                ["brief.time_reversal_a3"],
                "Skull hotspot still exceeds focus (2.53x within-field); normalization caveats apply to absolute MPa.",
            ),
            artifact(
                "report.tr_comparison_20260717",
                "TR vs baseline vs heuristic phase-correction comparison report",
                "outputs/time_reversal_comparison_20260717/time_reversal_comparison.json",
                "comparison_report",
                "time_reversal_reference_engineering_observation",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["scale-invariant comparison at matched config", "heuristic-to-reference distance quantified"],
                ["clinical safety", "paper-grade convergence", "transcranial efficacy"],
                ["summary.tr_refocus_y+5_z0"],
                "Reference bound for 079 (+5,0): t/g ~0.36, skull/focus ~2.5x; future heuristics must compare at matched config.",
            ),
            artifact(
                "feedback.time_reversal_a3",
                "A.3 time-reversal post-execution gap feedback",
                "outputs/evidence_briefs/time_reversal_a3/gap_feedback.json",
                "gap_feedback",
                "post_execution_feedback",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["execution gates and remaining gaps recorded", "throughput recalibrated to 0.32M voxel-steps/s"],
                ["tuned focus", "MItc", "medical safety"],
                ["report.tr_comparison_20260717"],
                "A.3 closed at engineering level; A.4 screening should use TR as same-config reference.",
            ),
            artifact(
                "brief.d60_pml16_cfl0p1_sensitivity",
                "D60 free-field PML16/CFL0.1 sensitivity evidence brief",
                "outputs/evidence_briefs/d60_pml16_cfl0p1_sensitivity/evidence_brief.json",
                "evidence_brief",
                "pre_execution_evidence",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["parameter-only sensitivity plan on Gate-B-passed dx0.75 baseline", "resource estimates from measured baseline runtime"],
                ["convergence claim", "paper-grade claim"],
                [],
                "Sensitivity observation only; executed under 2026-07-17 delegation after Gate B pass.",
            ),
        ],
    )
    sensitivity_artifacts = []
    if (PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pml16_pointwave_20260717/run/summary.json").exists():
        sensitivity_artifacts.append(
            artifact(
                "summary.d60_pml16_sensitivity",
                "D60 dx0.75 PML16 sensitivity run summary",
                "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pml16_pointwave_20260717/run/summary.json",
                "pressure_summary",
                "pml_sensitivity_observation",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["PML16 variant executed with identical model grid (PML-outside, cropped back)"],
                ["paper-grade convergence", "boundary-question closure"],
                ["brief.d60_pml16_cfl0p1_sensitivity"],
                "Compare against Gate B metric set; see sensitivity gap feedback for verdict.",
            )
        )
    if (PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_cfl0p1_pointwave_20260717/run/summary.json").exists():
        sensitivity_artifacts.append(
            artifact(
                "summary.d60_cfl0p1_sensitivity",
                "D60 dx0.75 CFL0.1 sensitivity run summary",
                "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_cfl0p1_pointwave_20260717/run/summary.json",
                "pressure_summary",
                "cfl_sensitivity_observation",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["CFL0.1 variant executed with halved dt and doubled nt"],
                ["paper-grade convergence", "timestep-question closure"],
                ["brief.d60_pml16_cfl0p1_sensitivity"],
                "Compare against Gate B metric set; see sensitivity gap feedback for verdict.",
            )
        )
    if (PROJECT_ROOT / "outputs/evidence_briefs/d60_pml16_cfl0p1_sensitivity/gap_feedback.json").exists():
        sensitivity_deps = ["brief.d60_pml16_cfl0p1_sensitivity"]
        if (PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pml16_pointwave_20260717/run/summary.json").exists():
            sensitivity_deps.append("summary.d60_pml16_sensitivity")
        if (PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_cfl0p1_pointwave_20260717/run/summary.json").exists():
            sensitivity_deps.append("summary.d60_cfl0p1_sensitivity")
        sensitivity_artifacts.append(
            artifact(
                "feedback.d60_pml16_cfl0p1_sensitivity",
                "D60 PML16/CFL0.1 sensitivity gap feedback",
                "outputs/evidence_briefs/d60_pml16_cfl0p1_sensitivity/gap_feedback.json",
                "gap_feedback",
                "post_execution_feedback",
                "M2_standard_engineering_baseline_hardening",
                "pass",
                ["metric deltas vs baseline recorded", "remaining Gate B gaps status updated"],
                ["convergence claim", "paper-grade claim"],
                sensitivity_deps,
                "dx0.375 remains the only Gate B residual gap after this sensitivity pass.",
            )
        )
    a5_report_path = PROJECT_ROOT / "outputs/a5_heldout_tr_confirmation_20260719/heldout_tr_report.json"
    if a5_report_path.exists():
        a5_report = json.loads(a5_report_path.read_text(encoding="utf-8"))
        registry["gate_states"]["pressure_execution_gate"]["reason"] += (
            f" The preregistered A5 held-out TR result is {a5_report.get('status')} "
            f"({a5_report.get('n_pass')}/3 pass); mapping and thermal expansion remain blocked."
        )
        registry["gate_states"]["pressure_execution_gate"]["next_action"] = (
            "Do not launch mapping, thermal, or additional trajectory batches. Design and evidence-gate a "
            "skull/global-hotspot suppression method before exactly-one new acoustic intervention."
        )
    hamming_report_path = PROJECT_ROOT / "outputs/a5_hamming_hotspot_report_20260720/hamming_hotspot_report.json"
    if hamming_report_path.exists():
        hamming_report = json.loads(hamming_report_path.read_text(encoding="utf-8"))
        registry["gate_states"]["pressure_execution_gate"]["reason"] += (
            f" The single Hamming pilot is {hamming_report.get('status')}; fixed-window scanning is rejected."
        )
        registry["gate_states"]["pressure_execution_gate"]["next_action"] = (
            "Do not launch mapping, thermal, trajectory batches, or another fixed aperture window. "
            "Design an explicit skull/global-hotspot-constrained optimization with a fresh evidence brief."
        )
    dual_point_feedback_path = PROJECT_ROOT / "outputs/evidence_briefs/dual_point_hotspot_constrained_tr/gap_feedback.json"
    if dual_point_feedback_path.exists():
        dual_point_feedback = json.loads(dual_point_feedback_path.read_text(encoding="utf-8"))
        registry["gate_states"]["pressure_execution_gate"]["reason"] += (
            f" Dual-point hotspot-constrained TR is {dual_point_feedback.get('status')}; "
            "geometry and C-order mapping are dry-run verified, but no hotspot pressure was authorized."
        )
        registry["gate_states"]["pressure_execution_gate"]["next_action"] = (
            "Keep mapping, thermal, trajectory batches, and fixed-window scans stopped. A future Evidence Brief may "
            "authorize exactly one hotspot calibration; constrained refocus remains blocked until offline gates pass."
        )
        registry["recommended_next_action"] = registry["gate_states"]["pressure_execution_gate"]["next_action"]
    bbb_final_result_path = PROJECT_ROOT / "outputs/dual_point_constrained_refocus_20260721/result/four_gate_result.json"
    if bbb_final_result_path.exists():
        bbb_final = json.loads(bbb_final_result_path.read_text(encoding="utf-8"))
        registry["gate_states"]["pressure_execution_gate"]["reason"] += (
            f" Exactly one hotspot calibration and one constrained refocus completed; final status is {bbb_final.get('status')} "
            f"with target retention {bbb_final.get('metrics', {}).get('target_window_retention', 0.0):.3f}."
        )
        registry["gate_states"]["pressure_execution_gate"]["next_action"] = (
            "The dual-point packet is closed and authorizes no additional pressure run. A successor method must use "
            "a new Evidence Brief and enforce target retention as a hard optimization constraint."
        )
        registry["recommended_next_action"] = registry["gate_states"]["pressure_execution_gate"]["next_action"]
        sensitivity_artifacts.append(artifact("brief.bbb_dual_point_constrained_refocus_20260721", "Exactly-one dual-point constrained-refocus Evidence Brief", "outputs/evidence_briefs/dual_point_constrained_refocus_20260721/evidence_brief.json", "evidence_brief", "pre_execution_evidence", "M2_bbb_pure_simulation_prototype", "pass", ["frozen exactly-one protocol and four pressure gates"], ["execution result", "clinical safety"], [], "Use only with its gap feedback and final four-gate result."))
        sensitivity_artifacts.append(artifact("result.bbb_dual_point_constrained_refocus_20260721", "Exactly-one dual-point constrained-refocus four-gate result", "outputs/dual_point_constrained_refocus_20260721/result/four_gate_result.json", "pressure_gate_result", "single_case_single_trajectory_engineering_evidence", "M2_bbb_pure_simulation_prototype", "block", ["skull-peak reduction and target-retention tradeoff under matched normalization"], ["clinical safety", "BBB dose", "method generalization"], ["brief.bbb_dual_point_constrained_refocus_20260721"], "Close this method; any successor must hard-constrain target retention in a new EDD packet."))
        sensitivity_artifacts.append(artifact("report.bbb_simulation_plan_v1_20260721", "Case 079 BBB pure-simulation planning report v1", "outputs/bbb_simulation_plan_report_20260721/plan_report.json", "planning_report", "paper_oriented_pure_simulation_prototype", "M2_bbb_pure_simulation_prototype", "pass", ["traceable planning contract, synthetic ROI, acoustic-cost ranking, virtual controls, and exposure boundaries"], ["clinical treatment plan", "patient dose", "real hardware export"], ["result.bbb_dual_point_constrained_refocus_20260721"], "Freeze as the v1 stage closeout; next extend with registered anatomy and target-constrained hotspot optimization."))
        sensitivity_artifacts.append(artifact("feedback.bbb_simulation_plan_v1_20260721", "BBB pure-simulation planning report v1 gap feedback", "outputs/evidence_briefs/bbb_plan_report/gap_feedback.json", "gap_feedback", "post_execution_feedback", "M2_bbb_pure_simulation_prototype", "pass", ["17/17 report checks and nonclinical boundaries recorded"], ["clinical efficacy", "clinical safety"], ["report.bbb_simulation_plan_v1_20260721"], "Preserve the stage closeout and address only the recorded blockers."))
    blend_result_path = PROJECT_ROOT / "outputs/target_preserving_blend_validation_20260722/result/four_gate_result.json"
    if blend_result_path.exists():
        blend_result = json.loads(blend_result_path.read_text(encoding="utf-8"))
        registry["gate_states"]["pressure_execution_gate"]["reason"] += (
            f" The alpha=0.40 target-preserving blend is {blend_result.get('status')}: target retention "
            f"{blend_result.get('metrics', {}).get('target_window_retention', 0.0):.3f}, skull-peak reduction "
            f"{blend_result.get('metrics', {}).get('skull_peak_reduction', 0.0):.3f}."
        )
        registry["gate_states"]["pressure_execution_gate"]["next_action"] = (
            "No pressure run is authorized. Implement the offline time-domain amplitude-bounded optimizer in "
            "SKULL_REGION_OPTIMIZATION_PLAN_20260722.md; if it fails, move to trajectory or geometry optimization."
        )
        registry["recommended_next_action"] = registry["gate_states"]["pressure_execution_gate"]["next_action"]
        sensitivity_artifacts.append(artifact("brief.bbb_target_preserving_blend_validation_20260722", "Exactly-one target-preserving waveform-blend Evidence Brief", "outputs/evidence_briefs/target_preserving_blend_validation_20260722/evidence_brief.json", "evidence_brief", "pre_execution_evidence", "M2_bbb_pure_simulation_prototype", "pass", ["frozen alpha=0.40 exactly-one field protocol"], ["execution result", "clinical safety"], [], "Read with its final four-gate result and gap feedback."))
        sensitivity_artifacts.append(artifact("result.bbb_target_preserving_blend_validation_20260722", "Target-preserving alpha=0.40 blend four-gate result", "outputs/target_preserving_blend_validation_20260722/result/four_gate_result.json", "pressure_gate_result", "single_case_single_trajectory_engineering_evidence", "M2_bbb_pure_simulation_prototype", "block", ["85.45 percent target retention and 15.40 percent skull-peak reduction under matched normalization"], ["whole-skull safety", "BBB dose", "generalization"], ["brief.bbb_target_preserving_blend_validation_20260722"], "Close convex blending; proceed only through the amplitude-bounded offline plan."))
        sensitivity_artifacts.append(artifact("feedback.bbb_second_skull_hotspot_calibration_20260722", "Second skull-hotspot calibration gap feedback", "outputs/evidence_briefs/second_skull_hotspot_calibration_20260722/gap_feedback.json", "gap_feedback", "post_execution_feedback", "M2_bbb_pure_simulation_prototype", "pass", ["second measured hotspot transfer vector"], ["refocus result", "whole-skull control"], ["result.bbb_target_preserving_blend_validation_20260722"], "Use only in offline multi-hotspot optimization."))
        sensitivity_artifacts.append(artifact("feedback.bbb_three_vector_skull_region_20260722", "Three-vector skull-region offline optimization gap feedback", "outputs/evidence_briefs/three_vector_skull_region_optimization_20260722/gap_feedback.json", "gap_feedback", "offline_method_feedback", "M2_bbb_pure_simulation_prototype", "block", ["48 candidate offline tradeoff and endpoint-model validation"], ["pressure efficacy", "whole-skull safety"], ["feedback.bbb_second_skull_hotspot_calibration_20260722"], "Replace post-hoc peak screening with an internal time-domain amplitude constraint."))
        sensitivity_artifacts.append(artifact("plan.bbb_skull_region_amplitude_bounded_20260722", "Skull-region time-domain amplitude-bounded optimization plan", "SKULL_REGION_OPTIMIZATION_PLAN_20260722.md", "execution_plan", "evidence_driven_next_method", "M2_bbb_pure_simulation_prototype", "warn", ["next offline method and stop conditions"], ["pressure authorization", "clinical claim"], ["feedback.bbb_three_vector_skull_region_20260722"], "Implement offline only; require a separate Evidence Brief before at most one future field."))
    amplitude_result_path = PROJECT_ROOT / "outputs/time_domain_amplitude_bounded_skull_region_20260722/offline_amplitude_bounded_gate.json"
    if amplitude_result_path.exists():
        amplitude_result = json.loads(amplitude_result_path.read_text(encoding="utf-8"))
        registry["gate_states"]["pressure_execution_gate"]["reason"] += (
            f" The amplitude-bounded H1 search found {amplitude_result.get('hard_pass_count', 0)} "
            f"minimum-gate candidates but {amplitude_result.get('pressure_margin_pass_count', 0)} "
            "pressure-margin candidates."
        )
        registry["gate_states"]["pressure_execution_gate"]["next_action"] = (
            "No pressure run is authorized. Close H1 source-weight tuning and execute the offline trajectory/geometry "
            "ranking in TRAJECTORY_GEOMETRY_OPTIMIZATION_PLAN_20260722.md."
        )
        registry["recommended_next_action"] = registry["gate_states"]["pressure_execution_gate"]["next_action"]
        sensitivity_artifacts.append(artifact("brief.bbb_amplitude_bounded_skull_region_20260722", "Time-domain amplitude-bounded skull-region Evidence Brief", "outputs/evidence_briefs/time_domain_amplitude_bounded_skull_region_20260722/evidence_brief.json", "evidence_brief", "pre_execution_evidence", "M2_bbb_pure_simulation_prototype", "pass", ["frozen waveform basis, exact peak semantics, hard and margin gates"], ["pressure efficacy", "whole-skull safety"], ["feedback.bbb_three_vector_skull_region_20260722"], "Read with the offline gate and gap feedback."))
        sensitivity_artifacts.append(artifact("result.bbb_amplitude_bounded_skull_region_20260722", "Time-domain amplitude-bounded skull-region offline gate", "outputs/time_domain_amplitude_bounded_skull_region_20260722/offline_amplitude_bounded_gate.json", "offline_method_result", "single_case_two_point_waveform_optimization", "M2_bbb_pure_simulation_prototype", "block", ["4305 candidates, 1261 exact waveform checks, 56 minimum-gate passes"], ["pressure validation", "whole-skull safety", "clinical dose"], ["brief.bbb_amplitude_bounded_skull_region_20260722"], "Do not pressure-validate because no candidate passed the preregistered margin."))
        sensitivity_artifacts.append(artifact("feedback.bbb_amplitude_bounded_skull_region_20260722", "Time-domain amplitude-bounded skull-region gap feedback", "outputs/evidence_briefs/time_domain_amplitude_bounded_skull_region_20260722/gap_feedback.json", "gap_feedback", "offline_method_feedback", "M2_bbb_pure_simulation_prototype", "block", ["56 hard passes and zero pressure-margin passes; H1 weight route closed"], ["pressure efficacy", "whole-skull safety"], ["result.bbb_amplitude_bounded_skull_region_20260722"], "Move to trajectory or transducer geometry without refining the H1 coefficient grid."))
        sensitivity_artifacts.append(artifact("plan.bbb_trajectory_geometry_20260722", "Trajectory and geometry optimization plan", "TRAJECTORY_GEOMETRY_OPTIMIZATION_PLAN_20260722.md", "execution_plan", "evidence_driven_next_method", "M2_bbb_pure_simulation_prototype", "warn", ["offline reuse-first trajectory and geometry ranking with stop conditions"], ["pressure authorization", "clinical claim"], ["feedback.bbb_amplitude_bounded_skull_region_20260722"], "Execute offline ranking first; require a separate Evidence Brief and dry-run for at most one field."))

    trajectory_reuse_path = PROJECT_ROOT / "outputs/trajectory_geometry_reuse_gate_20260722/reuse_gate.json"
    if trajectory_reuse_path.exists():
        trajectory_reuse = json.loads(trajectory_reuse_path.read_text(encoding="utf-8"))
        registry["gate_states"]["pressure_execution_gate"]["reason"] += (
            f" Existing H3 reuse is {trajectory_reuse.get('status')}, with target retention "
            f"{trajectory_reuse.get('target_pressure_retention_vs_reference', 0.0):.3f} and skull-peak reduction "
            f"{trajectory_reuse.get('skull_peak_reduction_vs_reference', 0.0):.3f} versus H1."
        )
        registry["gate_states"]["pressure_execution_gate"]["next_action"] = (
            "No pressure run is required. Preserve H3 as the selected Case 079 engineering trajectory; "
            "prioritize registered anatomy or additional cases over further H1 tuning."
        )
        registry["recommended_next_action"] = registry["gate_states"]["pressure_execution_gate"]["next_action"]
        sensitivity_artifacts.append(artifact("brief.bbb_trajectory_reuse_20260722", "Existing H3 trajectory reuse Evidence Brief", "outputs/evidence_briefs/trajectory_geometry_reuse_gate_20260722/evidence_brief.json", "evidence_brief", "pre_execution_evidence", "M2_bbb_pure_simulation_prototype", "pass", ["frozen same-protocol H1-to-H3 reuse gates"], ["clinical safety", "multi-case generalization"], ["feedback.bbb_amplitude_bounded_skull_region_20260722"], "Read with the reuse gate and gap feedback."))
        sensitivity_artifacts.append(artifact("result.bbb_trajectory_reuse_20260722", "Existing H3 trajectory reuse gate", "outputs/trajectory_geometry_reuse_gate_20260722/reuse_gate.json", "trajectory_selection_result", "single_case_existing_fullwave_reuse", "M2_bbb_pure_simulation_prototype", "pass", ["H3 target retention, skull-peak reduction and 11 gate checks"], ["clinical safety", "multi-case generalization"], ["brief.bbb_trajectory_reuse_20260722"], "Use H3 as the selected existing Case 079 engineering field without a new pressure run."))
        sensitivity_artifacts.append(artifact("feedback.bbb_trajectory_reuse_20260722", "Existing H3 trajectory reuse gap feedback", "outputs/evidence_briefs/trajectory_geometry_reuse_gate_20260722/gap_feedback.json", "gap_feedback", "post_execution_feedback", "M2_bbb_pure_simulation_prototype", "pass", ["11/11 reuse checks and zero new pressure runs"], ["clinical safety", "registered anatomy"], ["result.bbb_trajectory_reuse_20260722"], "Align downstream interfaces to H3."))

    h3_element_path = PROJECT_ROOT / "outputs/bbb_element_plan_h3_20260722/element_plan_summary.json"
    if h3_element_path.exists():
        sensitivity_artifacts.append(artifact("brief.bbb_h3_virtual_elements_20260722", "H3 virtual-element plan Evidence Brief", "outputs/evidence_briefs/bbb_element_plan_h3_20260722/evidence_brief.json", "evidence_brief", "pre_execution_evidence", "M2_bbb_pure_simulation_prototype", "pass", ["H3 mask hash, virtual slots, quantization and response gate"], ["physical hardware export", "pressure efficacy"], ["result.bbb_trajectory_reuse_20260722"], "Read with attempt-1 and final gap feedback."))
        sensitivity_artifacts.append(artifact("result.bbb_h3_virtual_elements_20260722", "H3 virtual-element plan summary", "outputs/bbb_element_plan_h3_20260722/element_plan_summary.json", "virtual_control_interface", "trajectory_aligned_software_fixture", "M2_bbb_pure_simulation_prototype", "pass", ["3709 source points, 49 slots, 48 nonempty controls and predicted response retention"], ["physical transducer geometry", "channel calibration"], ["brief.bbb_h3_virtual_elements_20260722"], "Use only as a virtual interface fixture."))
        sensitivity_artifacts.append(artifact("feedback.bbb_h3_virtual_elements_20260722", "H3 virtual-element plan gap feedback", "outputs/evidence_briefs/bbb_element_plan_h3_20260722/gap_feedback.json", "gap_feedback", "post_execution_feedback", "M2_bbb_pure_simulation_prototype", "pass", ["6/6 tests and trajectory-aligned virtual controls"], ["physical hardware export"], ["result.bbb_h3_virtual_elements_20260722"], "Preserve the physical-device boundary."))

    for spec in RECENT_ARTIFACT_SPECS:
        sensitivity_artifacts.append(artifact(**spec))
    registry["project_maturity_level"]["current"] = "M2_acoustic_baseline_plus_bbb_simulation_prototype"
    registry["project_maturity_level"]["rationale"] = (
        "BBB WP0-WP6 software prototype and matched acoustic engineering evidence are complete; "
        "registered anatomy, physical hardware, formal convergence, thermal and clinical gates remain open."
    )
    registry["project_maturity_level"]["next_target"] = "workspace_closed_then_matched_baseline_vs_tr_decision"
    registry["recommended_next_action"] = (
        "Keep new pressure execution paused after the 2026-07-29 workspace closeout. If scientific work resumes, "
        "create a fresh EDD packet for exactly one matched baseline-versus-TR comparison on the H3-large geometry."
    )
    registry["gate_states"]["pressure_execution_gate"]["next_action"] = registry["recommended_next_action"]
    upsert_artifacts(registry, sensitivity_artifacts)
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_JSON.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(registry)
    print(f"Wrote {rel(REGISTRY_JSON)}")
    print(f"Wrote {rel(REGISTRY_MD)}")


if __name__ == "__main__":
    main()
