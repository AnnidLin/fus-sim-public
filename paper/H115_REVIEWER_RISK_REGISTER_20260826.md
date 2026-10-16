# UCL H115 reviewer-risk register

## Decision boundary

The H115 branch is suitable for a computational-methods manuscript only as a transparent **nonpassing external comparison** with a negative nominal-source sensitivity and a two-grid stability observation. It does not support a title, abstract or conclusion claiming successful experimental validation, formal convergence, Case079 validation, or clinical/safety accuracy.

## Anticipated reviewer questions

| Priority | Likely reviewer concern | Evidence already available | Required manuscript response | Residual action before submission |
|---|---|---|---|---|
| High | Why call this validation when two held-out endpoints fail? | Supplementary Table 1 reports all eight gates; effective dx0.50 and dx0.30 each pass 6/8. | Use “external comparison” or “nonpassing validation attempt”; retain axial peak-position and transverse L2 failures in Results, Abstract and Limitations. | Final title/abstract lint; do not convert package integrity into physical validity. |
| High | Was source amplitude tuned using the validation data? | The frozen measurement contract fits one global amplitude scalar to axial peak pressure and holds axial shape/position plus the transverse plane out. | State the calibration/held-out split explicitly and avoid describing transverse agreement as independently calibrated pressure accuracy. | Preserve the frozen contract in the supplement or repository snapshot. |
| High | Is the effective bowl a measured H115 source model? | Effective 61.39/50.40-mm geometry is paper-derived; the HDF5 nominal 64/64-mm equal-amplitude candidate is 0/8 and materially worse. | Describe the result as source-model sensitivity. Do not infer manufacturer geometry or ring drive from the better effective model. | Independent per-ring acoustic amplitude/phase or a measured complex hologram is needed for a future positive-validation study. |
| High | Was the +1-mm shift selected after seeing the data? | Registration sweep was frozen as secondary; +1 mm is the smallest passing axial-peak arm but lacks independent origin uncertainty. | Report it only as descriptive sensitivity and retain the unshifted comparison as primary. | No post-hoc coordinate correction is allowed in the present result. |
| High | Does the water comparison validate the Case079 skull simulation? | The H115 branch is homogeneous water at 270 kHz with a different source and context of use. | State explicitly that it tests the analysis/source workflow, not Case079 anatomy, HU mapping, skull propagation or absolute pressure. | Author must supply Case079 data provenance and mapping citations independently. |
| Medium | Is hydrophone spatial averaging modelled correctly? | A 0.2-mm amplitude-domain circular average changes transverse L2 from 15.004% to 15.039%. | Call this an approximate sensitivity, not complex-pressure aperture integration or deconvolution. | A phase-resolved hydrophone transfer/spatial-averaging model would be needed for stronger attribution. |
| Medium | Do two grids establish convergence? | dx0.50 versus dx0.30 gives correlation 0.999881, scaled L2 1.310% and 0-mm discrete axial-peak shift. | Use “two-grid numerical-sensitivity observation”; do not use “grid-converged.” | A third justified grid and formal order/error analysis are required for convergence. |
| Medium | Is measurement uncertainty fully propagated? | The public record supplies 9% hydrophone amplitude calibration uncertainty; total endpoint covariance/uncertainty is unavailable and was not invented. | Separate the documented calibration component from unavailable total uncertainty; do not turn threshold margins into confidence intervals. | Obtain scan-position, repeatability and processing uncertainty for a formal uncertainty budget. |
| Medium | How general is a single H115 water dataset? | One transducer dataset and one scan configuration are evaluated. | Restrict the conclusion to this public comparator and present it as a falsification-oriented method check. | Add independent transducers, scans or laboratories in future work. |
| Low | Can the paper-facing result be reconstructed without another solver? | Fresh-path reconstruction reproduces 3/3 analyses and 10/10 derived checks; the paper bundle and execution package validate. | Cite the reproduction recipe, fixed hashes, software/environment boundary and retained raw fields. | Archive a versioned repository/data snapshot or DOI before submission. |
| High | Is Case079 lawfully reusable and can the CT be shared? | Local download metadata traces the file to PhysioNet CT-ICH v1.3.1; the official record documents dataset ethics approval and de-identification, while its restricted-data licence prohibits sharing access. | Cite DOI 10.13026/4nae-zg36, state the provider-reported ethics/de-identification basis, and exclude the raw CT. | Author privately confirms the registered-access record and journal-specific consent/waiver wording. |
| High | Is `simple_hu300` a validated literature mapping? | The exact implementation is documented, but Marsac/Webb support heterogeneous/scanner-specific mapping context rather than this binary constant set. | Report the full equation/constants and call it a frozen unvalidated engineering profile; do not claim it is literature-derived. | Independent scanner/material calibration or a prospectively designed mapping sensitivity is required for accuracy claims. |
| High | Is the target anatomically registered and is skull segmentation validated? | The planning contract labels the ROI synthetic/non-anatomical; segmentation is threshold-only and no Case079 registration, reference mask or expert sign-off was found. | Restrict claims to an engineering target and disclose the coarse 5-mm source slice spacing and QC gaps. | Supply registered anatomy and expert/reference QC in a future study, not by relabelling current evidence. |

## Reviewer-facing bottom line

The strongest defensible statement is that grid refinement and the documented hydrophone aperture do not explain the remaining mismatch, while the nominal equal-amplitude geometry worsens it substantially. The unresolved evidence gap is source drive/complex field and measurement-registration uncertainty—not a justification for further blind grid refinement or post-hoc tuning.

## Author-only submission gates

1. Confirm the title and abstract use the nonpassing-comparison boundary.
2. Confirm the private PhysioNet access record and journal-specific consent/waiver wording; keep raw CT excluded.
3. Accept the exact binary mapping and target as explicitly unvalidated engineering choices, or add new independent calibration/anatomical evidence in a future trace.
4. Choose the project licence, freeze the source revision and archive the compact reproducibility candidate under a stable identifier.
5. Keep all eight H115 endpoints, including unfavourable ones, in the submitted supplement.
