from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "outputs/reproducibility_package"
OUT_INDEX = OUT_DIR / "data_index.json"
OUT_REPORT = OUT_DIR / "final_report.md"

ARTIFACTS = [
    ("acoustic_paper_grade_plan", "ACOUSTIC_PAPER_GRADE_EXECUTION_PLAN.md", "governance", True),
    ("acoustic_paper_grade_brief", "outputs/evidence_briefs/acoustic_paper_grade_route/evidence_brief.json", "governance", True),
    ("acoustic_paper_grade_matrix", "outputs/acoustic_paper_grade_plan_20260711/experiment_matrix.csv", "governance", True),
    ("paper_gate_a_selection", "outputs/paper_gate_a_trajectory_selection_079/gate_a_trajectory_selection.json", "geometry_gate", True),
    ("paper_gate_b_dry_run_report", "outputs/paper_gate_b_freefield_closure/gate_b_dry_run_report.json", "freefield_gate", True),
    ("paper_gate_b_dx075_result", "outputs/paper_gate_b_freefield_closure/dx0p75_freefield_result.json", "freefield_gate", True),
    ("freefield_curvature_report", "outputs/freefield_curvature_calibration/curvature_calibration_report.json", "freefield_gate", True),
    ("freefield_aperture_feedback", "outputs/evidence_briefs/freefield_aperture_calibration/gap_feedback.json", "freefield_gate", True),
    ("acoustic_stage_closeout", "outputs/stage_closeout_20260712.md", "governance", True),
    ("d60_resume_feedback", "outputs/evidence_briefs/freefield_aperture_calibration_resume_20260713/gap_feedback.json", "freefield_gate", True),
    ("d60_closure_report", "outputs/freefield_aperture_calibration/d60_dx0p75_resume_20260713/d60_freefield_closure_report.json", "freefield_gate", True),
    ("d60_pressure_summary", "outputs/freefield_aperture_calibration/d60_dx0p75_resume_20260713/run/summary.json", "freefield_gate", True),
    ("d60_pressure_field", "outputs/freefield_aperture_calibration/d60_dx0p75_resume_20260713/run/pressure_max_mpa.npz", "freefield_gate", True),
    ("d60_gate_a_feedback", "outputs/evidence_briefs/paper_gate_a_d60_trajectory_selection/gap_feedback.json", "geometry_gate", True),
    ("d60_gate_a_selection", "outputs/paper_gate_a_d60_trajectory_selection_079/gate_a_d60_trajectory_selection.json", "geometry_gate", True),
    ("d60_dx0p5_feedback", "outputs/evidence_briefs/freefield_d60_dx0p5_convergence/gap_feedback.json", "freefield_gate", True),
    ("d60_dx0p5_recovery_feedback", "outputs/evidence_briefs/freefield_d60_dx0p5_fieldonly_recovery/gap_feedback.json", "freefield_gate", True),
    ("d60_dx0p5_summary", "outputs/freefield_aperture_calibration/d60_dx0p5_fieldonly_20260713/run/summary.json", "freefield_gate", True),
    ("d60_dx0p5_field", "outputs/freefield_aperture_calibration/d60_dx0p5_fieldonly_20260713/run/pressure_max_mpa.npz", "freefield_gate", True),
    ("d60_grid_convergence_report", "outputs/freefield_aperture_calibration/d60_grid_convergence_20260713/d60_grid_convergence_report.json", "freefield_gate", True),
    ("plan", "NEXT_PHASE_EXECUTION_PLAN.md", "governance", True),
    ("manifest", "outputs/reproducibility_manifest/case_079_reproducibility_manifest.json", "governance", True),
    ("evidence_registry", "outputs/evidence_registry/evidence_registry.json", "governance", True),
    ("run_ledger", "outputs/run_ledger.jsonl", "governance", True),
    ("dx075_model_summary", "outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/summary.json", "model", True),
    ("dx075_entry_plan", "outputs/corrected_entry_plan_resolution_chain/079_candidate_006_dx0p75/selected_entry_plan.json", "coordinate_chain", True),
    ("dx075_entry_validation", "outputs/corrected_entry_plan_resolution_chain/079_candidate_006_dx0p75/corrected_entry_plan_resolution_chain_validation.json", "coordinate_chain", True),
    ("dx05_entry_plan", "outputs/corrected_entry_plan_resolution_chain/079_candidate_006_dx0p5/selected_entry_plan.json", "coordinate_chain", True),
    ("dx05_entry_validation", "outputs/corrected_entry_plan_resolution_chain/079_candidate_006_dx0p5/corrected_entry_plan_resolution_chain_validation.json", "coordinate_chain", True),
    ("dx05_dry_run", "outputs/corrected_entry_plan_resolution_chain/079_candidate_006_dx0p5/dry_run_quality/quality_dry_run_summary.json", "coordinate_chain", True),
    ("pressure_summary", "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard/summary.json", "pressure", True),
    ("pressure_focus_metrics", "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard/focus_metrics.json", "pressure", True),
    ("pressure_field", "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard/pressure_max_mpa.npz", "pressure", True),
    ("p3a_report", "outputs/p3a_pml16_sensitivity_analysis/079_candidate_006_dx0p75/p3a_pml16_sensitivity_report.json", "sensitivity", True),
    ("p3b_report", "outputs/p3b_cfl0p1_sensitivity_analysis/079_candidate_006_dx0p75/p3b_cfl0p1_sensitivity_report.json", "sensitivity", True),
    ("thermal_summary", "outputs/corrected_pennes_thermal/pennes_summary.json", "thermal", True),
    ("thermal_field", "outputs/corrected_pennes_thermal/pennes_temperature_c.npz", "thermal", True),
    ("thermal_schedule", "outputs/corrected_pennes_thermal/pulse_schedule.csv", "thermal", True),
    ("thermal_curve", "outputs/corrected_pennes_thermal/temperature_time_curve.csv", "thermal", True),
    ("simulation_environment", "outputs/corrected_entry_plan_resolution_chain/079_candidate_006_dx0p5/dry_run_quality/quality_dry_run_summary.json", "environment", True),
    ("collinear_pressure_summary", "outputs/collinear_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard/summary.json", "pressure", True),
    ("collinear_pressure_field", "outputs/collinear_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard/pressure_max_mpa.npz", "pressure", True),
    ("collinear_thermal_summary", "outputs/collinear_pennes_thermal/pennes_summary.json", "thermal", True),
    ("collinear_thermal_field", "outputs/collinear_pennes_thermal/pennes_temperature_c.npz", "thermal", True),
    ("sweep_005_pressure_summary", "outputs/ct_sweep_scan_079_dx0p75/sweep_005/summary.json", "pressure", True),
    ("sweep_005_pressure_field", "outputs/ct_sweep_scan_079_dx0p75/sweep_005/pressure_max_mpa.npz", "pressure", True),
    ("sweep_005_thermal_summary", "outputs/ct_sweep_scan_079_dx0p75/sweep_005/pennes_thermal/pennes_summary.json", "thermal", True),
    ("sweep_005_thermal_field", "outputs/ct_sweep_scan_079_dx0p75/sweep_005/pennes_thermal/pennes_temperature_c.npz", "thermal", True),
    ("sweep_000_pressure_summary", "outputs/ct_sweep_scan_079_dx0p75/sweep_000/summary.json", "pressure", True),
    ("sweep_000_pressure_field", "outputs/ct_sweep_scan_079_dx0p75/sweep_000/pressure_max_mpa.npz", "pressure", True),
    ("sweep_000_thermal_summary", "outputs/ct_sweep_scan_079_dx0p75/sweep_000/pennes_thermal/pennes_summary.json", "thermal", True),
    ("sweep_000_thermal_field", "outputs/ct_sweep_scan_079_dx0p75/sweep_000/pennes_thermal/pennes_temperature_c.npz", "thermal", True),
    ("dx05_sweep_000_pressure_summary", "outputs/ct_sweep_scan_079_dx0p5/sweep_000/summary.json", "pressure", True),
    ("dx05_sweep_000_pressure_field", "outputs/ct_sweep_scan_079_dx0p5/sweep_000/pressure_max_mpa.npz", "pressure", True),
    ("dx05_sweep_000_thermal_summary", "outputs/ct_sweep_scan_079_dx0p5/sweep_000/pennes_thermal/pennes_summary.json", "thermal", True),
    ("dx05_sweep_000_thermal_field", "outputs/ct_sweep_scan_079_dx0p5/sweep_000/pennes_thermal/pennes_temperature_c.npz", "thermal", True),
    ("dx05_sweep_000_grid_comparison", "outputs/ct_sweep_grid_convergence_analysis/079_sweep_000_dx075_vs_dx05/grid_comparison.json", "sensitivity", True),
    ("dx05_sweep_000_hotspot_audit", "outputs/ct_sweep_hotspot_audit/079_sweep_000_dx0p5/hotspot_audit.json", "hotspot_audit", True),
    ("dx05_sweep_000_hotspot_axis_profile", "outputs/ct_sweep_hotspot_audit/079_sweep_000_dx0p5/beam_axis_profile.csv", "hotspot_audit", True),
    ("dx05_sweep_003_pressure_summary", "outputs/ct_sweep_scan_079_dx0p5/sweep_003/summary.json", "pressure", True),
    ("dx05_sweep_003_pressure_field", "outputs/ct_sweep_scan_079_dx0p5/sweep_003/pressure_max_mpa.npz", "pressure", True),
    ("dx05_sweep_003_thermal_summary", "outputs/ct_sweep_scan_079_dx0p5/sweep_003/pennes_thermal/pennes_summary.json", "thermal", True),
    ("dx05_sweep_003_thermal_field", "outputs/ct_sweep_scan_079_dx0p5/sweep_003/pennes_thermal/pennes_temperature_c.npz", "thermal", True),
    ("dx05_sweep_000_p038_pressure_summary", "outputs/ct_sweep_scan_079_dx0p5/sweep_000_p038/summary.json", "pressure", True),
    ("dx05_sweep_000_p038_pressure_field", "outputs/ct_sweep_scan_079_dx0p5/sweep_000_p038/pressure_max_mpa.npz", "pressure", True),
    ("dx05_sweep_000_p038_thermal_summary", "outputs/ct_sweep_scan_079_dx0p5/sweep_000_p038/pennes_thermal/pennes_summary.json", "thermal", True),
    ("dx05_sweep_000_p038_thermal_field", "outputs/ct_sweep_scan_079_dx0p5/sweep_000_p038/pennes_thermal/pennes_temperature_c.npz", "thermal", True),
    ("dx05_sweep_000_p038_scaled_validation", "outputs/ct_sweep_scaled_pressure_validation/079_sweep_000_dx0p5_p038/scaled_pressure_validation.json", "scaled_validation", True),
]

