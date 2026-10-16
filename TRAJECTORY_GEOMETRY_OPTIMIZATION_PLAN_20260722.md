# Trajectory and Geometry Optimization: Next Execution Plan

**Date:** 2026-07-22  
**Scope:** Case 079 pure-simulation acoustic planning; no clinical or BBB-dose claim.

## Trigger

The H1 time-domain amplitude-bounded source-weight search produced 56 minimum-gate candidates but no candidate met the preregistered pressure-validation margin. H1 source-weight tuning is therefore closed.

## Highest-efficiency route

Change the propagation geometry before changing exposure. Reuse existing CT, target, held-out trajectory fields, path-cost outputs and source masks to rank trajectory/geometry options offline. Do not start a broad pressure sweep.

1. Assemble one comparison table for the existing held-out trajectories with skull path length, incidence/entry risk, target pressure, global/skull peak, target/global ratio and focus displacement.
2. Reject source-unsafe, non-bone-crossing and target-delivery-failed trajectories using existing evidence only.
3. Generate a small, deterministic local neighborhood around the best admissible trajectory and score it with the existing minimum-acoustic-cost path model.
4. Select at most one geometry candidate only if it improves the preregistered acoustic cost and skull-risk proxies with no target-path regression.
5. Before any pressure execution, create a separate Evidence Brief and run the k-Wave dry-run resource gate. At most one pressure validation is permitted for the selected geometry.

## Offline acceptance

- Exact Case 079 target and coordinate contract.
- True skull crossing under the frozen HU/profile semantics.
- Source mask contains no soft-tissue source points.
- Better acoustic path cost and no worse skull-risk proxy than H1.
- Deterministic ranking and complete parameter traceability.

## Pressure-validation gate

No pressure is authorized by this plan. A future candidate must have an independently frozen geometry, expected compute/storage estimate, target-retention criterion, skull-peak reduction criterion and stop condition in a new Evidence Brief.

## Stop conditions

- No broad offset, aperture or radius pressure grid.
- No further H1 phase-weight refinement.
- If no offline geometry improves H1, preserve the current result as a method-limit finding and move to multi-case/registered-anatomy evidence rather than tuning the same case indefinitely.

## Paper value

This route tests the mechanistic conclusion from the completed experiments: when source weighting cannot jointly preserve target delivery and control a broad skull hotspot ridge, changing the acoustic path is more informative than adding control points.
