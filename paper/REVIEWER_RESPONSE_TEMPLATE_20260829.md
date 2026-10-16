# Evidence-bounded reviewer response template

Trace: `TRACE-20260829-001`

Use this only after receiving actual reviewer comments. Replace bracketed text
with the reviewer quotation, manuscript locations and author-approved wording.
Do not claim that a technical package check establishes physical validation.

## Response structure

> Reviewer comment: `[PASTE COMMENT]`

**Response.** We thank the reviewer for raising this point. `[DIRECT ANSWER]`
The corresponding manuscript text now states: `[SHORT AUTHOR-APPROVED TEXT]`.
This change appears in `[SECTION / PAGE / LINE]` and is supported by
`[AUDITED ARTIFACT OR PRIMARY SOURCE]`.

## Prepared high-risk responses

### External comparison did not pass every endpoint

The H115 comparison is reported as nonpassing. The effective-source dx0.50-mm
and dx0.30-mm cases each passed 6/8 frozen endpoints; axial peak-position error
and transverse normalized L2 remained outside their preregistered limits. We
therefore use “external comparison” or “nonpassing validation attempt,” retain
all unfavourable endpoints, and make no claim of successful source validation.

Evidence: `paper/tables/ucl_h115_validation_20260826/` and
`outputs/ucl_h115_source_registration_audit_20260825/package_validation.json`.

### Two grids do not establish convergence

The dx0.50-to-dx0.30 result is a two-grid numerical-sensitivity observation.
Although the simulated fields were highly consistent, a third justified grid
and formal order/error analysis were not performed. The manuscript therefore
does not use “grid converged.”

Evidence: `paper/figures/ucl_h115_grid_sensitivity_corrected_20260825/`.

### Source geometry and amplitude were not independently measured

The effective bowl is paper-derived rather than a measured per-ring acoustic
source. The nominal equal-amplitude 64/64-mm candidate performed worse (0/8),
which is reported as source-model sensitivity, not as evidence that the
effective geometry reproduces the manufacturer's drive. Independent per-ring
complex calibration or a measured hologram remains unavailable.

Evidence: `paper/figures/ucl_h115_source_registration_20260825/`.

### Case079 mapping and anatomical QC are limited

The exact `simple_hu300` equations and constants are disclosed as a frozen,
unvalidated engineering profile. The target is synthetic/non-anatomical and
the skull segmentation is threshold-only; no Case079 reference mask,
anatomical registration or expert sign-off was identified. We therefore do not
claim validated material assignment or anatomical targeting accuracy.

Evidence: `paper/CT_HU_MAPPING_TARGET_QC_AUDIT_20260829.md`.

### Restricted Case079 data cannot be redistributed

Case079 is traced to PhysioNet CT-ICH v1.3.1 (DOI 10.13026/4nae-zg36). The
provider reports dataset-level ethics approval and de-identification, while the
restricted-data licence prohibits sharing access. The raw CT is excluded; the
responsible author must privately confirm the registered-access record and any
journal-specific consent/waiver wording.

Evidence: `paper/CASE079_PROVENANCE_COMPLIANCE_AUDIT_20260829.md`.

### Reproducibility does not equal physical accuracy

The fixed-scope paper bundle, reconstruction checks and traceability matrix
show that the reported outputs are internally reproducible and traceable. They
do not convert the nonpassing H115 comparison into successful validation or
establish absolute intracranial pressure accuracy, formal convergence,
clinical efficacy or safety.

Evidence: `paper/h115_paper_bundle_20260826/`,
`paper/submission_traceability_20260829/` and
`paper/h115_submission_preflight_20260826/`.

## Final response-letter checks

- `[ ]` Every response answers the reviewer before describing edits.
- `[ ]` Every numerical statement links to a retained audited artifact.
- `[ ]` Every literature statement cites the primary source actually checked.
- `[ ]` Failed endpoints and limitations remain visible.
- `[ ]` No new parameter interpretation is introduced without an Evidence Brief.
- `[ ]` Page and line locations are updated after final typesetting.

