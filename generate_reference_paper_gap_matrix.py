from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path("outputs/reference_paper_gap_matrix_20260715")

# Authoritative current project values as of 2026-07-15.
# These are read from existing outputs; no new simulation is run.
CURRENT = {
    "source_geometry": {
        "frequency_hz": 500_000,
        "aperture_mm": 60.0,
        "nominal_radius_mm": 78.330,
        "f_number": 1.3055,
        "source_pressure_mpa": 1.0,
        "transducer_model": "geometric_bowl_makeBowl",
    },
    "free_field_d60_r78p330_dx0p75": {
        "dx_mm": 0.75,
        "ppw": 4.0,
        "pml_size": 12,
        "pml_thickness_mm": 9.0,
        "cfl": 0.2,
        "grid": "153x120x100",
        "global_peak_mpa": 12.817,
        "target_pressure_mpa": 12.701,
        "target_to_global_ratio": 0.9910,
        "refined_focus_error_percent": 1.364,
        "lateral_minus6db_mm": 4.968,
        "axial_minus6db_mm": 38.438,
        "boundary_distance_voxels": 27,
        "target_waveform_recorded": True,
        "status": "kwave_ok",
    },
    "free_field_d60_dx0p5": {
        "dx_mm": 0.5,
        "ppw": 6.0,
        "pml_size": 12,
        "pml_thickness_mm": 6.0,
        "cfl": 0.2,
        "grid": "218x168x138",
        "status": "field_only_kwave_ok_no_target_waveform",
        "refined_focus_error_percent": 5.472,
        "core_output_available": False,
    },
    "ct_case079_corrected_baseline": {
        "dx_mm": 0.75,
        "ppw": 4.0,
        "pml_size": 12,
        "cfl": 0.2,
        "skull_model": "binary_hu300",
        "skull_sound_speed_m_s": 2800,
        "skull_density_kg_m3": 1900,
        "alpha_power": 1.5,
        "target_window_peak_mpa": 2.449,
        "global_peak_mpa": 5.179,
        "target_to_global_ratio": 0.473,
        "max_skull_hu_on_beam_axis": 286.1,
        "skull_crossing_mm": 0.0,
    },
    "ct_case079_offset_y+5": {
        "dx_mm": 0.75,
        "target_window_peak_mpa": 0.596,
        "global_peak_mpa": 9.698,
        "target_to_global_ratio": 0.055,
        "skull_crossing_mm": "moderate",
    },
    "thermal": {
        "model": "Pennes_bioheat",
        "protocol": "5_s_on_15_s_off_20_s_total",
        "max_dT_baseline_C": 1.476,
        "skull_CEM43_baseline_min": 0.006,
        "brain_CEM43_baseline_min": 0.002,
    },
}

