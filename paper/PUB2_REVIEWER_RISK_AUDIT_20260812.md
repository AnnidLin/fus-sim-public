# PUB.2 adversarial reviewer-risk audit

| Reviewer objection | Current evidence | Risk | Required response |
|---|---|---|---|
| “This is only one subject.” | Case079 only | Critical for general claims | Narrow to case study or add independent anatomies |
| “Time reversal improving focus is expected.” | Large matched localization effect plus auditable workflow | High | Emphasize reproducibility, failure recovery and quantitative boundary evidence; avoid novelty overclaim |
| “Numerical convergence is incomplete.” | Paired PML passed; CFL interrupted; grid/domain incomplete | Critical | Complete controlled sensitivity or explicitly frame as preliminary engineering validation |
| “The run is labelled standard, not paper grade.” | `is_paper_grade=false` in summaries | High | State honestly; build convergence dossier before paper-grade designation |
| “Absolute pressure may be wrong.” | No experimental ground truth; mapping assumptions remain | Critical | Centre localization/selectivity, report simulated pressure with uncertainty boundary |
| “PML difference is tiny because domains were compared incorrectly.” | Crop-origin alignment and full PML12-domain coverage checks passed | Low | Show alignment schematic and difference-map method |
| “TR and baseline were not matched.” | Frozen matrix reports no protocol drift | Low | Publish parameter table and machine-readable config comparison |
| “The interrupted CFL run was cherry-picked away.” | Immutable interruption/gap feedback; no outputs | Low | Report planned-restart interruption and exclusion rule transparently |
| “Resource claims are unverifiable.” | Device histories and extrema validated | Low | Include hardware/software environment and extrema in supplement |
| “Clinical safety is implied by pressure.” | Claim boundary explicitly prohibits it | Manageable | Keep safety language out of title, abstract and conclusion |

## Likely editorial outcomes

- **Current conservative submission:** potentially suitable for a technical,
  methods, software or simulation case-study venue if the workflow contribution
  and reproducibility package are foregrounded.
- **Broad biomedical efficacy submission:** likely rejected for one case, absent
  experimental validation and incomplete uncertainty/convergence evidence.
- **After numerical + independent-case strengthening:** credible basis for a
  broader computational tFUS methods manuscript.

## Abstract red-line rules

- Use “in a patient-specific computational case” rather than “in patients”.
- Use “improved simulated localization” rather than “improved treatment”.
- Use “was insensitive to the tested PML perturbation” rather than “was
  numerically robust” or “converged”.
- Do not call 1 MPa an in-situ pressure; it is the prescribed source excitation.
- Do not mention safety unless stating that safety was not evaluated.

