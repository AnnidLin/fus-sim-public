from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "outputs" / "reproducibility_manifest"
OUT_JSON = OUT_DIR / "case_079_reproducibility_manifest.json"
OUT_MD = OUT_DIR / "case_079_reproducibility_manifest.md"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def sha256(path: Path) -> str | None:
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
        "plan": PROJECT_ROOT / "TWO_WEEK_REPRODUCIBILITY_PLAN.md",
        "evidence_registry": PROJECT_ROOT / "outputs/evidence_registry/evidence_registry.json",
        "run_ledger": PROJECT_ROOT / "outputs/run_ledger.jsonl",
        "authorization_package": PROJECT_ROOT
        / "outputs/one_run_authorization_package/079_candidate_006/one_run_authorization_package.json",
        "entry_plan": PROJECT_ROOT / "outputs/case_refinement_plan/079/candidate_006/entry_plan.json",
        "dx0p75_model_summary": PROJECT_ROOT / "outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/summary.json",
        "dx0p5_model_summary": PROJECT_ROOT / "outputs/ct_acoustic_model_3d_profile_hu300_dx0p5/summary.json",
        "dx0p75_pressure_summary": PROJECT_ROOT
        / "outputs/ct_standard_pressure_authorization/079_candidate_006_dx0p75_pml12_standard/summary.json",
        "dx0p5_pressure_summary": PROJECT_ROOT / "outputs/corrected_pressure_runs/079_candidate_006_dx0p5_pml12_cfl0p2_standard/summary.json",
        "grid_convergence_analysis": PROJECT_ROOT
        / "outputs/ct_grid_convergence_analysis/079_candidate_006/ct_grid_convergence_analysis.json",
        "corrected_entry_plan_chain": PROJECT_ROOT
        / "outputs/corrected_entry_plan_resolution_chain/079_candidate_006_dx0p75/corrected_entry_plan_resolution_chain.json",
        "corrected_entry_plan_validation": PROJECT_ROOT
        / "outputs/corrected_entry_plan_resolution_chain/079_candidate_006_dx0p75/corrected_entry_plan_resolution_chain_validation.json",
        "corrected_entry_plan_dry_run": PROJECT_ROOT
        / "outputs/corrected_entry_plan_resolution_chain/079_candidate_006_dx0p75/dry_run_quality/quality_dry_run_summary.json",
        "corrected_pressure_runner": PROJECT_ROOT
        / "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard/runner_status.json",
        "corrected_pressure_summary": PROJECT_ROOT
        / "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard/summary.json",
        "corrected_pressure_focus_metrics": PROJECT_ROOT
        / "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard/focus_metrics.json",
        "p3_numerical_sensitivity_plan": PROJECT_ROOT
        / "outputs/p3_numerical_sensitivity_plan/079_candidate_006_dx0p75/p3_numerical_sensitivity_plan.json",
        "p3_numerical_sensitivity_plan_validation": PROJECT_ROOT
        / "outputs/p3_numerical_sensitivity_plan/079_candidate_006_dx0p75/p3_numerical_sensitivity_plan_validation.json",
        "p3a_pml16_sensitivity_report": PROJECT_ROOT
        / "outputs/p3a_pml16_sensitivity_analysis/079_candidate_006_dx0p75/p3a_pml16_sensitivity_report.json",
        "p3a_pml16_sensitivity_report_validation": PROJECT_ROOT
        / "outputs/p3a_pml16_sensitivity_analysis/079_candidate_006_dx0p75/p3a_pml16_sensitivity_report_validation.json",
        "p3b_cfl0p1_sensitivity_report": PROJECT_ROOT
        / "outputs/p3b_cfl0p1_sensitivity_analysis/079_candidate_006_dx0p75/p3b_cfl0p1_sensitivity_report.json",
        "p3b_cfl0p1_sensitivity_report_validation": PROJECT_ROOT
        / "outputs/p3b_cfl0p1_sensitivity_analysis/079_candidate_006_dx0p75/p3b_cfl0p1_sensitivity_report_validation.json",
        "p3c_dx0p5_entry_validation": PROJECT_ROOT
        / "outputs/corrected_entry_plan_resolution_chain/079_candidate_006_dx0p5/corrected_entry_plan_resolution_chain_validation.json",
        "corrected_pennes_summary": PROJECT_ROOT / "outputs/corrected_pennes_thermal/pennes_summary.json",
    }