# Reference papers selected for the acoustic-field-first manuscript.
# Values are taken from literature_tFUS_review/04_基础与综述/02_方法与参数/07_tFUS文献与公开代码参数对照.md
# and the individual paper notes, with explicit uncertainty flags.
REFERENCES: list[dict[str, Any]] = [
    {
        "paper_id": "Gao2022_local",
        "citation": "Gao et al., 2022 (Ultrasound Med Biol) — 经颅聚焦超声调控系统的参数仿真研究",
        "role": "seed_protocol_and_baseline_geometry",
        "frequency_hz": 500_000,
        "aperture_mm": 25.0,
        "radius_mm": 30.0,
        "f_number": 1.2,
        "source_pressure_mpa": 1.0,
        "transducer_model": "single_bowl",
        "dx_mm": 0.42,
        "ppw": "~7.1 (1500 m/s water, 500 kHz)",
        "pml_size": "reported_in_paper",
        "cfl": "reported_in_paper",
        "skull_model": "binary_or_hu_porosity",
        "skull_sound_speed_m_s": "hu_dependent_up_to_~3100",
        "skull_density_kg_m3": "hu_dependent_up_to_~2200",
        "alpha_power": "not_explicitly_reported",
        "validation": "local_thesis_no_hydrophone",
        "primary_outcomes": ["target_pressure", "temperature_rise", "thermal_dose"],
        "relevant_figures": ["2D/3D_pressure_maps", "temperature_time_curve", "parameter_sweep"],
    },
    {
        "paper_id": "Legon2014",
        "citation": "Legon et al., 2014 (Nature Neuroscience) — Transcranial focused ultrasound modulates S1 in humans",
        "role": "human_neuromodulation_parameter_anchor",
        "frequency_hz": 500_000,
        "aperture_mm": "not_reported",
        "radius_mm": "not_reported",
        "f_number": "not_reported",
        "source_pressure_mpa": "~0.80 (peak rarefactional, in situ estimate)",
        "transducer_model": "single-element_focused",
        "dx_mm": "not_reported",
        "ppw": "not_reported",
        "pml_size": "not_reported",
        "cfl": "not_reported",
        "skull_model": "not_reported",
        "skull_sound_speed_m_s": "not_reported",
        "skull_density_kg_m3": "not_reported",
        "alpha_power": "not_reported",
        "validation": "human_behavioral_and_imaging",
        "primary_outcomes": ["behavioral_modulation", "pressure_estimate", "beam_fwhm_lateral_4.9_mm_axial_18_mm"],
        "relevant_figures": ["experimental_setup", "beam_profile"],
    },
    {
        "paper_id": "Montanaro2021",
        "citation": "Montanaro et al., 2021 (Physics in Medicine & Biology) — The impact of CT image parameters and skull heterogeneity modeling",
        "role": "ct_parameter_and_mapping_sensitivity_reference",
        "frequency_hz": "method_paper_not_fixed",
        "aperture_mm": "not_reported",
        "radius_mm": "not_reported",
        "f_number": "not_reported",
        "source_pressure_mpa": "not_reported",
        "transducer_model": "not_reported",
        "dx_mm": "not_reported",
        "ppw": "not_reported",
        "pml_size": "not_reported",
        "cfl": "not_reported",
        "skull_model": "homogeneous_vs_ct_heterogeneous",
        "skull_sound_speed_m_s": "ct_dependent_range",
        "skull_density_kg_m3": "ct_dependent_range",
        "alpha_power": "not_reported",
        "validation": "simulation_intercomparison",
        "primary_outcomes": ["skull_volume_change", "pressure_ratio_vs_homogeneous", "ct_resolution_sensitivity"],
        "relevant_figures": ["skull_segmentation_comparison", "pressure_difference_maps"],
    },
    {
        "paper_id": "Pasquinelli2020",
        "citation": "Pasquinelli et al., 2020 (Journal of Neural Engineering) — Transducer modeling for accurate acoustic simulations",
        "role": "free_field_transducer_calibration_reference",
        "frequency_hz": "not_fixed",
        "aperture_mm": "not_reported",
        "radius_mm": "not_reported",
        "f_number": "not_reported",
        "source_pressure_mpa": "hydrophone_measured",
        "transducer_model": "geometric_piston_vs_hydrophone",
        "dx_mm": "not_reported",
        "ppw": "not_reported",
        "pml_size": "not_reported",
        "cfl": "not_reported",
        "skull_model": "none_free_field_water",
        "skull_sound_speed_m_s": 1500,
        "skull_density_kg_m3": 1000,
        "alpha_power": "not_reported",
        "validation": "hydrophone_measurement",
        "primary_outcomes": ["focal_pressure", "focal_position", "axial_lateral_profiles"],
        "relevant_figures": ["hydrophone_vs_simulation_profiles", "transducer_geometry"],
    },
    {
        "paper_id": "Chen2023",
        "citation": "Chen et al., 2023 (Medical Physics) — Numerical and experimental evaluation of low-intensity tFUS wave propagation using human skulls",
        "role": "human_skull_quantitative_benchmark",
        "frequency_hz": 500_000,
        "aperture_mm": 30.0,
        "radius_mm": 36.0,
        "f_number": 1.2,
        "source_pressure_mpa": "~0.34 (@100 Vpp, free-field estimate)",
        "transducer_model": "single-element_focused",
        "dx_mm": 0.25,
        "ppw": "~7",
        "pml_size": "not_reported",
        "cfl": "not_reported",
        "skull_model": "ct_based_heterogeneous",
        "skull_sound_speed_m_s": "ct_dependent",
        "skull_density_kg_m3": "ct_dependent",
        "alpha_power": "~0.8-1.0 (fitted)",
        "validation": "human_skull_hydrophone",
        "primary_outcomes": ["transcranial_pressure", "transmission_efficiency_30_40_percent", "focal_shift"],
        "relevant_figures": ["skull_ct", "pressure_maps", "transmission_efficiency_bar"],
    },
    {
        "paper_id": "Jin2020_Kranion",
        "citation": "Jin et al., 2020 (BMC Biomedical Engineering) — Open-source phase correction toolkit",
        "role": "phase_correction_method_reference",
        "frequency_hz": 650_000,
        "aperture_mm": "not_reported",
        "radius_mm": "not_reported",
        "f_number": "not_reported",
        "source_pressure_mpa": "pnp_maps",
        "transducer_model": "ExAblate_1024_element",
        "dx_mm": "not_reported",
        "ppw": "not_reported",
        "pml_size": "not_reported",
        "cfl": "not_reported",
        "skull_model": "ct_ray_tracing",
        "skull_sound_speed_m_s": "ray_traced",
        "skull_density_kg_m3": "ray_traced",
        "alpha_power": "not_reported",
        "validation": "cadaver_skull_hydrophone",
        "primary_outcomes": ["phase_profile", "corrected_vs_uncorrected_pnp", "focal_displacement"],
        "relevant_figures": ["phase_map", "pnp_comparison", "ray_paths"],
    },
    {
        "paper_id": "Treeby2010",
        "citation": "Treeby & Cox, 2010 (Journal of the Acoustical Society of America) — k-Wave: MATLAB toolbox for the simulation and reconstruction of photoacoustic wave fields",
        "role": "solver_foundation",
        "frequency_hz": "arbitrary",
        "aperture_mm": "arbitrary",
        "radius_mm": "arbitrary",
        "f_number": "arbitrary",
        "source_pressure_mpa": "arbitrary",
        "transducer_model": "arbitrary",
        "dx_mm": "user_defined",
        "ppw": "user_defined",
        "pml_size": "user_defined",
        "cfl": "user_defined",
        "skull_model": "user_defined",
        "skull_sound_speed_m_s": "user_defined",
        "skull_density_kg_m3": "user_defined",
        "alpha_power": "user_defined",
        "validation": "benchmark_problems_and_applications",
        "primary_outcomes": ["wave_equation_accuracy", "pml_performance", "heterogeneous_propagation"],
        "relevant_figures": ["benchmark_comparisons"],
    },
]

