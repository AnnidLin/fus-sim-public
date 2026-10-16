# Acoustic-Field-First Paper-Grade Execution Plan

> **Historical supporting plan.** Since 2026-07-31, `PAPER_EXECUTION_MASTER_PLAN.md` is the only active execution plan. Use this file for background requirements, not to authorize or reprioritize work.

Date: 2026-07-11

## 1. Recommended Paper Scope

### Working question

Can source-safe, CT-informed geometry matching and phase correction improve target delivery while controlling skull-entry hotspots in patient-specific transcranial tFUS, and are the conclusions robust to numerical resolution and skull-property mapping?

### Fastest defensible manuscript

Use a **single-case, multi-trajectory computational methods study** on Case 079:

- 500 kHz low-intensity tFUS;
- three source-safe skull-crossing trajectories spanning low, medium, and high path difficulty;
- uncorrected radius-matched bowl versus corrected segmented-aperture phase control;
- one representative full-wave time-reversal comparison as a reference method;
- free-field source validation, CT mapping sensitivity, and numerical convergence;
- pressure-field outcomes only until the acoustic field is locked.

This can support a simulation-methods or thesis-level paper. It cannot support population, clinical-safety, or experimental-accuracy claims because only one CT and no hydrophone/skull measurement pair are available.

### Explicitly postponed

- Pan/Sun-style 82 physical circular elements, BBB microbubbles, PCD, and thrombolysis;
- thermal dose optimization before the acoustic candidate is locked;
- AI surrogate, synthetic CT, poroelastic/shear-wave solver, and profile promotion;
- broad frequency, aperture, phase-model, and apodization factorial sweeps.

The current 15x15 source is a **195-active-patch segmented circular aperture**, not the 82-element random array in the Pan/Sun theses. The paper must use the correct name.

## 2. Reference Alignment

| Evidence source | What to reproduce | What not to claim |
|---|---|---|
| Gao 2022 local thesis | 500 kHz, 1 MPa source convention, CT skull model, source-position screening, grid checks | Numerical equality across different CT anatomy |
| Pasquinelli 2020 | Free-field focal position, peak gain, axial/lateral profiles and -6 dB widths | Experimental calibration without hydrophone data |
| Jin 2020/Kranion | Corrected versus uncorrected pressure, focal displacement, phase profile and pressure gain | Clinical-array equivalence |
| Montanaro 2021 | Sensitivity to skull heterogeneity/mapping assumptions | Accuracy ranking without experimental ground truth |
| Pan/Sun local theses | Time-reversal concept and phased excitation as a reference method | BBB, MI, thrombolysis, or exact 82-element replication |
| ITRUSST/BabelBrain local notes | PPW, CFL, PML, in-situ pressure definitions and standardized reporting | Clinical safety from pressure simulation alone |

## 3. Frozen Primary Outcomes

Primary outcomes:

1. target-window peak pressure normalized by matched free-field peak;
2. target-window peak distance to target;
3. post-entry/global skull peak and its material label;
4. target-to-post-entry and target-to-global pressure ratios;
5. -6 dB focal volume, axial length, and lateral width;
6. focal centroid error and secondary-lobe ratio.

Secondary outcomes:

- phase-delay range and spatial distribution;
- source safety and source-patch occupancy;
- runtime, memory, grid size, PPW, PML, CFL, and environment record;
- waveform-derived target PNP. MItc remains blocked unless brain-wide maximum PNPtc is recorded.

Never optimize or select a method using only target pressure. Selection requires target delivery, focal localization, and skull-hotspot control together.

## 4. Experimental Route

### Gate A: Freeze source model and trajectories

No pressure runs.

1. Freeze Case 079 target and CT resolution chain.
2. Select exactly three skull-crossing trajectories on the same target-centered source sphere using geometry only, so source-to-target distance and transducer curvature remain fixed:
   - background-only source voxels;
   - skull crossing present;
   - no air/sinus/eye intersection;
   - incidence angle preferably below 30 degrees because the current fluid solver omits shear conversion;
   - deliberately span skull path length/incidence difficulty.
3. Freeze one final source geometry before paper runs. Keep source-to-target distance, curvature radius, aperture, frequency, and source-pressure convention identical across trajectories; change only source direction/entry path.
4. Freeze two main methods:
   - `M0`: uncorrected radius-matched bowl;
   - `M1`: corrected segmented aperture using the final phase method.
5. Reserve full-wave time reversal as `M_TR` on one representative trajectory only.

Gate A passes only when all three trajectories are source-safe and the source/target geometry is resolution-consistent.

### Gate B: Free-field source closure

Run the final source without skull at dx 0.75 and 0.5 mm. Do not reuse the ap30/r35 calibration for an r74 source.

Required outputs:

- focus coordinate and distance error versus geometric focus;
- peak gain relative to source pressure;
- axial and lateral pressure profiles;
- -6 dB axial/lateral widths and focal volume;
- boundary-reflection review.

Acceptance:

- focal-position error <=5% of geometric focus distance;
- dx0.75 versus dx0.5 peak gain change <=5%;
- lateral width change <=10% and centroid shift <=1 mm;
- PML/boundary contamination absent.

If Gate B fails, correct the source model before any CT pressure batch.

### Gate C: Quick sequential screening

Use dx0.75 quick runs only for method selection. Existing Case 079 `(+5,0)` r74 single-bowl and corrected path-integral v2 runs may be reused as screening evidence.

For the other two trajectories, run `M0` then `M1`; stop a trajectory if source safety or target propagation fails. Add one geometric-phase ablation only on the representative trajectory if needed for the methods figure.

