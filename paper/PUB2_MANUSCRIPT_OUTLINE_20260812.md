# PUB.2 manuscript outline

## Working title

CT-informed full-wave time reversal improves focal localization in a controlled transcranial ultrasound simulation workflow

## Central claim

In one frozen CT-informed computational case, matched full-wave time reversal moved the simulated global pressure maximum towards the intended target; this localization conclusion was unchanged by the tested PML perturbation.

## Abstract scaffold

**Background.** Transcranial ultrasound simulations require subject-specific acoustic modelling and auditable numerical controls because skull-induced phase aberration can displace the pressure maximum from the intended target.

**Methods.** We evaluated a frozen Case079 CT-informed k-Wave configuration at 250 kHz. A matched baseline simulation was compared with a full-wave time-reversal refocusing chain. Primary endpoints were the target-to-global-peak pressure ratio and the distance from the global peak to the intended target. A paired PML12/PML16 perturbation assessed sensitivity of the baseline and refocused fields. Execution metadata, device histories and artifact hashes were retained.

**Results.** Time reversal increased the target-to-global-peak ratio from 0.4774 to 0.9849 and reduced the peak-to-target distance from 57.38 to 2.49 mm. Simulated target pressure increased from 1.891 to 2.554 MPa, while the global maximum decreased from 3.962 to 2.593 MPa. PML12-to-PML16 relative field differences were 1.83e-5/6.75e-5 (L2/L-infinity) for baseline and 5.05e-5/1.46e-4 for time reversal; the peak-distance endpoints were unchanged.

**Conclusion.** The frozen single-case workflow provides evidence that full-wave time reversal improved simulated focal localization and that this conclusion was insensitive to the tested PML perturbation. Generalization, absolute-pressure accuracy and numerical convergence remain unevaluated pending independent anatomy, CFL, grid and domain evidence.

## Introduction: paragraph plan

1. Define the targeting problem: skull heterogeneity distorts phase and can move the dominant pressure maximum.
2. Explain why subject-specific full-wave modelling and refocusing are attractive, but distinguish physical plausibility from validated predictive accuracy.
3. Identify the reproducibility gap: simulation papers often under-report mapping, geometry, positioning, grid/time/boundary choices and failure handling.
4. State the narrow objective and endpoints without implying clinical performance.

## Methods: paragraph plan

1. **Study scope and evidence level:** retrospective computational Case079; engineering validation; no clinical or safety endpoint.
2. **CT acoustic model:** source image, HU mapping, attenuation model, units and model hash.
3. **Geometry and targeting:** coordinate convention, target definition, entry plan, bowl aperture/radius and source-point construction.
4. **Numerical model:** k-Wave/Python versions, CPU backend, 0.75-mm grid, 250-kHz excitation, CFL, time window and PML levels.
5. **Baseline/TR protocol:** matched inputs, calibration/refocus stages and immutable comparison matrix.
6. **Endpoints:** target/global ratio, peak-to-target distance, target pressure and global peak; define extraction locations before reporting results.
7. **PML sensitivity:** common-domain alignment, relative L2/L-infinity and localization endpoint comparison.
8. **Reproducibility and monitoring:** execution/device records, interruption policy, artifact hashes and validation gates.

## Results: paragraph plan

1. Report protocol matching and successful artifact validation before outcome values.
2. Lead with localization endpoints, then report simulated pressure endpoints with explicit modelling qualification.
3. Report PML field differences and unchanged localization distances; avoid calling this full convergence.
4. Report resource envelope only as reproducibility information, not as a scientific outcome.
5. State that CFL0.1 produced no admissible core result because the run was interrupted by a planned Windows Update restart.

## Discussion: paragraph plan

1. Interpret the localization change as the main result; avoid equating it with treatment efficacy.
2. Explain why reduced global maximum alongside increased target pressure suggests redistribution of the simulated field, while remaining model-specific.
3. Discuss the narrow meaning of the PML result: boundary-layer perturbation at one case and one grid, not proof of total numerical convergence.
4. Compare the reporting approach with ITRUSST consensus expectations and transcranial simulation benchmark practice.
5. List limitations in order of scientific impact: single anatomy, no experimental ground truth, incomplete CFL/grid/domain evidence, material-mapping uncertainty and standard-preset status.
6. End with the falsification-oriented next study: matched sensitivities and independent cases using predefined endpoints.

## Figure-to-claim map

| Figure | Intended message | Claim boundary |
|---|---|---|
| 1 | Frozen and auditable workflow | Process reproducibility only |
| 2 | Baseline and TR spatial localization | One computational case |
| 3 | Endpoint changes | Simulated metrics, no efficacy inference |
| 4 | PML12/PML16 field agreement | Tested perturbation only |
| S1 | Parameter and protocol matching | No unreported tuning |
| S2 | Device/resource histories | Execution provenance only |

## Writing lock

Every sentence containing `robust`, `accurate`, `validated`, `generalizable`, `safe`, `in situ` or `converged` requires a claim-evidence review before submission.