# Gap assessment items: each maps a paper expectation to the current project state.
GAP_ITEMS: list[dict[str, Any]] = [
    {
        "item_id": "FREQ_500KHZ",
        "parameter": "Frequency",
        "paper_expectation": "500 kHz is common for human tFUS (Gao 2022, Legon 2014, Chen 2023, TUSX)",
        "current_value": f"{CURRENT['source_geometry']['frequency_hz'] / 1000:.0f} kHz",
        "gap_level": "satisfied",
        "evidence_path": "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_confirmation_20260714",
        "notes": "Baseline frequency matches literature; frequency sweep is not required for the manuscript core.",
    },
    {
        "item_id": "SRC_GEOM_FNUMBER",
        "parameter": "Transducer F-number",
        "paper_expectation": "F~1.2 (Gao 2022 aperture 25/radius 30; Chen 2023 aperture 30/radius 36)",
        "current_value": f"aperture {CURRENT['source_geometry']['aperture_mm']:.1f} mm / radius {CURRENT['source_geometry']['nominal_radius_mm']:.3f} mm -> F={CURRENT['source_geometry']['f_number']:.3f}",
        "gap_level": "satisfied",
        "evidence_path": "outputs/acoustic_stage_closeout_20260714",
        "notes": "D60 source calibrated in free field; radius corrected from 74.435 to 78.330 mm to reduce focal error to 1.364%.",
    },
    {
        "item_id": "SRC_PRESSURE_DEFINITION",
        "parameter": "Source pressure definition",
        "paper_expectation": "Distinguish source/free-field/in-situ pressure (Pasquinelli 2020, Chen 2023)",
        "current_value": f"source_pressure={CURRENT['source_geometry']['source_pressure_mpa']:.1f} MPa; free-field target pressure={CURRENT['free_field_d60_r78p330_dx0p75']['target_pressure_mpa']:.3f} MPa",
        "gap_level": "fillable_from_existing",
        "evidence_path": "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_confirmation_20260714/d60_r78p330_confirmation_report.md",
        "notes": "Free-field calibration chain exists for D60/R78.330. Need to explicitly report source-to-free-field gain in Methods.",
    },
    {
        "item_id": "GRID_PPW",
        "parameter": "Grid resolution (PPW)",
        "paper_expectation": "PPW >= 6-8 for paper grade (Montanaro 2021; Chen 2023 ~7 PPW)",
        "current_value": f"dx0.75 PPW={CURRENT['free_field_d60_r78p330_dx0p75']['ppw']}; dx0.5 PPW={CURRENT['free_field_d60_dx0p5']['ppw']}",
        "gap_level": "requires_new_computation",
        "evidence_path": "outputs/freefield_aperture_calibration/d60_dx0p5_fieldonly_20260713",
        "notes": "dx0.75 only gives PPW=4. dx0.5 gives PPW=6 but its target waveform and refined focus error (5.472%) failed the Gate B acceptance. dx0.375/0.3 would be needed for paper-grade PPW.",
    },
    {
        "item_id": "PML_CFL",
        "parameter": "PML / CFL",
        "paper_expectation": "PML thickness and CFL reported; boundary reflections controlled",
        "current_value": f"PML={CURRENT['free_field_d60_r78p330_dx0p75']['pml_size']} (thickness {CURRENT['free_field_d60_r78p330_dx0p75']['pml_thickness_mm']:.1f} mm); CFL={CURRENT['free_field_d60_r78p330_dx0p75']['cfl']}; boundary distance={CURRENT['free_field_d60_r78p330_dx0p75']['boundary_distance_voxels']} voxels",
        "gap_level": "satisfied",
        "evidence_path": "outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_confirmation_20260714",
        "notes": "PML12/CFL0.2 is documented; boundary distance is adequate for the dx0.75 free-field run.",
    },
    {
        "item_id": "FOCUS_METRICS",
        "parameter": "Focus metrics (-6 dB widths, focal position error)",
        "paper_expectation": "Report axial/lateral -6 dB widths and focal error (Pasquinelli 2020, Chen 2023)",
        "current_value": f"dx0.75 lateral {CURRENT['free_field_d60_r78p330_dx0p75']['lateral_minus6db_mm']:.3f} mm, axial {CURRENT['free_field_d60_r78p330_dx0p75']['axial_minus6db_mm']:.3f} mm, refined focus error {CURRENT['free_field_d60_r78p330_dx0p75']['refined_focus_error_percent']:.3f}%",
        "gap_level": "satisfied",
        "evidence_path": "outputs/acoustic_stage_closeout_20260714/d60_source_correction_metrics.csv",
        "notes": "Free-field metrics are computed and traceable. CT metrics are not yet available for manuscript.",
    },
    {
        "item_id": "SKULL_MODEL",
        "parameter": "Skull acoustic mapping",
        "paper_expectation": "Continuous HU-based or porosity-based mapping (Montanaro 2021, Chen 2023, PRESTUS)",
        "current_value": f"{CURRENT['ct_case079_corrected_baseline']['skull_model']}; c={CURRENT['ct_case079_corrected_baseline']['skull_sound_speed_m_s']} m/s; rho={CURRENT['ct_case079_corrected_baseline']['skull_density_kg_m3']} kg/m3; alpha_power={CURRENT['ct_case079_corrected_baseline']['alpha_power']}",
        "gap_level": "currently_unachievable",
        "evidence_path": "outputs/ct_acoustic_model_3d_profile_hu300",
        "notes": "Only binary HU300 is validated for pressure. Continuous/prestus profiles are model-build-only and pressure-blocked by alpha_semantics gate.",
    },
    {
        "item_id": "SKULL_CROSSING",
        "parameter": "True skull crossing / transmission efficiency",
        "paper_expectation": "Beam crosses realistic skull thickness; transmission efficiency reported (Chen 2023 ~30-40%)",
        "current_value": f"corrected baseline beam axis max HU={CURRENT['ct_case079_corrected_baseline']['max_skull_hu_on_beam_axis']:.1f}, crossing {CURRENT['ct_case079_corrected_baseline']['skull_crossing_mm']:.1f} mm; offset (+5,0) target/global={CURRENT['ct_case079_offset_y+5']['target_to_global_ratio']:.3f}",
        "gap_level": "currently_unachievable",
        "evidence_path": "outputs/thick_skull_external_validity_079",
        "notes": "Current corrected baseline avoids bone. Thick-skull offset (+5,0) run shows target/global 0.055 (focus objective failed). No validated transmission efficiency chain exists.",
    },
    {
        "item_id": "TARGET_GLOBAL_RATIO",
        "parameter": "Target/global peak ratio / focal quality",
        "paper_expectation": "Corrected methods reach target/global >70-80% (Jin 2020, Leung 2021)",
        "current_value": f"corrected baseline target/global={CURRENT['ct_case079_corrected_baseline']['target_to_global_ratio']:.3f}; best source-array quick={CURRENT['ct_case079_offset_y+5']['target_to_global_ratio']:.3f}",
        "gap_level": "currently_unachievable",
        "evidence_path": "outputs/focus_apodization_review_20260710",
        "notes": "Focus is the main scientific blocker. Global peak remains 30-56 mm from target. Source-array phase correction did not improve Case 079 because the baseline has negligible skull aberration.",
    },
    {
        "item_id": "THERMAL_SAFETY",
        "parameter": "Thermal safety metrics",
        "paper_expectation": "Report CEM43, max temperature rise, protocol details (Gao 2022, ITRUSST)",
        "current_value": f"Pennes model; max dT={CURRENT['thermal']['max_dT_baseline_C']:.3f} C; skull CEM43={CURRENT['thermal']['skull_CEM43_baseline_min']:.3f} min; brain CEM43={CURRENT['thermal']['brain_CEM43_baseline_min']:.3f} min",
        "gap_level": "fillable_from_existing",
        "evidence_path": "outputs/pennes_protocol_dose_target_020",
        "notes": "Thermal pipeline exists but is only meaningful after a valid acoustic candidate is locked. Current thermal numbers are for the edge-skimming baseline, not a true transcranial field.",
    },
    {
        "item_id": "VALIDATION_HYDROPHONE",
        "parameter": "Experimental / hydrophone validation",
        "paper_expectation": "Hydrophone or human-behavioral validation (Pasquinelli 2020, Jin 2020, Chen 2023, Legon 2014)",
        "current_value": "none",
        "gap_level": "currently_unachievable",
        "evidence_path": "N/A",
        "notes": "No hydrophone or biological data available. Manuscript must be framed as computational methods study with literature benchmarking only.",
    },
    {
        "item_id": "MULTI_SUBJECT",
        "parameter": "Multi-subject / multi-trajectory generalization",
        "paper_expectation": "More than one skull or several trajectories (Montanaro 2021, Chen 2023)",
        "current_value": "Case 079 only; D60 Gate A has 3 candidate trajectories selected but not pressure-validated",
        "gap_level": "requires_new_computation",
        "evidence_path": "outputs/paper_gate_a_d60_trajectory_selection_079",
        "notes": "Three D60 trajectories are selected and machine-safe. Pressure runs on them would satisfy the multi-trajectory expectation of the acoustic paper plan.",
    },
]

