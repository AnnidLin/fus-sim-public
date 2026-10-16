# Submission-readiness 10-hour worklog — TRACE-20260829-001

Start: 2026-08-29 00:02 Asia/Shanghai  
Target window: approximately 10 hours  
Mode: low-token, evidence-gated, non-solver by default

## 00:02–00:22 — intake and evidence boundary

- Confirmed the prior H115 comparison remains nonpassing and the submission
  preflight remains false because of three author-owned blockers.
- Confirmed no new pressure solver is authorized by current evidence.
- Inspected the frozen `simple_hu300` profile, the historical Case079 baseline,
  the CT/T2 registration QC record and current manuscript/preflight pointers.
- Opened the trace-specific Evidence Brief and froze acceptance, stop and claim
  rules before any manuscript or mapping work.

## Next checkpoint

Produce a local Case079 provenance/compliance claim matrix and an author-fillable
template. Unknown source or permission facts must remain unresolved.

## 02:02–02:25 — Figure/table traceability closure

- Added a deterministic traceability generator covering Case079 Figures 2–4,
  both H115 supplementary figures and both H115 supplementary tables.
- The matrix independently checks retained input/output presence, declared
  figure hashes, table row counts, table generation status and explicit claim
  boundaries.
- Updated the manuscript evidence map: submission preflight is 17/17 technical
  checks, while Case079 provenance, CT mapping/QC, archive readiness and
  traceability are now explicit.
- No solver was started. This phase verifies traceability and integrity only;
  it does not upgrade the nonpassing H115 comparison or single-case Case079
  evidence.

## 00:22–00:42 — Case079 provenance and compliance

- Recovered the original download referrer and host URL from the local NIfTI's
  NTFS metadata; both identify PhysioNet CT-ICH v1.3.1 and file `079.nii`.
- Cross-checked the dataset DOI, ethics-board approval, de-identification release
  note, restricted access policy and no-sharing licence against the official
  PhysioNet record and licence page.
- Hashed and characterized the local NIfTI without scanning pressure outputs.
- Produced a claim/source matrix, manuscript-safe wording, archive exclusion
  rule and an author confirmation form.
- The source and dataset-level ethics/de-identification portions are now
  supported. Individual consent/waiver and the local user's signed agreement
  remain author-owned; raw CT redistribution is rejected by current evidence.

## Next checkpoint

Audit the exact mapping implementation and build a primary-source-to-equation
matrix without changing `simple_hu300` or any physical default.

## 00:42–01:02 — mapping, target and imaging-QC freeze

- Opened an independent Evidence Brief before making any mapping-related
  manuscript decision; no physical default or solver state changed.
- Extracted the exact binary label rule, constant material values and inferred
  attenuation-power semantics from implementation and profile files.
- Cross-checked the intended continuous-mapping context against Marsac 2017,
  Webb 2018 and PRESTUS. These sources support heterogeneous/scanner-specific
  mapping rationale, but do not match or validate the frozen `simple_hu300`
  property combination.
- Confirmed `target_020` is synthetic/engineering rather than anatomical,
  Case079 has threshold-only segmentation without ground truth or expert sign-off,
  and no Case079 anatomical registration is documented.
- Produced a 14-item claim/source matrix and manuscript-safe Methods/limitations
  wording. The mapping/QC author blocker is narrowed but not cleared.

## Next checkpoint

Inventory the stable code/data archive, classify licences and redistribution
constraints, and generate a deterministic DOI-ready local manifest without
uploading or pushing.

## 01:02–01:22 — DOI-ready local archive candidate

- Implemented a standard-library-only deterministic manifest generator with
  explicit prohibited-prefix checks, file hashes, sizes, exclusions and a
  content digest.
- Diagnosed and corrected a sandbox-specific test fixture problem by replacing
  writable temporary directories with read-only repository fixtures; 2/2 unit
  tests pass.
- Generated a 70-file, 1,530,915-byte candidate with zero missing files and zero
  prohibited raw/third-party-data matches.
- Preserved three release blockers: no current root licence decision, no frozen
  source revision and no minted DOI. `archive_ready=false` is therefore correct.
