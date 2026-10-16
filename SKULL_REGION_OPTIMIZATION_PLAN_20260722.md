# Skull-Region Hotspot Optimization: Next Execution Plan

**Date:** 2026-07-22  
**Scope:** Case 079 H1 engineering simulation; no clinical or BBB-dose claim.

## Current evidence

1. Phasor-only dual-point control reduced the skull peak by 58.4% but retained only 41.2% target pressure. The missing solver time-domain normalization was identified and corrected.
2. A 40% convex waveform blend retained 85.45% target pressure, improved target/global ratio and introduced no stronger non-target peak, but reduced the skull peak by only 15.40% versus the required 20%.
3. A second transfer vector was measured at the blend field's dominant skull peak `[77,120,97]`.
4. Target-plus-two-hotspot minimum-L2 response control passed all endpoint-model checks but produced excessive time-domain peaks; no offline candidate passed.

## Highest-efficiency next method

Implement a low-dimensional optimizer that includes the complete replay waveform maximum directly in the objective and constraints.

Decision variables should be coefficients over a small, measured basis containing the conventional replay and two hotspot-control directions. The optimizer must evaluate the real time-domain waveform, not only 500 kHz phasors.

Hard constraints:

- predicted target retention `>=0.85`;
- conservatively corrected suppression at both measured hotspots `>=0.20`;
- waveform global peak/control `<=1.50`;
- exact source mask, coordinate and solver normalization semantics.

Objective: maximize the minimum suppression across the two hotspots, with waveform peak as a secondary penalty.

## Validation ladder

1. Build synthetic tests for the amplitude-bounded optimizer.
2. Reproduce the conventional, strong-control and 40% blend endpoint responses.
3. Run a finite offline coefficient search or constrained optimizer; no k-Wave.
4. Require a margin above the hard gates: target `>=0.88` and both hotspot suppressions `>=0.23` before spending another pressure run.
5. If a candidate passes, create a new exactly-one Evidence Brief and dry-run. Otherwise close source-weight optimization for H1 and move to trajectory/geometry optimization.

## Stop conditions

- No more single-hotspot calibration after the two measured points.
- No blend-fraction or regularization pressure scan.
- At most one future full-field validation for the amplitude-bounded method.
- If that validation fails, change trajectory or transducer geometry rather than continuing weight tuning.

## Paper value

The completed sequence supplies a traceable method narrative: single-point control fails through normalization and hotspot migration; target-preserving blending nearly reaches the skull gate; region-aware optimization requires explicit time-domain amplitude constraints. These are engineering findings, not safety conclusions.
