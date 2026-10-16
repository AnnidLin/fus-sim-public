# UCL H115 paper-output reproduction recipe

## Scope

This recipe rebuilds the accepted H115 analyses, figures, tables and validators from retained artifacts. It does **not** authorize or require another k-Wave solve. The only nominal-source propagation is already complete and its exact dry-run command is preserved in `outputs/ucl_h115_water_nominal64_dx0p5_20260825/exact_dry_run_report.json`.

Run commands from the repository root with `D:\AIprogram\python-envs\kwave312\Scripts\python.exe`. Use fresh recheck output paths when independently reproducing results; do not overwrite accepted artifacts.
Create each fresh output directory before invoking an analysis script; the analysis interfaces write files but do not create missing parent directories.

## Frozen inputs

- UCL measurement summary: `outputs/ucl_270khz_freefield_summary_20260812/`
- exact input HDF5 SHA-256: `0275af014151ca972c0c7799af2735e345554c460f797f217bd8ceb4f3dfa0ad`
- effective dx0.50 field: `outputs/ucl_h115_water_validation_20260818/`
- effective dx0.30 field: `outputs/ucl_h115_water_dx0p3_grid_sensitivity_full_20260823/`
- nominal dx0.50 field: `outputs/ucl_h115_water_nominal64_dx0p5_20260825/`
- frozen measurement-comparison contract: `outputs/ucl_h115_water_papergrade_dryrun_dx0p5_20260812/validation_contract.json`
- frozen source/registration contract: `outputs/evidence_briefs/ucl_h115_source_registration_20260825/validation_contract.json`

## Non-solver reconstruction order

1. Rebuild the corrected effective-bowl measurement comparisons with `analyze_ucl_h115_water_validation.py` for dx0.50 and dx0.30, using the UCL measurement summary and the frozen **measurement-comparison** contract. Do not substitute the source/registration contract: it has a different schema and purpose. Write to fresh JSON paths.
2. Rebuild `source_registration_sensitivity.json` with `analyze_ucl_h115_source_registration.py`, using the effective and nominal simulation directories, measurement directory, Evidence Brief and corrected effective comparison.
3. Rebuild the corrected grid figure with `generate_ucl_h115_grid_sensitivity_figure.py`; explicitly pass the corrected dx0.50/dx0.30 comparison JSON paths.
4. Rebuild the source/registration/aperture figure with `generate_ucl_h115_source_registration_figure.py`.
5. Rebuild Supplementary Table 1 with `generate_h115_validation_table.py` and Supplementary Table 2 with `generate_h115_methods_table.py`.
6. Run `validate_h115_reconstruction.py` against the accepted audit, figure and table directories. Its strict rules remove only `generated_at_utc` from JSON and PDF `CreationDate`; PNG, CSV and Markdown must match byte-for-byte. Retain the generated `reproducibility_recheck.json`.
7. Run `validate_h115_manuscript_consistency.py`, then `validate_ucl_h115_source_registration_package.py` with `--manuscript-consistency`.
8. Only after the package validator is final, run `generate_h115_paper_bundle_manifest.py --output-dir <fresh-bundle-dir>` and verify it with `validate_h115_paper_bundle_manifest.py --manifest <fresh-bundle-dir>\manifest.json`.
9. Run the H115-focused tests and the bounded broad non-solver suite; retain the exclusion of `test_audit_nlm_public_case_readiness.py`, which requires a separate input-heavy historical NLM fixture.

## Accepted command interfaces

```text
analyze_ucl_h115_water_validation.py --simulation-dir <simulation> --measurement-dir <measurement> --contract outputs/ucl_h115_water_papergrade_dryrun_dx0p5_20260812/validation_contract.json --output <fresh-json>
analyze_ucl_h115_source_registration.py --effective-dir <effective> --nominal-dir <nominal> --measurement-dir <measurement> --brief <brief-json> --effective-comparison <corrected-json> --output <fresh-json>
validate_h115_reconstruction.py --recheck-dir <fresh-analysis-dir> --accepted-dir outputs/ucl_h115_source_registration_audit_20260825 --recheck-grid-figure-dir <fresh-grid-figure-dir> --accepted-grid-figure-dir paper/figures/ucl_h115_grid_sensitivity_corrected_20260825 --recheck-source-figure-dir <fresh-source-figure-dir> --accepted-source-figure-dir paper/figures/ucl_h115_source_registration_20260825 --recheck-tables-dir <fresh-table-dir> --accepted-tables-dir paper/tables/ucl_h115_validation_20260826 --output <fresh-analysis-dir>/reproducibility_recheck.json
generate_ucl_h115_grid_sensitivity_figure.py --reference-dir <dx0p5> --candidate-dir <dx0p3> --measurement-dir <measurement> --reference-comparison <corrected-dx0p5-json> --candidate-comparison <corrected-dx0p3-json> --output-dir <fresh-figure-dir>
generate_ucl_h115_source_registration_figure.py --effective-dir <effective> --nominal-dir <nominal> --measurement-dir <measurement> --effective-comparison <corrected-dx0p5-json> --sensitivity <sensitivity-json> --output-dir <fresh-figure-dir>
```

## Acceptance checks

- corrected effective comparisons each retain exactly two failed physical endpoints;
- nominal geometry retains zero of eight endpoint passes and is materially worse under every frozen source-explanation threshold;
- registration and aperture arms remain secondary and never replace primary results;
- package status is `passed_with_nonpassing_external_validation`;
- manuscript consistency has zero failed checks;
- paper bundle contains every expected file and all current size/SHA-256 checks pass;
- no wording upgrades the result to successful external validation, formal convergence, Case079 validation or a clinical/safety conclusion.

## Environment boundary

The accepted runs used Python k-Wave 0.6.1, Python 3.12.10, Windows 11 and the CPU backend. The three accepted H115 rows are classified as engineering evidence with `is_paper_grade=false`. Exact runtime and device extrema are in Supplementary Table 2.
