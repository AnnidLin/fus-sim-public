from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required JSON file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("/", "\\")
    except ValueError:
        return str(path)


def fmt(value: Any, digits: int = 3, suffix: str = "") -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (int, np.integer)):
        return f"{int(value)}{suffix}"
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.{digits}f}{suffix}"
    return f"{value}{suffix}"


def join_list(values: Any, digits: int = 3) -> str:
    if values is None:
        return "n/a"
    if not isinstance(values, (list, tuple)):
        return str(values)
    parts: list[str] = []
    for value in values:
        if isinstance(value, (float, np.floating)):
            parts.append(f"{float(value):.{digits}f}")
        else:
            parts.append(str(value))
    return "[" + ", ".join(parts) + "]"


def read_model_npz_summary(model_path: Path) -> dict[str, Any]:
    if not model_path.exists():
        raise FileNotFoundError(f"Missing model npz: {model_path}")
    data = np.load(model_path)
    result: dict[str, Any] = {"path": str(model_path), "fields": sorted(data.files)}
    for key in ["labels", "sound_speed", "density", "alpha_coeff"]:
        if key in data.files:
            result[f"{key}_shape"] = list(np.asarray(data[key]).shape)
            result[f"{key}_dtype"] = str(np.asarray(data[key]).dtype)
    if "dx_m" in data.files:
        result["dx_m"] = float(np.asarray(data["dx_m"]).item())
    if "target_index_ijk" in data.files:
        result["target_index_ijk"] = [int(v) for v in np.asarray(data["target_index_ijk"]).tolist()]
    return result


def image_refs(pressure_dir: Path, thermal_dir: Path, ct_summary_dir: Path) -> dict[str, str]:
    refs = {
        "ct_hu_slices": ct_summary_dir / "ct_hu_slices.png",
        "label_slices": ct_summary_dir / "label_slices.png",
        "sound_speed_slices": ct_summary_dir / "sound_speed_slices.png",
        "source_target_layout": pressure_dir / "source_target_layout.png",
        "pressure_axial": pressure_dir / "pressure_max_axial.png",
        "pressure_coronal": pressure_dir / "pressure_max_coronal.png",
        "pressure_sagittal": pressure_dir / "pressure_max_sagittal.png",
        "axis_profile": pressure_dir / "axis_profile.png",
        "thermal_curve": thermal_dir / "temperature_time_curve.png",
        "thermal_axial": thermal_dir / "pennes_temperature_rise_axial.png",
        "thermal_coronal": thermal_dir / "pennes_temperature_rise_coronal.png",
        "thermal_sagittal": thermal_dir / "pennes_temperature_rise_sagittal.png",
    }
    return {name: rel(path) for name, path in refs.items() if path.exists()}


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    model_path = Path(args.model)
    ct_summary_path = Path(args.ct_summary)
    pressure_dir = Path(args.pressure_dir)
    thermal_dir = Path(args.thermal_dir)
    sensitivity_dir = Path(args.sensitivity_dir)
    dose_dir = Path(args.dose_dir)

    ct = load_json(ct_summary_path)
    pressure = load_json(pressure_dir / "summary.json")
    thermal = load_json(thermal_dir / "pennes_summary.json")
    sensitivity = load_json(sensitivity_dir / "sensitivity_summary.json")
    dose = load_json(dose_dir / "dose_summary.json")
    model = read_model_npz_summary(model_path)
    refs = image_refs(pressure_dir, thermal_dir, ct_summary_path.parent)

    return {
        "case_id": str(args.case_id),
        "generated_from": {
            "model": rel(model_path),
            "ct_summary": rel(ct_summary_path),
            "pressure_dir": rel(pressure_dir),
            "thermal_dir": rel(thermal_dir),
            "sensitivity_dir": rel(sensitivity_dir),
            "dose_dir": rel(dose_dir),
        },
        "ct_model": {
            "source": ct.get("source") or {},
            "resampling": ct.get("resampling") or {},
            "thresholds_hu": ct.get("thresholds_hu") or {},
            "grid_shape": ct.get("grid_shape"),
            "dx_m": ct.get("dx_m"),
            "target_index_ijk": ct.get("target_index_ijk"),
            "materials": ct.get("materials") or {},
            "voxel_counts": ct.get("voxel_counts") or {},
            "hu_range": ct.get("hu_range"),
            "model_npz": model,
        },
        "pressure": {
            "config": pressure.get("config") or {},
            "model_shape": pressure.get("model_shape"),
            "crop_origin_ijk": pressure.get("crop_origin_ijk"),
            "target_index_ijk_cropped": pressure.get("target_index_ijk"),
            "entry_plan": pressure.get("entry_plan") or {},
            "source": pressure.get("source") or {},
            "runtime": pressure.get("runtime") or {},
            "metrics": pressure.get("pressure") or {},
            "tuning_note": pressure.get("tuning_note"),
            "simulation_quality": pressure.get("simulation_quality") or {},
            "alpha_semantics": pressure.get("alpha_semantics") or {},
        },
        "thermal_protocol": {
            "summary": thermal,
        },
        "thermal_sensitivity": {
            "summary": sensitivity,
        },
        "thermal_dose": {
            "summary": dose,
        },
        "image_references": refs,
        "limitations": [
            "CT segmentation uses first-pass HU thresholds only; no skull cleanup, brain mask, or tissue-specific segmentation.",
            "The selected target is a CT geometry candidate, not a verified anatomical hippocampus or clinical target.",
            "The pressure simulation uses a cropped quick 3D domain and CPU-friendly grid, not a paper-scale full-head model.",
            "The thermal model uses approximate Pennes parameters and simplified boundary conditions.",
            "All safety numbers are engineering estimates for platform validation, not medical safety claims.",
        ],
        "recommended_next_steps": [
            "Improve CT segmentation and target definition before claiming anatomical relevance.",
            "Repeat the report on at least one more CT case or a public dataset.",
            "Run a higher-resolution or larger-domain pressure validation only after target and segmentation are credible.",
            "Calibrate thermal material and perfusion parameters against literature values used in the reference paper.",
        ],
    }


