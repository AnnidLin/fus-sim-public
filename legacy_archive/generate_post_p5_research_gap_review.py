from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs/post_p5_research_gap_review/079_candidate_006"
OUT_JSON = OUT_DIR / "research_gap_review.json"
OUT_MD = OUT_DIR / "research_gap_review.md"

BASE_DIR = ROOT / "outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard"
DX05_DRY = ROOT / "outputs/corrected_entry_plan_resolution_chain/079_candidate_006_dx0p5/dry_run_quality/quality_dry_run_summary.json"
P3A = ROOT / "outputs/p3a_pml16_sensitivity_analysis/079_candidate_006_dx0p75/p3a_pml16_sensitivity_report.json"
P3B = ROOT / "outputs/p3b_cfl0p1_sensitivity_analysis/079_candidate_006_dx0p75/p3b_cfl0p1_sensitivity_report.json"
FREEFIELD = ROOT / "outputs/freefield_calibration/ap30_r35_f500/freefield_summary.json"
FUTURE_DIR = ROOT / "outputs/corrected_pressure_sensitivity/079_candidate_006_dx0p5_pml12_cfl0p2_standard"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def peak_geometry(point: list[int], source: np.ndarray, target: np.ndarray, dx_mm: float) -> dict[str, float]:
    vector = target - source
    unit = vector / np.linalg.norm(vector)
    point_vector = np.asarray(point, dtype=float) - source
    axial_from_source = float(np.dot(point_vector, unit) * dx_mm)
    lateral = float(np.linalg.norm(point_vector - np.dot(point_vector, unit) * unit) * dx_mm)
    target_distance = float(np.linalg.norm(vector) * dx_mm)
    return {
        "axial_from_source_mm": axial_from_source,
        "axial_shortfall_to_target_mm": target_distance - axial_from_source,
        "lateral_offset_from_beam_axis_mm": lateral,
    }


def build() -> dict[str, Any]:
    base_dry = load(BASE_DIR / "quality_dry_run_summary.json")
    runner = load(BASE_DIR / "runner_status.json")
    focus = load(BASE_DIR / "focus_metrics.json")
    dx05 = load(DX05_DRY)
    p3a = load(P3A)
    p3b = load(P3B)
    freefield = load(FREEFIELD)

    source = np.asarray(base_dry["source"]["source_center_index_ijk"], dtype=float)
    target = np.asarray(base_dry["source"]["target_index_ijk"], dtype=float)
    dx_mm = float(base_dry["simulation_quality"]["dx_mm"])
    base_work = int(base_dry["simulation_quality"]["voxel_count"]) * int(base_dry["simulation_quality"]["nt"])
    dx05_work = int(dx05["simulation_quality"]["voxel_count"]) * int(dx05["simulation_quality"]["nt"])
    work_ratio = dx05_work / base_work
    baseline_runtime_s = float(runner["execution"]["runtime_s"])
    estimated_runtime_s = baseline_runtime_s * work_ratio
    hard_stop_min = 75

    peak_geometry_metrics = {
        name: peak_geometry(focus[key], source, target, dx_mm)
        for name, key in (
            ("global_peak", "global_peak_index_ijk"),
            ("effective_peak", "effective_peak_index_ijk"),
            ("target_window_peak", "target_window_peak_index_ijk"),
        )
    }
    pressure_conflict = (FUTURE_DIR / "pressure_max_mpa.npz").exists() or (FUTURE_DIR / "summary.json").exists()
    return {
        "review_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_id": "079",
        "candidate_id": "candidate_006",
        "scope": "post-P5 read-only evidence-gap prioritization",
        "current_claim_level": "auditable_research_dataset_candidate_not_numerical_convergence",
        "observations": {
            "pml16_stable_within_thresholds": p3a["decision"]["p3a_stable_within_thresholds"],
            "cfl01_stable_within_thresholds": p3b["decision"]["p3b_stable_within_thresholds"],
            "global_peak_to_target_distance_mm": focus["global_peak_to_target_distance_mm"],
            "effective_peak_to_target_distance_mm": focus["effective_peak_to_target_distance_mm"],
            "target_to_global_peak_ratio": focus["target_to_global_peak_ratio"],
            "peak_geometry": peak_geometry_metrics,
            "freefield_ap30_r35_global_peak_to_geometric_focus_distance_mm": freefield["pressure"]["global_peak_to_target_distance_mm"],
        },
        "dx0p5_feasibility": {
            "dry_run_quality_only": dx05["dry_run_quality_only"],
            "source_labels": dx05["source"]["source_label_counts"],
            "grid_size": dx05["simulation_quality"]["grid_size"],
            "nt": dx05["simulation_quality"]["nt"],
            "ppw": dx05["simulation_quality"]["ppw_min_sound_speed"],
            "memory_estimate_mb": dx05["simulation_quality"]["memory_estimate"]["estimated_mb"],
            "baseline_measured_runtime_s": baseline_runtime_s,
            "work_ratio_vs_dx0p75": work_ratio,
            "first_order_runtime_estimate_s": estimated_runtime_s,
            "first_order_runtime_estimate_min": estimated_runtime_s / 60.0,
            "hard_stop_min": hard_stop_min,
            "fits_hard_stop": estimated_runtime_s <= hard_stop_min * 60,
            "runtime_estimate_method": "measured dx0.75 runtime scaled by voxel_count times nt; scheduling estimate, not benchmark guarantee",
            "future_output_dir": str(FUTURE_DIR.relative_to(ROOT)).replace("\\", "/"),
            "output_conflict": pressure_conflict,
            "pressure_execution_authorized": False,
        },
        "ranked_gaps": [
            {
                "rank": 1,
                "gap": "prefocal pressure maximum lacks a root-cause and metric-semantics audit",
                "evidence_value": "high",
                "compute_cost": "low",
                "risk": "low",
            },
            {
                "rank": 2,
                "gap": "corrected dx0.5 pressure comparison and grid sensitivity are absent",
                "evidence_value": "high after focus interpretation",
                "compute_cost": "very_high_on_current_cpu",
                "risk": "hard_stop_overrun",
            },
            {
                "rank": 3,
                "gap": "Pennes material and protocol assumptions remain approximate",
                "evidence_value": "medium",
                "compute_cost": "low_to_medium",
                "risk": "interpretation_overreach",
            },
        ],
        "decision": {
            "recommended_next_packet": "P6a_focus_metric_semantics_and_prefocal_root_cause_audit",
            "authorization": "not_required_read_only_no_kwave",
            "reason": "The dominant unresolved interpretation gap can be audited from existing arrays and code before a dx0.5 run whose first-order estimate exceeds the 75-minute hard stop.",
            "dx0p5_pressure_status": "deferred_not_authorized_runtime_budget_and_interpretability",
        },
        "blocked_claims": [
            "numerical convergence",
            "tuned focus",
            "validated pressure baseline",
            "paper-grade reproduction",
            "clinical or medical safety",
        ],
    }


