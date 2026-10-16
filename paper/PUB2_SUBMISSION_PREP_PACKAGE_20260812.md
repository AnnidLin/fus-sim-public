# PUB.2 submission preparation package

> Prepared from validated artifacts only. This package does not upgrade the
> current `standard` simulations to paper-grade numerical convergence.

## Recommended paper positioning

### Conservative manuscript now

**Type:** reproducible computational-methods case study / technical validation.

**Working title:**

> CT-informed full-wave time reversal improves focal localization in a
> controlled transcranial ultrasound simulation workflow

**One-sentence argument:**

> In a frozen CT-informed Case079 configuration, matched full-wave time reversal
> relocated the dominant acoustic peak towards the intended target, and the
> localization result was insensitive to the tested PML perturbation, within a
> single-case engineering evidence boundary.

This version can be drafted now. It must not use `validated clinical`, `safe`,
`accurate in-situ pressure`, `generalizable`, or `numerically converged`.

### Stronger manuscript after targeted additions

Retain the same central argument, but add matched CFL, grid/domain sensitivity
and independent anatomy. This would support a broader robustness claim and
reduce the principal reviewer objections: one-case evaluation and incomplete
numerical convergence.

## Proposed paper architecture

1. **Introduction** — skull-induced phase distortion, need for reproducible
   patient-specific targeting, and the gap between attractive refocusing results
   and auditable numerical evidence.
2. **Workflow and frozen configuration** — CT mapping, coordinate/entry-plan
   traceability, bowl source construction, baseline and TR stages, and EDD gates.
3. **Matched reference result** — baseline-versus-TR localization endpoints.
4. **Boundary sensitivity** — matched PML12/PML16 fields on an aligned common
   domain.
5. **Reproducibility and resource behavior** — exact historical field replay,
   low-memory refocus, monitoring and package validation.
6. **Limitations** — standard preset, incomplete CFL/grid/domain evidence,
   single anatomy, no experimental ground truth and no safety inference.

## Claim policy

| Proposed claim | Evidence | Decision |
|---|---|---|
| TR improved spatial localization in Case079 | target/global 0.477400→0.984864; peak distance 57.379→2.487 mm | Supported |
| TR increased target pressure in this run | 1.891→2.554 MPa (+35.04%) | Supported as simulated pressure only |
| TR reduced the global maximum pressure | 3.962→2.593 MPa (−34.54%) | Supported; interpretation must remain model-specific |
| PML12→16 did not change the localization conclusion | paired baseline/TR field differences and unchanged peak distance | Supported for this perturbation and case |
| Results are numerically converged | CFL/grid/domain chain incomplete | Not supported |
| Absolute intracranial pressure is accurate | no experimental ground truth; mapping uncertainty remains | Not supported |
| Method generalizes across subjects | one anatomy | Not supported |
| Method is clinically effective or safe | no biological or exposure validation | Prohibited |

## Figures and tables

### Minimum viable set

- **Figure 1 — Reproducible workflow:** CT acoustic model → frozen entry plan →
  matched baseline/TR → common-domain sensitivity analysis → EDD validation.
- **Figure 2 — Main localization result:** matched baseline and TR pressure
  slices with identical coordinates, target marker, global peak marker and
  shared colour policy.
- **Figure 3 — Quantitative endpoints:** target/global ratio, peak-to-target
  distance, target pressure and global peak for baseline and TR.
- **Figure 4 — PML sensitivity:** PML12/PML16 difference maps for baseline and TR
  plus relative L2/L∞ summary.
- **Table 1 — Frozen numerical parameters:** use
  `paper/tables/PUB2_FROZEN_PARAMETERS_20260812.csv`.
- **Table 2 — Primary results and PML sensitivity:** use
  `paper/tables/PUB2_PRIMARY_RESULTS_20260812.csv`.

### Additions for the stronger version

- CFL0.2/CFL0.1 matched baseline/TR panels.
- At least one grid refinement and expanded-domain comparison.
- Independent-case distribution plots rather than a second anecdotal image.
- Failure-case panel if an independent case does not refocus comparably.

