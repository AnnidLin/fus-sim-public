# Submission archive readiness

Trace: `TRACE-20260829-001`  
Status: `blocked_local_candidate`

## Result

A deterministic local archive candidate has been generated with **136 files**,
**1,722,038 bytes** total and content digest
`99e37dbb5411b7f2181ef560abf64017f9154a03cb65b85e13267be2ba320c5e`.
It includes the paper-facing bundle, compact evidence, relevant code, pinned
requirements and focused tests. It contains no prohibited raw CT, third-party
source snapshot or UCL intake file.

Canonical files:

- `paper/submission_archive_20260829/manifest.json`
- `paper/submission_archive_20260829/manifest.md`
- `paper/submission_archive_20260829/files.csv`
- `paper/submission_archive_spec_20260829.json`

## Blocking items

1. **Project licence unresolved.** No repository-root licence file is present.
   `legacy_archive/LICENSE` contains an MIT licence and a named 2026 copyright,
   but its archived location does not prove that it governs the current code or
   that the current author wants to reapply it. An author decision is required.
2. **Source revision not frozen.** The current working tree contains substantial
   prior and current uncommitted work. The archive must be regenerated from a
   selected clean release commit or immutable tag.
3. **DOI not minted.** This trace performs local preparation only; no upload or
   DOI creation is authorized.

## Data disposition

- Case079 raw CT: excluded; users must obtain CT-ICH v1.3.1 directly from
  PhysioNet under the restricted-data process.
- CT-derived voxel property fields and masks: excluded pending a derived-data
  privacy/redistribution decision.
- Full pressure fields: excluded from the compact archive; retain hashes and
  execution-package summaries.
- UCL source measurement: external DOI `10.5522/04/28025240.v2`, CC BY 4.0;
  archive references the publisher rather than repackaging the intake file.
- PRESTUS/BabelBrain source snapshots: excluded; cite upstream repositories and
  their licences.

## Author decisions required before DOI upload

- Confirm the project copyright holder(s) and choose the repository licence;
  restoring an MIT licence is one candidate, not an automatic decision.
- Choose the release version and immutable source revision.
- Select the repository/archive service and complete its metadata form,
  authors/ORCIDs, affiliations, funding and related identifiers.
- Review the derived-data exclusion boundary and approve the final data
  availability statement.
- Regenerate the manifest from the frozen revision and require zero missing or
  prohibited files before upload.

## Verification

- Generator unit tests: 2/2 passed.
- Candidate files: 136/136 found after manuscript/preflight/traceability, author-material, decision-sheet, handoff, inventory, reference, environment, dependency-licence, pre-close, negative-results, numeric-transcription, caption-semantic, reviewer-path, entry-document, claim-scope, author-query and archive-integrity tooling audits.
- Figure/table traceability: 5/5 artifact groups passed all six deterministic checks.
- Missing files: 0.
- Prohibited matches: 0.
- No external upload, commit, push or DOI action occurred.