def markdown(review: dict[str, Any]) -> str:
    obs = review["observations"]
    feas = review["dx0p5_feasibility"]
    geom = obs["peak_geometry"]
    lines = [
        "# Post-P5 Research Gap Review",
        "",
        f"- claim level: `{review['current_claim_level']}`",
        f"- recommended next packet: `{review['decision']['recommended_next_packet']}`",
        f"- authorization: `{review['decision']['authorization']}`",
        "",
        "## Evidence",
        "",
        f"- PML16 stable within thresholds: `{obs['pml16_stable_within_thresholds']}`",
        f"- CFL0.1 stable within thresholds: `{obs['cfl01_stable_within_thresholds']}`",
        f"- global peak axial shortfall: `{geom['global_peak']['axial_shortfall_to_target_mm']:.3f}` mm; lateral offset: `{geom['global_peak']['lateral_offset_from_beam_axis_mm']:.3f}` mm",
        f"- effective peak axial shortfall: `{geom['effective_peak']['axial_shortfall_to_target_mm']:.3f}` mm; lateral offset: `{geom['effective_peak']['lateral_offset_from_beam_axis_mm']:.3f}` mm",
        f"- free-field ap30/r35 peak-to-focus distance: `{obs['freefield_ap30_r35_global_peak_to_geometric_focus_distance_mm']}` mm",
        "",
        "## dx0.5 Feasibility",
        "",
        f"- grid / nt: `{feas['grid_size']}` / `{feas['nt']}`",
        f"- work ratio vs dx0.75: `{feas['work_ratio_vs_dx0p75']:.3f}`",
        f"- first-order runtime estimate: `{feas['first_order_runtime_estimate_min']:.1f}` min",
        f"- hard stop: `{feas['hard_stop_min']}` min; fits: `{feas['fits_hard_stop']}`",
        f"- output conflict: `{feas['output_conflict']}`",
        "",
        "## Decision",
        "",
        review["decision"]["reason"],
        "",
        "No pressure or thermal simulation is authorized or executed by this review.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    review = build()
    OUT_JSON.write_text(json.dumps(review, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(markdown(review), encoding="utf-8")
    print(json.dumps({"recommended_next_packet": review["decision"]["recommended_next_packet"], "dx0p5_estimated_min": round(review["dx0p5_feasibility"]["first_order_runtime_estimate_min"], 1), "pressure_authorized": False}))


if __name__ == "__main__":
    main()