- No archive was uploaded, committed, pushed or published.

## Next checkpoint

Update manuscript data availability, Methods/limitations, reviewer-risk and
submission preflight so the newly supported provenance and archive boundaries
are reflected consistently without clearing unresolved author decisions.

## 01:22–01:42 — manuscript and preflight integration

- Replaced the manuscript's Case079 provenance placeholder with the supported
  PhysioNet CT-ICH v1.3.1 DOI, dataset ethics/de-identification statement,
  restricted-access route and raw-data exclusion.
- Added the exact `simple_hu300` equations/constants, 5-mm source-slice limit,
  threshold-only segmentation and non-anatomical target boundary; added Marsac
  2017 and Webb 2018 only for the claims they directly support.
- Updated Methods evidence, reporting checklist and reviewer-risk register with
  three new high-priority risks covering restricted data, unvalidated mapping
  and missing target/segmentation registration.
- Expanded deterministic preflight from 10 to 17 checks. All 17 pass while
  `submission_ready=false` remains enforced by three narrower author/evidence
  blockers.
- Refreshed the 31-file paper bundle and local archive candidate. The archive is
  now 1,538,969 bytes with digest
  `ccc01f3a23f641bab94eebe5dc4530f6a386e5167d47170cb5115a473bed24c5`;
  missing/prohibited counts remain zero.

## Next checkpoint

Strengthen figure/table traceability and author-facing submission materials,
then run focused regression before the broader governance refresh.

## 02:02–02:25 — figure/table traceability and package refresh

- Added `generate_submission_traceability_matrix.py` and a focused test.
- Traced three figure groups and two supplementary tables to 20 retained source
  files and 15 rendered/table outputs, with current SHA-256 values.
- All six checks pass: inputs present, outputs present, declared hashes match,
  row counts match, table generators passed and claim boundaries are present.
- Expanded submission preflight to 18/18 passing technical checks while keeping
  `submission_ready=false` and the same three author/evidence blockers.
- Refreshed and independently validated the 31-file paper bundle.
- Refreshed the local archive to 75 files, 1,572,882 bytes, digest
  `74d7334778e68cd2b67ca90fc13e27e466f2f320e6aa9f06fbe999848343c2c7`;
  missing/prohibited counts remain zero and `archive_ready=false` remains
  correct.
- No solver, upload, commit, push or DOI action occurred.

## Next checkpoint

Prepare author-facing submission metadata and a concise response-to-reviewer
risk template, then run bounded non-solver governance regression. The task
continues toward the 10-hour window.

## 02:22–02:45 — author materials and governance regression

- Added an author metadata/declaration form covering journal choice, authorship,
  ORCID/affiliations, CRediT roles, funding, conflicts, ethics/consent, private
  PhysioNet access confirmation, licence, frozen revision and DOI.
- Added six evidence-bounded reviewer-response patterns for the known high-risk
  questions: nonpassing H115 endpoints, two-grid limitation, unmeasured source,
  Case079 mapping/QC, restricted CT and reproducibility-versus-validity.
- Corrected two stale submission-preparation statements: the archive now has 77
  files, and baseline CFL0.2-to-0.1 passed while matched TR CFL remains missing.
- Expanded technical preflight to 20/20 checks; `submission_ready=false` and the
  three author/evidence blockers remain unchanged.
- Run-ledger, evidence-registry and reproducibility-manifest validators all
  passed with zero failed checks. The first sandboxed attempt could not write
  reports; the authorized project-local rerun completed successfully.
- Refreshed and validated the 31-file paper bundle. The 77-file archive is
  complete with zero missing/prohibited matches but remains correctly blocked
  from release.
- No solver, external upload, commit, push or DOI action occurred.

## Next checkpoint

Audit title/abstract/conclusion terminology against the frozen claim boundary,
then produce a compact submission decision sheet and run the remaining bounded
non-solver consistency checks. The task continues toward the 10-hour window.

## 02:42–03:05 — manuscript claim lint and submission decision