### Existing figure quality gate

The original baseline/TR slice PNGs are analysis diagnostics, not final paper
figures. Visual review found overlapping target/global-peak labels, inconsistent
titles and no documented shared colour scale. Submission-oriented replacements
were generated directly from the accepted NPZ fields in
`paper/figures/pub2_20260812`, with:

- identical crop, orientation and physical-coordinate axes;
- one declared pressure definition and shared scale for matched comparisons;
- non-overlapping target/global-peak symbols and a separate legend;
- panel labels, scale bars and export at journal-ready vector or high-resolution
  raster quality;
- a scripted figure manifest linking every panel to its source artifact hash.

The remaining figure task is journal-specific typography/layout adaptation after
the target journal is selected; the scientific panels and provenance manifest
are now available.

## Numerical-quality interpretation

The completed runs used the project `standard` preset. The generated quality
metadata explicitly reports `is_paper_grade=false` and
`preset_is_not_paper_grade`. In project terms, the current result is therefore
engineering validation, not a completed paper-grade convergence package.

The `paper_grade` preset does not by itself create convergence: it requires a
grid-convergence report, PML review, CFL review and environment record. Repeating
the identical physics solely to change the preset label would add little
evidence. The efficient route is to complete the missing sensitivity dossier,
then run or designate a final frozen configuration under the paper-grade gate.

## Prioritized evidence plan

### Priority A — no expensive solver work

1. Generate publication figures from the accepted reference and PML fields.
2. Complete the ITRUSST-style reporting checklist: tool/version, material
   assignment, transducer geometry and positioning, grid/time/PML/CFL,
   spatial-peak location and target pressure.
3. Convert the current scaffold into full Introduction, Methods, Results and
   Discussion sections with claim–artifact links.
4. Export citations and write a reproducibility/data-availability statement.

### Priority B — minimum numerical strengthening

1. Recover CFL0.1 baseline in a new output root after a Windows pending-restart
   gate.
2. If the paper claims TR robustness to time step, also run a fresh matched
   CFL0.1 calibration/refocus chain; baseline-only CFL cannot establish TR
   robustness.
3. Run one expanded-domain matched pair or explicitly narrow the manuscript to
   PML-only boundary sensitivity.
4. Perform a blinded comparison using the frozen endpoints before interpreting
   whether the result is favourable.

### Priority C — strongest scientific gain

1. Add at least 3–5 independent anatomies if available and licensed; report the
   distribution and failures, not only the best case.
2. Add experimental or public-reference comparison for pressure/location if
   feasible.
3. Evaluate material-mapping uncertainty separately from numerical uncertainty.

## Stop/go rules for future computation

- Do not tune parameters to improve the reported endpoint after looking at the
  result.
- Every new cell changes one frozen factor and has an Evidence Brief amendment.
- Predefine endpoint tolerances before execution; report failures as results.
- Do not start a long run while Windows reports a pending restart.
- Stop escalating computation if independent cases reverse the main effect;
  analyze the failure boundary instead.

## Submission-readiness scorecard

| Dimension | Current | Needed for stronger paper |
|---|---|---|
| Main effect | Strong single-case effect | Replication distribution |
| Matched protocol | Passed | Preserve |
| PML sensitivity | Passed for baseline and TR | Preserve |
| CFL sensitivity | Baseline CFL0.2-to-0.1 passed frozen limits; matched TR CFL remains incomplete | Matched baseline/TR preferred for a TR time-step robustness claim |
| Grid/domain sensitivity | Incomplete for PUB.2 | At least one controlled level each |
| Reproducibility | Strong artifact and hash trail | Submission snapshot/DOI |
| External validation | Public benchmark lane exists, not direct case ground truth | Experimental/reference comparison |
| Claim discipline | Explicit engineering boundary | Preserve through abstract/title |

## Recommended decision

Begin writing the conservative manuscript and figures now. Treat additional
computation as falsification-oriented strengthening, not a search for prettier
numbers. The shortest meaningful upgrade is a clean matched CFL sensitivity;
the highest scientific-value upgrade is independent-case replication.
