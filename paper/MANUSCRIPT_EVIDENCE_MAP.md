# Manuscript Evidence Map

> Parent plan: `PAPER_EXECUTION_MASTER_PLAN.md`  
> Update this file after every paper-facing analysis.

| Manuscript component | Required evidence | Current artifact | Status | Blocking gap |
|---|---|---|---|---|
| Abstract primary result | Matched Case079 baseline–TR endpoints | `outputs/h3_large_full_bowl_matched_standard_20260730/comparison/matched_comparison.json` | ready_with_engineering_boundary | Numerical and external validation not complete |
| Introduction gap | Literature/platform comparison | `literature_tFUS_review/06_报告与数据/reports/PLATFORM_BENCHMARK_AND_PUBLICATION_ROUTE_20260731.md` | ready | Final manuscript citations still need reference-manager export |
| Methods: solver | k-Wave equations/version/configuration | README, environment lock, run summaries and `paper/tables/ucl_h115_validation_20260826/h115_methods_parameters.json` | ready_with_scope_boundary | H115 table is complete for its three engineering runs; Case079 consolidated submission table remains incomplete |
| Methods: analysis freeze | Endpoints, unit, inclusion/exclusion, claim policy | `paper/PAPER_ANALYSIS_FREEZE_20260731.md` | ready | None |
| Methods: reproducibility | Ledger, registry, manifests, hashes | `outputs/run_ledger.jsonl`, evidence registry and manifests | ready | Submission snapshot/DOI later |
| Figure 1 | Workflow and evidence flow | Existing pipeline/governance structure | planned | Figure generator not written |
| Figure 2 | Public benchmark comparison | BM1/BM3/BM4 comparisons; `outputs/itrusst_phase_a_summary_20260807/itrusst_phase_a_summary.json`; `outputs/itrusst_phase_a_diagnostic_20260812/discrepancy_decomposition.json`; `benchmarking/itrusst_phase1_contract.json`; PUB.1 brief/feedback | ready_with_engineering_boundary | Preserve formal BM3/BM4 differences; fitted shifts/gains are diagnostic only |
| Figure 3 | Baseline–TR field and focus | Pressure NPZ and focus metrics exist | data_ready | Paper figure generator and caption needed |
| Figure 4 | dx/PML/CFL/domain sensitivity | PML paired analysis plus `outputs/pub2_250khz_cfl0p1_baseline_analysis_20260812/cfl0p1_baseline_analysis.json` | partial | Baseline CFL passed; TR CFL, dx and domain remain for stronger exit |
| Supplementary external-validation figures | Corrected UCL H115 grid audit plus source/registration/aperture sensitivity | `paper/figures/ucl_h115_grid_sensitivity_corrected_20260825/figure_manifest.json`; `paper/figures/ucl_h115_source_registration_20260825/figure_manifest.json` | ready_with_nonpassing_boundary | Preserve both remaining failed endpoints; shifted/aperture arms are secondary; two grids are not formal convergence |
| Supplementary Table 1 | All eight frozen H115 held-out endpoints across effective dx0.50, effective dx0.30 and nominal dx0.50 | `paper/tables/ucl_h115_validation_20260826/h115_validation_endpoints.json`; `.csv`; `.md` | ready_with_nonpassing_boundary | 24 rows machine-generated from audited comparison JSON; 6/8, 6/8 and 0/8 pass respectively |
| Supplementary Table 2 | H115 geometry, discretization, runtime and device parameters for the three accepted comparison runs | `paper/tables/ucl_h115_validation_20260826/h115_methods_parameters.json`; `.csv`; `.md` | ready | Shared 270 kHz/16-cycle/180-us contract and all device gates are machine checked; all rows remain non-paper-grade metadata |
| H115 claim-boundary audit | Paper-use decision, blocked claims and next evidence | `paper/UCL_H115_PAPER_READINESS_20260823.md` amended under TRACE-20260825-001 | ready | Effective bowl retained over nominal; per-ring acoustic calibration or complex hologram remains unavailable |
| H115 Chinese decision brief | Plain-language paper-use verdict, endpoint interpretation and next evidence | `paper/UCL_H115_VALIDATION_DECISION_BRIEF_ZH_20260826.md` | ready_with_nonpassing_boundary | Explanatory only; audited JSON and manifests remain authoritative |
| H115 paper bundle manifest | Fixed-scope hashes for manuscript, reporting/feasibility evidence, reproduction recipe, Chinese deliverables index, reviewer-risk register, submission preflight, both figures, two supplementary tables and small validation artifacts | `paper/h115_paper_bundle_20260826/manifest.json`; `.md` | ready | 31/31 files present; large pressure field deliberately remains in the execution package validator |
| H115 reproduction recipe | Ordered non-solver commands, frozen inputs, acceptance checks and environment boundary | `paper/H115_REPRODUCTION_RECIPE_20260826.md` | ready | Explicitly reuses retained fields and does not authorize another solver |
| H115 independent reconstruction check | Fresh analyses, figures and supplementary tables compared with accepted outputs | `outputs/ucl_h115_recheck_20260826/reproducibility_recheck.json` | ready | 3/3 analyses plus 10/10 derived checks pass; only JSON generation timestamps and PDF `CreationDate` are normalized |
| H115 reviewer-risk register | Anticipated reviewer objections, evidence, required wording and residual submission actions | `paper/H115_REVIEWER_RISK_REGISTER_20260826.md` | ready | Preserves nonpassing, source-model, registration, uncertainty and context-of-use boundaries |
| H115 submission preflight | Deterministic technical checks separated from author-owned blockers | `paper/h115_submission_preflight_20260826/submission_preflight.json`; `.md` | conditional | 29/29 technical checks pass; submission remains false pending author and release actions |
| Case079 provenance/compliance | Dataset identity, ethics, de-identification, access and redistribution boundary | `paper/CASE079_PROVENANCE_COMPLIANCE_AUDIT_20260829.md`; `outputs/evidence_briefs/submission_readiness_20260829/case079_claim_source_matrix.csv` | conditional | Author must privately verify the registered PhysioNet access record and journal-specific consent/waiver wording; raw CT remains excluded |
| CT mapping/target/QC audit | Primary-source support for HU mapping plus target, registration and segmentation QC | `paper/CT_HU_MAPPING_TARGET_QC_AUDIT_20260829.md`; `outputs/evidence_briefs/ct_hu_mapping_qc_20260829/` | ready_with_engineering_boundary | Exact binary constants, threshold-only segmentation and synthetic target are not independently validated |
| DOI-ready archive candidate | Fixed local scope, hashes, exclusions and release blockers | `paper/submission_archive_20260829/manifest.json`; `paper/SUBMISSION_ARCHIVE_READINESS_20260829.md` | conditional | Project license, immutable source revision and minted DOI remain unresolved; no upload performed |
| Figure/table traceability | Current source/output hashes and claim boundaries for three figure groups and two H115 tables | `paper/submission_traceability_20260829/traceability_matrix.json`; `.csv`; `.md` | ready | Integrity/traceability only; does not upgrade H115 or Case079 physical evidence |
| Author and reviewer materials | Journal metadata/declarations plus evidence-bounded response patterns | `paper/SUBMISSION_AUTHOR_METADATA_FORM_20260829.md`; `paper/REVIEWER_RESPONSE_TEMPLATE_20260829.md` | conditional | Authors must fill private/documentary fields; prepared responses are templates, not replies to actual reviewers |
| Submission decision sheet | Layered GO/NO-GO status and minimum author actions | `paper/SUBMISSION_DECISION_SHEET_20260829.md` | conditional | Technical draft circulation is supported; journal submission, physical-validation claims and public release remain NO-GO |
| Chinese author handoff | Plain-language status, prohibited claims, author actions and reading order | `paper/SUBMISSION_AUTHOR_HANDOFF_ZH_20260829.md` | ready_with_boundaries | Explanatory only; audited JSON, manifests and author documentary records remain authoritative |
| Journal-neutral submission inventory | Manuscript word/section/reference/legend counts plus bundle/archive inventory | `paper/submission_inventory_20260829/submission_inventory.json`; `.md` | conditional | Machine inventory passes; target journal and journal-specific limits remain author inputs |
| Reference claim-scope audit | Supports/does-not-support boundary for all 11 cited works | `paper/MANUSCRIPT_REFERENCE_AUDIT_20260829.json`; `.md` | ready_with_boundaries | Adequate for current scoped wording; no citation directly validates simple_hu300 or Case079 pressure/anatomy |
| Journal-selection rubric | Weighted journal-neutral screening and disqualifiers | `paper/JOURNAL_SELECTION_CRITERIA_20260829.md` | conditional | Requires 2–4 author-supplied candidate journals, budget/access preferences and current official policy checks |
| Environment/interface audit | Runtime versions, accepted backend/quality boundary and 11 CLI help checks | `paper/REPRODUCIBILITY_ENVIRONMENT_AUDIT_20260829.json`; `.md` | conditional | Scientific runtime matches; pytest is absent/unpinned, so no fresh full-suite claim is made |
| Author action ledger | Owner, evidence and release impact for ten unresolved actions | `paper/AUTHOR_ACTION_LEDGER_20260829.json`; `.md` | open | Administrative completion cannot upgrade physical claims; private records stay outside the repository |
| Dependency licence/exclusion inventory | Installed metadata for 29 pinned packages plus prohibited prefixes and exclusions | `paper/dependency_licence_inventory_20260829/` | conditional | Installed versions and metadata are inventoried; root project licence still requires the copyright-holder decision |
| H115 Chinese deliverables index | Plain-language route from conclusion to manuscript, tables, figures, reconstruction and package checks | `paper/H115_DELIVERABLES_INDEX_ZH_20260826.md` | ready | Gives status lights, key numbers, file map and the evidence-supported next step |
| Figure 5 | Material mapping sensitivity | Binary models and profile infrastructure | blocked | Continuous mapping PUB.3 |
| Figure 6 | Cross-platform comparison | Platform capability matrix only | blocked | Exchange contract PUB.4 and comparison PUB.5 |
| Table 1 | Frozen physical/numerical parameters | Run summaries, PUB.2 paired analysis and `paper/PUB2_METHODS_RESULTS_EVIDENCE_20260812.md` | partial | Convert scaffold to consolidated submission table |
| Table 2 | Primary/secondary endpoints | Main Case079 endpoints ready | partial | Sensitivity and independent case |
| Table 3 | Platform/resource/failure comparison | `literature_tFUS_review/06_报告与数据/platform_comparison_20260731.csv` | partial | Measured runs for PUB.5 |
| Independent robustness | Additional licensed anatomy | NLM proxy only | blocked | PUB.6 |
| Independent experimental validation | Public UCL H115 hydrophone comparator | dx0.50/dx0.30 plus nominal-source sensitivity and corrected coordinate audit; UCL dataset DOI 10.5522/04/28025240.v2 | attempted_nonpassing | Axial peak and transverse L2 remain nonpassing; no independent registration shift, per-ring calibration or Case079 validation |
| ITRUSST checklist | Standard reporting fields | `paper/PUB2_REPORTING_CHECKLIST_20260812.md` plus Methods/Results evidence scaffold | partial | Core fields consolidated; remaining author and validation blockers must be resolved before final reporting sign-off |
| Limitations | Domain, mapping, single-case, missing ground truth | Snapshot and gap feedback | ready | Must remain synchronized with new evidence |