def command_packet(
    packet_id: str,
    status: str,
    agent_class: str,
    authorization: str,
    goal: str,
    inputs: list[str],
    expected_outputs: list[str],
    gates: list[str],
    hard_stop_min: int | None,
    claim_level: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "packet_id": packet_id,
        "status": status,
        "agent_budget_class": agent_class,
        "authorization": authorization,
        "goal": goal,
        "inputs": inputs,
        "expected_outputs": expected_outputs,
        "required_gates": gates,
        "hard_stop_min": hard_stop_min,
        "claim_level": claim_level,
        "next_action": next_action,
    }


def build_manifest() -> dict[str, Any]:
    p = paths()
    registry = read_json(p["evidence_registry"])
    auth = read_json(p["authorization_package"])
    entry_plan = read_json(p["entry_plan"])
    dx075_model = read_json(p["dx0p75_model_summary"])
    dx05_model = read_json(p["dx0p5_model_summary"])
    dx075_summary = read_json(p["dx0p75_pressure_summary"])
    dx05_summary = read_json(p["dx0p5_pressure_summary"])
    grid_analysis = read_json(p["grid_convergence_analysis"])
    corrected_chain = read_json(p["corrected_entry_plan_chain"])
    corrected_validation = read_json(p["corrected_entry_plan_validation"])
    corrected_dry_run = read_json(p["corrected_entry_plan_dry_run"])
    corrected_runner = read_json(p["corrected_pressure_runner"])
    corrected_pressure = read_json(p["corrected_pressure_summary"])
    corrected_focus = read_json(p["corrected_pressure_focus_metrics"])
    p3_plan = read_json(p["p3_numerical_sensitivity_plan"])
    p3_validation = read_json(p["p3_numerical_sensitivity_plan_validation"])
    p3a_report = read_json(p["p3a_pml16_sensitivity_report"])
    p3a_validation = read_json(p["p3a_pml16_sensitivity_report_validation"])
    p3b_report = read_json(p["p3b_cfl0p1_sensitivity_report"])
    p3b_validation = read_json(p["p3b_cfl0p1_sensitivity_report_validation"])
    p3c_validation = read_json(p["p3c_dx0p5_entry_validation"])
    ledger_entries = read_jsonl(p["run_ledger"])
    p1_complete = nested(corrected_validation, ["chain_valid"], False) is True
    p2_complete = (
        p1_complete
        and nested(corrected_runner, ["status"]) == "kwave_ok"
        and p["corrected_pressure_summary"].exists()
        and p["corrected_pressure_focus_metrics"].exists()
    )
    p3_plan_ready = nested(p3_validation, ["plan_valid"], False) is True
    p3a_complete = nested(p3a_validation, ["report_valid"], False) is True
    p3a_stable = nested(p3a_report, ["decision", "p3a_stable_within_thresholds"], False) is True
    p3b_complete = nested(p3b_validation, ["report_valid"], False) is True
    p3b_stable = nested(p3b_report, ["decision", "p3b_stable_within_thresholds"], False) is True
    p3c_complete = nested(p3c_validation, ["chain_valid"], False) is True
    p4_complete = p2_complete and p["corrected_pennes_summary"].exists()
    p5_complete = (PROJECT_ROOT / "outputs/reproducibility_package/final_report.md").exists()

    executed_runs = []
    invalidated_runs = []
    for item in ledger_entries:
        record = {
            "run_id": item.get("run_id"),
            "status": item.get("runner_status"),
            "claim_level": item.get("claim_level"),
            "output_dir": item.get("output_dir"),
            "summary_path": item.get("summary_path"),
            "pressure_path": item.get("pressure_path"),
            "authorization": item.get("authorization"),
            "blocked_claims": item.get("blocked_claims", []),
        }
        if item.get("claim_level") == "coordinate_mapping_diagnostic_not_grid_convergence":
            invalidated_runs.append(
                record
                | {
                    "invalidated_reason": "entry_plan/model dx_m and model_shape mismatch; cannot interpret as grid convergence",
                    "replacement_required": True,
                }
            )
        else:
            executed_runs.append(record)

    entry_plan_gate = nested(auth, ["completed_context", "entry_plan_resolution_gate"], {})
    planned_packets = [
        command_packet(
            "P1_correct_entry_plan_dx0p75",
            "completed" if p1_complete else "planned",
            "M",
            "not_required_for_generation_or_dry_run",
            "Regenerate or transform entry/source/target plan for the dx0.75 acoustic model.",
            [rel(p["dx0p75_model_summary"]), rel(p["entry_plan"])],
            [
                "outputs/reproducibility_manifest/corrected_entry_plan_dx0p75.json",
                "dry-run-quality summary for corrected dx0.75 plan",
            ],
            [
                "entry_plan.dx_m matches model dx_m",
                "entry_plan.model_shape matches model grid_shape",
                "dry-run-quality passes without --allow-entry-plan-resolution-mismatch",
                "crop material range includes skull material when skull crossing is expected",
            ],
            None,
            "coordinate_chain_prerequisite",
            "Corrected pressure baseline exists; use its metrics to plan P3 sensitivity."
            if p2_complete
            else "Corrected dx0.75 entry plan and dry-run-quality are available; request P2 authorization next."
            if p1_complete
            else "Generate corrected dx0.75 entry plan before any corrected pressure run.",
        ),
        command_packet(
            "P2_corrected_dx0p75_standard_pressure",
            "completed" if p2_complete else "awaiting_user_authorization" if p1_complete else "blocked_until_P1_and_user_authorization",
            "L",
            "required",
            "Run exactly one corrected dx0.75 standard CT pressure baseline after P1 passes.",
            ["corrected dx0.75 entry plan", rel(p["dx0p75_model_summary"])],
            [
                "corrected pressure output directory",
                "summary.json",
                "pressure_max_mpa.npz",
                "focus_metrics.json",
            ],
            [
                "P1 corrected entry-plan dry-run-quality passes",
                "output directory has no pressure conflict",
                "run through run_kwave_command.py",
                "checkpoint_sec=120",
            ],
            60,
            "paper_reproducible_research_dataset_candidate",
            "Use corrected baseline metrics to design the smallest P3 sensitivity set; do not claim tuned focus."
            if p2_complete
            else "Request explicit authorization for exactly one corrected dx0.75 standard pressure run."
            if p1_complete
            else "Request explicit authorization only after corrected dry-run-quality passes.",
        ),
        command_packet(
            "P3_numerical_sensitivity_selected_dataset",
            "completed_p3a_p3b_and_p3c_prerequisite"
            if p3b_complete and p3b_stable and p3c_complete
            else "p3a_p3b_completed_p3c_prerequisite_ready"
            if p3b_complete and p3b_stable
            else "p3b_completed_review_required"
            if p3b_complete
            else "p3a_completed_p3b_awaiting_authorization"
            if p3a_complete and p3a_stable
            else "p3a_completed_review_required"
            if p3a_complete
            else "authorization_packets_ready"
            if p3_plan_ready
            else "planned"
            if p2_complete
            else "blocked_until_corrected_baseline",
            "L_or_XL",
            "required_per_real_run",
            "Run the smallest numerical sensitivity set needed to justify interpretation of the selected corrected pressure dataset.",
            ["corrected pressure baseline summary"],
            ["sensitivity summaries", "comparison report", "updated registry"],
            ["each real run has a one-run authorization packet", "no blind batch execution"],
            None,
            "research_reproducibility_sensitivity_evidence",
            "P3c coordinate-chain prerequisite is complete; corrected dx0.5 pressure remains separately authorized work."
            if p3b_complete and p3b_stable and p3c_complete
            else "Proceed to P3c corrected dx0.5 coordinate-chain prerequisite; do not run dx0.5 pressure yet."
            if p3b_complete and p3b_stable
            else "Pause for P3b timestep analysis before any further pressure run."
            if p3b_complete
            else "Request explicit authorization for P3b CFL0.1 timestep sensitivity only."
            if p3a_complete and p3a_stable
            else "Pause for P3a boundary analysis before any further pressure run."
            if p3a_complete
            else "Request explicit authorization for P3a PML16 boundary sensitivity only."
            if p3_plan_ready
            else "Prepare one-run authorization packets for sensitivity legs based on corrected baseline metrics."
            if p2_complete
            else "Choose CFL/PML/grid legs after corrected baseline metrics are known.",
        ),
        command_packet(
            "P4_corrected_pennes_thermal",
            "completed" if p4_complete else "awaiting_user_authorization" if p2_complete else "blocked_until_selected_pressure_dataset",
            "L",
            "required",
            "Generate thermal/Pennes dataset from the selected corrected pressure output.",
            [rel(p["corrected_pressure_summary"])],
            ["outputs/corrected_pennes_thermal/pennes_summary.json", "CEM43 outputs", "plots"],
            ["thermal assumptions recorded", "claim boundary excludes clinical safety"],
            None,
            "research_thermal_dataset_not_clinical_safety",
            "P5 final package is next." if p4_complete else "Run Pennes thermal solver on corrected baseline." if p2_complete else "Run Pennes only after corrected pressure baseline exists.",
        ),
        command_packet(
            "P5_final_reproducibility_package",
            "completed" if p5_complete else "awaiting_generation" if p4_complete else "blocked_until_core_outputs_exist",
            "M",
            "not_required",
            "Generate final reproducibility report and data index.",
            [rel(p["corrected_pressure_summary"]), "outputs/corrected_pennes_thermal/pennes_summary.json"],
            ["outputs/reproducibility_package/final_report.md", "data index with hashes"],
            ["validators pass", "commit and push complete"],
            None,
            "auditable_research_dataset_candidate_not_numerical_convergence",
            "Completed." if p5_complete else "Generate final reproducibility package." if p4_complete else "Prepare package after P2-P4 complete.",
        ),
    ]

    blocked_runs = []
    if nested(auth, ["decision", "entry_plan_resolution_gate_status"]) == "block":
        blocked_runs.append(
            {
                "run_id": "grid_dx0p5_pressure_comparison",
                "status": "blocked",
                "reason": nested(entry_plan_gate, ["reason"], "entry_plan resolution gate is blocked"),
                "next_action": nested(
                    entry_plan_gate,
                    ["next_action"],
                    "Regenerate or transform entry_plan for the target acoustic model before pressure.",
                ),
            }
        )

    input_inventory = []
    for name, path in p.items():
        input_inventory.append(
            {
                "name": name,
                "path": rel(path),
                "exists": path.exists(),
                "sha256": sha256(path),
            }
        )

    return {
        "manifest_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_id": "079",
        "candidate_id": "candidate_006",
        "scope": "two-week paper-reproducible research dataset execution manifest",
        "source_plan": rel(p["plan"]),
        "current_state": {
            "maturity": nested(registry, ["project_maturity_level", "current"]),
            "entry_plan_resolution_gate": entry_plan_gate,
            "entry_plan_dx_m": None if entry_plan is None else entry_plan.get("dx_m"),
            "entry_plan_model_shape": None if entry_plan is None else entry_plan.get("model_shape"),
            "dx0p75_model_dx_m": None if dx075_model is None else dx075_model.get("dx_m"),
            "dx0p75_model_shape": None if dx075_model is None else dx075_model.get("grid_shape"),
            "dx0p5_model_dx_m": None if dx05_model is None else dx05_model.get("dx_m"),
            "dx0p5_model_shape": None if dx05_model is None else dx05_model.get("grid_shape"),
            "dx0p75_pressure_claim_level": "standard_engineering_pressure_output" if dx075_summary else None,
            "corrected_dx0p75_pressure_claim_level": "corrected_standard_pressure_research_dataset_candidate"
            if p2_complete
            else None,
            "dx0p5_pressure_claim_level": nested(
                grid_analysis,
                ["claim_level"],
                "coordinate_mapping_diagnostic_not_grid_convergence" if dx05_summary else None,
            ),
            "corrected_dx0p75_entry_plan_chain_valid": p1_complete,
            "corrected_dx0p75_selected_entry_plan": nested(corrected_chain, ["selected_entry_plan"]),
            "corrected_dx0p75_dry_run_grid_size": nested(corrected_dry_run, ["simulation_quality", "grid_size"]),
            "corrected_dx0p75_dry_run_nt": nested(corrected_dry_run, ["simulation_quality", "nt"]),
            "corrected_dx0p75_dry_run_sim_time_s": nested(corrected_dry_run, ["simulation_quality", "simulation_time_s"]),
            "corrected_dx0p75_runner_status": nested(corrected_runner, ["status"]),
            "corrected_dx0p75_runtime_s": nested(corrected_runner, ["execution", "runtime_s"]),
            "corrected_dx0p75_target_pressure_mpa": nested(corrected_focus, ["target_pressure_mpa"]),
            "corrected_dx0p75_target_window_peak_mpa": nested(corrected_focus, ["target_window_peak_mpa"]),
            "corrected_dx0p75_global_peak_to_target_distance_mm": nested(
                corrected_focus,
                ["global_peak_to_target_distance_mm"],
            ),
            "corrected_dx0p75_target_to_global_peak_ratio": nested(corrected_focus, ["target_to_global_peak_ratio"]),
            "corrected_dx0p75_tuning_note": nested(corrected_pressure, ["tuning_note"]),
            "p3_plan_ready": p3_plan_ready,
            "p3_immediate_next_packet": nested(p3_plan, ["immediate_next_packet"]),
            "p3_plan_path": rel(p["p3_numerical_sensitivity_plan"]) if p["p3_numerical_sensitivity_plan"].exists() else None,
            "p3a_report_valid": p3a_complete,
            "p3a_stable_within_thresholds": p3a_stable,
            "p3a_report_path": rel(p["p3a_pml16_sensitivity_report"]) if p["p3a_pml16_sensitivity_report"].exists() else None,
            "p3a_recommended_next_packet": nested(p3a_report, ["decision", "recommended_next_packet"]),
            "p3b_report_valid": p3b_complete,
            "p3b_stable_within_thresholds": p3b_stable,
            "p3b_report_path": rel(p["p3b_cfl0p1_sensitivity_report"]) if p["p3b_cfl0p1_sensitivity_report"].exists() else None,
            "p3b_recommended_next_packet": nested(p3b_report, ["decision", "recommended_next_packet"]),
            "p3c_dx0p5_coordinate_chain_valid": p3c_complete,
        },
        "input_inventory": input_inventory,
        "executed_runs": executed_runs,
        "invalidated_runs": invalidated_runs,
        "blocked_runs": blocked_runs,
        "planned_packets": planned_packets,
        "claim_boundaries": [
            "No clinical or medical safety conclusion.",
            "No medical efficacy conclusion.",
            "No default mapping profile promotion.",
            "No broad validated baseline claim beyond the generated dataset.",
            "Historical dx0.5 pressure is diagnostic only until corrected entry planning exists.",
            "Corrected dx0.5 pressure has not been executed; numerical convergence is not demonstrated.",
        ],
        "immediate_next_packet": (
            "P6b_post_skull_beam_axis_profile_and_interface_audit"
            if p5_complete
            else "P5_final_reproducibility_package"
            if p4_complete
            else "P4_corrected_pennes_thermal"
            if p2_complete
            else "P2_corrected_dx0p75_standard_pressure"
            if p1_complete
            else "P1_correct_entry_plan_dx0p75"
        ),
        "immediate_next_packet_detail": (
            nested(p3b_report, ["decision", "recommended_next_packet"])
            if p3b_complete
            else
            nested(p3a_report, ["decision", "recommended_next_packet"])
            if p3a_complete
            else
            nested(p3_plan, ["immediate_next_packet"])
            if p3_plan_ready
            else None
        ),
        "not_executed_by_manifest": [
            "additional pressure simulation beyond P2",
            "paper-grade candidate run",
        ] if p4_complete else [
            "additional pressure simulation beyond P2",
            "thermal simulation",
            "paper-grade candidate run",
        ],
    }


