# Manuscript numeric-transcription audit

Status: `passed_numeric_transcription`

## Source-derived tokens

- `ratio_pair`: `0.4774 to 0.9849`
- `distance_pair`: `57.38 to 2.49 mm`
- `target_pressure_pair`: `1.891 to 2.554 MPa`
- `global_pressure_pair`: `3.962 to 2.593 MPa`
- `target_pressure_change`: `+35.04%`
- `global_pressure_change`: `−34.54%`
- `pml_baseline_l2`: `1.83 × 10−5`
- `pml_baseline_linf`: `6.75 × 10−5`
- `pml_tr_l2`: `5.05 × 10−5`
- `pml_tr_linf`: `1.46 × 10−4`
- `cfl_l2_linf`: `0.654%/1.375%`
- `cfl_target_change`: `−0.770%`

## Checks

- [x] `ratio_pair`
- [x] `distance_pair`
- [x] `target_pressure_pair`
- [x] `global_pressure_pair`
- [x] `target_pressure_change`
- [x] `global_pressure_change`
- [x] `pml_baseline_l2`
- [x] `pml_baseline_linf`
- [x] `pml_tr_l2`
- [x] `pml_tr_linf`
- [x] `cfl_l2_linf`
- [x] `cfl_target_change`
- [x] `pressure_units_are_mpa`
- [x] `distance_units_are_mm`
- [x] `cfl_claim_is_baseline_only`
- [x] `pressure_accuracy_boundary_retained`

Scalar transcription and units only; this audit does not validate the underlying physics or authorize submission.
