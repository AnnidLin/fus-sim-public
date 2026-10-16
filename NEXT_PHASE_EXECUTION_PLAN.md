# fus-sim Next Phase Execution Plan

> **Historical plan only.** Active execution moved on 2026-07-31 to `PAPER_EXECUTION_MASTER_PLAN.md`. Do not use this file to authorize new simulations or override the PUB gate order.

> Historical note from 2026-07-11: `ACOUSTIC_PAPER_GRADE_EXECUTION_PLAN.md` previously served as the acoustic-field-first route. Both plans are now subordinate to `PAPER_EXECUTION_MASTER_PLAN.md`.

> Status date: 2026-07-10
> Scope: Case 079 acoustic-field-first engineering baseline hardening. This plan replaces older broad M5-first roadmaps for near-term execution.

## Current Position

`fus-sim` is at **M2_standard_engineering_baseline_hardening**. The CT-to-pressure-to-Pennes pipeline is reproducible for Case 079, and corrected dx0.75/dx0.5 baselines show engineering-level stability. The project is not paper-grade and does not support clinical safety claims.

Authoritative near-term interpretation:

- Corrected baseline dx0.75: target-window peak `2.449 MPa`, global peak `5.179 MPa`, max dT `1.476 C`, overall safe under the local Pennes gate.
- Corrected baseline dx0.5: target-window peak `2.391 MPa`, global peak `4.918 MPa`, max dT `1.533 C`, overall safe under the local Pennes gate.
- The high corrected target pressure is a **free-field-like / edge-skimming result**, not validated thick-skull transcranial residual pressure.
- Main scientific bottlenecks are focus deficiency, missing free-field calibration chain, and missing thick-skull external-validity validation.

## 2026-07-08 Priority Decision

The near-term project priority is now the acoustic field. Thermal analysis remains important, but only as a downstream boundary check once an acoustic candidate is physically interpretable. Do not spend new compute on broader thermal sweeps until the free-field calibration chain, true skull-crossing geometry, and focus-correction sensitivity are clarified.

## 2026-07-10 Recovery Checkpoint

- P1 current-tuned free-field calibration and source/free-field/in-situ definition boundary are complete for engineering use. The matched corrected/free-field target-window ratio is 32.335%; MItc remains blocked without waveform-derived PNPtc.
- P2 source-array delay semantics were corrected; previous multi-patch phase results are invalidated. Source-safe Tukey failed. A radius-matched r74.435 quick diagnostic restored a target-local peak but retained the skull-entry hotspot, so no escalation is authorized.
- P3 Case 079 `(+5,0)` ap30/r35 standard pressure run completed at 100 us: runner `kwave_ok`, target-window 0.596 MPa, global skull peak 9.698 MPa, target/global 0.055. The focus objective failed.
- Immediate next action: do not start Pennes or another pressure batch. Design a source-safe hotspot-mitigation candidate and return to quick acoustic screening before any new standard authorization.
## Execution Rule

Proceed in this order:

1. **P0 governance and metadata closure** (closed; re-check only after new evidence)
2. **P1 free-field source-pressure calibration**
3. **P2 phase-correction-sensitive geometry selection and focus optimization**
4. **P3 thick-skull external-validity validation**
5. **P4 paper-grade precision upgrades**

Do not jump to dx0.3, large batch pressure runs, broad thermal sweeps, profile default promotion, or paper-grade claims before the acoustic P1-P3 gates are closed.

## P0: Governance And Metadata Closure

Goal: remove the `alpha_semantics` metadata blocker and make the project state auditable before any new pressure simulation.

Expected duration: 0.5-1 day.

Actions:

- Fix `alpha_semantics` Option B:
  - `build_ct_acoustic_model.py` infers alpha semantics for profiles without an explicit block.
  - `simulate_kwave_3d_focus.py` treats `missing_alpha_semantics` and `legacy_unspecified` as unspecified legacy metadata, not explicit pressure rejection.
  - `alpha_power != 1.0` with `alpha_mode=null` is not blocked, because k-Wave only needs alpha-mode review for the `alpha_power == 1.0` dispersion case.
- Write/update `outputs/evidence_briefs/alpha_semantics_gap_closure/evidence_brief.md/json`.
- Refresh `run_ledger`, `evidence_registry`, reproducibility manifest, and final package metadata.
- Run health check and validators.

Acceptance criteria:

- `validate_run_ledger.py`, `validate_evidence_registry.py`, `validate_reproducibility_manifest.py`, and `validate_final_reproducibility_package.py` report zero failed checks.
- New dry-run/model summaries no longer report `alpha_semantics_status=missing_alpha_semantics` for newly built binary/continuous profiles.
- Existing historical pressure/thermal outputs are not overwritten.

Risk controls:

- No new k-Wave pressure run in P0 unless explicitly authorized.
- Rebuild or dry-run outputs should use new validation directories when overwrite risk exists.
- Any generated evidence brief is execution-pre evidence only; execution results go to `gap_feedback`.

## P1: Free-Field Calibration Chain

Goal: establish source pressure -> free-field focal pressure -> in situ pressure boundaries for the current transducer geometry.

Expected duration: 0.5-2 days depending on whether a standard water run is authorized.

Actions:

- Use aperture `30 mm`, radius `35 mm`, frequency `500 kHz`, and the current source-pressure convention.
- Run or prepare water-only free-field calibration.
- Extract P_free, focus coordinate, axial/lateral FWHM, and MI/MItc interpretation boundaries.

Acceptance criteria:

- `free_field_calibration_summary.json` exists for the current tuned geometry.
- Reports clearly separate source pressure, free-field focus pressure, and transcranial in situ pressure.

## P2: Minimal Focus Optimization Prototype

Goal: show that the global peak can be pulled toward target before spending compute on high-resolution thick-skull studies.

Expected duration: 3-7 days for a minimal prototype.

Preferred approach:

- Start with a source-point-array or phase-delay prototype rather than a large 64/128-channel production implementation.
- Optimize target-window pressure relative to global peak.

Acceptance criteria:

- Target/global ratio reaches at least `70%`, or global peak is within `5 mm` of the target window center.
- If the prototype cannot improve focus after a small number of attempts, stop and write a feasibility report instead of running more pressure cases.

## P3: Thick-Skull External Validity

Goal: test whether conclusions survive a real bone-crossing path.

Expected duration: 1-3 days per authorized geometry.

Preferred order:

- First `(+5, +0)` entry offset as a moderate skull-crossing case.
- Then `(+0, +0)` collinear as a thick-skull boundary case if the moderate case is interpretable.

Acceptance criteria:

- A `thick_skull_external_validity_report.md` documents target pressure, global peak location, target-waveform boundary, and comparison limits. Thermal response is explicitly deferred because the acoustic candidate failed.
- The report states whether results are engineering validation, trend evidence, or paper-grade evidence.

## P4: Paper-Grade Upgrades

Only start after P0-P3 are resolved.

Candidate work:

- dx `0.3-0.5 mm` grid-convergence study with matched physical PML thickness.
- Continuous skull/profile validation after alpha/profile gates are clean.
- MATLAB/BabelBrain cross-checks.
- Uncertainty quantification and reproducibility package v2.

## Do Not Do Yet

- Do not run dx0.3 or large pressure batches before focus and free-field calibration are closed.
- Do not promote `prestus_fit_alpha_power_2`, `continuous_skull`, or any profile to default based only on model-build outputs.
- Do not describe `2.449 MPa` as true thick-skull transcranial residual pressure.
- Do not claim clinical safety, paper-grade convergence, or profile-default readiness.