# Figure mapping: reference paper figure types -> reusable project outputs.
FIGURE_MAPPING: list[dict[str, Any]] = [
    {
        "reference_paper": "Gao2022_local",
        "figure_type": "parameter_sweep / temperature_time_curve",
        "project_asset": "outputs/pennes_protocol_dose_target_020/temperature_time_curve.png",
        "reusable": True,
        "limitation": "Protocol is Gao-specific seed, not a consensus neuromodulation protocol; thermal numbers are for edge-skimming baseline.",
    },
    {
        "reference_paper": "Pasquinelli2020",
        "figure_type": "hydrophone-equivalent free-field axial/lateral profiles",
        "project_asset": "outputs/acoustic_stage_closeout_20260714/d60_source_correction_figure.png",
        "reusable": True,
        "limitation": "No real hydrophone; profiles are simulation-derived and need explicit source-pressure calibration.",
    },
    {
        "reference_paper": "Chen2023",
        "figure_type": "skull CT + pressure maps + transmission efficiency",
        "project_asset": "none",
        "reusable": False,
        "limitation": "True skull-crossing pressure run failed focus objective; no reliable transmission efficiency.",
    },
    {
        "reference_paper": "Jin2020_Kranion",
        "figure_type": "uncorrected vs corrected phase / PNP maps",
        "project_asset": "outputs/focus_apodization_review_20260710",
        "reusable": True,
        "limitation": "Previous multi-patch phase results invalidated by delay-semantics correction; only screening evidence remains.",
    },
    {
        "reference_paper": "Montanaro2021",
        "figure_type": "skull segmentation / mapping sensitivity comparison",
        "project_asset": "outputs/ct_acoustic_model_3d_profile_hu250, hu300, hu400",
        "reusable": True,
        "limitation": "Only model-build outputs; no pressure comparison across HU thresholds on the same trajectory.",
    },
    {
        "reference_paper": "Treeby2010",
        "figure_type": "solver validation / PML sanity",
        "project_asset": "outputs/freefield_pml_boundary_runs",
        "reusable": True,
        "limitation": "PML comparison was on small free-field model; not repeated for D60 source.",
    },
]


