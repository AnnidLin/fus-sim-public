# Submission decision sheet

Trace: `TRACE-20260829-001`  
Decision date: 2026-08-29  
Overall state: **NOT READY TO SUBMIT**

## Decision by layer

| Layer | Decision | Evidence | Meaning |
|---|---|---|---|
| Technical reconstruction | GO | H115 fresh reconstruction, 31-file paper bundle and 5-group traceability matrix pass | Reported retained outputs can be reconstructed and traced within the documented scope |
| Manuscript claim discipline | GO for bounded draft | Title/abstract/Methods/Results/limitations lint and technical preflight pass | A computational-methods case-study draft can be circulated internally |
| H115 physical validation | NO-GO | Effective dx0.50 and dx0.30 each pass 6/8 frozen endpoints | Must remain a nonpassing external comparison |
| Case079 quantitative/anatomical validation | NO-GO | Binary mapping is unvalidated; target is engineering-only; segmentation/registration QC is incomplete | Do not claim subject-specific accuracy, anatomical targeting or validated pressure |
| Public data/code release | NO-GO | Compact candidate is complete but `archive_ready=false` | Licence, immutable revision and DOI are still required |
| Journal submission | NO-GO | Target journal, authorship/declarations and restricted-data confirmation are unresolved | Author-owned fields must be completed from documentary evidence |

## What can be stated now

In one frozen Case079 computational configuration, time reversal improved the
simulated focal-localization endpoints, and that localization conclusion was
insensitive to the tested PML perturbation. A baseline-only CFL perturbation
passed its frozen limits. The separate H115 branch provides a transparent
nonpassing external comparison and a two-grid sensitivity observation.

## What cannot be stated

- successful H115 validation or accurate reproduction of the H115 ring drive;
- formal numerical convergence or TR time-step robustness;
- validated Case079 HU mapping, segmentation or anatomical registration;
- experimentally accurate intracranial pressure;
- clinical efficacy, safety or cross-subject generalization;
- public release readiness before the licence/revision/DOI gates close.

## Minimum author actions before submission

1. Select the target journal/article type and adapt limits and declarations.
2. Confirm author order, affiliations, ORCIDs, CRediT roles, funding and conflicts.
3. Privately verify the PhysioNet registered-access record and approve any
   journal-specific consent/waiver wording without publishing private records.
4. Approve the explicit unvalidated-engineering wording for mapping, target,
   segmentation and single-case numerical scope, or defer submission until new
   independent evidence exists.
5. Select the project licence, freeze an immutable revision and mint/report the
   archive DOI; regenerate the manifest from that revision.
6. Freeze a development/test dependency lock and retain a full non-solver test
   report; focused direct tests do not substitute for this release check.
7. Perform final line-numbered manuscript, figure and supplementary review while
   retaining every unfavourable endpoint.

## Computation decision

No further k-Wave run is authorized by this trace. The missing H115 per-ring
complex acoustic calibration/hologram was not found, so another pressure solve
would not close the main source-model gap. Additional computation requires a
new Evidence Brief, frozen contract, exact dry-run and device gate.