- Extended the manuscript consistency validator with title, abstract,
  data-availability and submission-readiness claim checks.
- The expanded terminology/artifact consistency report passes with zero failed
  checks; the title retains simulation scope and the abstract explicitly blocks
  convergence, pressure-accuracy, generalization, efficacy and safety claims.
- Added a layered submission decision sheet: technical reconstruction and
  bounded internal draft circulation are GO; H115 physical validation,
  Case079 quantitative/anatomical validation, public release and journal
  submission are NO-GO.
- Expanded deterministic technical preflight to 22/22 checks while preserving
  `submission_ready=false`.
- The local candidate now contains 78 files with zero missing/prohibited items;
  release remains blocked by licence, immutable revision and DOI.
- No additional k-Wave run is authorized because the missing per-ring complex
  acoustic calibration/hologram was not found. No solver or external action was
  performed.

## Next checkpoint

Check internal cross-document numbers and stale status strings after the latest
archive expansion, then assemble a concise Chinese handoff for the author and
continue bounded non-solver regression toward the 10-hour window.

## 03:02–03:25 — cross-document status lock and Chinese handoff

- Added a deterministic cross-document status validator and focused test.
- Twelve current-state checks pass: 81-file archive, zero missing/prohibited
  items, three retained release blockers, zero technical-preflight failures,
  `submission_ready=false`, manuscript consistency, 31-file bundle, canonical
  file-count agreement and explicit submission NO-GO wording.
- Added a Chinese author handoff explaining what is complete, what cannot be
  claimed, what the author must supply, which files to read and why another
  solver is not currently informative.
- Updated current canonical documents to the 81-file archive state; historical
  intermediate counts remain only in the dated worklog as an audit trail.
- Expanded technical preflight to 24/24 checks and refreshed all dependent
  manifests. Final local archive size is 1,594,565 bytes with digest
  `5c95b9273de44cd9f0bbe3cb00b1be9393c42f26eab5e68ae5f85b7c75656a65`.
- No solver, external upload, commit, push or DOI action occurred.

## Next checkpoint

Review the manuscript structure for journal-neutral completeness (word counts,
figures/tables/references and unresolved placeholders), prepare a machine-readable
submission inventory, and continue bounded non-solver verification.

## 03:22–03:48 — journal-neutral submission inventory

- Added a deterministic submission-inventory generator and focused test.
- Inventory passes all ten structural checks while keeping
  `submission_ready=false`, `target_journal=null` and journal-limit evaluation
  false.
- Current manuscript inventory: approximately 4,269 English tokens/words
  including references, 210-word abstract, 9 level-2 sections, 11 references,
  3 main figure legends, 2 supplementary figure legends and 2 supplementary
  table legends.
- The first build exposed a generator/preflight circular dependency and the
  expected 83/85-file bootstrap state. Removed the circular preflight dependency,
  regenerated the two inventory outputs, and reran the closure in dependency
  order. Final focused inventory/status tests pass.
- Technical preflight is 24/24 with zero failures; cross-document status and
  manuscript consistency pass; the paper bundle remains 31/31 valid.
- Final compact archive is 85 files, 1,605,902 bytes, digest
  `1ff216a0e1b6855ee1e0a3f89a3e554cf5a78838d8a0d9fdb09e1cf001263423`,
  with zero missing/prohibited files and three retained release blockers.
- No solver or external action occurred.

## Next checkpoint

Audit the 11 references and claim-to-citation coverage for completeness and
scope, without adding unsupported citations; then prepare journal-selection
criteria that the author can use without changing the current claims.

## 03:42–04:05 — reference scope and journal-selection criteria

- Audited all 11 references with an explicit supports/does-not-support boundary;
  numbering, citation coverage, DOI uniqueness and seven scope checks pass.
- Preserved the crucial limits: generic k-Wave and cranial-bone validation do
  not validate Case079; mapping papers do not validate `simple_hu300`; the UCL
  data record does not validate the simplified H115 source; hydrophone guidance
  does not convert amplitude averaging into a complex-pressure model.
