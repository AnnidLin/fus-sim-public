# fus-sim Workspace Closeout — 2026-08-23

> Historical closeout snapshot. Superseded for H115 source/registration evidence by `TRACE-20260825-001`, the dated coordinate audit, and `paper/UCL_H115_PAPER_READINESS_20260823.md` as amended 2026-08-25. The body below is preserved as the state known on 2026-08-23 and contains the pre-correction y-width result.

## Outcome

The current computational-methods-paper phase is closed at a reproducible engineering-evidence boundary. No solver or recurring monitor is active. The repository is not submission-ready and does not support clinical, safety, efficacy, absolute-pressure-accuracy, formal CT convergence or population-generalization claims.

## Current evidence state

| Workstream | State | Claim boundary |
|---|---|---|
| PUB.1 ITRUSST benchmark | BM1/BM3/BM4 comparisons and Phase-A summary complete | Public engineering benchmark reproduction; measured BM3/BM4 differences remain |
| Case079 matched baseline–TR | Fresh dx0.75/PML12 reference pair complete | Single-case localization observation: target/global `0.477400→0.984864`, peak distance `57.379→2.487 mm` |
| PML sensitivity | Matched PML12/PML16 baseline and TR evidence complete | Tested boundary perturbation is small; not formal convergence |
| CFL sensitivity | Recovered baseline CFL0.2→0.1 comparison passed the frozen contract | Baseline only; TR CFL robustness and formal convergence remain open |
| UCL H115 external comparison | dx0.50 and dx0.30 homogeneous-water packages complete | Both attempts fail the same three preregistered measurement endpoints; not successful validation |
| H115 water-grid sensitivity | Physical-coordinate-aligned two-grid comparison complete | Correlation `0.999881`, scaled L2 `1.310%`, axial peak shift `0 mm`; two grids are not asymptotic convergence |
| BBB planner | WP0–WP6 software prototype retained | Registered anatomy, hardware, PNP/MI, microbubble and PCD inputs remain unavailable |

## External-validation result

The dx0.30 H115 refinement completed in 6.41 h within the device gates. Refinement preserved the simulated field but did not repair the held-out measurement mismatch. At dx0.30, axial peak-position error was `2.177 mm`, transverse normalized L2 was `15.469%`, and transverse y-width error was `+28.144%`; all exceeded their frozen limits. The next scientific uncertainty is source representation and measurement registration, not further blind grid refinement.

## Paper state

Ready for bounded drafting:

- solver and reproducibility Methods;
- the single-case Case079 baseline–TR localization result;
- PML and baseline-CFL perturbation observations;
- the nonpassing H115 external-comparison result and two-grid sensitivity figure;
- explicit limitations and failure governance.

Still blocking a submission-grade positive validation claim:

- a source representation faithful to the documented H115 two-ring geometry;
- hydrophone aperture averaging and coordinate-registration uncertainty;
- an independent validation dataset after model development is frozen;
- CT-domain grid/domain sensitivity, TR CFL sensitivity, continuous mapping uncertainty and an additional anatomy;
- reference-manager-complete citations and final consolidated tables/figures.

The controlling paper-use audit is `paper/UCL_H115_PAPER_READINESS_20260823.md`. The manuscript evidence map is `paper/MANUSCRIPT_EVIDENCE_MAP.md`.

## Governance and reproducibility

- Run ledger: 62 entries, including both H115 water runs; zero paper-grade runs; medical/safety conclusions disabled.
- Evidence registry: 165 entries, zero missing artifacts at the final refresh.
- H115 package state: package integrity passed with a guarded nonpassing physical observation.
- Figure PNG/PDF hashes match their manifest.
- Bounded broad regression: 351/351 tests passed; one input-heavy historical NLM model audit is explicitly excluded from this bounded regression and recorded in H115 gap feedback.
- Evidence registry, run ledger and reproducibility manifest validators passed at closeout.

## Workspace and Git state

- Branch: `public-prep`.
- Last pre-closeout commit: `5173622`.
- Current H115 code, tests, paper files and governance changes remain uncommitted because the user requested project closeout, not a Git commit or push.
- Existing untracked `tmp/` and `_amend_sensitivity_queue.py` were preserved; their ownership and deletion scope were not assumed.
- Raw CT data, historical outputs, ledgers, registries and reproducibility records were not deleted or overwritten.

## Unique next action

Do not start another pressure run. First create a new Evidence Brief for a non-solver H115 source-model/registration study. Freeze the two-ring element geometry, phase/amplitude assumptions, hydrophone spatial averaging, coordinate uncertainty and acceptance policy without tuning against the current held-out profiles. Only after that review should one highest-information propagation be considered.

## Recovery entry

Read in this order:

1. `WORKSPACE_CLOSEOUT_20260823.md`
2. `AI_PROJECT_SNAPSHOT.md`
3. `paper/UCL_H115_PAPER_READINESS_20260823.md`
4. `paper/MANUSCRIPT_EVIDENCE_MAP.md`
5. `AI_TODO.md`
6. `HANDOFF_LOG.md` (`TRACE-20260823-001`)
