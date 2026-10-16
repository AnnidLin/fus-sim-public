# Paper Analysis Freeze

> Version: 1.0  
> Frozen: 2026-07-31  
> Parent plan: `PAPER_EXECUTION_MASTER_PLAN.md`

## Study type

Single-case computational-methods study with public numerical benchmarking, numerical/material sensitivity, cross-platform evaluation and an independent public-anatomy robustness check.

## Primary question

Under a matched transducer, trajectory, medium, domain, source and numerical protocol, does time reversal improve spatial localization at the intended target, and how stable is that improvement across numerical, material and platform perturbations?

## Primary demonstration

- Case: Case079;
- trajectory: H3;
- transducer: full bowl, aperture 60 mm, radius 74.435 mm;
- frequency: 250 kHz;
- source convention: 1 MPa, 2 cycles;
- numerical setup: PML12, CFL0.2, standard preset;
- current domain: lat30/post16 intermediate domain;
- comparison: matched baseline versus normalized TR.

## Primary endpoints

1. Target-window peak divided by global peak.
2. Euclidean distance from the global peak to the intended target, in millimetres.

Both endpoints must be reported together. An improvement in only one endpoint is not sufficient for a general “improved focusing” statement.

## Secondary endpoints

- target-window peak pressure;
- global peak pressure;
- axial and lateral `-6 dB` widths;
- brain- and skull-region peaks and their locations;
- normalized-field spatial overlap;
- runtime, peak memory and execution failure rate.

## Statistical unit

- The anatomical case is the independent unit.
- Voxels, source points, trajectories and repeat runs are not independent subjects.
- Current Case079 results are descriptive paired evidence.
- Population inference is prohibited until a multi-case design and sample-size justification exist.

## Current observed primary result

| Endpoint | Baseline | TR |
|---|---:|---:|
| target/global | 0.477400 | 0.984864 |
| peak-to-target distance | 57.379 mm | 2.487 mm |

Source: `outputs/h3_large_full_bowl_matched_standard_20260730/comparison/matched_comparison.json`.

## Inclusion criteria

- input hashes and registered paths resolve;
- baseline and TR shared configuration fields match;
- source is background-only;
- expected source-point count and model shape match;
- required NPZ/JSON artifacts are complete and finite;
- monitor status indicates a valid completed stage;
- analysis is performed by the registered metric implementation.

## Exclusion criteria

- configuration drift affecting causal interpretation;
- incomplete or corrupt pressure fields;
- source points intersect non-background medium where background-only is required;
- fixed-time termination of otherwise healthy runs;
- post-result changes to target window, target coordinate or primary metric;
- outputs that cannot be linked to an input/configuration hash.

Excluded and failed runs remain preserved and are reported; they are not silently deleted.

## Planned comparisons

1. Public ITRUSST benchmark versus reference outputs.
2. Case079 baseline versus TR under matched conditions.
3. Single-variable dx, PML, CFL and domain perturbations.
4. Binary versus continuous HU mapping sensitivity.
5. PRESTUS workflow comparison and BabelBrain independent-solver comparison.
6. Frozen workflow on at least one additional licensed public anatomy.

## Interpretation policy

- Spatial localization may be called stable only if both primary endpoints retain direction and the perturbation-specific uncertainty is reported.
- Absolute pressure may be called numerically converged only after a prospectively defined CT-specific convergence assessment passes.
- Cross-platform agreement is not experimental accuracy.
- Material-model comparison is sensitivity analysis unless ground truth exists.
- No thermal, clinical, BBB dosing or hardware recommendation is supported by this analysis.

## Change control

Any change to the primary question, demonstration case, primary endpoints, statistical unit or interpretation policy requires:

1. a version increment;
2. a dated rationale written before examining new affected results;
3. an impact statement for completed analyses;
4. updates to `PAPER_EXECUTION_MASTER_PLAN.md`, `AI_TODO.md` and `paper/MANUSCRIPT_EVIDENCE_MAP.md`.