def table_row(name: str, value: Any) -> str:
    return f"| {name} | {value} |"


def build_markdown(summary: dict[str, Any]) -> str:
    ct = summary["ct_model"]
    pressure = summary["pressure"]
    p_metrics = pressure["metrics"]
    entry = pressure["entry_plan"]
    source = pressure["source"]
    thermal = summary["thermal_protocol"]["summary"]
    sensitivity = summary["thermal_sensitivity"]["summary"]
    dose = summary["thermal_dose"]["summary"]
    sens_worst = sensitivity.get("worst_case") or {}
    dose_hot = dose.get("hottest_case") or {}
    refs = summary["image_references"]

    lines: list[str] = []
    lines.append(f"# 079 Case Simulation QC Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("- Current platform status: CT/NIfTI -> acoustic model -> extracranial source planning -> quick 3D k-Wave pressure -> Pennes thermal trend is runnable end to end.")
    lines.append(f"- Best quick pressure target-window peak: `{fmt(p_metrics.get('target_window_peak_mpa'), 3)} MPa`; effective peak remains `{fmt(p_metrics.get('effective_peak_to_target_distance_mm'), 2)} mm` from the target.")
    lines.append(f"- Protocol-averaged 3-train max temperature: `{fmt(thermal.get('max_temperature_c'), 3)} C`; dose scan up to `120` trains max temperature: `{fmt(dose_hot.get('max_temperature_c'), 3)} C`.")
    lines.append("- Interpretation: this is a working platform baseline, not a paper-level reproduction or medical safety conclusion.")
    lines.append("")

    lines.append("## CT Acoustic Model")
    lines.append("")
    source_info = ct.get("source", {})
    resampling = ct.get("resampling", {})
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(table_row("Source file", source_info.get("source_path", "n/a")))
    lines.append(table_row("Original shape xyz", join_list(source_info.get("original_shape_xyz"))))
    lines.append(table_row("Original spacing mm xyz", join_list(source_info.get("original_spacing_mm_xyz"), 4)))
    lines.append(table_row("HU range", join_list(ct.get("hu_range"), 2)))
    lines.append(table_row("Resampled shape xyz", join_list(resampling.get("resampled_shape_xyz"))))
    lines.append(table_row("dx", fmt(ct.get("dx_m"), 6, " m")))
    lines.append(table_row("HU thresholds", f"air < {ct.get('thresholds_hu', {}).get('air_background_lt')}, bone >= {ct.get('thresholds_hu', {}).get('bone_gte')}"))
    lines.append(table_row("Voxel counts", json.dumps(ct.get("voxel_counts", {}), ensure_ascii=False)))
    lines.append("")

    lines.append("## Pressure Configuration And Metrics")
    lines.append("")
    config = pressure.get("config", {})
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(table_row("Target index in full model", join_list(entry.get("target_index_ijk"))))
    lines.append(table_row("Entry index in full model", join_list(entry.get("entry_index_ijk"))))
    lines.append(table_row("Source center in full model", join_list(entry.get("source_center_index_ijk"))))
    lines.append(table_row("Source label counts", json.dumps(source.get("source_label_counts", {}), ensure_ascii=False)))
    lines.append(table_row("Aperture diameter", fmt(float(config.get("aperture_diameter_m", 0.0)) * 1000.0, 1, " mm")))
    lines.append(table_row("Curvature radius", fmt(float(config.get("transducer_radius_m", 0.0)) * 1000.0, 1, " mm")))
    lines.append(table_row("Cycles / sim time", f"{config.get('tone_burst_cycles')} cycles / {fmt(float(config.get('simulation_time_s', 0.0)) * 1e6, 1, ' us')}"))
    lines.append(table_row("Crop shape", join_list(pressure.get("model_shape"))))
    lines.append(table_row("Runtime", fmt(pressure.get("runtime", {}).get("runtime_s"), 1, " s")))
    lines.append(table_row("Target pressure", fmt(p_metrics.get("target_pressure_mpa"), 3, " MPa")))
    lines.append(table_row("Target-window peak", fmt(p_metrics.get("target_window_peak_mpa"), 3, " MPa")))
    lines.append(table_row("Effective peak", fmt(p_metrics.get("effective_peak_mpa"), 3, " MPa")))
    lines.append(table_row("Effective peak to target distance", fmt(p_metrics.get("effective_peak_to_target_distance_mm"), 2, " mm")))
    lines.append(table_row("Target/effective peak ratio", fmt(p_metrics.get("target_to_effective_peak_ratio"), 3)))
    
    quality = pressure.get("simulation_quality", {})
    alpha = pressure.get("alpha_semantics", {})
    lines.append(table_row("CFL / PML Size", f"{fmt(quality.get('cfl'))} / {fmt(quality.get('pml_size'))}"))
    lines.append(table_row("PPW (Min Sound Speed)", fmt(quality.get('ppw_min_sound_speed'), 3)))
    lines.append(table_row("Memory Estimate", f"{fmt(quality.get('memory_estimate', {}).get('estimated_mb'), 2)} MB"))
    lines.append(table_row("Alpha Power", fmt(alpha.get('alpha_power'), 3)))
    lines.append(table_row("Alpha Mode (Dispersion)", fmt(alpha.get('alpha_mode'))))
    lines.append(table_row("Alpha Semantics Status", fmt(alpha.get('alpha_semantics_status'))))
    lines.append("")

    lines.append("## Thermal Safety Trend")
    lines.append("")
    lines.append("| Scenario | Key Result |")
    lines.append("|---|---|")
    lines.append(table_row("3-train protocol-averaged", f"max {fmt(thermal.get('max_temperature_c'), 3, ' C')}; target rise {fmt(thermal.get('target_temperature_rise_c'), 3, ' C')}"))
    lines.append(table_row("Sensitivity worst case", f"{sens_worst.get('case', 'n/a')}: max {fmt(sens_worst.get('max_temperature_c'), 3, ' C')}; margin to 42 C {fmt(sensitivity.get('temperature_margin_to_threshold_c'), 3, ' C')}"))
    lines.append(table_row("Dose hottest case", f"{dose_hot.get('case', 'n/a')}: max {fmt(dose_hot.get('max_temperature_c'), 3, ' C')}; margin to 42 C {fmt(dose_hot.get('temperature_margin_to_threshold_c'), 3, ' C')}"))
    lines.append(table_row("Dose threshold result", f"first near threshold: {dose.get('first_near_threshold_case')}; first risk: {dose.get('first_risk_case')}"))
    lines.append("")

    lines.append("## Key Figure References")
    lines.append("")
    if refs:
        for name, path in refs.items():
            lines.append(f"- `{name}`: `{path}`")
    else:
        lines.append("- No figure references found.")
    lines.append("")

    lines.append("## Current Limits")
    lines.append("")
    for item in summary["limitations"]:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Recommended Next Steps")
    lines.append("")
    for item in summary["recommended_next_steps"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = build_summary(args)
    markdown = build_markdown(summary)
    (output_dir / f"case_report_{args.case_id}.md").write_text(markdown, encoding="utf-8")
    (output_dir / f"case_report_{args.case_id}_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"case_report={output_dir / f'case_report_{args.case_id}.md'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a case-level QC report from existing tFUS simulation outputs.")
    parser.add_argument("--case-id", default="079")
    parser.add_argument("--model", default=str(PROJECT_ROOT / "outputs" / "ct_acoustic_model_3d" / "acoustic_model_3d.npz"))
    parser.add_argument("--ct-summary", default=str(PROJECT_ROOT / "outputs" / "ct_acoustic_model_3d" / "summary.json"))
    parser.add_argument("--pressure-dir", default=str(PROJECT_ROOT / "outputs" / "ct_transducer_stability_target_020" / "ap30_r35_c8_t55"))
    parser.add_argument("--thermal-dir", default=str(PROJECT_ROOT / "outputs" / "pennes_protocol_avg_target_020_train3"))
    parser.add_argument("--sensitivity-dir", default=str(PROJECT_ROOT / "outputs" / "pennes_sensitivity_target_020_protocol_avg"))
    parser.add_argument("--dose-dir", default=str(PROJECT_ROOT / "outputs" / "pennes_protocol_dose_target_020"))
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "outputs" / "case_report_079"))
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except Exception as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