- Added a journal-neutral weighted screening rubric emphasizing computational-
  methods scope, acceptance of nonpassing validation results, restricted-data
  compatibility, supplement capacity and reproducibility policy.
- Did not rank journals because candidate titles, budget, open-access preference,
  audience and timing have not been supplied; current official policies must be
  checked when the author provides 2–4 candidates.
- Technical preflight expanded to 26/26 checks with zero failures. Inventory,
  status consistency, manuscript consistency and 31-file bundle all pass.
- Compact archive is 88 files, 1,615,769 bytes, digest
  `b97d2522edfbbd62ef64ed1913052cef7133bab3995371e7a04aa6d5d64c6fe8`;
  `archive_ready=false` and `submission_ready=false` remain enforced.
- No physical defaults, solver runs or external publication actions occurred.

## Next checkpoint

Audit reproducibility commands and environment declarations against retained
scripts/configuration, then create a final author-action ledger with owners,
evidence needed and release impact. Continue toward the 10-hour window.

## 04:02–04:25 — environment/interface audit and action ownership

- Verified the retained runtime against the manuscript: CPython 3.12.10,
  Windows 11, k-Wave-python 0.6.1, NumPy 2.2.6, SciPy 1.15.3, Matplotlib
  3.10.7, h5py 3.15.1 and C++/CPU execution.
- Loaded all 11 non-solver command interfaces named in the reproduction flow
  under `--help`; required argument names match the documented workflow.
- Recorded one honest reproducibility gap: pytest is not installed in the
  retained k-Wave runtime and is not pinned in `requirements-kwave312.txt`.
  Focused checks passed by direct invocation, but no fresh full pytest-suite
  claim is made.
- Created a ten-item author/release ledger assigning owners, required evidence
  and impact for journal selection, authorship/declarations, restricted-data
  confirmation, claim approval, licence, revision, DOI, test lock and final
  proof review.
- Expanded preflight to 28/28 passing technical checks; inventory/status/text
  consistency and the 31-file paper bundle remain valid.
- Compact archive is 92 files, 1,625,057 bytes, digest
  `6fae2c847e964a686e7a42f87320e128816929986e7aeedad7ef4bb64ffc9c5a`;
  release and submission states remain false.
- No solver, package installation, upload, commit, push or DOI action occurred.

## Next checkpoint

Use the remaining non-solver window to audit data/code availability wording,
third-party licence attribution and archive exclusions, then perform a compact
end-to-end pre-close verification without claiming completion before 10 hours.

## 04:22–04:48 — dependency licences and archive exclusions

- Added a standard-library dependency licence inventory using installed package
  metadata, without network access or package installation.
- All 29 exactly pinned scientific dependencies are installed at the expected
  versions and expose licence metadata. The report remains conditional because
  no repository-root project licence exists; this is correctly reserved for the
  copyright holder rather than inferred from `legacy_archive/LICENSE`.
- Rechecked prohibited prefixes and exclusions: raw Case079 CT, potentially
  reconstructable CT-derived volumes/masks, full pressure fields, PRESTUS/
  BabelBrain source snapshots, credentials, signed agreements and private ethics
  records remain outside the candidate archive.
- Focused dependency-inventory test passed. Preflight expanded to 29/29 checks;
  inventory, status, manuscript consistency and 31-file bundle remain valid.
- Compact archive is 97 files, 1,647,829 bytes, digest
  `520ed6035a1af94b32cef60bd086d61f4443caabbba2f5d1197f06368832e485`,
  with zero missing/prohibited matches and three release blockers.
- No solver, package installation or external action occurred.

## Next checkpoint

Perform a compact end-to-end pre-close audit of all trace outputs, unresolved
actions, manifests and claim boundaries; produce a dated closure snapshot but
keep the automation active until the planned 10-hour window is reached.

## 04:42–05:02 — bounded pre-close snapshot

- Added a deterministic pre-close snapshot and focused direct test. The
  snapshot records 4.667 elapsed hours at the heartbeat checkpoint and remains
  explicitly incomplete: `closure_complete=false`, `submission_ready=false`,
  `solver_authorized=false`, H115 `nonpassing`.
