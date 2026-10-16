from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "planning_contracts" / "examples" / "case079_h1_bbb_simulation_plan.json"
ROI_SUMMARY = ROOT / "outputs" / "bbb_roi_case079_20260721" / "roi_summary.json"
ROI_MASK = ROOT / "outputs" / "bbb_roi_case079_20260721" / "roi_mask.npz"
PATH_RANKING = ROOT / "outputs" / "bbb_acoustic_path_ranking_20260721" / "path_ranking.json"
ELEMENT_SUMMARY = ROOT / "outputs" / "bbb_element_plan_h3_20260722" / "element_plan_summary.json"
ELEMENT_CSV = ROOT / "outputs" / "bbb_element_plan_h3_20260722" / "element_drive_plan.csv"
EXPOSURE = ROOT / "outputs" / "bbb_exposure_proxy_case079_20260721" / "exposure_proxy_boundary.json"
HOTSPOT_RUN = ROOT / "outputs" / "dual_point_hotspot_calibration_20260721" / "run" / "runner_status.json"
HOTSPOT_GATE = ROOT / "outputs" / "dual_point_hotspot_calibration_20260721" / "offline_analysis" / "offline_gate.json"
REFOCUS_RESULT = ROOT / "outputs" / "dual_point_constrained_refocus_20260721" / "result" / "four_gate_result.json"
BLEND_RESULT = ROOT / "outputs" / "target_preserving_blend_validation_20260722" / "result" / "four_gate_result.json"
AMPLITUDE_RESULT = ROOT / "outputs" / "time_domain_amplitude_bounded_skull_region_20260722" / "offline_amplitude_bounded_gate.json"
TRAJECTORY_REUSE = ROOT / "outputs" / "trajectory_geometry_reuse_gate_20260722" / "reuse_gate.json"
MODEL = ROOT / "outputs" / "ct_acoustic_model_3d_profile_hu300_dx0p75" / "acoustic_model_3d.npz"
OUTPUT = ROOT / "outputs" / "bbb_simulation_plan_report_20260721"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def hotspot_status() -> dict[str, Any]:
    if AMPLITUDE_RESULT.exists():
        result = load_json(AMPLITUDE_RESULT)
        return {
            "status": result["status"],
            "method": "time_domain_amplitude_bounded_two_hotspot_basis",
            "hard_pass_count": result["hard_pass_count"],
            "pressure_margin_pass_count": result["pressure_margin_pass_count"],
            "selected": result["selected"],
            "additional_pressure_run_authorized": result["pressure_execution_authorized"],
            "last_pressure_result": str(BLEND_RESULT.relative_to(ROOT)),
            "source": str(AMPLITUDE_RESULT.relative_to(ROOT)),
        }
    if BLEND_RESULT.exists():
        result = load_json(BLEND_RESULT)
        return {
            "status": result["status"],
            "method": "target_preserving_waveform_blend_alpha_0p40",
            "passed": result["passed"],
            "metrics": result["metrics"],
            "gates": result["gates"],
            "additional_pressure_run_authorized": result["additional_pressure_run_authorized"],
            "source": str(BLEND_RESULT.relative_to(ROOT)),
        }
    if REFOCUS_RESULT.exists():
        result = load_json(REFOCUS_RESULT)
        return {
            "status": result["status"],
            "passed": result["passed"],
            "metrics": result["metrics"],
            "gates": result["gates"],
            "additional_pressure_run_authorized": result["additional_pressure_run_authorized"],
            "source": str(REFOCUS_RESULT.relative_to(ROOT)),
        }
    if HOTSPOT_GATE.exists():
        gate = load_json(HOTSPOT_GATE)
        return {
            "status": gate["status"],
            "selected": gate["selected"],
            "constrained_refocus_authorized_by_offline_gate": gate["constrained_refocus_authorized_by_offline_gate"],
            "source": str(HOTSPOT_GATE.relative_to(ROOT)),
        }
    if HOTSPOT_RUN.exists():
        run = load_json(HOTSPOT_RUN)
        return {
            "status": run["status"],
            "elapsed_s": run.get("elapsed_s"),
            "checkpoints": len(run.get("checkpoints", [])),
            "source": str(HOTSPOT_RUN.relative_to(ROOT)),
        }
    return {"status": "not_started"}