Submission preparation and reviewer-risk controls are consolidated in
`paper/PUB2_SUBMISSION_PREP_PACKAGE_20260812.md` and
`paper/PUB2_REVIEWER_RISK_AUDIT_20260812.md`.

Paragraph-level drafting and reporting controls are provided in
`paper/PUB2_MANUSCRIPT_OUTLINE_20260812.md` and
`paper/PUB2_REPORTING_CHECKLIST_20260812.md`. The reviewer-facing parameter and
result workbook is
`outputs/pub2_submission_prep_20260812/PUB2_EVIDENCE_TABLES_20260812.xlsx`.

The evidence-constrained English manuscript draft is
`paper/PUB2_MANUSCRIPT_DRAFT_V0_1_20260812.md`. Submission-oriented Figures 2–4
and their source/output hash manifest are in `paper/figures/pub2_20260812/`.

The FDA/ASME/ITRUSST-aligned verification audit and machine-readable decision
matrix are `paper/PUB2_VERIFICATION_LITERATURE_AND_GAP_AUDIT_20260812.md` and
`paper/PUB2_VERIFICATION_DECISION_MATRIX_20260812.json`.
Prospective acceptance limits are frozen in
`paper/PUB2_VERIFICATION_CONTRACT_20260812.md/json`; they are project targets,
not universal standards.

## Current manuscript-level conclusion

The present evidence supports a single-case engineering observation that matched TR improves spatial localization in the registered H3-large intermediate-domain setup. Paired PML12/PML16 analysis supports robustness to the tested absorbing-layer perturbation. The recovered baseline CFL0.2-to-0.1 comparison passed all frozen limits, but does not test TR time-step sensitivity. In the separate H115 water branch, dx0.50-to-dx0.30 refinement preserved the simulated field; a dated coordinate audit removed a false width failure, leaving axial peak position and transverse normalized L2 nonpassing. Nominal H115 geometry was materially worse than the paper-derived effective bowl, and approximate 0.2-mm aperture averaging was not explanatory. This remains a useful nonpassing source-model observation rather than successful external validation. The evidence does not yet support paper-grade numerical convergence, quantitative pressure accuracy, clinical safety or population generalization.
