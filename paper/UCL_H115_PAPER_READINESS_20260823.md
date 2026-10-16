# UCL H115 water-validation paper-readiness audit

Amended 2026-08-25 under `TRACE-20260825-001` after the coordinate-line regression fix and nominal-source sensitivity.

## Verdict

This branch is ready to be reported as a transparent, nonpassing external source-model validation attempt and as a two-grid numerical-sensitivity observation. It is not ready to support a claim of successful experimental validation, formal grid convergence, or validation of the Case079 transcranial model.

## Evidence status

| Component | Status | Paper use |
|---|---|---|
| Frozen UCL qCW comparison contract | Complete | Methods |
| dx0.50-mm H115 water calculation | Complete, package-valid | Methods and comparison baseline |
| dx0.30-mm single-variable refinement | Complete, package-valid | Numerical-sensitivity result |
| Device and execution trace | Passed all frozen gates | Reproducibility / Supplementary Methods |
| dx0.50-to-dx0.30 physical alignment | Complete | Supplementary Results |
| Experimental comparison | Nonpassing: 6 endpoints pass, 2 fail after dated coordinate audit | Results and limitations, with all endpoints retained |
| Grid convergence | Incomplete: two grids only | Do not claim asymptotic convergence |
| H115 source representation | Nominal equal-amplitude 64/64-mm bowl rejected; effective bowl retained | Source-model sensitivity, not full ring calibration |
| Case079/skull validation | Not tested by this branch | Explicitly out of scope |

## Defensible result statement

Refining the homogeneous-water H115 model from dx0.50 to dx0.30 mm preserved the source-aligned field outside the frozen 5-mm nearfield (correlation 0.999881; amplitude-fitted relative L2 1.310%; relative L-infinity 2.170% of the reference peak; discrete axial-peak shift 0 mm). A dated audit found that micron-scale x-coordinate jitter had been misread as the 1.5-mm raster spacing during line-width extraction. After correction, y-width error was +5.989% at dx0.50 and +7.160% at dx0.30, so both width checks pass. The two remaining nonpassing dx0.30 endpoints are axial peak-position error (2.177 mm) and transverse normalized L2 (15.469%).

The independently documented nominal 64-mm-radius/64-mm-diameter equal-amplitude source was then evaluated once at dx0.50 mm. It was materially worse than the paper-derived effective bowl: axial peak-position error increased from 1.856 to 10.028 mm, axial normalized L2 from 3.780% to 31.030%, and transverse normalized L2 from 15.004% to 118.286%. A descriptive +1.0-mm axial-origin arm is the smallest frozen shift that passes the peak-position gate for the effective bowl, but no independent origin uncertainty authorizes that correction. Approximate 0.2-mm amplitude-domain aperture averaging changes transverse L2 only from 15.004% to 15.039%.

## Claims that remain blocked

- successful external or experimental validation;
- formal/asymptotic grid convergence or a grid-convergence index;
- quantitative validation of absolute Case079 pressure;
- validation of skull propagation, thermal dose, safety, efficacy, or clinical performance;
- tuning the source model against the held-out profiles and then reusing those profiles as independent validation.

## Manuscript placement

- Methods: frozen amplitude-fit/held-out contract, H115 water geometry, dx/PML/CFL, physical-coordinate alignment, 5-mm nearfield exclusion, and device gates.
- Results: report the full pass/fail endpoint set and the two-grid field metrics together.
- Discussion: state that nominal geometry is rejected, 0.2-mm aperture averaging is not explanatory, and an unsupported post-hoc axial shift cannot replace the primary result. Ring-specific acoustic calibration remains unavailable.
- Supplement: use `paper/figures/ucl_h115_grid_sensitivity_corrected_20260825/figure_ucl_h115_grid_sensitivity.png`, `paper/figures/ucl_h115_source_registration_20260825/figure_ucl_h115_source_registration.png`, `paper/tables/ucl_h115_validation_20260826/h115_validation_endpoints.md`, and `h115_methods_parameters.md`; the fixed paper bundle is indexed by `paper/h115_paper_bundle_20260826/manifest.json`.
- Reviewer preparation: use `paper/H115_REVIEWER_RISK_REGISTER_20260826.md` to preserve the calibration/held-out split, source-model, registration, hydrophone, two-grid and context-of-use boundaries during title, abstract and response-letter drafting.

## Next evidence required before a positive validation claim

The next positive-validation route requires independently measured per-ring acoustic amplitude/phase or a measured complex hologram implemented under a new source contract. A third, finer or otherwise justified grid would still be required for formal convergence, but neither more blind grid refinement nor post-hoc registration is currently authorized.

## Verification record

- focused H115 tests: 18/18 passed;
- bounded broad non-solver regression: 364/364 passed (the input-heavy historical NLM readiness audit remains explicitly excluded);
- evidence registry, run ledger and reproducibility manifest: valid;
- package validation: passed with a guarded nonpassing physical observation;
- pressure rerun authorization: none.