- Unified the archive count at 101 files across the manuscript, reporting
  checklist, author form, Chinese handoff, inventory and consistency checks.
- Refreshed the 31-file paper bundle, technical preflight, manuscript
  consistency, submission inventory and cross-document status consistency;
  every technical check passed while author/release blockers remained intact.
- The refreshed archive has 101 files, 1,657,951 bytes, digest
  `9f7f9afcd3c2c26d335c9da40587c727167be8d5540d62acdced24ec886da17b`,
  zero missing/prohibited matches, and the same three author-controlled release
  blockers (project licence, frozen revision and DOI).
- No solver, package installation, external upload, commit or push occurred.

## Next checkpoint

Continue the remaining non-solver window with journal-neutral claim-to-evidence
auditing and a compact regression inventory. Do not close the trace or remove
the heartbeat before the planned 10-hour window and all retained checks are
complete.

## 05:02–05:22 — negative-results and limitations audit

- Added an executable audit that cross-checks the 24-row H115 endpoint table,
  manuscript Results/Discussion, reviewer-risk register, Case079 mapping/QC
  audit and provenance/compliance audit.
- Confirmed that 12 failed H115 rows remain visible: four failures across the
  two effective-source grids and all eight nominal-source endpoints. The exact
  effective-grid axial-position and transverse-L2 failures, nominal worsening,
  post-hoc-registration prohibition and two-grid non-convergence boundary are
  all retained in the manuscript.
- Confirmed that the unvalidated mapping/segmentation/engineering-target limits
  and private PhysioNet consent/access confirmation remain explicit.
- The focused direct test passed. This reporting-bias safeguard does not change
  `submission_ready=false` or upgrade the H115 result.

## Next checkpoint

Audit numerical values and units copied from machine-readable tables into the
manuscript and legends, then retain a compact mismatch report. Continue without
a solver unless genuinely new H115 complex-source evidence appears.

## 05:22–05:42 — manuscript numeric-transcription audit

- Added a source-derived scalar audit against the retained Case079 reference
  pair, PML pair and completed CFL0.1 baseline analysis.
- Verified manuscript transcription and units for target/global ratios,
  peak-to-target distances, target and global pressures, relative changes, four
  PML field-difference values, and the CFL L2/L-infinity and target-pressure
  changes.
- Verified that the CFL statement remains baseline-only and that simulated MPa
  values are not presented as validated intracranial exposure estimates.
- All numeric-transcription checks and the focused direct test passed. No
  manuscript number required correction.

## Next checkpoint

Audit figure legends and table captions against their manifests, including
coordinate/projection definitions and the pressure-field definition. Preserve
the nonpassing and engineering-only boundaries.

## 05:42–06:02 — figure/table caption semantics audit

- Added an executable audit covering all five paper-facing figure/table
  artifact groups.
- Confirmed that Figure 2 discloses the maximum projection, k/z direction,
  target-relative coordinates, shared scale and non-slice interpretation;
  Figure 4 discloses signed PML subtraction, crop-origin alignment and its
  single-perturbation/non-convergence boundary.
- Confirmed that the H115 supplementary captions preserve source-relative and
  secondary-sensitivity semantics, do not replace the unshifted primary result,
  and do not misdescribe amplitude averaging as complex-pressure deconvolution.
- Confirmed that Supplementary Table 1 retains the nonpassing verdict despite
  package integrity, while Table 2 retains machine-level non-paper-grade flags.
- All caption-semantic checks and the focused direct test passed; no caption
  correction was required.

## Next checkpoint

Consolidate the three new audits into the local archive candidate in one batch,
refresh all counts/hashes and rerun the bounded preflight chain. Keep author
actions and the H115 nonpassing verdict unchanged.

## 06:02–06:22 — audit consolidation and full bounded refresh

- Added the negative-results, numeric-transcription and caption-semantic audit
  scripts, focused tests and reports to the local archive specification.
- Refreshed the manuscript, author form, Chinese handoff, reporting checklist,
  inventory and validators to one canonical 113-file count.
