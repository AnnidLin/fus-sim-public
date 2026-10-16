# fus-sim Workspace Closeout — 2026-07-29

## Outcome

The active scientific and platform work through 2026-07-29 is consolidated here. The repository remains an engineering simulation workspace, not a clinical planning system. No k-Wave process or recurring monitor is active at closeout.

## Current platform state

| Workstream | State | Boundary |
|---|---|---|
| k-Wave execution and monitoring | Operational: stage-aware monitor, dynamic emergency ceiling, low-token attention files | Long runs still require EDD and dry-run resource gates |
| Case079 acoustics | Free-field convergence, thick-skull diagnostics, TR and matched frequency studies available | Baseline global peaks remain off target in the latest matched 250 kHz factorial |
| BBB planner | WP0-WP6 software prototype complete | Registered anatomy, physical hardware, waveform PNP/MI, microbubble and PCD inputs are unavailable |
| NLM public case | Public post-mortem engineering proxy pipeline and quick/TR runs available | Not a patient cohort or clinical dataset; some source configurations are mixed-medium |
| Governance | Ledger, evidence registry, reproducibility manifest/package regenerated | Claims remain engineering-level unless a stronger gate is explicitly passed |
| Literature/paper assets | Knowledge base and manuscript-support packages exist | Modified literature matrices require normal review; no external expert validation is implied |

## Latest reliable findings

1. The 2026-07-28 H3/wide-domain raw outputs are preserved, but their trajectory-only and domain-only causal interpretations are blocked by protocol drift. See `outputs/250khz_h3_wide_comparability_audit_20260729/comparability_audit.json`.
2. The matched 2x2 Case079 250 kHz factorial completed all four cells with background-only sources and no unexpected protocol drift. See `outputs/factorial_250khz_trajectory_transducer_20260729/factorial_report.json`.
3. The large ap60/r74.435 transducer is the dominant baseline target/global factor. H3 trajectory is detrimental with the small transducer and beneficial with the large transducer, so the effect is an interaction rather than a universal trajectory advantage.
4. All four matched baseline global peaks remain approximately 56-58 mm from the target. Baseline target dominance is not established.
5. The matched 500 kHz TR PML16 and CFL0.1 perturbations passed their preregistered pause thresholds, but two perturbations do not constitute formal numerical convergence.

## Workspace organization decisions

- Root `test_*.py` files were moved into `tests/`; the standard command is `python -m unittest discover -s tests -t . -p "test_*.py"`.
- `scratch/` remains an ignored local evidence area because it contains historical launch scripts, PID records and C++ cross-validation probes.
- `.tmp/`, root `__pycache__/`, three empty malformed `outputs...` directories and a zero-byte geometry log were removed after target verification.
- Stage-specific scripts remain at the root for this closeout because current reports and governance files still reference their names. A later archive pass requires a reference-preserving migration, not a blind move.
- `governance_recent_evidence.py` is the declaration source for the 2026-07-24 through 2026-07-30 run and artifact additions consumed by the ledger and registry generators.

## Governance state

- Run ledger: 54 entries after adding 15 complete runs from 2026-07-24 through 2026-07-29.
- Evidence registry: 130 entries after adding the 2026-07-30 H3-large matched baseline–TR brief, report and feedback.
- The reproducibility manifest and final package were regenerated after the ledger and registry update.
- The original H3/wide report is retained with a warning boundary; the independent comparability audit controls causal interpretation.

## Next scientific entry — completed 2026-07-30

The H3-large baseline-versus-TR entry was completed by strict reuse of existing pressure outputs after a fresh Evidence Brief, configuration/input/artifact equivalence audit and two dry-run quality gates. No redundant pressure propagation was launched. Target/global changed from 0.487821 to 0.969082 and global-peak distance to target from 56.290 to 6.230 mm. See `outputs/h3_large_matched_baseline_tr_20260730/matched_comparison.json`.

Keep pressure execution paused. Do not proceed directly to standard/paper-grade escalation, thermal simulation, clinical dosing, broad trajectory batches or a new public-case claim without a separate EDD packet and explicit compute authorization.
## Verification and local history

- Full unit suite: 201 tests passed.
- Syntax audit: 300 non-legacy Python files parsed successfully.
- Ledger, evidence registry, reproducibility manifest, final package and public-case governance validators passed.
- Local logical commits: `d19def9` (BBB/NLM platform), `3f4c66a` (acoustic monitoring and sensitivity), `f193d92` (literature knowledge base), followed by this workspace-governance closeout commit.
- No remote push was performed.
- 2026-07-30 follow-up verification: 203 tests, 302-file AST scan and five governance validators passed.
