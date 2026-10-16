from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "outputs" / "bbb_simulation_plan_report_20260721"


def main() -> None:
    report = json.loads((OUTPUT / "plan_report.json").read_text(encoding="utf-8"))
    roi = json.loads((ROOT / "outputs" / "bbb_roi_case079_20260721" / "roi_summary.json").read_text(encoding="utf-8"))
    ranking = json.loads((ROOT / "outputs" / "bbb_acoustic_path_ranking_20260721" / "path_ranking.json").read_text(encoding="utf-8"))
    elements = json.loads((ROOT / "outputs" / "bbb_element_plan_h3_20260722" / "element_plan_summary.json").read_text(encoding="utf-8"))
    exposure = json.loads((ROOT / "outputs" / "bbb_exposure_proxy_case079_20260721" / "exposure_proxy_boundary.json").read_text(encoding="utf-8"))
    amplitude = json.loads((ROOT / "outputs" / "time_domain_amplitude_bounded_skull_region_20260722" / "offline_amplitude_bounded_gate.json").read_text(encoding="utf-8"))
    reuse = json.loads((ROOT / "outputs" / "trajectory_geometry_reuse_gate_20260722" / "reuse_gate.json").read_text(encoding="utf-8"))
    checks = {
        "status_ready": report["status"] == "pure_simulation_prototype_report_ready",
        "roi_count_exact": report["roi"]["voxel_count"] == roi["voxel_count"] == 251,
        "roi_boundary_explicit": report["roi"]["anatomical_status"] == "synthetic_not_anatomical",
        "best_path_exact": report["path"]["lowest_validated_acoustic_cost"] == ranking["lowest_validated_acoustic_cost_path"],
        "shortest_counterexample": report["path"]["shortest_differs_from_acoustic_optimum"] is True,
        "element_count_exact": report["element_plan"]["active_element_count"] == elements["active_element_count"] == 48,
        "element_slots_exact": report["element_plan"]["virtual_element_slots"] == elements["virtual_element_slots"] == 49,
        "element_trajectory_aligned": report["element_plan"]["trajectory"] == reuse["selected_trajectory"],
        "hardware_boundary_explicit": report["element_plan"]["hardware_geometry_required"] is True,
        "mi_blocked_exact": report["exposure"]["mi_status"] == exposure["proxy"]["mi_status"] == "blocked_no_waveform_pnp",
        "mi_is_null": report["exposure"]["mechanical_index"] is None,
        "hotspot_final_status_exact": report["hotspot"]["status"] == amplitude["status"],
        "hotspot_hard_pass_count_exact": report["hotspot"]["hard_pass_count"] == amplitude["hard_pass_count"] == 56,
        "hotspot_margin_closed": report["hotspot"]["pressure_margin_pass_count"] == 0,
        "selected_existing_trajectory_exact": report["path"]["selected_existing_fullwave_trajectory"] == reuse["selected_trajectory"] == ranking["lowest_validated_acoustic_cost_path"],
        "trajectory_reuse_gate_pass": report["path"]["reuse_gate_status"] == reuse["status"] == "existing_trajectory_reuse_gate_pass",
        "no_additional_pressure_authorized": report["hotspot"]["additional_pressure_run_authorized"] is False,
        "no_clinical_claim": report["clinical_safety_claim"] is False,
        "report_runs_no_pressure": report["pressure_executed_by_report"] is False,
        "csv_exists": (OUTPUT / "path_metrics.csv").is_file(),
        "figures_nonempty": all((OUTPUT / name).stat().st_size > 10_000 for name in report["figures"]),
        "markdown_exists": (OUTPUT / "plan_report.md").is_file(),
    }
    result = {"status": "pass" if all(checks.values()) else "fail", "passed": sum(checks.values()), "total": len(checks), "checks": checks}
    (OUTPUT / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