- The archive now contains 113 files and 1,680,036 bytes with digest
  `3acb55da7b1f82f614bdb42e85836c3e8d3bde5512445106e4b167367ec71f25`;
  no file is missing and no prohibited prefix is included.
- The 31-file paper bundle, manuscript consistency, 29-check technical
  preflight, journal-neutral inventory and cross-document status consistency
  all pass. Six focused direct tests pass.
- At the 06:02 checkpoint, elapsed work is 6.001/10 hours;
  `closure_complete=false`, `submission_ready=false`, `solver_authorized=false`.
  The same three author-controlled release blockers remain.

## Next checkpoint

Use the remaining window for journal-neutral reproducibility instructions and
an executable-reader path audit, then repeat a bounded final regression near
the 10-hour mark. Do not infer successful physical validation.

## 06:22–06:42 — reviewer non-solver reproduction path

- Added a journal-neutral reviewer guide that separates compact evidence
  reconstruction from long k-Wave solver reproduction.
- The guide records both external dataset DOIs/access routes, restricted
  Case079 exclusions, archive hash locations, scratch-output commands and the
  three unresolved release controls.
- Added an executable audit confirming that seven referenced validation/audit
  scripts exist and are already present in the compact candidate, all outputs
  are directed to scratch paths, and no `--execute` solver command appears.
- Confirmed that the route preserves `submission_ready=false`, the H115
  nonpassing verdict and the distinction between file identity and scientific
  validity. The focused test passed after one line-wrap-tolerant matcher fix.

## Next checkpoint

Audit the repository-facing README/runbook for stale maturity, test-count or
paper-readiness language that could contradict the submission packet. Make only
bounded documentation corrections supported by current evidence.

## 06:42–07:02 — repository entry-document correction

- Updated README status from 2026-08-10 to 2026-08-29 and replaced the stale
  interrupted-CFL statement with the retained recovered baseline result.
- Added the H115 6/8, 6/8 and nominal 0/8 verdicts, explicit
  `submission_ready=false`, author/release blockers and no-solver boundary at
  the repository entry point.
- Corrected the misleading “11 test modules” description: 112 test files are
  present, but the legacy unittest command does not execute every pytest-style
  file. The full test lock/report remains an explicit pre-release action.
- Added the reviewer non-solver guide to the documentation map and marked the
  RUNBOOK as operational recipes rather than solver authorization; older
  example input paths are explicitly cautioned.
- The entry-document audit and focused test pass. No physical parameter,
  solver configuration or output was changed.

## Next checkpoint

Check current manuscript/title/abstract wording for journal-neutral scope and
search for residual positive-validation or convergence phrasing outside quoted
or explicitly negated contexts. Record any false positives rather than editing
unsupported claims.

## 07:02–07:22 — title/abstract and overclaim audit

- The first scope scan found a reporting omission: the abstract described the
  favourable Case079/PML findings but omitted the manuscript's substantial H115
  nonpassing branch.
- Added one evidence-backed abstract sentence reporting effective-source 6/8 at
  both grids, nominal equal-amplitude 0/8 and the nonpassing external-comparison
  verdict. The title and main Case079 conclusion were not strengthened.
- Added an executable claim-scope audit covering title, abstract, Methods,
  Discussion and Data availability. No forbidden positive-validation,
  convergence, pressure-accuracy, clinical-safety or submission-ready phrase
  remains.
- Stabilized README test wording at “more than 100 files” so future focused-test
  additions do not create false stale-count failures; it still explicitly says
  the legacy unittest command is not a full-suite claim.
- Claim-scope and entry-document focused tests pass.

## Next checkpoint

Recompute manuscript inventory after the abstract addition, check the abstract
word count against a conservative journal-neutral 250-word ceiling, and audit
whether all six author queries still map to the author-action ledger.

## 07:22–07:42 — abstract length and author-query ownership

- Recomputed the amended abstract at 244 words, below a conservative
  journal-neutral 250-word ceiling. The whole draft is approximately 4,303
  English tokens/words including references; target-journal rules remain
  unevaluated because no journal is selected.
