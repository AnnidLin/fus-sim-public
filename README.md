# fus-sim

This workspace starts a lightweight Python reproduction path for transcranial focused ultrasound simulation.

`fus-sim` helps researchers build reproducible k-Wave and CT-derived acoustic/thermal safety workflows with explicit parameter provenance, dry-run quality gates, conservative validation reports, and clear boundaries between exploratory outputs and reusable defaults.

This repository is research software, not a clinical planning tool. See [DISCLAIMER.md](DISCLAIMER.md) before using or extending the project.

## What This Project Provides

- Lightweight focused-transducer pressure-field prototypes.
- k-Wave 2D/3D simulation entry points with quality metadata.
- CT/NIfTI/DICOM acoustic model builders for user-provided data.
- CT-HU acoustic mapping profiles with source and evidence notes.
- Thermal estimate and Pennes-style sensitivity workflows.
- Evidence brief generators, dry-run gates, and run-ledger utilities.

## Public-Safe Quickstart

The smallest demo does not require CT data or k-Wave. It generates a simple spherical-focus pressure field using only `numpy` and `pillow`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-light.txt
.\.venv\Scripts\python.exe simulate_spherical_focus.py
```

Expected outputs:

- `outputs/spherical_focus/pressure_field.png`
- `outputs/spherical_focus/pressure_field_mpa.csv`
- `outputs/spherical_focus/summary.txt`

For k-Wave and CT-derived workflows, use `requirements-kwave312.txt` and provide your own data under `data/`. Do not commit raw medical data or generated heavy outputs.

## Public Release Notes

- Raw CT/DICOM/NIfTI data, generated `.npz` arrays, ZIP datasets, binaries, and paper PDFs are intentionally excluded from the public repository.
- Literature notes cite and summarize sources; they should not redistribute paper files.
- Contributions that touch physical parameters, acoustic mapping, boundary conditions, thermal assumptions, or simulation presets should follow [EVIDENCE_DRIVEN_DEVELOPMENT.md](EVIDENCE_DRIVEN_DEVELOPMENT.md).

## Status

The project is active research software. Current outputs are useful for reproducibility engineering and conservative simulation workflow development, but they are not paper-grade or clinical validation unless explicitly marked as such.

## Evidence-Driven Development

New platform modules should start from an evidence brief before implementation. This keeps paper parameters, public-tool references, and current platform gaps tied to engineering decisions.

```powershell
python generate_module_evidence_brief.py --module freefield_calibration --output-dir outputs\evidence_briefs\freefield_calibration
```

Outputs:

- `outputs/evidence_briefs/<module>/evidence_brief.md`
- `outputs/evidence_briefs/<module>/evidence_brief.json`

Supported modules:

- `freefield_calibration`
- `ct_hu_mapping`
- `thermal_safety`
- `entry_planning`
- `kwave_simulation_quality`
- `multicase_pipeline`
- `fit_alpha_power_migration`
- `fit_alpha_power_formula_audit`

Rules are documented in `EVIDENCE_DRIVEN_DEVELOPMENT.md`. The first generated brief is `outputs/evidence_briefs/freefield_calibration/evidence_brief.md`.

## Parameter Evidence Layer

The current roadmap shifts the platform from "can run" toward "each default parameter has evidence." Use the parameter evidence generator before treating a value as a platform default:

```powershell
python generate_platform_parameter_profile.py
```

Outputs:

- `outputs/parameter_profiles/platform_parameter_profile.json`
- `outputs/parameter_profiles/platform_parameter_source_report.md`
- `outputs/parameter_profiles/unsupported_or_uncertain_parameters.md`

The Chinese report records the current interpretation boundaries:

- `500 kHz` is the Gao2022 baseline frequency, not the only accepted tFUS frequency.
- `1 MPa` is source/excitation pressure, not target in-situ pressure.
- `25/30 mm` is the Gao baseline transducer geometry.
- `30/35 mm` is the current 079 tuned geometry, not a literature consensus.
- `6% duty / 300 Hz / 67 ms / 2.5 s` is the Gao protocol, not a general tFUS protocol.
- Current quick cropped-domain outputs are screening results, not paper-grade reproduction.

## Free-Field Transducer Calibration

Roadmap stage 2 adds a water/free-field sanity check before treating any transducer geometry as a reusable platform setting.

```powershell
python simulate_freefield_transducer.py --aperture-mm 25 --radius-mm 30 --frequency-khz 500 --source-pressure-mpa 1 --medium water --output-dir outputs\freefield_calibration\ap25_r30_f500
python simulate_freefield_transducer.py --aperture-mm 30 --radius-mm 35 --frequency-khz 500 --source-pressure-mpa 1 --medium water --output-dir outputs\freefield_calibration\ap30_r35_f500
python compare_freefield_calibration.py --baseline-dir outputs\freefield_calibration\ap25_r30_f500 --candidate-dir outputs\freefield_calibration\ap30_r35_f500 --output-dir outputs\freefield_calibration
```

Outputs:

- `outputs/freefield_calibration/ap25_r30_f500/`: Gao baseline `ap25/r30/f500`.
- `outputs/freefield_calibration/ap30_r35_f500/`: current 079 tuned `ap30/r35/f500`.
- `outputs/freefield_calibration/freefield_calibration_report.md`: Chinese comparison report.
- `outputs/freefield_calibration/freefield_comparison.json`: machine-readable comparison.

Boundary: these are quick uniform-medium calibration runs. Source pressure, free-field pressure, and transcranial in-situ pressure remain separate quantities.

## CT-HU Acoustic Mapping Profiles

CT material mapping is now profile-based. The old hard-coded `HU >= 300` behavior is preserved by `simple_hu300.json`, while `simple_hu250.json` is available only for sensitivity comparison.

```powershell
python generate_module_evidence_brief.py --module ct_hu_mapping --output-dir outputs\evidence_briefs\ct_hu_mapping
python build_ct_acoustic_model.py --nifti-file data\raw_ct\079.nii --target-dx-mm 1.0 --target-index 93,121,63 --mapping-profile acoustic_mapping_profiles\simple_hu300.json --output-dir outputs\ct_acoustic_model_3d_profile_hu300
python compare_ct_mapping_profiles.py --baseline-dir outputs\ct_acoustic_model_3d --candidate-dir outputs\ct_acoustic_model_3d_profile_hu300 --extra-dir outputs\ct_acoustic_model_3d_profile_hu250 --output-dir outputs\ct_mapping_profile_compare_079
```

Profile files:

- `acoustic_mapping_profiles/simple_hu300.json`: current baseline-compatible binary profile.
- `acoustic_mapping_profiles/simple_hu250.json`: threshold sensitivity candidate.
- `acoustic_mapping_profiles/gao_binary_hu300.json`: Gao-oriented baseline family, still marked usable with caution.
- `acoustic_mapping_profiles/continuous_skull_draft.json`: future continuous skull mapping draft, not default.

Outputs:

- `outputs/evidence_briefs/ct_hu_mapping/evidence_brief.md`
- `outputs/ct_acoustic_model_3d_profile_hu300/`
- `outputs/ct_acoustic_model_3d_profile_hu250/`
- `outputs/ct_mapping_profile_compare_079/mapping_profile_comparison.md`

Boundary: mapping-profile comparison does not run k-Wave and does not replace the current tuned best by itself.

### PRESTUS fit-alpha-power=2 model-build route

The source-backed attenuation route `prestus_fit_alpha_power_2` now has an evidence brief and isolated 079 model-build validation:

```powershell
python generate_module_evidence_brief.py --module fit_alpha_power_migration --output-dir outputs\evidence_briefs\fit_alpha_power_migration
python build_ct_acoustic_model.py --nifti-file data\raw_ct\079.nii --target-dx-mm 1.0 --target-index 93,121,63 --mapping-profile acoustic_mapping_profiles\prestus_fit_alpha_power_2.json --output-dir outputs\ct_acoustic_model_3d_profile_prestus_fit_alpha_power_2
```

Outputs:

- `outputs/evidence_briefs/fit_alpha_power_migration/evidence_brief.md`
- `outputs/ct_acoustic_model_3d_profile_prestus_fit_alpha_power_2/`
- `outputs/fit_alpha_power_migration/079_fit_alpha_power_2_vs_no_dispersion/`
- `outputs/fit_alpha_power_migration/079_fit_alpha_power_2_vs_draft/`
- `outputs/fit_alpha_power_migration/079_fit_alpha_power_2_dry_run/quality_dry_run_summary.json`

Boundary: this is model-build-only validation. The profile remains `review_pending_model_build_only_do_not_use_as_default`, and `pressure_allowed_by_alpha_semantics=false`; it must not be treated as a validated pressure baseline.

The follow-up formula audit is available at:

- `outputs/evidence_briefs/fit_alpha_power_formula_audit/evidence_brief.md`
- `outputs/fit_alpha_power_formula_audit/formula_audit_report.md`
- `outputs/fit_alpha_power_formula_audit/sample_fit_table.csv`

It confirms the PRESTUS/Python formula migration at source-fragment and numeric-sanity level. It also explains why `alpha_power=2` gives a skull alpha prefactor range near `16-34.8 dB/(MHz^2 cm)`. This still does not authorize pressure simulation.

The current 079 `candidate_006` entry-path property comparison including this profile is:

- `outputs/entry_path_property_profiles/079_candidate_006_fit_alpha_power_2/entry_path_profile.csv`
- `outputs/entry_path_property_profiles/079_candidate_006_fit_alpha_power_2/entry_path_property_summary.json`
- `outputs/entry_path_property_profiles/079_candidate_006_fit_alpha_power_2/fit_alpha_entry_path_interpretation.md`
- `outputs/entry_path_property_profiles/079_candidate_006_fit_alpha_power_2/path_material_profiles.png`
- `outputs/entry_path_property_profiles/079_candidate_006_fit_alpha_power_2/path_alpha_by_semantics.png`

Boundary: the path profile shows material values along the selected beam path only. It is not acoustic propagation and keeps pressure blocked.

The MATLAB/Python numerical cross-check package for `fitPowerLawParamsMulti` is:

- `outputs/fit_alpha_power_matlab_crosscheck/input_fixture.csv`
- `outputs/fit_alpha_power_matlab_crosscheck/python_expected_outputs.csv`
- `outputs/fit_alpha_power_matlab_crosscheck/run_fit_alpha_crosscheck.m`
- `outputs/fit_alpha_power_matlab_crosscheck/crosscheck_report.md`

Current machine status: MATLAB was not found, so the package is ready but not executed.

## Current model

`simulate_spherical_focus.py` builds a small 2D pressure-field approximation for a concave focused transducer. It uses the thesis parameters recorded in `项目任务总结.md`:

- frequency: 500 kHz
- source pressure: 1 MPa
- transducer curvature radius: 30 mm
- aperture diameter: 25 mm

The script samples the transducer as coherent point sources on a spherical cap, adds a simple attenuation layer as a first skull placeholder, then exports:

- `outputs/spherical_focus/pressure_field.png`
- `outputs/spherical_focus/pressure_field_mpa.csv`
- `outputs/spherical_focus/summary.txt`

## Run

```powershell
python simulate_spherical_focus.py
```

## Environment

For full k-Wave workflows, use a Python 3.12 environment with `requirements-kwave312.txt` installed.
Python 3.14 is still installed separately and is not used for k-Wave work.

To verify the environment:

```powershell
python -c "import numpy, scipy, matplotlib, h5py; import kwave; print('ok')"
```

## Notes

This starter script is not yet a k-Wave time-domain solver. It is a fast baseline for checking geometry, parameters, focus location, and output workflow before building the full k-wave-python model.

## 2D k-Wave baseline

`simulate_kwave_2d_focus.py` is the first real k-Wave time-domain baseline. It is only used to prove the architecture can run before moving to 3D. It keeps the same thesis parameters for the transducer and runs a small CPU-only 2D model in a homogeneous soft-tissue medium:

- frequency: 500 kHz
- source pressure: 1 MPa
- transducer curvature radius: 30 mm
- aperture diameter: 25 mm
- medium sound speed: 1540 m/s
- medium density: 1000 kg/m^3

Run:

```powershell
python simulate_kwave_2d_focus.py
```

Outputs:

- `outputs/kwave_2d_focus/pressure_max.png`
- `outputs/kwave_2d_focus/pressure_max_mpa.csv`
- `outputs/kwave_2d_focus/source_layout.png`
- `outputs/kwave_2d_focus/summary.txt`

The script sets `TEMP`, `TMP`, and `MPLCONFIGDIR` to project-local folders before importing k-Wave/matplotlib, which avoids cache-write problems caused by the current Windows user path.

## 3D acoustic model layer

`build_3d_acoustic_model.py` builds the first 3D model layer for the platform. It does not run the expensive 3D solver yet; it prepares the k-Wave-ready 3D acoustic property arrays that a later `kspaceFirstOrder3D` script will consume.

Run:

```powershell
python build_3d_acoustic_model.py
```

Outputs:

- `outputs/skull_model_3d/acoustic_model_3d.npz`
- `outputs/skull_model_3d/label_slices.png`
- `outputs/skull_model_3d/sound_speed_slices.png`
- `outputs/skull_model_3d/summary.txt`
- `outputs/skull_model_3d/summary.json`

The `.npz` file contains `labels`, `sound_speed`, `density`, `alpha_coeff`, `dx_m`, and `target_index_ijk`. The placeholder target is placed in the left hemisphere so a later focused source can be positioned outside the left temporal skull. This is the interface that should stay stable when the procedural skull placeholder is replaced with CT-derived labels.

## 3D k-Wave pressure baseline

`simulate_kwave_3d_focus.py` reads `outputs/skull_model_3d/acoustic_model_3d.npz` and runs a small 3D CPU k-Wave pressure simulation. By default it uses a cropped quick domain around the left temporal source-target path to keep memory and runtime manageable. Use `--full` only when you want to try the full placeholder model.

Run:

```powershell
python simulate_kwave_3d_focus.py
```

Outputs:

- `outputs/kwave_3d_focus/pressure_max_mpa.npz`
- `outputs/kwave_3d_focus/pressure_max_axial.png`
- `outputs/kwave_3d_focus/pressure_max_coronal.png`
- `outputs/kwave_3d_focus/pressure_max_sagittal.png`
- `outputs/kwave_3d_focus/source_target_layout.png`
- `outputs/kwave_3d_focus/axis_profile.csv`
- `outputs/kwave_3d_focus/axis_profile.png`
- `outputs/kwave_3d_focus/focus_metrics.txt`
- `outputs/kwave_3d_focus/focus_metrics.json`
- `outputs/kwave_3d_focus/summary.txt`
- `outputs/kwave_3d_focus/summary.json`

To re-analyze an existing 3D output without re-running k-Wave:

```powershell
python analyze_kwave_3d_focus.py
```

Current main line:

```text
3D acoustic model -> 3D pressure simulation -> CT/DICOM replacement -> thermal simulation
```

## CT/NIfTI/DICOM acoustic model

`build_ct_acoustic_model.py` converts a local CT NIfTI file or DICOM folder into the same acoustic model interface used by the 3D simulator. Put CT files/folders under `data/raw_ct/`; generated data and caches stay inside this project.

Install CT import support if needed:

```powershell
$env:TEMP='.tmp'
$env:TMP='.tmp'
python -m pip install --cache-dir .tmp\pip-cache pydicom==3.0.1 nibabel==5.4.2
```

Convert the downloaded 079 NIfTI CT case:

```powershell
python build_ct_acoustic_model.py --nifti-file data\raw_ct\079.nii --target-dx-mm 1.0
```

Convert a DICOM CT case:

```powershell
python build_ct_acoustic_model.py --dicom-dir data\raw_ct\case001
```

Outputs:

- `outputs/ct_acoustic_model_3d/acoustic_model_3d.npz`
- `outputs/ct_acoustic_model_3d/ct_hu_slices.png`
- `outputs/ct_acoustic_model_3d/label_slices.png`
- `outputs/ct_acoustic_model_3d/sound_speed_slices.png`
- `outputs/ct_acoustic_model_3d/summary.txt`
- `outputs/ct_acoustic_model_3d/summary.json`

Run 3D k-Wave with a CT-derived model:

```powershell
python simulate_kwave_3d_focus.py --model outputs\ct_acoustic_model_3d\acoustic_model_3d.npz --output-dir outputs\kwave_3d_focus_ct_079
python analyze_kwave_3d_focus.py --input-dir outputs\kwave_3d_focus_ct_079
```

For the 079 quick run, the default target is the centroid of soft-tissue voxels. This is enough to validate the real CT pipeline, but the next modeling step is to choose a clinically meaningful target and force the source bowl to sit outside the skull along the desired entry path.

Plan a left-side extracranial entry path and run a faster smoke simulation:

```powershell
python plan_ct_target_entry.py --model outputs\ct_acoustic_model_3d\acoustic_model_3d.npz --output-dir outputs\ct_entry_plan_079
python simulate_kwave_3d_focus.py --model outputs\ct_acoustic_model_3d\acoustic_model_3d.npz --entry-plan outputs\ct_entry_plan_079\entry_plan.json --output-dir outputs\kwave_3d_focus_ct_079_entry_fast --sim-time-us 25 --quick-lateral-mm 17 --quick-post-target-mm 8
```

Scan several left-side entry offsets safely. The default command only generates and ranks candidates; it does not run k-Wave:

```powershell
python scan_ct_entry_positions.py --model outputs\ct_acoustic_model_3d\acoustic_model_3d.npz --output-dir outputs\ct_entry_scan_079
```

Run k-Wave only for the lightest ranked candidate:

```powershell
python scan_ct_entry_positions.py --model outputs\ct_acoustic_model_3d\acoustic_model_3d.npz --output-dir outputs\ct_entry_scan_079 --run-fast --max-fast-runs 1
```

The scan runner now estimates fast simulation time from source-target distance. For the 079 center candidate this gives about 51 us, long enough for the wave to reach the target region.

Validate the top three geometry-ranked candidates while reusing any existing `kwave_fast` result:

```powershell
python scan_ct_entry_positions.py --model outputs\ct_acoustic_model_3d\acoustic_model_3d.npz --output-dir outputs\ct_entry_scan_079 --run-fast --top-ranked 3
```

The early 079 entry scan found `candidate_011` as the best of the first three candidates by target-window pressure. The current best quick-3D configuration is now:

```text
target: outputs/ct_target_candidates_079 target_020 -> [93,121,63]
entry offset: (10, 0) mm
source standoff: 16 mm
source mask: background only
aperture: 30 mm
curvature radius: 35 mm
cycles: 8
sim time: 55 us
output: outputs/ct_transducer_stability_target_020/ap30_r35_c8_t55/
```

This current best gives a target-window peak pressure of about `2.254 MPa` in quick mode. A first-order thermal estimate can be generated from this pressure field:

```powershell
python estimate_temperature_rise.py --pressure-dir outputs\ct_transducer_stability_target_020\ap30_r35_c8_t55 --output-dir outputs\thermal_estimate_target_020_best --sonication-s 1.0
```

The thermal estimate is a first-order heat deposition calculation, not a full Pennes bioheat simulation. For 1 second equivalent continuous sonication it reports about `1.45 C` at the target voxel and about `23.76 C` maximum temperature rise near the high-absorption region, so later safety analysis should refine duty cycle, perfusion, and diffusion.

A lightweight Pennes-style bioheat estimate adds duty cycle, thermal diffusion, and soft-tissue perfusion:

```powershell
python simulate_pennes_bioheat.py --pressure-dir outputs\ct_transducer_stability_target_020\ap30_r35_c8_t55 --output-dir outputs\pennes_bioheat_target_020_best --duration-s 0.067 --duty-cycle 0.06 --dt-s 0.005
```

Using the paper-like `67 ms` stimulus train and `6%` duty cycle, the lightweight Pennes estimate reports about `0.006 C` at the target voxel and about `0.094 C` maximum temperature rise. This is still a quick cropped-domain safety estimate with approximate material and perfusion maps.

The Pennes script also supports explicit pulse timing. For the paper-like `300 Hz` PRF and `6%` duty cycle, one `67 ms` train produces about `0.006 C` target rise and `0.099 C` max rise; three trains separated by `2.5 s` produce about `0.018 C` target rise and `0.175 C` max rise:

```powershell
python simulate_pennes_bioheat.py --pressure-dir outputs\ct_transducer_stability_target_020\ap30_r35_c8_t55 --output-dir outputs\pennes_bioheat_target_020_pulse_train1 --pulse-mode explicit --prf-hz 300 --pulse-duty-cycle 0.06 --train-duration-s 0.067 --trains 1 --dt-s 0.001
python simulate_pennes_bioheat.py --pressure-dir outputs\ct_transducer_stability_target_020\ap30_r35_c8_t55 --output-dir outputs\pennes_bioheat_target_020_pulse_train3 --pulse-mode explicit --prf-hz 300 --pulse-duty-cycle 0.06 --train-duration-s 0.067 --inter-train-s 2.5 --trains 3 --dt-s 0.005
```

The thermal script supports three heat-source modes:

- `explicit`: use the pulse schedule directly at each thermal step.
- `protocol-averaged`: use the protocol's effective duty cycle over the full train/inter-train duration.
- `averaged`: use a constant user-specified duty cycle over `duration-s`; this is useful as a conservative upper bound.

For the paper-like three-train protocol, `protocol-averaged` uses an effective duty cycle of about `0.242%` over `5.201 s`. It gives about `0.016 C` target rise and `0.155 C` max rise, close to the explicit three-train result:

```powershell
python simulate_pennes_bioheat.py --pressure-dir outputs\ct_transducer_stability_target_020\ap30_r35_c8_t55 --output-dir outputs\pennes_protocol_avg_target_020_train3 --pulse-mode protocol-averaged --prf-hz 300 --pulse-duty-cycle 0.06 --train-duration-s 0.067 --inter-train-s 2.5 --trains 3 --dt-s 0.005
```

A protocol-averaged sensitivity scan over soft-tissue perfusion and skull conductivity can be run with:

```powershell
python scan_pennes_sensitivity.py --pressure-dir outputs\ct_transducer_stability_target_020\ap30_r35_c8_t55 --output-dir outputs\pennes_sensitivity_target_020_protocol_avg --pulse-mode protocol-averaged
```

The protocol-averaged 12-case scan completed in about 34 seconds. The worst case was zero soft-tissue perfusion with skull conductivity `0.20 W/m/K`, giving max temperature about `37.19 C`, target rise about `0.016 C`, and target-window rise about `0.023 C`.

The old constant-averaged upper-bound scan can still be reproduced with `--pulse-mode averaged`. Its worst case gives max temperature about `41.63 C`, target rise about `0.415 C`, and target-window rise about `0.580 C`. It remains below `42 C` but is intentionally conservative because it applies `6%` duty across the full `5.201 s` interval.

To estimate dose accumulation over repeated paper-like trains, run:

```powershell
python scan_pennes_protocol_dose.py --pressure-dir outputs\ct_transducer_stability_target_020\ap30_r35_c8_t55 --output-dir outputs\pennes_protocol_dose_target_020
```

The default dose scan uses the conservative thermal materials `soft_perfusion_s=0` and skull conductivity `0.20 W/m/K`, then scans `1,3,10,30,60,90,120` trains. In the current quick model, the hottest scanned case is `120` trains with max temperature about `37.87 C`, target rise about `0.124 C`, and margin to `42 C` about `4.13 C`. This is a dose-trend estimate from the cropped quick model, not a medical safety claim.

Generate a case-level QC report that gathers the CT model, current best pressure run, and thermal trend outputs:

```powershell
python generate_case_report.py --model outputs\ct_acoustic_model_3d\acoustic_model_3d.npz --ct-summary outputs\ct_acoustic_model_3d\summary.json --pressure-dir outputs\ct_transducer_stability_target_020\ap30_r35_c8_t55 --thermal-dir outputs\pennes_protocol_avg_target_020_train3 --sensitivity-dir outputs\pennes_sensitivity_target_020_protocol_avg --dose-dir outputs\pennes_protocol_dose_target_020 --output-dir outputs\case_report_079
```

The report is written to `outputs/case_report_079/case_report_079.md` with a machine-readable companion `case_report_079_summary.json`. It is meant for internal review and explicitly separates platform validation from paper-level reproduction or medical safety claims.

Evaluate CT skull threshold sensitivity before rebuilding the acoustic model:

```powershell
python evaluate_ct_segmentation.py --nifti-file data\raw_ct\079.nii --target-index 93,121,63 --entry-index 63,131,63 --output-dir outputs\ct_segmentation_eval_079
```

This writes `outputs/ct_segmentation_eval_079/segmentation_eval.csv` plus per-threshold label previews. For the current target/entry path, `250 HU` and `300 HU` retain a bone crossing, while `400 HU` and above lose the current entry-path skull crossing. The evaluator recommends `250 HU` as a separate rebuild candidate, but it does not overwrite the current model or any best-result outputs.

The `250 HU` candidate can be rebuilt and compared without replacing the current best model:

```powershell
python build_ct_acoustic_model.py --nifti-file data\raw_ct\079.nii --target-dx-mm 1.0 --bone-threshold-hu 250 --target-index 93,121,63 --output-dir outputs\ct_acoustic_model_3d_bone_250
python simulate_kwave_3d_focus.py --model outputs\ct_acoustic_model_3d_bone_250\acoustic_model_3d.npz --entry-plan outputs\ct_entry_offset_scan_target_020_safe\candidate_006\entry_plan.json --output-dir outputs\ct_pressure_compare_bone_250\ap30_r35_c8_t55 --sim-time-us 55 --cycles 8 --quick-lateral-mm 17 --quick-post-target-mm 8 --aperture-mm 30 --radius-mm 35
python compare_pressure_runs.py --baseline-dir outputs\ct_transducer_stability_target_020\ap30_r35_c8_t55 --candidate-dir outputs\ct_pressure_compare_bone_250\ap30_r35_c8_t55 --output-dir outputs\ct_pressure_compare_bone_250
```

In the current comparison, the `250 HU` source mask remains background-only, but target-window peak drops from `2.254 MPa` to `1.645 MPa`, and effective peak distance does not improve. Keep the `300 HU` run as the current best; do not keep tuning bone threshold blindly.

## Multi-case inventory and QC

`inventory_ct_cases.py` scans local CT inputs under `data/raw_ct/` and writes a manifest without downloading data, rebuilding acoustic models, or running k-Wave. It currently recognizes NIfTI files (`.nii`, `.nii.gz`) and DICOM folders:

```powershell
python inventory_ct_cases.py --input-dir data\raw_ct --output-dir data\processed
```

Outputs:

- `data/processed/ct_case_manifest.csv`
- `data/processed/ct_case_manifest.json`

Run lightweight QC for one case before converting it into an acoustic model:

```powershell
python validate_ct_case.py --case-id 079 --ct-path data\raw_ct\079.nii --output-dir outputs\ct_case_qc\079
python validate_ct_case.py --case-id synthetic_case --ct-path data\raw_ct\synthetic_case --output-dir outputs\ct_case_qc\synthetic_case
```

Current local cases:

- `079.nii`: real NIfTI CT case, `512 x 512 x 40`, spacing about `0.390625 x 0.390625 x 5.0 mm`; QC warns that the z spacing is coarse but confirms CT-like intensity and bone voxels.
- `synthetic_case`: small synthetic DICOM test set used to keep the DICOM reader path exercised.

The next multi-case main line is:

```text
case manifest -> new-case QC -> CT acoustic model conversion -> reusable quick pressure run -> multi-case report
```

Build independent acoustic models for all manifest-approved local cases without touching the current 079 best model:

```powershell
python batch_build_ct_models.py --manifest data\processed\ct_case_manifest.json --output-root outputs\ct_acoustic_models_batch
python batch_build_ct_models.py --manifest data\processed\ct_case_manifest.json --output-root outputs\ct_acoustic_models_batch --run
```

The first command is a dry-run plan. The second command writes per-case model folders such as:

- `outputs/ct_acoustic_models_batch/079_bone300_dx1/`
- `outputs/ct_acoustic_models_batch/synthetic_case_bone300_dx1/`

Each case folder includes `acoustic_model_3d.npz`, `summary.json`, preview images, and `build_status.json`. The current default batch settings are `bone-threshold-hu=300`, `target-dx-mm=1.0`, and `max-shape=220`.

Prepare reusable quick-pressure entry/safety packages from the batch models without running k-Wave:

```powershell
python prepare_case_quick_pressure.py --batch-summary outputs\ct_acoustic_models_batch\batch_summary.json --output-dir outputs\case_quick_pressure_plan
```

Outputs:

- `outputs/case_quick_pressure_plan/quick_pressure_plan.csv`
- `outputs/case_quick_pressure_plan/quick_pressure_plan_summary.json`
- `outputs/case_quick_pressure_plan/CASE_ID/entry_plan.json`
- `outputs/case_quick_pressure_plan/CASE_ID/source_safety.json`
- `outputs/case_quick_pressure_plan/CASE_ID/recommended_commands.ps1`

For the current local cases, `079` is ready for a manual smoke run and its source mask is background-only. `synthetic_case` is retained as a DICOM reader test and is marked with geometry/source warnings because it is not a realistic skull case.

Run the prepared `079` smoke case manually and summarize smoke outputs:

```powershell
python simulate_kwave_3d_focus.py --model outputs\ct_acoustic_models_batch\079_bone300_dx1\acoustic_model_3d.npz --entry-plan outputs\case_quick_pressure_plan\079\entry_plan.json --output-dir outputs\case_quick_pressure_runs\079_smoke --sim-time-us 45 --cycles 6 --quick-lateral-mm 17 --quick-post-target-mm 8 --aperture-mm 25 --radius-mm 30
python analyze_kwave_3d_focus.py --input-dir outputs\case_quick_pressure_runs\079_smoke
python summarize_quick_pressure_runs.py --plan-summary outputs\case_quick_pressure_plan\quick_pressure_plan_summary.json --runs-root outputs\case_quick_pressure_runs
```

Current smoke summary:

- `079`: `kwave_ok`, source mask remains background-only, target-window peak about `0.013 MPa`, effective peak distance about `55.0 mm`.
- `synthetic_case`: not run because it is a geometry-warning DICOM test case.

The `079_smoke` run validates the multi-case plumbing from batch model to k-Wave output. It is not tuned and is expected to be much weaker at the target than the earlier hand-optimized `target_020 + ap30/r35/cycles8/t55` result.

Prepare a per-case refinement plan for weak smoke runs without launching k-Wave:

```powershell
python prepare_case_refinement_plan.py --run-summary outputs\case_quick_pressure_runs\quick_pressure_run_summary.json --output-dir outputs\case_refinement_plan
```

For `079`, this refinement planner recovers the earlier useful target candidate `[93,121,63]` from the batch model and writes:

- `outputs/case_refinement_plan/079/target_candidates.csv`
- `outputs/case_refinement_plan/079/entry_candidates.csv`
- `outputs/case_refinement_plan/079/best_entry_plan.json`
- `outputs/case_refinement_plan/079/source_safety.json`
- `outputs/case_refinement_plan/079/recommended_refinement_commands.ps1`

The generated recommendation is geometry/safety-ranked and does not claim pressure optimality. The top geometry candidate is source-safe and light; the known pressure-tuned `(10,0)` offset remains visible in `entry_candidates.csv` as a safe comparison candidate.

Validate the pressure-tuned refinement candidate `(10,0)` as a single direct k-Wave run:

```powershell
python simulate_kwave_3d_focus.py --model outputs\ct_acoustic_models_batch\079_bone300_dx1\acoustic_model_3d.npz --entry-plan outputs\case_refinement_plan\079\candidate_006\entry_plan.json --output-dir outputs\case_refinement_runs\079_candidate_006_offset_10_0 --sim-time-us 55 --cycles 8 --quick-lateral-mm 17 --quick-post-target-mm 8 --aperture-mm 30 --radius-mm 35
python analyze_kwave_3d_focus.py --input-dir outputs\case_refinement_runs\079_candidate_006_offset_10_0
python summarize_refinement_runs.py --runs-root outputs\case_refinement_runs --case-id 079 --candidate-id candidate_006 --run-dir outputs\case_refinement_runs\079_candidate_006_offset_10_0 --entry-plan outputs\case_refinement_plan\079\candidate_006\entry_plan.json
```

This recovered the hand-tuned quick result from the batch/refinement path: `target_window_peak_mpa=2.254`, about `169x` the default smoke result, with source mask still background-only. This confirms the reusable multi-case pipeline can reproduce the known 079 tuned route.

Generate the current multi-case stage report without running new simulations:

```powershell
python generate_multicase_stage_report.py --manifest data\processed\ct_case_manifest.json --batch-summary outputs\ct_acoustic_models_batch\batch_summary.json --quick-plan outputs\case_quick_pressure_plan\quick_pressure_plan_summary.json --smoke-summary outputs\case_quick_pressure_runs\quick_pressure_run_summary.json --refinement-plan outputs\case_refinement_plan\refinement_plan_summary.json --refinement-summary outputs\case_refinement_runs\refinement_run_summary.json --output-dir outputs\multicase_stage_report
```

Report outputs:

- `outputs/multicase_stage_report/multicase_stage_report.md`
- `outputs/multicase_stage_report/multicase_stage_report_summary.json`
- `outputs/multicase_stage_report/multicase_case_table.csv`

The report documents that there is currently one real CT case (`079`) and one DICOM reader test case (`synthetic_case`). It is intended for internal project review and keeps the distinction between reusable platform validation and paper-level reproduction explicit.

登记公开 CT 数据源，并生成 dry-run 下载计划；这一步不下载任何文件：

```powershell
python catalog_public_ct_sources.py --output-dir data\processed
python plan_public_ct_download.py --sources data\processed\public_ct_sources.json --output-dir outputs\public_ct_download_plan
```

输出：

- `data/processed/public_ct_sources.csv`
- `data/processed/public_ct_sources.json`
- `outputs/public_ct_download_plan/download_plan.md`
- `outputs/public_ct_download_plan/download_plan.json`

这一步故意保持“无下载”。后续只有在选定小体积、许可证清晰的 DICOM 或 NIfTI 病例后，才把公开数据放到 `data/raw_ct/public/<case_id>/`。NRRD 数据源会标记为 `requires_format_support`，需要先单独实现读取或转换。

生成下一例公开 CT 病例的候选 shortlist：

```powershell
python shortlist_public_ct_cases.py --sources data\processed\public_ct_sources.json --output-dir outputs\public_ct_case_shortlist
```

输出：

- `outputs/public_ct_case_shortlist/public_ct_case_shortlist.md`
- `outputs/public_ct_case_shortlist/public_ct_case_shortlist.csv`
- `outputs/public_ct_case_shortlist/public_ct_case_shortlist.json`

当前第一推荐公开病例目标是 TCIA Head-Neck Cetuximab 中手动选择的一个 CT series：patient `0522c0027`、study date `2000-05-17`、series `5577`。这只是下载目标建议，仍需在 TCIA/NBIA 中人工选择，不能批量下载完整 collection。

为这个公开病例目标准备下载前/下载后的接入守门检查：

```powershell
python prepare_public_case_import.py --case-id hn_cetuximab_0522c0027_series5577 --output-dir outputs\public_case_import
```

在本地放入文件之前，该命令会写出 `pending_manual_download` 状态。手动把单个 CT series 放入 `data/raw_ct/public/hn_cetuximab_0522c0027_series5577/` 后，重新运行同一命令，它会执行轻量 DICOM/CT QC，并生成后续 manifest、batch build、quick pressure 准备命令。公开病例的 manifest 会写到 `data/processed/public_import/`，避免覆盖当前本地 `079` manifest。

为选中的单个 TCIA/NBIA series 生成中文手动下载指南：

```powershell
python write_tcia_download_guide.py --import-status outputs\public_case_import\hn_cetuximab_0522c0027_series5577\import_status.json --output-dir outputs\public_tcia_download_guide
```

输出：

- `outputs/public_tcia_download_guide/tcia_download_guide.md`
- `outputs/public_tcia_download_guide/tcia_download_checklist.md`
- `outputs/public_tcia_download_guide/post_download_commands.ps1`
- `outputs/public_tcia_download_guide/guide_summary.json`

这份指南是人工操作指南：它明确记录 `0522c0027 / 2000-05-17 / series 5577` 这个目标，警告不要下载完整 collection，并且只包含下载后的本地检查命令。

如果从平台下载到的是 GC/Gen3 manifest CSV，而不是 DICOM zip 本体，先复核 manifest：

```powershell
python review_public_gc_manifest.py --manifest "data\processed\GC File Manifest 2026-05-17 13-34-32.csv" --output-dir outputs\public_gc_manifest_review
```

输出：

- `outputs/public_gc_manifest_review/gc_manifest_review.md`
- `outputs/public_gc_manifest_review/gc_manifest_review.json`
- `outputs/public_gc_manifest_review/post_manifest_next_commands.ps1`

当前 GC manifest 只包含一个 CT DICOM zip：`1.3.6.1.4.1.22213.2.26564.2.zip`，大小约 `31.565 MB`，Participant ID 为 `0522c0027`。注意 `Study Access=Controlled`，后续真实下载可能需要授权。

下载到 zip 后，先用本地 zip 守门脚本检查完整性；默认只检查，不解压：

```powershell
python prepare_public_zip_import.py --manifest-review outputs\public_gc_manifest_review\gc_manifest_review.json --output-dir outputs\public_zip_import
```

默认期望 zip 放在：

```text
data\raw_ct\public_downloads\1.3.6.1.4.1.22213.2.26564.2.zip
```

如果大小和 MD5 都匹配，再显式加 `--extract` 解压到：

```text
data\raw_ct\public\hn_cetuximab_0522c0027_series5577\
```

Visible Human Head CT 的 Dataverse zip 已接入为两个公开病例：

```powershell
python prepare_visible_human_zip_import.py --zip-path data\raw_ct\dataverse_files.zip --output-dir outputs\visible_human_zip_import --extract
python inventory_ct_cases.py --input-dir data\raw_ct\public --output-dir data\processed\public_import
python batch_build_ct_models.py --manifest data\processed\public_import\ct_case_manifest.json --output-root outputs\ct_acoustic_models_public --run
python prepare_case_quick_pressure.py --batch-summary outputs\ct_acoustic_models_public\batch_summary.json --output-dir outputs\case_quick_pressure_plan_public
```

当前公开病例：

- `visible_human_female_head_1mm`：234 张 CT DICOM，spacing `1.0 x 1.0 x 1.0 mm`，QC `ok`
- `visible_human_male_head_1mm`：245 张 CT DICOM，spacing `1.0 x 1.0 x 1.0 mm`，QC `ok`

两个病例已经完成 CT 声学模型转换，输出在 `outputs/ct_acoustic_models_public/`。默认 quick pressure plan 已生成，但 source mask 有少量软组织重叠 warning，因此下一步应先做 source standoff / entry offset 安全调参，不直接跑 k-Wave。

Visible Human 公开病例的源面安全扫描和单例 quick smoke：

```powershell
python scan_visible_human_safe_entries.py --models-root outputs\ct_acoustic_models_public --output-dir outputs\visible_human_source_safety_scan
python simulate_kwave_3d_focus.py --model outputs\ct_acoustic_models_public\visible_human_female_head_1mm_bone300_dx1\acoustic_model_3d.npz --entry-plan outputs\visible_human_source_safety_scan\visible_human_female_head_1mm\candidate_031\entry_plan.json --output-dir outputs\visible_human_quick_smoke_runs\visible_human_female_head_1mm_best_safe --sim-time-us 45 --cycles 6 --quick-lateral-mm 17 --quick-post-target-mm 8 --aperture-mm 25 --radius-mm 30
python analyze_kwave_3d_focus.py --input-dir outputs\visible_human_quick_smoke_runs\visible_human_female_head_1mm_best_safe
python summarize_visible_human_smoke_runs.py --runs-root outputs\visible_human_quick_smoke_runs
```

当前结果：`visible_human_female_head_1mm / candidate_031` 的 source mask 完全在背景区（`{"0":97}`），quick smoke 成功生成压力场和焦域指标。目标窗口峰值约 `0.0035 MPa`，有效峰值距目标约 `97.7 mm`，说明这只是公开病例链路 smoke 验证，还需要后续时间窗、target/entry 和换能器参数调优。

对同一安全候选延长时间窗到 `85 us` 后，结果与 `45 us` 基本一致：

```powershell
python simulate_kwave_3d_focus.py --model outputs\ct_acoustic_models_public\visible_human_female_head_1mm_bone300_dx1\acoustic_model_3d.npz --entry-plan outputs\visible_human_source_safety_scan\visible_human_female_head_1mm\candidate_031\entry_plan.json --output-dir outputs\visible_human_quick_smoke_runs\visible_human_female_head_1mm_candidate031_c6_t85 --sim-time-us 85 --cycles 6 --quick-lateral-mm 17 --quick-post-target-mm 8 --aperture-mm 25 --radius-mm 30
python summarize_visible_human_smoke_runs.py --runs-root outputs\visible_human_quick_smoke_runs --case-run visible_human_female_head_1mm_t45=visible_human_female_head_1mm_best_safe --case-run visible_human_female_head_1mm_t85=visible_human_female_head_1mm_candidate031_c6_t85
```

`t85` 的 `nt=512`、source mask 仍为 `{"0":97}`，但目标窗口峰值仍约 `0.0035 MPa`，有效峰值距目标仍约 `97.7 mm`。因此当前问题不是传播时间窗不足，下一步应做 Visible Human 的 target/entry 或 aperture/radius 调参。

Visible Human female 的第一轮 target refinement 选择了 `target_037=[110,122,40]`，并在 `standoff=32 mm`、`entry offset=(0,10) mm` 下找到 source-safe 候选：

```powershell
python select_ct_target_candidates.py --model outputs\ct_acoustic_models_public\visible_human_female_head_1mm_bone300_dx1\acoustic_model_3d.npz --source-standoff-mm 28 --output-dir outputs\visible_human_refinement_plan\visible_human_female_head_1mm
python scan_ct_entry_positions.py --model outputs\ct_acoustic_models_public\visible_human_female_head_1mm_bone300_dx1\acoustic_model_3d.npz --target-index 110,122,40 --source-standoff-mm 32 --y-offsets-mm=-10,0,10 --z-offsets-mm=-10,0,10 --output-dir outputs\visible_human_refinement_plan\visible_human_female_head_1mm_target_037_entry_scan_s32
python simulate_kwave_3d_focus.py --model outputs\ct_acoustic_models_public\visible_human_female_head_1mm_bone300_dx1\acoustic_model_3d.npz --entry-plan outputs\visible_human_refinement_plan\visible_human_female_head_1mm_target_037_entry_scan_s32\candidate_005\entry_plan.json --output-dir outputs\visible_human_quick_smoke_runs\visible_human_female_head_1mm_target037_s32_candidate005_c6_t65 --sim-time-us 65 --cycles 6 --quick-lateral-mm 17 --quick-post-target-mm 8 --aperture-mm 25 --radius-mm 30
```

该候选 source mask 仍为纯背景（`{"0":95}`），但目标窗口峰值约 `0.0029 MPa`，低于默认候选的 `0.0035 MPa`；有效峰值距目标约 `77.1 mm`，比默认候选的 `97.7 mm` 更近但仍明显偏离目标。结论是：`target_037` 当前只证明了安全 refinement 流程可运行，尚未解决 Visible Human 聚焦弱的问题。下一步应优先比较更多目标点或做小范围 aperture/radius 调参，而不是继续延长同一时间窗。

Visible Human female 多目标安全筛选进一步比较了 `target_055,target_074,target_040,target_004,target_028`：

```powershell
python scan_visible_human_target_refinement.py --model outputs\ct_acoustic_models_public\visible_human_female_head_1mm_bone300_dx1\acoustic_model_3d.npz --target-candidates outputs\visible_human_refinement_plan\visible_human_female_head_1mm\target_candidates.csv --skip-targets target_037 --top-targets 5 --output-dir outputs\visible_human_refinement_plan\visible_human_female_head_1mm_multi_target_scan
python simulate_kwave_3d_focus.py --model outputs\ct_acoustic_models_public\visible_human_female_head_1mm_bone300_dx1\acoustic_model_3d.npz --entry-plan outputs\visible_human_refinement_plan\visible_human_female_head_1mm_multi_target_scan\target_074\target_074_s40_y0_z10\entry_plan.json --output-dir outputs\visible_human_quick_smoke_runs\visible_human_female_head_1mm_multi_target_best --sim-time-us 65 --cycles 6 --quick-lateral-mm 17 --quick-post-target-mm 8 --aperture-mm 25 --radius-mm 30
```

本轮推荐并验证了 `target_074=[118,122,48]`、`standoff=40 mm`、`entry offset=(0,10) mm`。source mask 仍为纯背景（`{"0":95}`），目标窗口峰值升至约 `0.0092 MPa`，高于默认 `t85` 与 `target_037`；但有效峰值距目标约 `111.9 mm`，更远，且 source-to-target 到达时间估计约 `81.8 us`，本次按 quick 上限只跑 `65 us`。因此它是“目标窗口改善但尚未聚焦”的候选，下一步如果继续该路线，应优先对同一候选跑更长时间窗（例如 `90 us`）或选择 source-to-target 更短的目标候选。

`target_074` 的 `90 us` 时间窗复核已完成：

```powershell
python simulate_kwave_3d_focus.py --model outputs\ct_acoustic_models_public\visible_human_female_head_1mm_bone300_dx1\acoustic_model_3d.npz --entry-plan outputs\visible_human_refinement_plan\visible_human_female_head_1mm_multi_target_scan\target_074\target_074_s40_y0_z10\entry_plan.json --output-dir outputs\visible_human_quick_smoke_runs\visible_human_female_head_1mm_target074_s40_t90 --sim-time-us 90 --cycles 6 --quick-lateral-mm 17 --quick-post-target-mm 8 --aperture-mm 25 --radius-mm 30
```

`90 us` 与 `65 us` 指标完全一致：`target_window_peak_mpa≈0.0092`、`effective_peak_to_target_distance_mm≈111.9`，source mask 仍为纯背景（`{"0":95}`）。因此 `target_074` 的目标区偏弱不是时间窗不足导致。下一步应转向 source-to-target 更短的候选（例如 `target_040_s28_y0_z0`）或换能器/入射方向调参，而不是继续延长同一候选时间窗。

更短路径候选 `target_040_s28_y0_z0` 已完成单次 quick 验证：

```powershell
python simulate_kwave_3d_focus.py --model outputs\ct_acoustic_models_public\visible_human_female_head_1mm_bone300_dx1\acoustic_model_3d.npz --entry-plan outputs\visible_human_refinement_plan\visible_human_female_head_1mm_multi_target_scan\target_040\target_040_s28_y0_z0\entry_plan.json --output-dir outputs\visible_human_quick_smoke_runs\visible_human_female_head_1mm_target040_s28_y0_z0_t65 --sim-time-us 65 --cycles 6 --quick-lateral-mm 17 --quick-post-target-mm 8 --aperture-mm 25 --radius-mm 30
```

该候选 source mask 纯背景（`{"0":97}`），目标窗口峰值约 `0.0030 MPa`，有效峰值距目标约 `79.1 mm`。它比 `target_074` 的有效峰值距离更近，但目标窗口声压低；同时仍略差于 `target_037` 的有效峰值距离约 `77.1 mm`。因此当前左侧 `left_x` 几何目标点 quick 验证未找到明确聚焦改善，后续应转向 aperture/radius 调参或扩展到其他入射方向，而不是继续盲跑同类候选。


## 证据驱动执行纪律

项目已新增真实根目录规则文件：

```text
AGENTS.md
```

新模块实现前必须先生成 evidence brief。执行前证据和执行后反馈必须分开：

```text
outputs/evidence_briefs/<module>/evidence_brief.md
outputs/evidence_briefs/<module>/evidence_brief.json
outputs/evidence_briefs/<module>/gap_feedback.md
outputs/evidence_briefs/<module>/gap_feedback.json
```

当前已生成 k-Wave 数值质量 brief：

```powershell
python generate_module_evidence_brief.py --module kwave_simulation_quality --output-dir outputs\evidence_briefs\kwave_simulation_quality
```

该 brief 明确：quick 只能用于 screening；standard/paper-grade 必须记录 PPW、PML、CFL、grid size、runtime、backend、memory estimate 和网格收敛/边界风险。下一步应先实现 `simulation_presets.json` 和 summary metadata，再考虑任何新的 standard k-Wave 运行。

当前已实现 simulation preset / dry-run 质量层：

```text
simulation_presets.json
simulation_quality.py
outputs/evidence_briefs/kwave_simulation_quality/gap_feedback.md
outputs/quality_dry_runs/079_candidate_006/quality_dry_run_summary.json
outputs/quality_dry_runs/freefield_ap25_r30/quality_dry_run_summary.json
```

`--dry-run-quality` 只估算 preset、PPW、PML、CFL、grid size、nt/dt、backend、device 和 memory estimate，不调用 k-Wave，也不生成 `pressure_max_mpa.npz`。

已完成第一个自由场 `standard` sanity run：

```text
outputs/freefield_standard_sanity/ap25_r30_f500_standard/
```

该 run 使用 Gao baseline `aperture=25 mm`、`radius=30 mm`、`frequency=500 kHz`、`source_pressure=1 MPa`、均匀水介质，`simulation_quality.quality_level=standard`、`is_paper_grade=false`。结果用于验证 preset/summary 链路，不代表 paper-grade 复现，也不是经颅 in-situ pressure。

## k-Wave 稳定运行入口

为避免 Windows `Start-Process` 的 `Path/PATH` 冲突和 PowerShell Job 权限 warning，后续 k-Wave 长任务优先使用：

```text
kwave_run_healthcheck.py
run_kwave_command.py
```

默认 runner 只生成计划，不执行 k-Wave：

```powershell
python run_kwave_command.py --script simulate_freefield_transducer.py --output-dir outputs\kwave_runner_tests\freefield_standard_plan --preset standard --aperture-mm 25 --radius-mm 30 --frequency-khz 500 --source-pressure-mpa 1 --medium water --dx-mm 1.0
```

只有显式追加 `--execute` 才会真实运行；runner 会先执行 `--dry-run-quality`，并记录 stdout、stderr 和 `runner_status.json`。

## 自由场网格收敛 dry-run 计划

已新增自由场网格收敛计划层，用来在真实 finer-grid k-Wave 前先比较 `dx / PPW / grid / nt / memory / runtime risk`。本阶段不运行 k-Wave，也不生成压力场。

```powershell
python generate_module_evidence_brief.py --module freefield_grid_convergence --output-dir outputs\evidence_briefs\freefield_grid_convergence
python plan_freefield_grid_convergence.py --aperture-mm 25 --radius-mm 30 --frequency-khz 500 --source-pressure-mpa 1 --medium water --dx-mm 1.0,0.75,0.5 --preset standard --output-dir outputs\freefield_grid_convergence_plan\ap25_r30_f500
```

当前 dry-run 结论：`dx=0.75 mm` 是下一次最多单个 finer-grid sanity run 的推荐候选，PPW 约 `3.95`，相对工作量约 `3.17x`；`dx=0.5 mm` 相对工作量约 `14.93x`，暂时只作为风险估算点。任何真实运行都必须通过 `run_kwave_command.py --execute`，并保留 2 分钟检查点和硬停止条件。该计划仍不是 paper-grade 结果。

已完成一个 `dx=0.75 mm` 自由场 finer-grid sanity：

```text
outputs/freefield_grid_convergence_runs/ap25_r30_f500_dx0.75/
outputs/freefield_grid_convergence_runs/freefield_grid_convergence_comparison.md
```

结果仍为 `standard`，`is_paper_grade=false`。PPW 从 `2.96` 提高到约 `3.95`；effective peak 从约 `6.168 MPa` 变为约 `5.719 MPa`，target-window peak 从约 `5.771 MPa` 变为约 `5.425 MPa`，effective peak 到几何焦点距离从约 `7.0 mm` 变为约 `7.5 mm`。整体焦点位置可解释，但 runtime 实际约 `854.6 s`，约为 `dx=1.0 mm` 的 `6.24x`，高于 dry-run 工作量估计，因此后续不要直接跑 `dx=0.5 mm`；应先做 PML/边界复核或重新估算运行预算。

已新增自由场 PML/边界 dry-run 计划层：

```powershell
python generate_module_evidence_brief.py --module freefield_pml_boundary_review --output-dir outputs\evidence_briefs\freefield_pml_boundary_review
python plan_freefield_pml_boundary_review.py --aperture-mm 25 --radius-mm 30 --frequency-khz 500 --source-pressure-mpa 1 --medium water --dx-mm 0.75 --pml-size 8,12,16 --preset standard --output-dir outputs\freefield_pml_boundary_plan\ap25_r30_f500_dx075
```

当前 PML dry-run 结论：`pml=12` 是下一次最多单个边界 sanity run 的推荐候选，PML 厚度约 `9.0 mm`，grid `93x67x67`，相对工作量约 `1.04x`；`pml=16` 相对工作量约 `1.09x`。本阶段没有运行 k-Wave，也没有生成压力场。

已完成一个 `dx=0.75 mm, pml=12` 自由场边界 sanity：

```text
outputs/freefield_pml_boundary_runs/ap25_r30_f500_dx0.75_pml12/
outputs/freefield_pml_boundary_runs/freefield_pml_boundary_comparison.md
```

与 `pml=8` 的 `dx=0.75 mm` 结果相比，effective peak 变化约 `0.00018%`，target-window peak 变化约 `0.00054%`，焦点距离和 FWHM 无变化。该结果说明当前小型自由场模型对 `pml=8 -> 12` 没有明显 focal metric 敏感性信号；但它仍是 `standard` 边界 sanity，不是 paper-grade，也不是完整边界反射能量分析。

自由场阶段已收束为质量报告：

```text
outputs/freefield_quality_report/freefield_quality_report.md
outputs/freefield_quality_report/freefield_quality_summary.json
```

报告结论是：自由场 standard sanity、finer-grid sanity 和 PML boundary sanity 已足够支持“停止追加自由场单 case，回到 079 CT standard-review 规划”。当前仍不是 paper-grade，不建议直接跑 `dx=0.5 mm`。

## 079 CT Standard-Review 计划包

已按证据驱动流程为 079 当前有效候选生成 CT standard-review 计划包。本阶段只做 evidence brief、dry-run quality 和推荐 runner 命令，不运行新的 CT k-Wave，不生成新的压力场。

```text
outputs/evidence_briefs/ct_standard_review/evidence_brief.md
outputs/evidence_briefs/ct_standard_review/gap_feedback.md
outputs/ct_standard_review_plan/079_candidate_006/ct_standard_review_plan.md
outputs/ct_standard_review_plan/079_candidate_006/quality_dry_run/quality_dry_run_summary.json
outputs/ct_standard_review_plan/079_candidate_006/recommended_runner_command.ps1
```

当前 dry-run 标记为 `preset=standard`、`is_paper_grade=false`，PPW 约 `3.00`，grid 为 `66x45x35`，`nt=770`，source mask 仍为背景-only。历史 079 candidate_006 参考结果为 target-window peak 约 `2.254 MPa`，但该历史 summary 缺少统一 `simulation_quality` 字段。下一步若继续，只建议通过生成的 runner 命令执行最多一个 079 CT standard-review run，并保持 2 分钟检查点和 30 分钟硬停止。

## Continuous CT-HU Mapping 状态纠偏

已新增 continuous mapping reconciliation 包，用来收口 `continuous_skull` 的状态冲突：

```text
outputs/evidence_briefs/continuous_mapping_reconciliation/evidence_brief.md
outputs/ct_hu_mapping_reconciliation/state_reconciliation_report.md
outputs/ct_hu_mapping_reconciliation/implemented_formula_audit.md
outputs/ct_hu_mapping_reconciliation/output_inventory.csv
outputs/ct_hu_mapping_reconciliation/superseding_notice.md
```

当前 authoritative 状态：`continuous_skull` 已有 exploratory model 和 exploratory standard comparison run，但仍不是 validated baseline。`acoustic_mapping_profiles/continuous_skull.json` 继续保持 `review_pending_do_not_use_as_default`。既有 `outputs/continuous_vs_binary_comparison/comparison_report.md` 必须与 `superseding_notice.md` 一起阅读，不能把其中 “约 0.3% 内差异” 写成 paper-grade、最终物理结论或默认 profile 证据。

下一步主线应是：源码/论文公式抽取 -> model-build-only validation -> profile notes 与 summary schema 一致性修复。完成这些前，不继续做新的 continuous CT pressure 对照。

## Continuous CT-HU Mapping 公式来源抽取

已新增 continuous mapping 公式来源抽取包：

```text
outputs/evidence_briefs/continuous_mapping_formula_extraction/evidence_brief.md
outputs/ct_hu_mapping_formula_extraction/formula_source_matrix.csv
outputs/ct_hu_mapping_formula_extraction/formula_extraction_report.md
outputs/ct_hu_mapping_formula_extraction/missing_evidence_checklist.md
```

当前结论：本地证据只支持“CT-derived skull heterogeneity 是合理方向”，还没有锁定 `sound_speed`、`density`、`alpha`、`HU clamp` 的 primary formula。当前 `continuous_property_volume()` 是 exploratory engineering implementation，不是 validated source formula。下一步应优先抽取 PRESTUS/BabelBrain 源码里的 CT-to-acoustic 函数，或先做 model-build-only validation；仍不建议继续跑 pressure。

## PRESTUS/BabelBrain 源码公式抽取

已将公开源码下载到项目内作为只读参考：

```text
data/source_code_refs/PRESTUS_source/
data/source_code_refs/BabelBrain_source/
outputs/source_formula_extraction/source_download_summary.json
```

已生成源码命中和关键候选报告：

```text
outputs/evidence_briefs/source_code_formula_extraction/evidence_brief.md
outputs/source_formula_extraction/source_formula_hits.csv
outputs/source_formula_extraction/source_formula_review.md
outputs/source_formula_extraction/key_formula_candidates.md
```

关键发现：

- PRESTUS 提供 `medium_pct_density.m`、`medium_pct_soundspeed.m`、`medium_pct_attenuation.m`，包含 `k-plan`、`k-wave`、`marsac`、`aubry`、`mueller` 等 mapping route。
- BabelBrain 提供 `HUtoDensityKWave()`、porosity-to-density/sound-speed/attenuation、`HUtoAttenuationWebb()` 等候选函数。
- 当前 fus-sim `continuous_skull` 线性插值更接近 PRESTUS `marsac` 的 density/speed 方向，但 attenuation 还不能直接沿用当前 `4-12 dB/MHz/cm` 线性范围。

下一步建议新建 source-backed draft profile，并先做 model-build-only validation，不继续跑 pressure。

## Source-backed Mapping Draft Profile

已新增 PRESTUS-backed draft profile，并只做模型构建级验证：

```text
acoustic_mapping_profiles/prestus_marsac_mueller_draft.json
outputs/ct_acoustic_model_3d_profile_prestus_marsac_mueller_draft/
outputs/ct_mapping_model_build_validation/prestus_marsac_mueller_079/model_build_validation.md
```

该 profile 明确为 `review_pending_model_build_only_do_not_use_as_default`。density/sound speed 采用 PRESTUS Marsac-style route；attenuation 采用 PRESTUS Mueller-style draft route。079 模型构建结果显示 skull sound speed 约 `1500-3360 m/s`，skull density 约 `1000-2100 kg/m3`，skull alpha 约 `8.0-17.4 dB/MHz/cm`。这说明 draft route 已能构建 property volume，但 attenuation 和低 density/speed 分布仍需人工复核；当前不允许直接进入 pressure simulation。

## 079 Candidate 006 Entry Path Property Profile

已生成 079 `candidate_006` 的路径属性剖面：

```text
outputs/evidence_briefs/entry_path_property_profile/evidence_brief.md
outputs/entry_path_property_profiles/079_candidate_006/entry_path_profile.csv
outputs/entry_path_property_profiles/079_candidate_006/entry_path_property_report.md
outputs/entry_path_property_profiles/079_candidate_006/entry_path_property_summary.json
```

该报告比较 `simple_hu300`、`continuous_skull`、`prestus_marsac_mueller` 三个模型在同一 source/entry/target 路径上的属性。关键发现：当前入射路径上的 skull HU 较低，约 `311-375 HU`。二值模型将其固定为 `2800 m/s`、`1900 kg/m3`、alpha `8`；`continuous_skull` 给出约 `2219 m/s`、`1513 kg/m3`、alpha `4.15`；PRESTUS draft 给出约 `1535 m/s`、`1021 kg/m3`、alpha `17.31`。这说明 draft route 在低 HU 入口骨段上会产生接近水/软组织的声速密度，但同时给出较高衰减，必须先做 attenuation 单位审计和路径可视化，不应直接跑 pressure。

## Alpha Unit Audit

已新增 attenuation 单位审计：

```text
outputs/evidence_briefs/alpha_unit_audit/evidence_brief.md
outputs/alpha_unit_audit/alpha_unit_matrix.csv
outputs/alpha_unit_audit/alpha_unit_audit_report.md
```

结论：`prestus_marsac_mueller_draft` 当前被标记为 `blocked_for_pressure_until_alpha_semantics_resolved`。PRESTUS `mueller` route 的代码逻辑清楚：先计算 500 kHz 下的 alpha(f)，再按 `alpha(f) / 0.5^alpha_power` 转成 alpha0；但 fus-sim 当前 CT 模型只保存 `alpha_coeff`，没有在 NPZ/summary 中保存 `alpha_power` 或 alpha 语义。因此在补齐 alpha semantics 前，不应使用 draft profile 跑 pressure。

## Alpha Semantics Metadata

已补齐 alpha semantics metadata 链路：

```text
outputs/evidence_briefs/alpha_semantics_metadata/evidence_brief.md
outputs/alpha_semantics_metadata_validation/079_prestus_marsac_mueller_draft/
outputs/alpha_semantics_metadata_validation/079_prestus_marsac_mueller_draft_validation/model_build_validation.md
```

`prestus_marsac_mueller_draft.json` 现在包含 `alpha_semantics`，新构建的验证模型在 `summary.json` 和 `acoustic_model_3d.npz` 中均记录 `alpha_power=1.0`、`alpha_coeff_kind=alpha0_prefactor`、`alpha_unit_semantics=dB/MHz/cm`、`alpha_source_route=PRESTUS medium_pct_attenuation.m mueller route`。这只是 intended semantics metadata，不等于 pressure validation；draft profile 仍保持 review pending。

## k-Wave Alpha Power Interface Audit

已完成只读接口审计：

```text
outputs/evidence_briefs/kwave_alpha_power_interface_audit/evidence_brief.md
outputs/kwave_alpha_power_interface_audit/interface_audit_report.md
outputs/kwave_alpha_power_interface_audit/source_inventory.csv
```

结论：`simulate_kwave_3d_focus.py` 已经从 `.npz` 读取 `alpha_power` 并传入 `kWaveMedium`；本地 k-wave-python 源码也确认 `alpha_coeff` 与 `alpha_power` 是配套接口。但 `prestus_marsac_mueller_draft` 的 `alpha_power=1.0` 仍需要 `alpha_mode` / dispersion 语义审计，因此该 profile 仍不能用于 pressure simulation。下一步应先补 `alpha_mode` 和 alpha semantics 的 dry-run/summary 字段，不应直接跑 draft pressure。

## Alpha Semantics Propagation

已完成 alpha semantics 字段传播：

```text
outputs/evidence_briefs/alpha_semantics_propagation/evidence_brief.md
outputs/evidence_briefs/alpha_semantics_propagation/gap_feedback.md
outputs/alpha_semantics_propagation_dry_run/079_prestus_candidate006/quality_dry_run_summary.json
```

`simulate_kwave_3d_focus.py` 现在会在 dry-run/model summary 中记录 `alpha_power`、`alpha_mode`、`alpha_coeff_kind`、`alpha_source_route`、`alpha_semantics_status` 和 `pressure_allowed_by_alpha_semantics`。当前 `prestus_marsac_mueller_draft` 的 dry-run 结果仍为 `pressure_allowed_by_alpha_semantics=false`，因为 `alpha_power=1.0` 且 `alpha_mode` 还没有证据决定；因此仍不允许直接跑 draft pressure。

## Alpha Mode Policy Review

已完成 `alpha_power=1.0` 的 `alpha_mode/no_dispersion` 只读策略审查：

```text
outputs/evidence_briefs/alpha_mode_policy_review/evidence_brief.md
outputs/alpha_mode_policy_review/policy_review.md
outputs/alpha_mode_policy_review/evidence_inventory.csv
```

结论：k-wave-python 支持 `alpha_mode=no_dispersion` 来规避 `alpha_power=1` 的 dispersion 问题，但这不是自动物理真值；PRESTUS 源码还提供了 `fit_alpha_power` 路线，默认固定到 `alpha_power=2` 并重拟合 alpha0。当前推荐策略是 `keep_blocked`，不修改现有 `prestus_marsac_mueller_draft`，也不运行 pressure。下一步如果继续 source-backed mapping，应新建 dry-run-only 的实验 profile 计划，而不是覆盖当前 draft。

## Source-backed Alpha Profile Options

已生成两条 source-backed alpha 路线的草案和计划：

```text
outputs/evidence_briefs/source_backed_alpha_profile_options/evidence_brief.md
outputs/source_backed_alpha_profile_options/profile_option_report.md
outputs/source_backed_alpha_profile_options/profile_drafts/
```

两个草案都只放在 `outputs/` 下，没有写入主 `acoustic_mapping_profiles/`：

- `prestus_marsac_mueller_no_dispersion_experimental.json`：实验性 `alpha_mode=no_dispersion` 路线，只允许后续 isolated model-build-only validation，不允许 pressure。
- `prestus_fit_alpha_power_2_plan_only.json`：PRESTUS `fitPowerLawParamsMulti` 路线的 plan-only 草案，必须先迁移公式，不能只改 `alpha_power=2`。

当前仍未运行 k-Wave，未重建 CT，未放行 pressure simulation。

## No-dispersion Model-build Validation

已对 no-dispersion experimental profile 草案做 isolated model-build-only validation：

```text
outputs/ct_acoustic_model_3d_profile_no_dispersion_experimental/
outputs/no_dispersion_model_build_validation/079_no_dispersion_vs_draft/model_build_validation.md
outputs/no_dispersion_model_build_validation/079_no_dispersion_dry_run/quality_dry_run_summary.json
```

验证结果：新模型和 dry-run 均记录 `alpha_power=1.0`、`alpha_mode=no_dispersion`、`alpha_coeff_kind=alpha0_prefactor`、`alpha_semantics_status=experimental_dry_run_only_no_pressure`，并保持 `pressure_allowed_by_alpha_semantics=false`。本阶段未运行 k-Wave、未生成 pressure field；该模型不能作为 validated baseline。

## Source-backed Alpha Stage Report

已生成 source-backed alpha mapping 阶段收口报告：

```text
outputs/evidence_briefs/source_backed_alpha_stage_report/evidence_brief.md
outputs/source_backed_alpha_stage_report/source_backed_alpha_stage_report.md
outputs/source_backed_alpha_stage_report/source_backed_alpha_stage_summary.json
outputs/evidence_briefs/source_backed_alpha_stage_report/gap_feedback.md
```

当前判断：

- `simple_hu300` 仍是当前可复现 baseline。
- `prestus_fit_alpha_power_2` 和 `no_dispersion` 仍是 exploratory / review-pending 路线，不能自动升级为默认 profile。
- 报告发现 `fit_alpha_power_migration` 的 gap feedback 与 dry-run summary 对 `pressure_allowed_by_alpha_semantics` 的记录存在冲突；在冲突解决前按保守策略处理：不升级、不新跑 pressure。
- 本阶段未运行 k-Wave，未重建 CT，未生成新的 `pressure_max_mpa.npz`。