def build_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Case 079 Reproducibility Manifest",
        "",
        f"- generated at: `{manifest['generated_at']}`",
        f"- scope: {manifest['scope']}",
        f"- source plan: `{manifest['source_plan']}`",
        f"- immediate next packet: `{manifest['immediate_next_packet']}`",
        "",
        "## Current State",
        "",
    ]
    state = manifest["current_state"]
    for key in (
        "maturity",
        "entry_plan_dx_m",
        "entry_plan_model_shape",
        "dx0p75_model_dx_m",
        "dx0p75_model_shape",
        "dx0p5_model_dx_m",
        "dx0p5_model_shape",
        "dx0p75_pressure_claim_level",
        "corrected_dx0p75_pressure_claim_level",
        "dx0p5_pressure_claim_level",
        "corrected_dx0p75_runner_status",
        "corrected_dx0p75_runtime_s",
        "corrected_dx0p75_target_pressure_mpa",
        "corrected_dx0p75_target_window_peak_mpa",
        "corrected_dx0p75_global_peak_to_target_distance_mm",
        "corrected_dx0p75_target_to_global_peak_ratio",
        "corrected_dx0p75_tuning_note",
        "p3_plan_ready",
        "p3_immediate_next_packet",
        "p3_plan_path",
        "p3a_report_valid",
        "p3a_stable_within_thresholds",
        "p3a_report_path",
        "p3a_recommended_next_packet",
        "p3b_report_valid",
        "p3b_stable_within_thresholds",
        "p3b_report_path",
        "p3b_recommended_next_packet",
        "p3c_dx0p5_coordinate_chain_valid",
    ):
        lines.append(f"- {key}: `{state.get(key)}`")

    lines.extend(["", "## Executed Runs", ""])
    for run in manifest["executed_runs"]:
        lines.append(f"- `{run['run_id']}`: status `{run['status']}`, claim `{run['claim_level']}`")
    if not manifest["executed_runs"]:
        lines.append("- none")

    lines.extend(["", "## Invalidated / Diagnostic Runs", ""])
    for run in manifest["invalidated_runs"]:
        lines.append(f"- `{run['run_id']}`: `{run['invalidated_reason']}`")
    if not manifest["invalidated_runs"]:
        lines.append("- none")

    lines.extend(["", "## Blocked Runs", ""])
    for run in manifest["blocked_runs"]:
        lines.append(f"- `{run['run_id']}`: {run['reason']}")
    if not manifest["blocked_runs"]:
        lines.append("- none")

    lines.extend(["", "## Planned Packets", ""])
    lines.append("| Packet | Status | Class | Authorization | Claim Level | Next Action |")
    lines.append("|---|---|---:|---|---|---|")
    for packet in manifest["planned_packets"]:
        lines.append(
            f"| `{packet['packet_id']}` | `{packet['status']}` | `{packet['agent_budget_class']}` | "
            f"`{packet['authorization']}` | `{packet['claim_level']}` | {packet['next_action']} |"
        )

    lines.extend(["", "## Claim Boundaries", ""])
    lines.extend(f"- {item}" for item in manifest["claim_boundaries"])
    lines.extend(["", "## Not Executed By This Manifest", ""])
    lines.extend(f"- {item}" for item in manifest["not_executed_by_manifest"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    OUT_JSON.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(build_markdown(manifest), encoding="utf-8")
    print(f"Wrote {rel(OUT_JSON)}")
    print(f"Wrote {rel(OUT_MD)}")


if __name__ == "__main__":
    main()