- Added an executable mapping from all six pre-submission author queries to
  owned ledger actions, including required evidence and submission/release
  impact.
- Expanded A05 without adding a new action so the scientific lead explicitly
  owns the single-case numerical-scope decision in addition to mapping,
  segmentation and target boundaries. Q6 maps separately to licence, immutable
  revision and DOI actions.
- All six queries are covered by pending actions; the focused audit test passed
  and `submission_ready=false` remains unchanged.

## Next checkpoint

Review the author metadata form and decision sheet against the action ledger for
missing declaration fields or contradictory GO/NO-GO wording, then consolidate
the remaining new audits into the archive near the final window.

## 07:42–08:02 — author materials and decision consistency

- Found and corrected one author-material omission: A09 (freeze the
  development/test dependency lock and retain a full non-solver test report)
  was absent from the decision sheet, author form and Chinese handoff.
- Propagated the expanded A05 single-case numerical-scope boundary into all
  author-facing materials and added an explicit sign-off that absent CT
  grid/domain and TR-CFL evidence must not be described as completed.
- Added an executable A01–A10 coverage audit. Every pending action now maps to
  author-facing fields with a responsible evidence route.
- Confirmed the layered decisions remain: reconstruction GO, internal bounded
  draft GO, H115 physical validation NO-GO, Case079 quantitative/anatomical
  validation NO-GO, public release NO-GO and journal submission NO-GO.
- The focused consistency test passed; private evidence is still required and
  no action was marked complete.

## Next checkpoint

Batch the reviewer guide and four later audits into the compact archive,
refresh hashes/counts and preflight, then reserve the remaining window for final
governance validation and an honest 10-hour closeout.

## 08:02–08:22 — late-stage audit consolidation

- Added the reviewer reproduction guide plus reviewer-path, entry-document,
  claim-scope, abstract/query and author-material audit scripts, tests and
  reports to the archive specification.
- Unified manuscript, checklist, author form, Chinese handoff, inventory and
  validators at 134 candidate files.
- The refreshed candidate contains 134 files and 1,716,779 bytes with digest
  `ac2515be6c069ac7980dad19c788f1c543832547929ffe3a836af8982917d20b`;
  missing and prohibited counts remain zero.
- All five late-stage audits, five focused tests, the 31-file bundle, 29-check
  technical preflight, manuscript consistency, inventory and cross-document
  status consistency pass.
- The 08:02 snapshot records 8.002/10 hours, `closure_complete=false`,
  `submission_ready=false` and `solver_authorized=false`; the licence,
  immutable-revision and DOI blockers remain.

## Next checkpoint

Run final governance validators and a compact archive/path integrity audit,
then prepare the final closure record only after the 10-hour window is reached.

## 08:22–08:42 — governance and independent archive integrity

- Refreshed the run ledger, evidence registry and Case079 reproducibility
  manifest validators; all report valid with zero failed checks.
- Added an archive-integrity validator and focused test to the candidate, while
  deliberately keeping the generated integrity report outside the archive to
  avoid a self-referential hash cycle.
- Independently rehashed all 136 candidate files and checked byte counts,
  repository-relative unique paths, CSV/JSON agreement, total size, content
  digest, exclusions, external dependencies and exact release blockers.
- The candidate is 1,722,038 bytes with digest
  `8e93893bf6c423cc3c1b6754d51b0ea93069c12562ec1c555db638f0705016a9`;
  the independent recomputation matches exactly, with zero mismatches.
- Status remains `passed_archive_integrity_blocked_release`, not release-ready;
  the 08:22 snapshot records 8.335/10 hours and remains incomplete.

## Next checkpoint

Refresh the final manuscript/preflight/inventory chain against the 136-file
candidate, then use the last hour for a final status snapshot and trace closure
without changing author-controlled blockers.

## 08:42–09:02 — final-chain ordering correction

- Ran manuscript consistency, 29-check technical preflight, 31-file paper
  bundle generation/validation, archive generation, inventory, cross-document
  status and independent archive integrity in dependency order.
