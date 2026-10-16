# Submission figure/table traceability matrix

Status: **passed**

| Artifact | Inputs | Outputs | Boundary |
|---|---:|---:|---|
| Case079 Figures 2-4 | 7 | 6 | Single Case079 engineering evidence; PML perturbation only; not formal convergence, efficacy or safety evidence. |
| Supplementary Figure 1: H115 grid sensitivity | 3 | 2 | Two-grid homogeneous-water sensitivity and nonpassing external comparison; not formal convergence or successful source validation. |
| Supplementary Figure 2: H115 source/registration | 3 | 2 | Engineering sensitivity with a nonpassing primary external comparison; registration and aperture panels are secondary only. |
| Supplementary Table 1: H115 endpoints | 3 | 3 | Held-out engineering comparison only; external validation remains nonpassing. |
| Supplementary Table 2: H115 methods | 6 | 3 | Reproducibility table only; external validation remains nonpassing and two grids are not formal convergence. |

## Deterministic checks

- all_inputs_present: `true`
- all_outputs_present: `true`
- all_declared_hashes_match: `true`
- table_rows_match: `true`
- table_generation_passed: `true`
- claim_boundaries_present: `true`

Traceability and package integrity only; H115 external validation remains nonpassing and Case079 remains single-case engineering evidence.
