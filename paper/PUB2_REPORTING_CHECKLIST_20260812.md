# PUB.2 reporting checklist

Primary external reporting reference: ITRUSST consensus on reporting standards for transcranial ultrasound stimulation studies: https://pmc.ncbi.nlm.nih.gov/articles/PMC10896372/

| Reporting item | Status | Current evidence or required action |
|---|---|---|
| Simulation package and version | Ready | Python k-Wave 0.6.1 recorded |
| Runtime and operating system | Ready | Python 3.12.10 and Windows 11 recorded |
| Solver backend | Ready | CPU backend recorded |
| Input anatomy and case identifier | Conditional | PhysioNet CT-ICH v1.3.1, DOI, dataset ethics approval and provider-reported de-identification are documented; author must confirm the private registered-access record and any journal-specific consent/waiver requirement |
| Acoustic material assignment | Ready with limitation | Exact `simple_hu300` thresholds/constants and alpha semantics are documented; no matching primary calibration was found, so it must remain an unvalidated engineering profile |
| Coordinate convention | Ready | Frozen entry plan and artifact trail available |
| Target definition | Ready with limitation | `target_020` is an engineering geometric candidate, explicitly not anatomical or clinically selected; no Case079 multimodal registration |
| Transducer geometry | Ready | 60-mm aperture, 74.435-mm radius, 4,971 source points |
| Transducer placement/orientation | Ready | Link entry-plan artifact and include schematic |
| Excitation | Ready | 250 kHz, prescribed 1-MPa source amplitude, two cycles |
| Spatial discretization | Ready | 0.75-mm spacing and minimum PPW 8 |
| Temporal discretization | Partial | Reference CFL 0.2 and dt recorded; matched CFL sensitivity incomplete |
| Simulation duration | Ready | 100 us and 1,867 reference steps |
| PML/boundary settings | Ready for tested scope | PML12/PML16 paired analysis complete; distinguish PML from expanded-domain testing |
| Grid-convergence assessment | Partial, separate water branch | H115 dx0.50/dx0.30 fields are highly similar, but two grids do not establish formal convergence and do not substitute for Case079 CT grid convergence |
| Domain-size sensitivity | Missing | Required unless scope is explicitly PML-only |
| Primary outcome definitions | Ready | Ratio, peak distance, target pressure and global peak defined |
| Field normalization and units | Ready | Stored field is `max(abs(p_max), abs(p_min))/1e6` MPa at each voxel; figures and draft state temporal peak magnitude |
| Common-domain comparison | Ready | Crop-origin alignment and coverage checks documented |
| Hardware/resource reporting | Ready | Runtime and device extrema retained |
| Failure/interruption handling | Ready | CFL interruption and exclusion rule documented |
| Data/code availability statement | Conditional | UCL and Case079 DOIs, licences/access route and exact input hashes are documented; raw/reconstructable CT data are excluded. A 136-file local archive candidate has zero missing/prohibited matches, but project licence, frozen revision and DOI remain author inputs |
| Experimental validation | Attempted, nonpassing | Corrected H115 dx0.50/dx0.30 comparisons fail axial peak and transverse L2; nominal geometry is materially worse and 0.2-mm aperture averaging is not explanatory. Do not apply the descriptive registration shift or imply successful/Case079 validation |
| Prospective verification thresholds | Ready | Frozen in `paper/PUB2_VERIFICATION_CONTRACT_20260812.md/json`; label them as project targets |
| Biological/clinical safety assessment | Not in scope | State explicitly and avoid safety conclusions |

## Submission gate

The current manuscript may proceed as a single-case computational-methods/technical-validation paper only if all `Ready` items are linked in the final supplement and all `Partial`/`Missing` items are disclosed. A broader numerical-robustness or biomedical-efficacy paper remains blocked.