COMMANDS = {
    "regenerate_manifest": "D:\\AIprogram\\python-envs\\kwave312\\Scripts\\python.exe generate_reproducibility_manifest.py",
    "validate_manifest": "D:\\AIprogram\\python-envs\\kwave312\\Scripts\\python.exe validate_reproducibility_manifest.py",
    "generate_package": "D:\\AIprogram\\python-envs\\kwave312\\Scripts\\python.exe generate_final_reproducibility_package.py",
    "validate_package": "D:\\AIprogram\\python-envs\\kwave312\\Scripts\\python.exe validate_final_reproducibility_package.py",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(relative_path: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8-sig"))


def git_value(*args: str) -> str:
    git = r"D:\AIprogram\tools\Git\cmd\git.exe"
    result = subprocess.run([git, *args], cwd=PROJECT_ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def artifact_index() -> list[dict[str, Any]]:
    items = []
    for artifact_id, relative_path, role, required in ARTIFACTS:
        path = PROJECT_ROOT / relative_path
        items.append(
            {
                "artifact_id": artifact_id,
                "path": relative_path.replace("\\", "/"),
                "role": role,
                "required": required,
                "exists": path.is_file(),
                "size_bytes": path.stat().st_size if path.is_file() else None,
                "sha256": sha256(path) if path.is_file() else None,
            }
        )
    return items


def build_index() -> dict[str, Any]:
    pressure = read_json("outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard/focus_metrics.json")
    thermal = read_json("outputs/corrected_pennes_thermal/pennes_summary.json")
    p3a = read_json("outputs/p3a_pml16_sensitivity_analysis/079_candidate_006_dx0p75/p3a_pml16_sensitivity_report.json")
    p3b = read_json("outputs/p3b_cfl0p1_sensitivity_analysis/079_candidate_006_dx0p75/p3b_cfl0p1_sensitivity_report.json")
    dx05_validation = read_json("outputs/corrected_entry_plan_resolution_chain/079_candidate_006_dx0p5/corrected_entry_plan_resolution_chain_validation.json")
    grid_comparison = read_json("outputs/ct_sweep_grid_convergence_analysis/079_sweep_000_dx075_vs_dx05/grid_comparison.json")
    hotspot_audit = read_json("outputs/ct_sweep_hotspot_audit/079_sweep_000_dx0p5/hotspot_audit.json")
    scaled_validation = read_json("outputs/ct_sweep_scaled_pressure_validation/079_sweep_000_dx0p5_p038/scaled_pressure_validation.json")
    return {
        "package_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_id": "079",
        "candidate_id": "candidate_006",
        "claim_level": "auditable_research_dataset_candidate_not_numerical_convergence",
        "git": {
            "commit": git_value("rev-parse", "HEAD"),
            "branch": git_value("branch", "--show-current"),
            "remote": "origin/public-prep",
        },
        "environment": {
            "python_executable": sys.executable,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "commands": COMMANDS,
        "artifacts": artifact_index(),
        "key_results": {
            "pressure": {
                "target_pressure_mpa": pressure.get("target_pressure_mpa"),
                "target_window_peak_mpa": pressure.get("target_window_peak_mpa"),
                "global_peak_mpa": pressure.get("global_peak_mpa"),
                "global_peak_to_target_distance_mm": pressure.get("global_peak_to_target_distance_mm"),
                "target_to_global_peak_ratio": pressure.get("target_to_global_peak_ratio"),
            },
            "sensitivity": {
                "pml16_stable_within_thresholds": p3a.get("decision", {}).get("p3a_stable_within_thresholds"),
                "cfl01_stable_within_thresholds": p3b.get("decision", {}).get("p3b_stable_within_thresholds"),
                "dx05_coordinate_chain_valid": dx05_validation.get("chain_valid"),
                "dx05_sweep000_pressure_executed": True,
                "dx05_sweep000_target_window_peak_delta_percent": grid_comparison.get("deltas_dx0p5_vs_dx0p75_percent", {}).get("target_window_peak_mpa"),
                "dx05_sweep000_skull_cem43_delta_percent": grid_comparison.get("deltas_dx0p5_vs_dx0p75_percent", {}).get("skull_max_cem43_min"),
                "numerical_convergence_demonstrated": grid_comparison.get("decision", {}).get("numerical_convergence_demonstrated"),
                "dx05_sweep000_hotspot_material": hotspot_audit.get("decision", {}).get("hotspot_material"),
                "dx05_sweep000_scaled_source_pressure_screening_mpa": hotspot_audit.get("source_pressure_scaling", {}).get("safe_threshold_estimate", {}).get("source_pressure_mpa"),
                "dx05_sweep000_scaled_source_pressure_validated": scaled_validation.get("decision", {}).get("scaled_validation_passed_local_thermal_gates"),
                "dx05_sweep000_scaled_source_pressure_pa": scaled_validation.get("decision", {}).get("validated_source_pressure_pa"),
                "dx05_sweep000_scaled_clinical_safety_allowed": scaled_validation.get("decision", {}).get("clinical_or_medical_safety_conclusion_allowed"),
            },
            "thermal": {
                "max_temperature_rise_c": thermal.get("max_temperature_rise_c"),
                "target_temperature_rise_c": thermal.get("target_temperature_rise_c"),
                "brain_max_cem43_min": thermal.get("brain_max_cem43_min"),
                "skull_max_cem43_min": thermal.get("skull_max_cem43_min"),
            },
        },
        "limitations": [
            "The dx0.5 sweep_000 pressure comparison completed, but it is a grid-sensitivity/hotspot diagnostic, not a numerical convergence demonstration.",
            "The dx0.5 0.38 MPa scaled run passes local engineering thermal-dose gates, but it is not a clinical or medical safety conclusion.",
            "PML and CFL observations passed predeclared thresholds but do not establish numerical convergence.",
            "The global and effective pressure peaks remain displaced from the target; this is not a tuned-focus baseline.",
            "The Pennes calculation uses approximate material maps and an averaged protocol representation.",
            "The dx0.5 sweep_000 thermal result is unsafe under the approximate Pennes protocol and should not be interpreted as a clinical safety conclusion.",
            "This package does not establish clinical safety, efficacy, or a validated default mapping profile.",
        ],
        "blocked_claims": [
            "numerical convergence",
            "paper-grade validated pressure baseline",
            "tuned focus",
            "clinical or medical safety",
            "medical efficacy",
            "default profile promotion",
        ],
        "next_research_gate": "Use 0.38 MPa as a local engineering validation point only; next work should improve focus or validate assumptions, not promote clinical safety.",
    }


def build_report(index: dict[str, Any]) -> str:
    pressure = index["key_results"]["pressure"]
    thermal = index["key_results"]["thermal"]
    rows = [
        "# Case 079 Final Reproducibility Package",
        "",
        f"- package version: `{index['package_version']}`",
        f"- generated at: `{index['generated_at']}`",
        f"- Git commit: `{index['git']['commit']}`",
        f"- claim level: `{index['claim_level']}`",
        "",
        "## Scope",
        "",
        "This package indexes the selected corrected pressure dataset, two numerical-sensitivity observations, the corrected dx0.5 coordinate-chain prerequisite, and the derived Pennes dataset. It is an auditable research dataset candidate, not evidence of numerical convergence or clinical safety.",
        "",
        "## Key Results",
        "",
        f"- target pressure: `{pressure['target_pressure_mpa']}` MPa",
        f"- target-window peak: `{pressure['target_window_peak_mpa']}` MPa",
        f"- global peak: `{pressure['global_peak_mpa']}` MPa",
        f"- global peak distance to target: `{pressure['global_peak_to_target_distance_mm']}` mm",
        f"- maximum modeled temperature rise: `{thermal['max_temperature_rise_c']}` C",
        f"- target modeled temperature rise: `{thermal['target_temperature_rise_c']}` C",
        "",
        "## Reproduction",
        "",
    ]
    rows.extend(f"1. `{command}`" for command in index["commands"].values())
    rows.extend(["", "## Artifact Index", "", "| Artifact | Role | Size (bytes) | SHA-256 |", "|---|---|---:|---|"])
    for item in index["artifacts"]:
        rows.append(f"| `{item['path']}` | `{item['role']}` | {item['size_bytes']} | `{item['sha256']}` |")
    rows.extend(["", "## Limitations", ""])
    rows.extend(f"- {item}" for item in index["limitations"])
    rows.extend(["", "## Next Research Gate", "", index["next_research_gate"], ""])
    return "\n".join(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index = build_index()
    OUT_INDEX.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_REPORT.write_text(build_report(index), encoding="utf-8")
    print(json.dumps({"artifact_count": len(index["artifacts"]), "missing_count": sum(not item["exists"] for item in index["artifacts"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