Candidate acceptance relative to `M0` on the same trajectory:

- target-window retention >=80%;
- skull/post-entry peak reduction >=20%;
- target-to-post-entry ratio improvement >=25%;
- target-window peak within 5 mm of target.

At least two of three trajectories must pass all criteria before expensive runs. Otherwise stop and redesign the correction method.

### Gate D: Full-wave time-reversal reference

On one medium-difficulty trajectory:

1. place a target point source and record complex 500 kHz response at active patches;
2. phase-conjugate the received field;
3. run the forward corrected field;
4. compare ray/path-integral phase, pressure, focal centroid, and -6 dB region with full-wave time reversal.

If `M1` is within 10% of time-reversal target pressure and within 1 mm focal-centroid error, use `M1` for all three final trajectories. Otherwise use time reversal for final correction, with a revised compute budget.

### Gate E: Final paper runs

Run only `M0` and the selected corrected method on all three trajectories at dx0.5 mm, PML12, CFL0.2, with full standardized outputs. These six runs form the main result table.

Do not call them paper-grade merely because the preset says `paper_grade`; Gate F must also pass.

### Gate F: Numerical robustness on one representative trajectory

Reuse its dx0.5 corrected run and add:

- dx0.75 corrected;
- dx0.375 corrected (8 PPW at 500 kHz in 1500 m/s medium);
- dx0.5/PML16;
- dx0.5/CFL0.1.

Acceptance:

- dx0.5 versus dx0.375: primary pressure metrics <=5% change, focal centroid <=1 mm, -6 dB dimensions <=10%;
- PML12 versus PML16: primary metrics <=2%, focal centroid <=0.5 mm;
- CFL0.2 versus CFL0.1: primary metrics <=2%, focal centroid <=0.5 mm.

If dx0.5 versus dx0.375 fails, add dx0.3 only after a new resource gate; otherwise report non-convergence and do not use paper-grade wording.

### Gate G: Skull mapping sensitivity

Do not run every profile. First build and inspect models without pressure:

- `simple_hu300` baseline;
- one literature-backed continuous HU mapping with closed alpha semantics;
- threshold variants 250 and 400 HU.

Select the two most different valid alternatives using skull volume, path sound speed, impedance, attenuation, and path length. On the representative trajectory at dx0.5, reuse the baseline and run only the two selected alternatives.

Report sensitivity; do not rank accuracy without hydrophone/skull ground truth. Primary metric variation above 20% must be treated as a major model uncertainty in the paper.

## 5. Adaptive Run Budget

| Block | New pressure runs | Typical CPU time | Decision value |
|---|---:|---:|---|
| Final-source free field, dx0.75/0.5 | 2 | 2-5 h | Blocks all CT work if source is wrong |
| Quick screening for two new trajectories | 4 | about 2 h | Eliminates weak methods cheaply |
| Optional representative ablation | 1 | about 0.5 h | Methods figure only |
| Full-wave time reversal reference | 2 | 1-3 h | Validates phase approximation |
| Main dx0.5 table: 3 trajectories x 2 methods | 6 | about 18 h | Core paper result |
| Convergence additions | 2 | about 10-14 h | dx0.75 and dx0.375 |
| PML/CFL checks | 2 | about 5-8 h | Numerical robustness |
| Mapping alternatives | 2 | about 6 h | Model uncertainty |

Expected new total: **20-21 pressure runs**, but only **12-14 expensive runs**. Serialized CPU time is approximately 45-60 h if current timings hold. Failed gates reduce, rather than increase, the run count.

Do not use a full factorial design. Do not run multiple frequencies, apertures, windows, and phase models simultaneously.

## 6. Paper Figures and Tables

Minimum figures:

1. workflow, Case 079 anatomy, target, and three trajectories;
2. final-source free-field axial/lateral profiles and -6 dB focus;
3. uncorrected versus corrected pressure fields for the representative trajectory;
4. target delivery, focal error, and skull-hotspot comparison across three trajectories;
5. ray/path-integral versus full-wave time-reversal phase and field comparison;
6. grid/PML/CFL convergence and mapping sensitivity.

Minimum tables:

1. CT, source, solver, grid, PML, CFL, and waveform parameters;
2. trajectory geometry and skull-path descriptors;
3. primary acoustic outcomes for `M0` and corrected method;
4. numerical and mapping uncertainty.

Use descriptive statistics across trajectories. Three trajectories from one CT are not three independent subjects; do not report population inference or clinical generalization.

## 7. Definition of Done

The acoustic field is ready for manuscript drafting only when:

- source model passes free-field closure;
- at least two of three source-safe skull-crossing trajectories pass correction criteria;
- full-wave reference supports the selected phase method or replaces it;
- dx, PML, and CFL robustness gates pass;
- skull mapping uncertainty is quantified;
- all arrays, waveforms, environment records, commands, ledgers, and evidence briefs are complete;
- figures and tables can be regenerated from scripts without manual editing.

After this point, thermal analysis may be added as a limited secondary section using the locked acoustic field. It must not reopen acoustic optimization.

## 8. Immediate Next Actions

1. Generate a geometry-only three-trajectory selection report for Case 079.
2. Freeze the final source geometry and method labels.
3. Prepare the final-source free-field dx0.75/dx0.5 Evidence Brief and dry-run package.
4. Implement/verify full-wave time-reversal recording and phase extraction before expensive CT runs.
5. Start pressure execution only after Gates A and B are approved.