- The first integrity pass correctly detected two changed inventory hashes. The
  cause was deterministic ordering: inventory outputs are themselves archived,
  so regenerating them after the archive manifest makes that manifest stale.
- Corrected the final order to finalize inventory first, then generate the
  archive, followed only by non-archived status/integrity reports. No evidence
  or scientific result was changed.
- The second independent pass rehashed all 136 files with zero mismatch. Final
  candidate size is 1,722,038 bytes and digest is
  `99e37dbb5411b7f2181ef560abf64017f9154a03cb65b85e13267be2ba320c5e`.
- Technical package status remains passed-author-inputs-pending; archive status
  remains blocked by licence, immutable revision and DOI.

## Next checkpoint

At the 09:02 checkpoint, run the complete bounded submission-focused direct
test set and final governance summaries. At 10 hours, freeze the closure
snapshot, close the EDD trace with retained blockers, and remove the heartbeat.

## 09:02–09:22 — complete submission-focused direct tests

- Ran the full bounded submission-focused direct set: 14/14 passed.
- Coverage includes dependency licences, five-group figure/table traceability,
  pre-close state, inventory/status consistency, negative-result retention,
  numeric transcription, caption semantics, reviewer reproduction path,
  repository entry documents, claim scope, abstract/query ownership, author
  material decisions and independent archive integrity.
- Re-read the current governance summaries: run ledger, evidence registry and
  reproducibility manifest are valid; technical preflight and status
  consistency pass; archive integrity passes while release remains blocked.
- This is deliberately not described as a fresh full repository test suite:
  the pinned development/test lock and retained full non-solver test report are
  still author/release action A09.
- No solver or external write occurred.

## Next checkpoint

Preserve the now-stable archive. Use the remaining window to prepare the final
EDD gap feedback and closure summary without adding files to the candidate or
changing its digest. Close only at or after 10.0 hours.

## 09:22–09:42 — EDD gap-feedback preparation

- Mapped all six Evidence Brief acceptance criteria to retained artifacts; all
  are technically satisfied within the non-solver scope.
- Added pre-close gap feedback outside the frozen candidate archive, recording
  the 136-file digest, independent integrity pass, 31-file bundle, zero
  preflight failures and 14/14 focused direct tests.
- Retained six substantive gaps: nonpassing H115/source-drive evidence,
  unvalidated Case079 mapping/QC, private PhysioNet confirmation, journal and
  author declarations, licence/revision/DOI, and the full test lock/report.
- The JSON structure and all criteria were checked. It remains explicitly
  `preclose_pending_time_window`; the trace and heartbeat stay open.

## Next checkpoint

At 10 hours, update only the closure timestamp/status, run a final read-only
status and process check, regenerate governance indexes if needed, then delete
the heartbeat. Do not alter the stable archive candidate.

## 09:42–10:02 — final read-only closure

- Reached the planned 10-hour window at 2026-08-29 10:02 Asia/Shanghai.
- Rechecked the stable candidate and independent integrity report: 136 files,
  1,722,038 bytes, digest
  `99e37dbb5411b7f2181ef560abf64017f9154a03cb65b85e13267be2ba320c5e`,
  with zero recorded mismatch.
- Rechecked cross-document status consistency and retained all three release
  blockers. No solver was started and no physical default was changed.
- Closed the technical trace with six explicit author/external-evidence gaps.
  `submission_ready=false`; H115 remains nonpassing; no public release or
  journal submission is authorized.
- The archived pre-close snapshot remains immutable historical evidence; this
  final closure record is deliberately outside the stable candidate.
- The archive manifest includes the Evidence Brief JSON, so its pre-close
  `in_progress_non_solver` value was intentionally preserved. Final state is
  recorded only in the non-archived gap-feedback and final-closure records.
- A final governance-regeneration attempt was stopped after existing output
  files rejected writes (`PermissionError`); no workaround or repeated loop was
  used. The retained 08:22 validation snapshots remain readable and report the
  evidence registry, run ledger and reproducibility manifest as valid with zero
  failed checks.