def build_json() -> dict[str, Any]:
    return {
        "report_title": "Reference Paper Gap Matrix for Acoustic-Field-First Manuscript",
        "date": "2026-07-15",
        "scope": "Compare key reference paper parameters with current fus-sim state; no new simulation.",
        "current_project_state": CURRENT,
        "reference_papers": REFERENCES,
        "gap_items": GAP_ITEMS,
        "figure_mapping": FIGURE_MAPPING,
        "summary_counts": {
            "satisfied": sum(1 for g in GAP_ITEMS if g["gap_level"] == "satisfied"),
            "fillable_from_existing": sum(1 for g in GAP_ITEMS if g["gap_level"] == "fillable_from_existing"),
            "requires_new_computation": sum(1 for g in GAP_ITEMS if g["gap_level"] == "requires_new_computation"),
            "currently_unachievable": sum(1 for g in GAP_ITEMS if g["gap_level"] == "currently_unachievable"),
        },
        "next_action": "Proceed to P2 (paper skeleton and results package) using only satisfied/fillable items; do not restart simulations for currently_unachievable gaps without a new decision.",
    }


def write_csv(matrix: dict[str, Any], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["item_id", "parameter", "paper_expectation", "current_value", "gap_level", "evidence_path", "notes"])
        for item in matrix["gap_items"]:
            writer.writerow([item["item_id"], item["parameter"], item["paper_expectation"], item["current_value"], item["gap_level"], item["evidence_path"], item["notes"]])


