from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from governance_recent_evidence import ITRUSST_RUN_SPECS, RECENT_RUN_SPECS


PROJECT_ROOT = Path(__file__).resolve().parent
LEDGER_PATH = PROJECT_ROOT / "outputs" / "run_ledger.jsonl"
SUMMARY_PATH = PROJECT_ROOT / "outputs" / "run_ledger_summary.json"
REPORT_PATH = PROJECT_ROOT / "outputs" / "run_ledger_summary.md"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def nested(data: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def build_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    blocked_claims = [
        "validated pressure baseline",
        "paper-grade reproduction",
        "medical/safety conclusion",
        "profile/default promotion",
    ]

    freefield_output_dir = PROJECT_ROOT / "outputs/freefield_current_tuned_calibration/ap30_r35_f500_dx0p75_pml12_standard"
    freefield_summary_path = freefield_output_dir / "freefield_summary.json"
    freefield_p1_summary_path = freefield_output_dir / "free_field_calibration_summary.json"
    if freefield_summary_path.exists():
        freefield_summary = read_json(freefield_summary_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "freefield_ap30_r35_f500_dx075_pml12_standard_2026-07-08",
                "case_id": "freefield",
                "candidate_id": "ap30_r35_current_tuned",
                "profile": "water",
                "preset": str(nested(freefield_summary, ["config", "preset"], "standard")),
                "output_dir": rel(freefield_output_dir),
                "runner_status": "kwave_ok",
                "runtime_s": float(nested(freefield_summary, ["runtime", "runtime_s"], 0.0)),
                "pressure_generated": (freefield_output_dir / "pressure_max_mpa.npz").exists(),
                "summary_generated": True,
                "claim_level": "free_field_calibration_standard_engineering_validation",
                "authorization": "explicit user authorization in Codex thread: 可以，开始吧, after acoustic-field-first plan",
                "command_route": "python legacy_archive/simulate_freefield_transducer.py with PYTHONPATH project root",
                "pressure_path": rel(freefield_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(freefield_summary_path),
                "execution_summary_path": rel(freefield_p1_summary_path) if freefield_p1_summary_path.exists() else rel(freefield_summary_path),
                "blocked_claims": blocked_claims
                + [
                    "transcranial in-situ pressure claim",
                    "clinical safety claim",
                    "paper-grade free-field calibration",
                ],
            }
        )

    thick_output_dir = PROJECT_ROOT / "outputs/thick_skull_candidate_runs/079_offset_y+005_z+000_ap30_r35_dx0p75_pml12_standard_pressure_20260710"
    thick_summary_path = thick_output_dir / "summary.json"
    thick_runner_path = thick_output_dir / "runner_status.json"
    thick_report_path = PROJECT_ROOT / "outputs/thick_skull_external_validity_079/thick_skull_external_validity_report.json"
    if thick_summary_path.exists() and thick_runner_path.exists() and thick_report_path.exists():
        thick_summary = read_json(thick_summary_path)
        thick_runner = read_json(thick_runner_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_offset_y+005_z+000_ap30_r35_dx075_pml12_standard_2026-07-10",
                "case_id": "079",
                "candidate_id": "offset_y+005_z+000",
                "profile": "simple_hu300",
                "preset": str(nested(thick_summary, ["config", "preset"], "standard")),
                "output_dir": rel(thick_output_dir),
                "runner_status": str(thick_runner.get("status", "unknown")),
                "runtime_s": float(nested(thick_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": (thick_output_dir / "pressure_max_mpa.npz").exists(),
                "summary_generated": thick_summary_path.exists(),
                "claim_level": "standard_engineering_external_validity_failure_observation",
                "authorization": "explicit user continuation after the documented dry-run authorization boundary",
                "command_route": "run_kwave_command.py --execute with 120 s checkpoints and 120 min hard stop",
                "pressure_path": rel(thick_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(thick_summary_path),
                "execution_summary_path": rel(thick_report_path),
                "blocked_claims": blocked_claims
                + [
                    "tuned-focus baseline",
                    "compliant MItc",
                    "clinical safety claim",
                    "paper-grade thick-skull validity",
                ],
            }
        )

    screening_runs = [
        (
            "079_plus5_tukey03_quick_2026-07-10",
            PROJECT_ROOT / "outputs/hotspot_mitigation_screening_079/tukey03_1x1_quick",
            PROJECT_ROOT / "outputs/hotspot_mitigation_screening_079/hotspot_mitigation_screening_report.json",
            "quick_engineering_negative_screen",
        ),
        (
            "079_plus5_radius_matched_r74p435_quick_2026-07-11",
            PROJECT_ROOT / "outputs/radius_matched_geometry_079/ap30_r74p435_single_bowl_quick_post8",
            PROJECT_ROOT / "outputs/radius_matched_geometry_079/radius_matched_geometry_report.json",
            "quick_engineering_diagnostic_candidate_rejected",
        ),
        (
            "079_plus5_radius_matched_pathintegral_15x15_quick_v2_2026-07-11",
            PROJECT_ROOT / "outputs/radius_matched_phase_control_079/ap30_r74p435_15x15_pathintegral_quick_v2",
            PROJECT_ROOT / "outputs/radius_matched_phase_control_079/radius_matched_phase_control_report.json",
            "quick_engineering_negative_screen_directional_near_miss",
        ),
    ]
    for run_id, output_dir, report_path, claim_level in screening_runs:
        summary_path = output_dir / "summary.json"
        runner_path = output_dir / "runner_status.json"
        if summary_path.exists() and runner_path.exists() and report_path.exists():
            summary = read_json(summary_path)
            runner = read_json(runner_path)
            entries.append(
                {
                    "ledger_version": "1.0.0",
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "run_id": run_id,
                    "case_id": "079",
                    "candidate_id": "offset_y+005_z+000",
                    "profile": "simple_hu300",
                    "preset": str(nested(summary, ["config", "preset"], "quick")),
                    "output_dir": rel(output_dir),
                    "runner_status": str(runner.get("status", "unknown")),
                    "runtime_s": float(nested(runner, ["execution", "runtime_s"], 0.0)),
                    "pressure_generated": (output_dir / "pressure_max_mpa.npz").exists(),
                    "summary_generated": True,
                    "claim_level": claim_level,
                    "authorization": "explicit acoustic-field-first continuation",
                    "command_route": "run_kwave_command.py --execute after dry-run quality gate",
                    "pressure_path": rel(output_dir / "pressure_max_mpa.npz"),
                    "summary_path": rel(summary_path),
                    "execution_summary_path": rel(report_path),
                    "blocked_claims": blocked_claims + ["tuned-focus baseline", "thermal or clinical safety"],
                }
            )
    standard_path = PROJECT_ROOT / "outputs/ct_standard_pressure_authorization/079_candidate_006_dx0p75_pml12_standard/standard_pressure_execution_summary.json"
    standard = read_json(standard_path)
    standard_output_dir = PROJECT_ROOT / str(standard["output_dir"])
    entries.append(
        {
            "ledger_version": "1.0.0",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "run_id": "079_candidate_006_simple_hu300_dx075_pml12_standard_2026-06-02",
            "case_id": str(standard["case_id"]),
            "candidate_id": str(standard["candidate_id"]),
            "profile": str(standard["mapping_profile"]),
            "preset": str(standard["preset"]),
            "output_dir": standard["output_dir"],
            "runner_status": nested(standard, ["runner", "status"]),
            "runtime_s": float(nested(standard, ["runner", "runtime_s"], 0.0)),
            "pressure_generated": bool(nested(standard, ["runner", "core_output_exists", "pressure"], False)),
            "summary_generated": bool(nested(standard, ["runner", "core_output_exists", "summary"], False)),
            "claim_level": "standard_engineering_pressure_output",
            "authorization": "explicit user authorization in Codex thread before run_kwave_command.py --execute",
            "command_route": "run_kwave_command.py --execute",
            "pressure_path": rel(standard_output_dir / "pressure_max_mpa.npz"),
            "summary_path": rel(standard_output_dir / "summary.json"),
            "execution_summary_path": rel(standard_path),
            "blocked_claims": blocked_claims,
        }
    )

    grid_output_dir = PROJECT_ROOT / "outputs/ct_grid_convergence_runs/079_candidate_006_dx0p5_standard"
    grid_runner_path = grid_output_dir / "runner_status.json"
    if grid_runner_path.exists():
        grid_runner = read_json(grid_runner_path)
        claim_level = "coordinate_mapping_diagnostic_not_grid_convergence"
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_candidate_006_simple_hu300_dx05_pml12_cfl02_standard_2026-06-13",
                "case_id": "079",
                "candidate_id": "candidate_006",
                "profile": "simple_hu300",
                "preset": "standard",
                "output_dir": rel(grid_output_dir),
                "runner_status": grid_runner.get("status"),
                "runtime_s": float(nested(grid_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": bool(nested(grid_runner, ["execution", "core_output_exists", "pressure"], False)),
                "summary_generated": bool(nested(grid_runner, ["execution", "core_output_exists", "summary"], False)),
                "claim_level": claim_level,
                "authorization": "explicit user authorization in Codex thread: 继续, after dx0.5 model-build and dry-run-quality completed",
                "command_route": "run_kwave_command.py --execute",
                "pressure_path": rel(grid_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(grid_output_dir / "summary.json"),
                "execution_summary_path": rel(grid_runner_path),
                "blocked_claims": blocked_claims,
            }
        )
    corrected_output_dir = PROJECT_ROOT / "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard"
    corrected_runner_path = corrected_output_dir / "runner_status.json"
    corrected_summary_path = corrected_output_dir / "summary.json"
    if corrected_runner_path.exists() and corrected_summary_path.exists():
        corrected_runner = read_json(corrected_runner_path)
        corrected_summary = read_json(corrected_summary_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_candidate_006_simple_hu300_dx075_pml12_cfl02_corrected_standard_2026-06-18",
                "case_id": "079",
                "candidate_id": "candidate_006",
                "profile": "simple_hu300",
                "preset": str(corrected_summary.get("config", {}).get("preset", "standard")),
                "output_dir": rel(corrected_output_dir),
                "runner_status": corrected_runner.get("status"),
                "runtime_s": float(nested(corrected_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": bool(nested(corrected_runner, ["execution", "core_output_exists", "pressure"], False)),
                "summary_generated": bool(nested(corrected_runner, ["execution", "core_output_exists", "summary"], False)),
                "claim_level": "corrected_standard_pressure_research_dataset_candidate",
                "authorization": "explicit user authorization in Codex thread: continue P2 corrected dx0.75 standard pressure baseline",
                "command_route": "run_kwave_command.py --execute",
                "pressure_path": rel(corrected_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(corrected_summary_path),
                "execution_summary_path": rel(corrected_runner_path),
                "blocked_claims": blocked_claims
                + [
                    "tuned focus baseline",
                    "numerical convergence claim",
                    "thermal or safety conclusion",
                ],
                "notes": [
                    str(corrected_summary.get("tuning_note", "")),
                    "Corrected entry plan matches dx0.75 model and was run without bypassing the resolution gate.",
                ],
            }
        )
    p3a_output_dir = PROJECT_ROOT / "outputs/corrected_pressure_sensitivity/079_candidate_006_dx0p75_pml16_cfl0p2_standard"
    p3a_runner_path = p3a_output_dir / "runner_status.json"
    p3a_summary_path = p3a_output_dir / "summary.json"
    p3a_report_path = PROJECT_ROOT / "outputs/p3a_pml16_sensitivity_analysis/079_candidate_006_dx0p75/p3a_pml16_sensitivity_report.json"
    if p3a_runner_path.exists() and p3a_summary_path.exists():
        p3a_runner = read_json(p3a_runner_path)
        p3a_summary = read_json(p3a_summary_path)
        p3a_report = read_json(p3a_report_path) if p3a_report_path.exists() else {}
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_candidate_006_simple_hu300_dx075_pml16_cfl02_standard_2026-06-18",
                "case_id": "079",
                "candidate_id": "candidate_006",
                "profile": "simple_hu300",
                "preset": str(p3a_summary.get("config", {}).get("preset", "standard")),
                "output_dir": rel(p3a_output_dir),
                "runner_status": p3a_runner.get("status"),
                "runtime_s": float(nested(p3a_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": bool(nested(p3a_runner, ["execution", "core_output_exists", "pressure"], False)),
                "summary_generated": bool(nested(p3a_runner, ["execution", "core_output_exists", "summary"], False)),
                "claim_level": "pml_boundary_sensitivity_observation_not_convergence",
                "authorization": "explicit user authorization in Codex thread: continue next step, interpreted as P3a PML16 boundary sensitivity only",
                "command_route": "run_kwave_command.py --execute",
                "pressure_path": rel(p3a_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(p3a_summary_path),
                "execution_summary_path": rel(p3a_runner_path),
                "analysis_path": rel(p3a_report_path) if p3a_report_path.exists() else None,
                "blocked_claims": blocked_claims
                + [
                    "tuned focus baseline",
                    "numerical convergence claim",
                    "thermal or safety conclusion",
                ],
                "notes": [
                    str(p3a_summary.get("tuning_note", "")),
                    f"p3a_stable_within_thresholds={nested(p3a_report, ['decision', 'p3a_stable_within_thresholds'], None)}",
                ],
            }
        )
    p3b_output_dir = PROJECT_ROOT / "outputs/corrected_pressure_sensitivity/079_candidate_006_dx0p75_pml12_cfl0p1_standard"
    p3b_runner_path = p3b_output_dir / "runner_status.json"
    p3b_summary_path = p3b_output_dir / "summary.json"
    p3b_report_path = PROJECT_ROOT / "outputs/p3b_cfl0p1_sensitivity_analysis/079_candidate_006_dx0p75/p3b_cfl0p1_sensitivity_report.json"
    if p3b_runner_path.exists() and p3b_summary_path.exists():
        p3b_runner = read_json(p3b_runner_path)
        p3b_summary = read_json(p3b_summary_path)
        p3b_report = read_json(p3b_report_path) if p3b_report_path.exists() else {}
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_candidate_006_simple_hu300_dx075_pml12_cfl01_standard_2026-06-19",
                "case_id": "079",
                "candidate_id": "candidate_006",
                "profile": "simple_hu300",
                "preset": str(p3b_summary.get("config", {}).get("preset", "standard")),
                "output_dir": rel(p3b_output_dir),
                "runner_status": p3b_runner.get("status"),
                "runtime_s": float(nested(p3b_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": bool(nested(p3b_runner, ["execution", "core_output_exists", "pressure"], False)),
                "summary_generated": bool(nested(p3b_runner, ["execution", "core_output_exists", "summary"], False)),
                "claim_level": "cfl_timestep_sensitivity_observation_not_convergence",
                "authorization": "explicit user authorization in Codex thread: continue next step, interpreted as P3b CFL0.1 timestep sensitivity only",
                "command_route": "run_kwave_command.py --execute",
                "pressure_path": rel(p3b_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(p3b_summary_path),
                "execution_summary_path": rel(p3b_runner_path),
                "analysis_path": rel(p3b_report_path) if p3b_report_path.exists() else None,
                "blocked_claims": blocked_claims
                + [
                    "tuned focus baseline",
                    "numerical convergence claim",
                    "thermal or safety conclusion",
                ],
                "notes": [
                    str(p3b_summary.get("tuning_note", "")),
                    f"p3b_stable_within_thresholds={nested(p3b_report, ['decision', 'p3b_stable_within_thresholds'], None)}",
                ],
            }
        )
    collinear_output_dir = PROJECT_ROOT / "outputs/collinear_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard"
    collinear_summary_path = collinear_output_dir / "summary.json"
    if collinear_summary_path.exists():
        collinear_summary = read_json(collinear_summary_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_candidate_006_simple_hu300_dx075_pml12_cfl02_collinear_standard_2026-06-26",
                "case_id": "079",
                "candidate_id": "candidate_006_collinear",
                "profile": "simple_hu300",
                "preset": str(collinear_summary.get("config", {}).get("preset", "standard")),
                "output_dir": rel(collinear_output_dir),
                "runner_status": "kwave_ok",
                "runtime_s": float(nested(collinear_summary, ["runtime", "runtime_s"], 0.0)),
                "pressure_generated": (collinear_output_dir / "pressure_max_mpa.npz").exists(),
                "summary_generated": True,
                "claim_level": "collinear_baseline_pressure_output",
                "authorization": "explicit user authorization for collinear entry path simulation and thermal safety verification",
                "command_route": "python simulate_kwave_3d_focus.py",
                "pressure_path": rel(collinear_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(collinear_summary_path),
                "execution_summary_path": rel(collinear_summary_path),
                "blocked_claims": blocked_claims
                + [
                    "tuned focus baseline",
                    "numerical convergence claim",
                    "thermal or safety conclusion",
                ],
                "notes": [
                    str(collinear_summary.get("tuning_note", "")),
                ],
            }
        )

    sweep_005_output_dir = PROJECT_ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005"
    sweep_005_runner_path = sweep_005_output_dir / "runner_status.json"
    sweep_005_summary_path = sweep_005_output_dir / "summary.json"
    if sweep_005_runner_path.exists() and sweep_005_summary_path.exists():
        sweep_005_runner = read_json(sweep_005_runner_path)
        sweep_005_summary = read_json(sweep_005_summary_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_sweep_005_simple_hu300_dx075_pml12_cfl02_standard_2026-06-28",
                "case_id": "079",
                "candidate_id": "sweep_005",
                "profile": "simple_hu300",
                "preset": str(sweep_005_summary.get("config", {}).get("preset", "standard")),
                "output_dir": rel(sweep_005_output_dir),
                "runner_status": sweep_005_runner.get("status"),
                "runtime_s": float(nested(sweep_005_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": bool(nested(sweep_005_runner, ["execution", "core_output_exists", "pressure"], False)),
                "summary_generated": bool(nested(sweep_005_runner, ["execution", "core_output_exists", "summary"], False)),
                "claim_level": "sweep_005_standard_pressure_output",
                "authorization": "explicit user authorization for sweep_005 standard preset simulation",
                "command_route": "run_kwave_command.py --execute",
                "pressure_path": rel(sweep_005_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(sweep_005_summary_path),
                "execution_summary_path": rel(sweep_005_runner_path),
                "blocked_claims": blocked_claims
                + [
                    "tuned focus baseline",
                    "numerical convergence claim",
                    "thermal or safety conclusion",
                ],
                "notes": [
                    "Optimal geometric sweep candidate simulation from Scheme A sweep scan."
                ],
            }
        )

    sweep_005_p500_output_dir = PROJECT_ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p500"
    sweep_005_p500_runner_path = sweep_005_p500_output_dir / "runner_status.json"
    sweep_005_p500_summary_path = sweep_005_p500_output_dir / "summary.json"
    if sweep_005_p500_runner_path.exists() and sweep_005_p500_summary_path.exists():
        sweep_005_p500_runner = read_json(sweep_005_p500_runner_path)
        sweep_005_p500_summary = read_json(sweep_005_p500_summary_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_sweep_005_p500_simple_hu300_dx075_pml12_cfl02_standard_2026-07-01",
                "case_id": "079",
                "candidate_id": "sweep_005_p500",
                "profile": "simple_hu300",
                "preset": str(sweep_005_p500_summary.get("config", {}).get("preset", "standard")),
                "output_dir": rel(sweep_005_p500_output_dir),
                "runner_status": sweep_005_p500_runner.get("status"),
                "runtime_s": float(nested(sweep_005_p500_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": bool(nested(sweep_005_p500_runner, ["execution", "core_output_exists", "pressure"], False)),
                "summary_generated": bool(nested(sweep_005_p500_runner, ["execution", "core_output_exists", "summary"], False)),
                "claim_level": "sweep_005_p500_scaled_pressure_output",
                "authorization": "explicit user authorization for sweep_005 pressure scaling 0.5 MPa",
                "command_route": "run_kwave_command.py --execute",
                "pressure_path": rel(sweep_005_p500_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(sweep_005_p500_summary_path),
                "execution_summary_path": rel(sweep_005_p500_runner_path),
                "blocked_claims": blocked_claims
                + [
                    "tuned focus baseline",
                    "numerical convergence claim",
                    "thermal or safety conclusion",
                ],
                "notes": [
                    "sweep_005 0.5 MPa scaled pressure output for Pareto frontier exploration."
                ],
            }
        )

    sweep_005_p600_output_dir = PROJECT_ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p600"
    sweep_005_p600_runner_path = sweep_005_p600_output_dir / "runner_status.json"
    sweep_005_p600_summary_path = sweep_005_p600_output_dir / "summary.json"
    if sweep_005_p600_runner_path.exists() and sweep_005_p600_summary_path.exists():
        sweep_005_p600_runner = read_json(sweep_005_p600_runner_path)
        sweep_005_p600_summary = read_json(sweep_005_p600_summary_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_sweep_005_p600_simple_hu300_dx075_pml12_cfl02_standard_2026-07-02",
                "case_id": "079",
                "candidate_id": "sweep_005_p600",
                "profile": "simple_hu300",
                "preset": str(sweep_005_p600_summary.get("config", {}).get("preset", "standard")),
                "output_dir": rel(sweep_005_p600_output_dir),
                "runner_status": sweep_005_p600_runner.get("status"),
                "runtime_s": float(nested(sweep_005_p600_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": bool(nested(sweep_005_p600_runner, ["execution", "core_output_exists", "pressure"], False)),
                "summary_generated": bool(nested(sweep_005_p600_runner, ["execution", "core_output_exists", "summary"], False)),
                "claim_level": "sweep_005_p600_scaled_pressure_output",
                "authorization": "explicit user authorization for sweep_005 pressure scaling 0.6 MPa",
                "command_route": "run_kwave_command.py --execute",
                "pressure_path": rel(sweep_005_p600_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(sweep_005_p600_summary_path),
                "execution_summary_path": rel(sweep_005_p600_runner_path),
                "blocked_claims": blocked_claims
                + [
                    "tuned focus baseline",
                    "numerical convergence claim",
                    "thermal or safety conclusion",
                ],
                "notes": [
                    "sweep_005 0.6 MPa scaled pressure output for Pareto frontier exploration."
                ],
            }
        )

    sweep_005_p700_output_dir = PROJECT_ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p700"
    sweep_005_p700_runner_path = sweep_005_p700_output_dir / "runner_status.json"
    sweep_005_p700_summary_path = sweep_005_p700_output_dir / "summary.json"
    if sweep_005_p700_runner_path.exists() and sweep_005_p700_summary_path.exists():
        sweep_005_p700_runner = read_json(sweep_005_p700_runner_path)
        sweep_005_p700_summary = read_json(sweep_005_p700_summary_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_sweep_005_p700_simple_hu300_dx075_pml12_cfl02_standard_2026-07-02",
                "case_id": "079",
                "candidate_id": "sweep_005_p700",
                "profile": "simple_hu300",
                "preset": str(sweep_005_p700_summary.get("config", {}).get("preset", "standard")),
                "output_dir": rel(sweep_005_p700_output_dir),
                "runner_status": sweep_005_p700_runner.get("status"),
                "runtime_s": float(nested(sweep_005_p700_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": bool(nested(sweep_005_p700_runner, ["execution", "core_output_exists", "pressure"], False)),
                "summary_generated": bool(nested(sweep_005_p700_runner, ["execution", "core_output_exists", "summary"], False)),
                "claim_level": "sweep_005_p700_scaled_pressure_output",
                "authorization": "explicit user authorization for sweep_005 pressure scaling 0.7 MPa",
                "command_route": "run_kwave_command.py --execute",
                "pressure_path": rel(sweep_005_p700_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(sweep_005_p700_summary_path),
                "execution_summary_path": rel(sweep_005_p700_runner_path),
                "blocked_claims": blocked_claims
                + [
                    "tuned focus baseline",
                    "numerical convergence claim",
                    "thermal or safety conclusion",
                ],
                "notes": [
                    "sweep_005 0.7 MPa scaled pressure output for Pareto frontier exploration."
                ],
            }
        )

    sweep_005_p800_output_dir = PROJECT_ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_005_p800"
    sweep_005_p800_runner_path = sweep_005_p800_output_dir / "runner_status.json"
    sweep_005_p800_summary_path = sweep_005_p800_output_dir / "summary.json"
    if sweep_005_p800_runner_path.exists() and sweep_005_p800_summary_path.exists():
        sweep_005_p800_runner = read_json(sweep_005_p800_runner_path)
        sweep_005_p800_summary = read_json(sweep_005_p800_summary_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_sweep_005_p800_simple_hu300_dx075_pml12_cfl02_standard_2026-07-02",
                "case_id": "079",
                "candidate_id": "sweep_005_p800",
                "profile": "simple_hu300",
                "preset": str(sweep_005_p800_summary.get("config", {}).get("preset", "standard")),
                "output_dir": rel(sweep_005_p800_output_dir),
                "runner_status": sweep_005_p800_runner.get("status"),
                "runtime_s": float(nested(sweep_005_p800_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": bool(nested(sweep_005_p800_runner, ["execution", "core_output_exists", "pressure"], False)),
                "summary_generated": bool(nested(sweep_005_p800_runner, ["execution", "core_output_exists", "summary"], False)),
                "claim_level": "sweep_005_p800_scaled_pressure_output",
                "authorization": "explicit user authorization for sweep_005 pressure scaling 0.8 MPa",
                "command_route": "run_kwave_command.py --execute",
                "pressure_path": rel(sweep_005_p800_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(sweep_005_p800_summary_path),
                "execution_summary_path": rel(sweep_005_p800_runner_path),
                "blocked_claims": blocked_claims
                + [
                    "tuned focus baseline",
                    "numerical convergence claim",
                    "thermal or safety conclusion",
                ],
                "notes": [
                    "sweep_005 0.8 MPa scaled pressure output for Pareto frontier exploration."
                ],
            }
        )

    sweep_000_output_dir = PROJECT_ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_000"
    sweep_000_runner_path = sweep_000_output_dir / "runner_status.json"
    sweep_000_summary_path = sweep_000_output_dir / "summary.json"
    if sweep_000_runner_path.exists() and sweep_000_summary_path.exists():
        sweep_000_runner = read_json(sweep_000_runner_path)
        sweep_000_summary = read_json(sweep_000_summary_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_sweep_000_simple_hu300_dx075_pml12_cfl02_standard_2026-06-28",
                "case_id": "079",
                "candidate_id": "sweep_000",
                "profile": "simple_hu300",
                "preset": str(sweep_000_summary.get("config", {}).get("preset", "standard")),
                "output_dir": rel(sweep_000_output_dir),
                "runner_status": sweep_000_runner.get("status"),
                "runtime_s": float(nested(sweep_000_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": bool(nested(sweep_000_runner, ["execution", "core_output_exists", "pressure"], False)),
                "summary_generated": bool(nested(sweep_000_runner, ["execution", "core_output_exists", "summary"], False)),
                "claim_level": "sweep_000_standard_pressure_output",
                "authorization": "explicit user authorization for sweep_000 standard preset simulation",
                "command_route": "run_kwave_command.py --execute",
                "pressure_path": rel(sweep_000_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(sweep_000_summary_path),
                "execution_summary_path": rel(sweep_000_runner_path),
                "blocked_claims": blocked_claims
                + [
                    "tuned focus baseline",
                    "numerical convergence claim",
                    "thermal or safety conclusion",
                ],
                "notes": [
                    "Collinear default sweep candidate simulation from Scheme A sweep scan."
                ],
            }
        )
    dx05_sweep_000_output_dir = PROJECT_ROOT / "outputs/ct_sweep_scan_079_dx0p5/sweep_000"
    dx05_sweep_000_runner_path = dx05_sweep_000_output_dir / "runner_status.json"
    dx05_sweep_000_summary_path = dx05_sweep_000_output_dir / "summary.json"
    if dx05_sweep_000_runner_path.exists() and dx05_sweep_000_summary_path.exists():
        dx05_sweep_000_runner = read_json(dx05_sweep_000_runner_path)
        dx05_sweep_000_summary = read_json(dx05_sweep_000_summary_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_sweep_000_simple_hu300_dx05_pml12_cfl02_standard_2026-06-29",
                "case_id": "079",
                "candidate_id": "sweep_000",
                "profile": "simple_hu300",
                "preset": str(dx05_sweep_000_summary.get("config", {}).get("preset", "standard")),
                "output_dir": rel(dx05_sweep_000_output_dir),
                "runner_status": dx05_sweep_000_runner.get("status"),
                "runtime_s": float(nested(dx05_sweep_000_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": bool(nested(dx05_sweep_000_runner, ["execution", "core_output_exists", "pressure"], False)),
                "summary_generated": bool(nested(dx05_sweep_000_runner, ["execution", "core_output_exists", "summary"], False)),
                "claim_level": "grid_sensitivity_hotspot_diagnostic_not_convergence",
                "authorization": "explicit user authorization in Codex thread: 可以, interpreted as exactly one dx0.5 sweep_000 standard pressure restart after prior shutdown interruption",
                "command_route": "run_kwave_command.py --execute",
                "pressure_path": rel(dx05_sweep_000_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(dx05_sweep_000_summary_path),
                "execution_summary_path": rel(dx05_sweep_000_runner_path),
                "analysis_path": rel(PROJECT_ROOT / "outputs/ct_sweep_grid_convergence_analysis/079_sweep_000_dx075_vs_dx05/grid_comparison.json"),
                "blocked_claims": blocked_claims
                + [
                    "tuned focus baseline",
                    "numerical convergence claim",
                    "thermal or medical safety conclusion",
                ],
                "notes": [
                    str(dx05_sweep_000_summary.get("tuning_note", "")),
                    "Corrected dx0.5 sweep_000 entry plan passed dry-run quality and includes skull material in the crop.",
                ],
            }
        )
    dx05_sweep_000_p038_output_dir = PROJECT_ROOT / "outputs/ct_sweep_scan_079_dx0p5/sweep_000_p038"
    dx05_sweep_000_p038_runner_path = dx05_sweep_000_p038_output_dir / "runner_status.json"
    dx05_sweep_000_p038_summary_path = dx05_sweep_000_p038_output_dir / "summary.json"
    dx05_sweep_000_p038_validation_path = (
        PROJECT_ROOT
        / "outputs/ct_sweep_scaled_pressure_validation/079_sweep_000_dx0p5_p038/scaled_pressure_validation.json"
    )
    if dx05_sweep_000_p038_runner_path.exists() and dx05_sweep_000_p038_summary_path.exists():
        dx05_sweep_000_p038_runner = read_json(dx05_sweep_000_p038_runner_path)
        dx05_sweep_000_p038_summary = read_json(dx05_sweep_000_p038_summary_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_sweep_000_simple_hu300_dx05_pml12_cfl02_standard_p038_2026-06-30",
                "case_id": "079",
                "candidate_id": "sweep_000",
                "profile": "simple_hu300",
                "preset": str(dx05_sweep_000_p038_summary.get("config", {}).get("preset", "standard")),
                "output_dir": rel(dx05_sweep_000_p038_output_dir),
                "runner_status": dx05_sweep_000_p038_runner.get("status"),
                "runtime_s": float(nested(dx05_sweep_000_p038_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": bool(nested(dx05_sweep_000_p038_runner, ["execution", "core_output_exists", "pressure"], False)),
                "summary_generated": bool(nested(dx05_sweep_000_p038_runner, ["execution", "core_output_exists", "summary"], False)),
                "claim_level": "scaled_pressure_engineering_validation_not_clinical_safety",
                "authorization": "user requested continuation after hotspot audit; exactly one dx0.5 sweep_000 0.38 MPa scaled-pressure validation run, restarted once after accidental interruption",
                "command_route": "run_kwave_command.py --execute",
                "pressure_path": rel(dx05_sweep_000_p038_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(dx05_sweep_000_p038_summary_path),
                "execution_summary_path": rel(dx05_sweep_000_p038_runner_path),
                "analysis_path": rel(dx05_sweep_000_p038_validation_path),
                "blocked_claims": blocked_claims
                + [
                    "clinical or medical safety conclusion",
                    "tuned focus baseline",
                    "numerical convergence claim",
                ],
                "notes": [
                    str(dx05_sweep_000_p038_summary.get("tuning_note", "")),
                    "0.38 MPa source pressure was selected from the prior hotspot screening estimate and validated only as a local engineering thermal-dose point.",
                ],
            }
        )
    dx05_sweep_003_output_dir = PROJECT_ROOT / "outputs/ct_sweep_scan_079_dx0p5/sweep_003"
    dx05_sweep_003_runner_path = dx05_sweep_003_output_dir / "runner_status.json"
    dx05_sweep_003_summary_path = dx05_sweep_003_output_dir / "summary.json"
    if dx05_sweep_003_runner_path.exists() and dx05_sweep_003_summary_path.exists():
        dx05_sweep_003_runner = read_json(dx05_sweep_003_runner_path)
        dx05_sweep_003_summary = read_json(dx05_sweep_003_summary_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_sweep_003_simple_hu300_dx05_pml12_cfl02_standard_2026-06-29",
                "case_id": "079",
                "candidate_id": "sweep_003",
                "profile": "simple_hu300",
                "preset": str(dx05_sweep_003_summary.get("config", {}).get("preset", "standard")),
                "output_dir": rel(dx05_sweep_003_output_dir),
                "runner_status": dx05_sweep_003_runner.get("status"),
                "runtime_s": float(nested(dx05_sweep_003_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": bool(nested(dx05_sweep_003_runner, ["execution", "core_output_exists", "pressure"], False)),
                "summary_generated": bool(nested(dx05_sweep_003_runner, ["execution", "core_output_exists", "summary"], False)),
                "claim_level": "grid_sensitivity_hotspot_diagnostic_not_convergence",
                "authorization": "explicit user authorization in Codex thread: 按计划进行就好, interpreted as exactly one dx0.5 sweep_003 standard preset simulation",
                "command_route": "run_kwave_command.py --execute",
                "pressure_path": rel(dx05_sweep_003_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(dx05_sweep_003_summary_path),
                "execution_summary_path": rel(dx05_sweep_003_runner_path),
                "blocked_claims": blocked_claims
                + [
                    "tuned focus baseline",
                    "numerical convergence claim",
                    "thermal or medical safety conclusion",
                ],
                "notes": [
                    str(dx05_sweep_003_summary.get("tuning_note", "")),
                    "Corrected dx0.5 sweep_003 entry plan passed dry-run quality and includes skull material in the crop.",
                ],
            }
        )
    # 1. Corrected dx0.5 standard run for candidate_006
    corr_dx05_output_dir = PROJECT_ROOT / "outputs/corrected_pressure_runs/079_candidate_006_dx0p5_pml12_cfl0p2_standard"
    corr_dx05_runner_path = corr_dx05_output_dir / "runner_status.json"
    corr_dx05_summary_path = corr_dx05_output_dir / "summary.json"
    if corr_dx05_runner_path.exists() and corr_dx05_summary_path.exists():
        corr_dx05_runner = read_json(corr_dx05_runner_path)
        corr_dx05_summary = read_json(corr_dx05_summary_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_candidate_006_simple_hu300_dx05_pml12_cfl02_corrected_standard_2026-07-03",
                "case_id": "079",
                "candidate_id": "candidate_006",
                "profile": "simple_hu300",
                "preset": "standard",
                "output_dir": rel(corr_dx05_output_dir),
                "runner_status": corr_dx05_runner.get("status"),
                "runtime_s": float(nested(corr_dx05_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": bool(nested(corr_dx05_runner, ["execution", "core_output_exists", "pressure"], False)),
                "summary_generated": bool(nested(corr_dx05_runner, ["execution", "core_output_exists", "summary"], False)),
                "claim_level": "corrected_standard_pressure_research_dataset_candidate",
                "authorization": "explicit user authorization for corrected dx0.5 standard pressure run",
                "command_route": "run_kwave_command.py --execute",
                "pressure_path": rel(corr_dx05_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(corr_dx05_summary_path),
                "execution_summary_path": rel(corr_dx05_runner_path),
                "blocked_claims": blocked_claims
                + [
                    "validated pressure baseline",
                    "paper-grade reproduction",
                    "medical/safety conclusion",
                    "profile/default promotion",
                    "tuned focus baseline",
                    "numerical convergence claim",
                    "thermal or safety conclusion",
                ],
                "notes": [
                    str(corr_dx05_summary.get("tuning_note", "")),
                    "Corrected entry plan matches dx0.5 model and was run without bypassing the resolution gate.",
                ],
            }
        )

    # 2. dx0.75 sweep_018 standard run
    sweep_018_output_dir = PROJECT_ROOT / "outputs/ct_sweep_scan_079_dx0p75/sweep_018"
    sweep_018_runner_path = sweep_018_output_dir / "runner_status.json"
    sweep_018_summary_path = sweep_018_output_dir / "summary.json"
    if sweep_018_runner_path.exists() and sweep_018_summary_path.exists():
        sweep_018_runner = read_json(sweep_018_runner_path)
        sweep_018_summary = read_json(sweep_018_summary_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_sweep_018_simple_hu300_dx075_pml12_cfl02_standard_2026-07-03",
                "case_id": "079",
                "candidate_id": "sweep_018",
                "profile": "simple_hu300",
                "preset": "standard",
                "output_dir": rel(sweep_018_output_dir),
                "runner_status": sweep_018_runner.get("status"),
                "runtime_s": float(nested(sweep_018_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": bool(nested(sweep_018_runner, ["execution", "core_output_exists", "pressure"], False)),
                "summary_generated": bool(nested(sweep_018_runner, ["execution", "core_output_exists", "summary"], False)),
                "claim_level": "sweep_018_standard_pressure_output",
                "authorization": "explicit user authorization for sweep_018 standard simulation",
                "command_route": "run_kwave_command.py --execute",
                "pressure_path": rel(sweep_018_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(sweep_018_summary_path),
                "execution_summary_path": rel(sweep_018_runner_path),
                "blocked_claims": blocked_claims
                + [
                    "validated pressure baseline",
                    "paper-grade reproduction",
                    "medical/safety conclusion",
                    "profile/default promotion",
                    "tuned focus baseline",
                    "numerical convergence claim",
                    "thermal or safety conclusion",
                ],
                "notes": [
                    str(sweep_018_summary.get("tuning_note", "")),
                ],
            }
        )

    # 3. dx0.5 sweep_001 standard run
    sweep_001_output_dir = PROJECT_ROOT / "outputs/ct_sweep_scan_079_dx0p5/sweep_001"
    sweep_001_runner_path = sweep_001_output_dir / "runner_status.json"
    sweep_001_summary_path = sweep_001_output_dir / "summary.json"
    if sweep_001_runner_path.exists() and sweep_001_summary_path.exists():
        sweep_001_runner = read_json(sweep_001_runner_path)
        sweep_001_summary = read_json(sweep_001_summary_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "079_sweep_001_simple_hu300_dx05_pml12_cfl02_standard_2026-07-03",
                "case_id": "079",
                "candidate_id": "sweep_001",
                "profile": "simple_hu300",
                "preset": "standard",
                "output_dir": rel(sweep_001_output_dir),
                "runner_status": sweep_001_runner.get("status"),
                "runtime_s": float(nested(sweep_001_runner, ["execution", "runtime_s"], 0.0)),
                "pressure_generated": bool(nested(sweep_001_runner, ["execution", "core_output_exists", "pressure"], False)),
                "summary_generated": bool(nested(sweep_001_runner, ["execution", "core_output_exists", "summary"], False)),
                "claim_level": "sweep_001_standard_pressure_output",
                "authorization": "explicit user authorization for sweep_001 standard simulation",
                "command_route": "run_kwave_command.py --execute",
                "pressure_path": rel(sweep_001_output_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(sweep_001_summary_path),
                "execution_summary_path": rel(sweep_001_runner_path),
                "blocked_claims": blocked_claims
                + [
                    "validated pressure baseline",
                    "paper-grade reproduction",
                    "medical/safety conclusion",
                    "profile/default promotion",
                    "tuned focus baseline",
                    "numerical convergence claim",
                    "thermal or safety conclusion",
                ],
                "notes": [
                    str(sweep_001_summary.get("tuning_note", "")),
                ],
            }
        )
    # D60 free-field paper-route point-waveform runs (2026-07-14 / 2026-07-16).
    d60_pointwave_runs = [
        (
            "d60_r78p330_dx0p75_pointwave_2026-07-14",
            PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pointwave_20260714/run",
            "freefield_d60_corrected_dx0p75_pointwave_engineering_calibration",
        ),
        (
            "d60_r78p330_dx0p5_pointwave_2026-07-16",
            PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p5_pointwave_20260716/run",
            "freefield_d60_corrected_dx0p5_pointwave_gate_b_candidate",
        ),
        (
            "d60_r78p330_dx0p75_pml16_pointwave_2026-07-17",
            PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pml16_pointwave_20260717/run",
            "freefield_d60_pml16_sensitivity_observation",
        ),
        (
            "d60_r78p330_dx0p75_cfl0p1_pointwave_2026-07-17",
            PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_cfl0p1_pointwave_20260717/run",
            "freefield_d60_cfl0p1_sensitivity_observation",
        ),
        (
            "d60_r78p330_dx0p375_pointwave_2026-07-18",
            PROJECT_ROOT / "outputs/freefield_aperture_calibration/d60_r78p330_dx0p375_pointwave_20260718/run",
            "freefield_d60_corrected_dx0p375_pointwave_gate_b_residual",
        ),
    ]
    for run_id, output_dir, claim_level in d60_pointwave_runs:
        summary_path = output_dir / "summary.json"
        runner_path = output_dir / "runner_status.json"
        if summary_path.exists() and runner_path.exists():
            summary = read_json(summary_path)
            runner = read_json(runner_path)
            entries.append(
                {
                    "ledger_version": "1.0.0",
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "run_id": run_id,
                    "case_id": "free_field_d60",
                    "candidate_id": "r78p330_corrected_freefield",
                    "profile": "free_field_homogeneous",
                    "preset": str(nested(summary, ["config", "preset"], "paper_grade")),
                    "output_dir": rel(output_dir),
                    "runner_status": str(runner.get("status", "unknown")),
                    "runtime_s": float(nested(runner, ["execution", "runtime_s"], 0.0)),
                    "pressure_generated": (output_dir / "pressure_max_mpa.npz").exists(),
                    "summary_generated": True,
                    "claim_level": claim_level,
                    "authorization": "ACOUSTIC_CURRENT_PLAN_20260714.md P3 Option A restart; user blanket authorization 2026-07-16",
                    "command_route": "run_kwave_point_waveform_command.py --execute after dry-run quality gate",
                    "pressure_path": rel(output_dir / "pressure_max_mpa.npz"),
                    "summary_path": rel(summary_path),
                    "execution_summary_path": rel(runner_path),
                    "blocked_claims": blocked_claims
                    + [
                        "paper-grade numerical convergence",
                        "transcranial efficacy",
                        "thermal or clinical safety",
                    ],
                }
            )
    time_reversal_runs = [
        (
            "tr_079_y+5_z0_dx0p75_2026-07-17",
            PROJECT_ROOT / "outputs/time_reversal_079_y+5_z0",
            "time_reversal_reference_method_engineering_observation",
        ),
    ]
    for run_id, output_dir, claim_level in time_reversal_runs:
        summary_path = output_dir / "summary.json"
        runner_path = output_dir / "runner_status.json"
        if summary_path.exists() and runner_path.exists():
            summary = read_json(summary_path)
            runner = read_json(runner_path)
            entries.append(
                {
                    "ledger_version": "1.0.0",
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "run_id": run_id,
                    "case_id": "079",
                    "candidate_id": "time_reversal_y+5_z0",
                    "profile": "simple_hu300",
                    "preset": str(nested(summary, ["config", "preset"], "standard")),
                    "output_dir": rel(output_dir),
                    "runner_status": str(runner.get("status", "unknown")),
                    "runtime_s": float(nested(runner, ["stages", "calibrate", "runtime_s"], 0.0))
                    + float(nested(runner, ["stages", "refocus", "runtime_s"], 0.0)),
                    "pressure_generated": (output_dir / "pressure_max_mpa.npz").exists(),
                    "summary_generated": True,
                    "claim_level": claim_level,
                    "authorization": "user blanket delegation 2026-07-17 23:25; evidence brief outputs/evidence_briefs/time_reversal_a3/",
                    "command_route": "simulate_time_reversal_focus.py two-stage (calibrate + refocus) via scratch/launch_overnight_20260717.py after dry-run quality gates",
                    "pressure_path": rel(output_dir / "pressure_max_mpa.npz"),
                    "summary_path": rel(summary_path),
                    "execution_summary_path": rel(runner_path),
                    "blocked_claims": blocked_claims
                    + [
                        "paper-grade numerical convergence",
                        "transcranial efficacy",
                        "thermal or clinical safety",
                    ],
                }
            )
    # A.4 adaptive quick screen (2026-07-18 night): 3 Gate A D60 trajectories x {baseline, tr}.
    a4_root = PROJECT_ROOT / "outputs/a4_quick_screen_20260718"
    a4_trajs = ["offset_y+00p0_z-20p0", "offset_y+17p5_z-02p5", "offset_y+17p5_z+10p0"]
    for traj in a4_trajs:
        for arm in ("baseline", "tr"):
            arm_dir = a4_root / traj / arm
            runner_path = arm_dir / "runner_status.json"
            summary_path = arm_dir / "summary.json"
            if not (runner_path.exists() and summary_path.exists()):
                continue
            runner = read_json(runner_path)
            if str(runner.get("status")) != "kwave_ok":
                continue
            summary = read_json(summary_path)
            runtime = sum(
                float(stage.get("elapsed_s", 0.0))
                for stage in runner.get("stages", [])
                if str(stage.get("stage")) in {"run", "calibrate", "refocus"}
            )
            entries.append(
                {
                    "ledger_version": "1.0.0",
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "run_id": f"a4_quick_screen_{traj}_{arm}_2026-07-18",
                    "case_id": "079",
                    "candidate_id": f"gate_a_d60_{traj}",
                    "profile": "simple_hu300",
                    "preset": str(nested(summary, ["config", "preset"], "quick")),
                    "output_dir": rel(arm_dir),
                    "runner_status": str(runner.get("status", "unknown")),
                    "runtime_s": runtime,
                    "pressure_generated": (arm_dir / "pressure_max_mpa.npz").exists(),
                    "summary_generated": True,
                    "claim_level": "a4_adaptive_quick_screen_engineering_observation",
                    "authorization": "user standing delegation 2026-07-18 22:50; evidence brief outputs/evidence_briefs/a4_quick_screen_tr_gated_trajectories/",
                    "command_route": (
                        "run_kwave_point_waveform_command.py --execute (point-waveform online extrema)"
                        if arm == "baseline"
                        else "simulate_time_reversal_focus.py two-stage (calibrate + refocus, --no-record-target-waveform)"
                    )
                    + " via scratch/a4_arm_runner_20260718.py after dry-run quality gates",
                    "pressure_path": rel(arm_dir / "pressure_max_mpa.npz"),
                    "summary_path": rel(summary_path),
                    "execution_summary_path": rel(runner_path),
                    "blocked_claims": blocked_claims
                    + [
                        "paper-grade numerical convergence",
                        "transcranial efficacy",
                        "thermal or clinical safety",
                    ],
                }
            )
    # A5 preregistered held-out TR confirmation (2026-07-19): three independent trajectories.
    a5_root = PROJECT_ROOT / "outputs/a5_heldout_tr_confirmation_20260719"
    for traj in ("offset_y-10p0_z-02p5", "offset_y+05p0_z+05p0", "offset_y+12p5_z-15p0"):
        arm_dir = a5_root / traj / "tr"
        runner_path = arm_dir / "runner_status.json"
        summary_path = arm_dir / "summary.json"
        if not (runner_path.exists() and summary_path.exists()):
            continue
        runner = read_json(runner_path)
        summary = read_json(summary_path)
        runtime = sum(
            float(stage.get("elapsed_s", 0.0))
            for stage in runner.get("stages", [])
            if str(stage.get("stage")) in {"calibrate", "refocus"}
        )
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": f"a5_heldout_tr_{traj}_2026-07-19",
                "case_id": "079",
                "candidate_id": f"heldout_d60_{traj}",
                "profile": "simple_hu300",
                "preset": str(nested(summary, ["config", "preset"], "quick")),
                "output_dir": rel(arm_dir),
                "runner_status": str(runner.get("status", "unknown")),
                "runtime_s": runtime,
                "pressure_generated": (arm_dir / "pressure_max_mpa.npz").exists(),
                "summary_generated": True,
                "claim_level": "single_case_engineering_heldout_tr_confirmation",
                "authorization": "user blanket delegation 2026-07-19; preregistered brief outputs/evidence_briefs/a5_heldout_tr_confirmation/",
                "command_route": "run_a5_heldout_tr_confirmation_20260719.py serial calibrate/refocus after per-stage dry-run gates",
                "pressure_path": rel(arm_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(summary_path),
                "execution_summary_path": rel(runner_path),
                "blocked_claims": blocked_claims
                + [
                    "mapping robustness",
                    "multi-subject generalization",
                    "transcranial efficacy",
                    "thermal or clinical safety",
                ],
            }
        )
    # A5 post-study Hamming hotspot-suppression pilot (2026-07-20): exactly one refocus.
    hamming_dir = PROJECT_ROOT / "outputs/a5_hotspot_suppression_hamming_20260720/offset_y-10p0_z-02p5/tr"
    hamming_runner_path = hamming_dir / "runner_status.json"
    hamming_summary_path = hamming_dir / "summary.json"
    if hamming_runner_path.exists() and hamming_summary_path.exists():
        runner = read_json(hamming_runner_path)
        summary = read_json(hamming_summary_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": "a5_hamming_hotspot_refocus_offset_y-10p0_z-02p5_2026-07-20",
                "case_id": "079",
                "candidate_id": "heldout_d60_offset_y-10p0_z-02p5_hamming",
                "profile": "simple_hu300",
                "preset": str(nested(summary, ["config", "preset"], "quick")),
                "output_dir": rel(hamming_dir),
                "runner_status": str(runner.get("status", "unknown")),
                "runtime_s": float(runner.get("elapsed_s", 0.0)),
                "pressure_generated": (hamming_dir / "pressure_max_mpa.npz").exists(),
                "summary_generated": True,
                "claim_level": "post_study_single_trajectory_engineering_pilot",
                "authorization": "user full-window delegation 2026-07-20; evidence brief outputs/evidence_briefs/a5_hotspot_suppression_hamming/",
                "command_route": "prepare_tr_hamming_replay_20260720.py then run_a5_hamming_refocus_20260720.py after exact mask/grid/dt dry-run gate",
                "pressure_path": rel(hamming_dir / "pressure_max_mpa.npz"),
                "summary_path": rel(hamming_summary_path),
                "execution_summary_path": rel(hamming_runner_path),
                "blocked_claims": blocked_claims
                + [
                    "A5 verdict reversal",
                    "mapping robustness",
                    "fixed-window efficacy",
                    "thermal or clinical safety",
                ],
            }
        )
    # 2026-07-24 through 2026-07-29 pressure runs closed during workspace consolidation.
    registered_output_dirs = {
        str(item.get("output_dir", "")).replace("\\", "/") for item in entries
    }
    for spec in RECENT_RUN_SPECS:
        if spec["output_dir"] in registered_output_dirs:
            continue
        output_dir = PROJECT_ROOT / spec["output_dir"]
        summary_path = output_dir / "summary.json"
        focus_path = output_dir / "focus_metrics.json"
        pressure_path = output_dir / "pressure_max_mpa.npz"
        if not (summary_path.is_file() and focus_path.is_file() and pressure_path.is_file()):
            continue
        summary = read_json(summary_path)
        config = summary.get("config", {})
        runtime_s = float(
            summary.get("runtime_s", nested(summary, ["runtime", "runtime_s"], 0.0))
        )
        status_path = output_dir / "monitor_status.json"
        if not status_path.is_file():
            status_path = output_dir / "runner_status.json"
        status = read_json(status_path) if status_path.is_file() else {}
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": spec["run_id"],
                "case_id": spec["case_id"],
                "candidate_id": spec["candidate_id"],
                "profile": spec["profile"],
                "preset": str(config.get("preset", "quick")),
                "output_dir": spec["output_dir"],
                "runner_status": str(status.get("status", "completed")),
                "runtime_s": runtime_s,
                "pressure_generated": True,
                "summary_generated": True,
                "claim_level": spec["claim_level"],
                "authorization": "user-delegated engineering execution with run-specific EDD and monitored stop gates",
                "command_route": "project-local monitored execution; see the registered execution summary",
                "pressure_path": rel(pressure_path),
                "summary_path": rel(summary_path),
                "execution_summary_path": spec["execution_summary_path"],
                "blocked_claims": blocked_claims
                + [
                    "formal numerical convergence",
                    "thermal or clinical safety",
                    "multi-case generalization",
                ],
            }
        )
    for spec in ITRUSST_RUN_SPECS:
        output_dir = PROJECT_ROOT / spec["output_dir"]
        summary_path = output_dir / "summary.json"
        pressure_path = output_dir / "p_amp.npz"
        comparison_path = PROJECT_ROOT / spec["execution_summary_path"]
        monitor_path = output_dir / "monitor_status.json"
        if not all(
            path.is_file()
            for path in (
                summary_path,
                pressure_path,
                comparison_path,
                monitor_path,
            )
        ):
            continue
        summary = read_json(summary_path)
        monitor = read_json(monitor_path)
        entries.append(
            {
                "ledger_version": "1.0.0",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "run_id": spec["run_id"],
                "case_id": spec["case_id"],
                "candidate_id": spec["candidate_id"],
                "profile": spec["profile"],
                "preset": str(nested(summary, ["config", "preset"], "benchmark-nominal")),
                "output_dir": spec["output_dir"],
                "runner_status": str(monitor.get("status", "unknown")),
                "runtime_s": float(summary.get("runtime_s", 0.0)),
                "pressure_generated": True,
                "summary_generated": True,
                "claim_level": spec["claim_level"],
                "authorization": "explicit user long-run authorization with benchmark-specific EDD, dry-run, smoke and monitored stop gates",
                "command_route": "simulate_itrusst_bm1.py axisymmetric OMP through monitor_kwave_process",
                "pressure_path": rel(pressure_path),
                "summary_path": rel(summary_path),
                "execution_summary_path": spec["execution_summary_path"],
                "blocked_claims": blocked_claims
                + [
                    "experimental or clinical validation",
                    "paper-grade numerical convergence",
                    "whole-skull validation",
                ],
            }
        )
    return entries


def main() -> None:
    entries = build_entries()
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in entries) + "\n", encoding="utf-8")
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ledger_version": "1.0.0",
        "ledger_path": rel(LEDGER_PATH),
        "entry_count": len(entries),
        "claim_levels": sorted({item["claim_level"] for item in entries}),
        "pressure_run_count": sum(1 for item in entries if item["pressure_generated"]),
        "paper_grade_run_count": sum(1 for item in entries if item["claim_level"] == "paper_grade_candidate"),
        "medical_or_safety_conclusion_allowed": False
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT_PATH.write_text(
        "# Run Ledger Summary\n\n"
        f"- entry count: `{summary['entry_count']}`\n"
        f"- pressure run count: `{summary['pressure_run_count']}`\n"
        f"- paper-grade run count: `{summary['paper_grade_run_count']}`\n"
        f"- claim levels: `{summary['claim_levels']}`\n",
        encoding="utf-8",
    )
    print(f"Wrote {rel(LEDGER_PATH)}")
    print(f"Wrote {rel(SUMMARY_PATH)}")


if __name__ == "__main__":
    main()