def plot_roi_geometry(output: Path, contract: dict[str, Any], ranking: dict[str, Any]) -> None:
    with np.load(MODEL, allow_pickle=False) as stored:
        hu = np.asarray(stored["hu"], dtype=np.float32)
    with np.load(ROI_MASK, allow_pickle=False) as stored:
        roi = np.asarray(stored["roi_mask"], dtype=bool)
    target = np.asarray(contract["target_roi"]["center_full_ijk"], dtype=int)
    best_id = ranking["lowest_validated_acoustic_cost_path"]
    best = next(row for row in ranking["records"] if row["trajectory"] == best_id)
    selection = load_json(ROOT / "outputs" / "a5_heldout_d60_trajectory_selection_20260719" / "heldout_selection.json")
    selected = next(row for row in selection["selected"] if row["candidate_id"] == best_id)["entry_plan"]
    source = np.asarray(selected["source_center_index_ijk"], dtype=int)
    entry = np.asarray(selected["entry_index_ijk"], dtype=int)

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    views = [
        (hu[:, :, target[2]].T, roi[:, :, target[2]].T, (0, 1), "Axial", "i", "j"),
        (hu[:, target[1], :].T, roi[:, target[1], :].T, (0, 2), "Coronal", "i", "k"),
        (hu[target[0], :, :].T, roi[target[0], :, :].T, (1, 2), "Sagittal", "j", "k"),
    ]
    for ax, (image, mask, dims, title, xlabel, ylabel) in zip(axes, views, strict=True):
        ax.imshow(np.clip(image, -200, 1200), cmap="gray", origin="lower", vmin=-200, vmax=1200)
        if np.any(mask):
            ax.contour(mask.astype(float), levels=[0.5], colors=["#00b894"], linewidths=1.5)
        ax.plot([source[dims[0]], entry[dims[0]], target[dims[0]]], [source[dims[1]], entry[dims[1]], target[dims[1]]], color="#e17055", linewidth=1.2)
        ax.scatter([target[dims[0]]], [target[dims[1]]], c="#00b894", s=25)
        ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    fig.suptitle(f"Case 079 synthetic ROI and lowest validated-cost path ({best_id})", fontsize=11)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_path_costs(output: Path, ranking: dict[str, Any]) -> None:
    rows = sorted(ranking["records"], key=lambda row: row["validated_rank"])
    labels = [row["trajectory"].replace("offset_", "") for row in rows]
    x = np.arange(len(rows))
    width = 0.25
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    ax.bar(x - width, [row["proxy_acoustic_cost"] for row in rows], width, label="Proxy cost", color="#0984e3")
    ax.bar(x, [row["fullwave_risk"] for row in rows], width, label="Full-wave risk", color="#e17055")
    ax.bar(x + width, [row["validated_acoustic_cost"] for row in rows], width, label="Validated cost", color="#00b894")
    ax.set_xticks(x, labels, rotation=15, ha="right")
    ax.set_ylabel("Normalized lower-is-better score")
    ax.set_title("Shortest distance is not the lowest validated acoustic cost")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_virtual_elements(output: Path) -> None:
    rows: list[dict[str, str]] = []
    with ELEMENT_CSV.open("r", encoding="utf-8") as handle:
        rows.extend(csv.DictReader(handle))
    j = np.array([float(row["centroid_j"]) for row in rows])
    k = np.array([float(row["centroid_k"]) for row in rows])
    amplitude = np.array([float(row["amplitude"]) for row in rows])
    phase = np.array([float(row["phase_deg"]) for row in rows])
    size = 30 + 170 * amplitude / max(float(np.max(amplitude)), 1e-12)
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    scatter = ax.scatter(j, k, s=size, c=phase, cmap="twilight", vmin=-180, vmax=180, edgecolors="black", linewidths=0.3)
    ax.set(xlabel="j centroid (voxel)", ylabel="k centroid (voxel)", title="Virtual 7x7 patch controls (not hardware elements)")
    ax.set_aspect("equal", adjustable="box")
    fig.colorbar(scatter, ax=ax, label="Phase (degrees)")
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the BBB pure-simulation planning report.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    contract = load_json(CONTRACT)
    roi = load_json(ROI_SUMMARY)
    ranking = load_json(PATH_RANKING)
    elements = load_json(ELEMENT_SUMMARY)
    exposure = load_json(EXPOSURE)
    hotspot = hotspot_status()
    trajectory_reuse = load_json(TRAJECTORY_REUSE)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with (args.output_dir / "path_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["validated_rank", "trajectory", "distance_mm", "proxy_cost", "fullwave_risk", "validated_cost", "observed_verdict"])
        for row in ranking["records"]:
            writer.writerow([row.get("validated_rank"), row["trajectory"], row["geometry"]["source_to_target_mm"], row["proxy_acoustic_cost"], row["fullwave_risk"], row["validated_acoustic_cost"], row.get("observed_verdict")])

    plot_roi_geometry(args.output_dir / "figure_roi_geometry.png", contract, ranking)
    plot_path_costs(args.output_dir / "figure_path_costs.png", ranking)
    plot_virtual_elements(args.output_dir / "figure_virtual_elements.png")

    report = {
        "status": "pure_simulation_prototype_report_ready",
        "plan_id": contract["plan_id"],
        "case_id": contract["patient_model"]["case_id"],
        "stage": contract["stage"],
        "roi": {
            "roi_id": roi["roi_id"],
            "voxel_count": roi["voxel_count"],
            "roi_volume_m3": roi["roi_volume_m3"],
            "anatomical_status": roi["anatomical_status"],
        },
        "path": {
            "shortest_euclidean": ranking["shortest_euclidean_path"],
            "lowest_validated_acoustic_cost": ranking["lowest_validated_acoustic_cost_path"],
            "shortest_differs_from_acoustic_optimum": ranking["shortest_is_not_lowest_validated_cost"],
            "candidate_count": ranking["candidate_count"],
            "selected_existing_fullwave_trajectory": trajectory_reuse["selected_trajectory"],
            "reuse_gate_status": trajectory_reuse["status"],
            "target_pressure_retention_vs_h1": trajectory_reuse["target_pressure_retention_vs_reference"],
            "skull_peak_reduction_vs_h1": trajectory_reuse["skull_peak_reduction_vs_reference"],
        },
        "hotspot": hotspot,
        "element_plan": {
            "status": elements["status"],
            "semantics": elements["element_semantics"],
            "trajectory": elements["trajectory"],
            "virtual_element_slots": elements["virtual_element_slots"],
            "active_element_count": elements["active_element_count"],
            "predicted_target_response_retention": elements["reconstruction"]["predicted_response_retention"],
            "hardware_geometry_required": elements["hardware_geometry_required_for_device_export"],
        },
        "exposure": {
            "status": exposure["status"],
            "mi_status": exposure["proxy"]["mi_status"],
            "mechanical_index": exposure["proxy"]["mechanical_index"],
            "blockers": exposure["blockers"],
        },
        "figures": ["figure_roi_geometry.png", "figure_path_costs.png", "figure_virtual_elements.png"],
        "limitations": [
            "synthetic_roi_not_registered_anatomy",
            "single_case_three_trajectory_ranking",
            "virtual_patches_not_device_hardware",
            "waveform_pnp_and_mi_unavailable",
            "microbubble_and_pcd_protocol_unavailable",
            "not_a_clinical_treatment_plan",
        ],
        "pressure_executed_by_report": False,
        "clinical_safety_claim": False,
        "claim_boundary": "research_pure_simulation_engineering_report",
    }
    (args.output_dir / "plan_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Case 079 BBB Pure-Simulation Planning Report",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Current plan",
        "",
        f"- ROI: `{roi['roi_id']}`, {roi['voxel_count']} voxels; `{roi['anatomical_status']}`.",
        f"- Shortest path: `{ranking['shortest_euclidean_path']}`.",
        f"- Lowest validated acoustic cost: `{ranking['lowest_validated_acoustic_cost_path']}`.",
        f"- Selected existing full-wave trajectory: `{trajectory_reuse['selected_trajectory']}` (`{trajectory_reuse['status']}`).",
        f"- Versus H1: target retention `{trajectory_reuse['target_pressure_retention_vs_reference']:.4f}`, skull-peak reduction `{trajectory_reuse['skull_peak_reduction_vs_reference']:.4f}`.",
        f"- Hotspot stage: `{hotspot['status']}`.",
        f"- Element layer: {elements['active_element_count']} `{elements['element_semantics']}` controls.",
        f"- MI: `{exposure['proxy']['mi_status']}`.",
        "",
        "## Interpretation",
        "",
        "The shortest trajectory is not the lowest validated acoustic-cost trajectory. This supports ranking paths with skull and full-wave terms rather than geometric distance alone.",
        "",
        "## Boundaries",
        "",
    ]
    lines.extend(f"- `{item}`" for item in report["limitations"])
    lines.extend(["", "This report is a research simulation artifact and is not a clinical treatment plan."])
    (args.output_dir / "plan_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "hotspot": hotspot["status"], "output_dir": str(args.output_dir)}, indent=2))


if __name__ == "__main__":
    main()