def write_report(matrix: dict[str, Any], path: Path) -> None:
    counts = matrix["summary_counts"]
    lines = [
        "# Reference Paper Gap Matrix (2026-07-15)",
        "",
        "> Scope: align reference paper parameters with the current fus-sim state for the acoustic-field-first manuscript. No new simulation was run.",
        "",
        "## Summary",
        "",
        f"- **Satisfied**: {counts['satisfied']}",
        f"- **Fillable from existing data**: {counts['fillable_from_existing']}",
        f"- **Requires new computation**: {counts['requires_new_computation']}",
        f"- **Currently unachievable**: {counts['currently_unachievable']}",
        "",
        "## Current project state (authoritative snapshot)",
        "",
        "### Source geometry",
        "",
        f"- Frequency: {CURRENT['source_geometry']['frequency_hz'] / 1000:.0f} kHz",
        f"- Aperture: {CURRENT['source_geometry']['aperture_mm']:.1f} mm",
        f"- Nominal radius: {CURRENT['source_geometry']['nominal_radius_mm']:.3f} mm",
        f"- F-number: {CURRENT['source_geometry']['f_number']:.4f}",
        f"- Source pressure convention: {CURRENT['source_geometry']['source_pressure_mpa']:.1f} MPa",
        f"- Transducer model: {CURRENT['source_geometry']['transducer_model']}",
        "",
        "### Free-field D60/R78.330 dx0.75 calibration",
        "",
        f"- Grid: {CURRENT['free_field_d60_r78p330_dx0p75']['grid']} (dx={CURRENT['free_field_d60_r78p330_dx0p75']['dx_mm']:.2f} mm)",
        f"- PPW: {CURRENT['free_field_d60_r78p330_dx0p75']['ppw']:.1f}",
        f"- PML: {CURRENT['free_field_d60_r78p330_dx0p75']['pml_size']} ({CURRENT['free_field_d60_r78p330_dx0p75']['pml_thickness_mm']:.1f} mm)",
        f"- CFL: {CURRENT['free_field_d60_r78p330_dx0p75']['cfl']}",
        f"- Global peak: {CURRENT['free_field_d60_r78p330_dx0p75']['global_peak_mpa']:.3f} MPa",
        f"- Target/global ratio: {CURRENT['free_field_d60_r78p330_dx0p75']['target_to_global_ratio']:.4f}",
        f"- Refined focus error: {CURRENT['free_field_d60_r78p330_dx0p75']['refined_focus_error_percent']:.3f}%",
        f"- Lateral -6 dB width: {CURRENT['free_field_d60_r78p330_dx0p75']['lateral_minus6db_mm']:.3f} mm",
        f"- Axial -6 dB width: {CURRENT['free_field_d60_r78p330_dx0p75']['axial_minus6db_mm']:.3f} mm",
        f"- Boundary distance: {CURRENT['free_field_d60_r78p330_dx0p75']['boundary_distance_voxels']} voxels",
        f"- Target waveform recorded: {CURRENT['free_field_d60_r78p330_dx0p75']['target_waveform_recorded']}",
        "",
        "### CT Case 079 corrected baseline",
        "",
        f"- Skull model: {CURRENT['ct_case079_corrected_baseline']['skull_model']}",
        f"- Skull sound speed: {CURRENT['ct_case079_corrected_baseline']['skull_sound_speed_m_s']} m/s",
        f"- Skull density: {CURRENT['ct_case079_corrected_baseline']['skull_density_kg_m3']} kg/m³",
        f"- Alpha power: {CURRENT['ct_case079_corrected_baseline']['alpha_power']}",
        f"- Target-window peak: {CURRENT['ct_case079_corrected_baseline']['target_window_peak_mpa']:.3f} MPa",
        f"- Global peak: {CURRENT['ct_case079_corrected_baseline']['global_peak_mpa']:.3f} MPa",
        f"- Target/global ratio: {CURRENT['ct_case079_corrected_baseline']['target_to_global_ratio']:.3f}",
        f"- Beam-axis max HU: {CURRENT['ct_case079_corrected_baseline']['max_skull_hu_on_beam_axis']:.1f}",
        f"- Skull crossing on beam axis: {CURRENT['ct_case079_corrected_baseline']['skull_crossing_mm']:.1f} mm",
        "",
        "## Gap matrix",
        "",
        "| Item | Parameter | Paper expectation | Current value | Gap level | Evidence path |",
        "|------|-----------|-------------------|---------------|-----------|---------------|",
    ]
    for item in matrix["gap_items"]:
        lines.append(
            f"| {item['item_id']} | {item['parameter']} | {item['paper_expectation']} | {item['current_value']} | {item['gap_level']} | {item['evidence_path']} |"
        )

    lines.extend([
        "",
        "### Gap level definitions",
        "",
        "- **satisfied**: current data already meets the paper expectation.",
        "- **fillable_from_existing**: can be satisfied by reorganizing or re-plotting existing outputs; no new k-Wave/Pennes run.",
        "- **requires_new_computation**: needs a new simulation or analysis that is technically feasible but requires explicit authorization and budget.",
        "- **currently_unachievable**: blocked by a fundamental limitation (no hydrophone data, focus objective failed, profile not pressure-eligible) that cannot be resolved within the current plan.",
        "",
        "## Reference papers in scope",
        "",
        "| Paper | Role | Frequency | Aperture / Radius | Validation |",
        "|-------|------|-----------|-------------------|------------|",
    ])
    for ref in matrix["reference_papers"]:
        lines.append(
            f"| {ref['paper_id']} | {ref['role']} | {ref['frequency_hz']} | {ref['aperture_mm']} / {ref['radius_mm']} | {ref['validation']} |"
        )

    lines.extend([
        "",
        "## Reusable figure mapping",
        "",
        "| Reference paper | Figure type | Project asset | Reusable? | Limitation |",
        "|-----------------|-------------|---------------|-----------|------------|",
    ])
    for fig in matrix["figure_mapping"]:
        lines.append(
            f"| {fig['reference_paper']} | {fig['figure_type']} | {fig['project_asset']} | {fig['reusable']} | {fig['limitation']} |"
        )

    lines.extend([
        "",
        "## Implications for manuscript drafting",
        "",
        "### What can be written now (satisfied + fillable)",
        "",
        "1. **Methods — source geometry and free-field calibration**: frequency, aperture, corrected radius, F-number, grid, PML, CFL, and focus metrics are all traceable to `outputs/acoustic_stage_closeout_20260714/`.",
        "2. **Results — free-field source correction**: the R78.330 correction reduced refined focal error from 3.555% to 1.364% and increased target/global ratio from 0.982 to 0.991. This is engineering free-field calibration evidence, not CT or clinical evidence.",
        "3. **Limitations**: explicitly state that dx0.5 confirmation was incomplete, CT pressure is blocked, no hydrophone data exist, and skull mapping is binary HU300 only.",
        "",
        "### What requires a new decision before writing as results",
        "",
        "1. **Grid convergence**: dx0.5 refined focus error 5.472% failed the preregistered 5% gate and the complete target waveform is missing. A new low-memory waveform architecture or dx0.375 run would be needed.",
        "2. **Multi-trajectory CT pressure**: three D60 trajectories are selected but not pressure-validated. Running them would require a fresh Evidence Brief and user authorization.",
        "",
        "### What must be excluded or framed as future work",
        "",
        "1. **True transcranial residual pressure / transmission efficiency**: current corrected baseline beam avoids bone; offset (+5,0) run failed focus objective.",
        "2. **Continuous skull mapping as default**: `prestus_fit_alpha_power_2` and `continuous_skull` are pressure-blocked.",
        "3. **Experimental validation**: no hydrophone or behavioral data.",
        "",
        "## Next step",
        "",
        matrix["next_action"],
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    matrix = build_json()
    (args.output_dir / "reference_paper_gap_matrix.json").write_text(
        json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_csv(matrix, args.output_dir / "reference_paper_gap_matrix.csv")
    write_report(matrix, args.output_dir / "reference_paper_gap_matrix.md")

    print(json.dumps({"status": "ok", "output_dir": str(args.output_dir), "summary_counts": matrix["summary_counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
