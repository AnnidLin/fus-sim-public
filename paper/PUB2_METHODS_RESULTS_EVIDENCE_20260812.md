# PUB.2 Methods and Results evidence scaffold

> Status: paired PML analysis and fresh CFL0.1 baseline recovery complete. This file is a
> claim-controlled manuscript scaffold, not a final paper section.

## One-sentence argument

In one CT-informed Case079 configuration, matched full-wave time reversal
improved focal localization relative to baseline propagation, and this
method-level observation was insensitive to a PML12-to-PML16 perturbation;
baseline time-step sensitivity passed the frozen limits, with all conclusions
bounded to single-case engineering evidence.

## Methods — frozen numerical experiment

We simulated acoustic propagation with the Python k-Wave backend on the CPU
using a Case079 explicit-alpha acoustic model and a frozen dx0.75-mm entry plan.
The source was a 250-kHz, two-cycle tone burst with a 1-MPa excitation pressure;
the pressure denotes the prescribed source amplitude and not free-field or
in-situ pressure. The transducer aperture and radius were 60 and 74.435 mm,
respectively. Reference calculations used the standard preset, CFL0.2, PML12,
a lat30/post16 cropped domain and 4,971 source points, all located in background.

The frozen `simple_hu300` engineering profile assigned background below -500 HU,
soft tissue from -500 to below 300 HU and skull at or above 300 HU. The skull
constants were 2800 m/s, 1900 kg/m3 and attenuation prefactor 8.0 with power 1.5.
The exact combined profile lacks a matching primary calibration and is retained
only for backward-compatible matched comparisons. The source CT had 5-mm slice
spacing before resampling; no ground-truth skull mask, expert segmentation
sign-off or Case079 anatomical registration was available. The target is an
engineering geometric candidate, not a clinical or anatomically registered ROI.

The matched reference comprised one baseline calculation and a fresh
calibrate-to-refocus time-reversal chain. The PML sensitivity experiment changed
only the absorbing-layer thickness from 12 to 16 grid points. Because this
altered the computational crop, PML16 calibration signals were generated anew.
Refocus suppressed an unused full-grid time-series record while retaining the
required maximum-pressure field and focus metrics; this changed memory use but
not acoustic propagation. Fields with different crop origins were compared on
their aligned common domain. The time-step experiment changed only CFL
from 0.2 to 0.1, doubling Nt from 1,867 to 3,734 while retaining the PML12 grid.

All long runs passed a preregistered dry-run quality gate and were executed at
BelowNormal priority with six thread limits. The process-tree gates were 6.5
equivalent CPU cores, 16 GiB working set and 4 GiB minimum system free memory.
Outputs were accepted only when solver return code, finite non-zero fields,
summaries, focus metrics and device histories passed independent package checks.

## Results — paired PML sensitivity

Increasing PML thickness from 12 to 16 produced small common-domain changes for
both methods. Relative L2 differences were 1.8345×10⁻⁵ for baseline and
5.0530×10⁻⁵ for time reversal; relative L∞ differences were 6.7538×10⁻⁵ and
1.4634×10⁻⁴, respectively. Baseline global-peak and target-pressure changes
were −1.0471×10⁻⁵ and −1.1534×10⁻⁵ in relative terms. The corresponding TR
changes were 2.7580×10⁻⁷ and 2.8938×10⁻⁶. Peak-to-target distance was unchanged
for both methods.

Under PML16, the target-to-global-peak ratio increased from 0.47740 at baseline
to 0.98487 with time reversal, while global peak-to-target distance decreased
from 57.38 to 2.49 mm. Thus, the PML perturbation did not alter the qualitative
localization advantage observed for TR in this single configuration.

## Results — baseline CFL sensitivity

- Fresh CFL0.1 recovery completed 3734/3734; the original restart-interrupted
  attempt remains excluded.
- Common-grid relative L2/L∞ differences were **0.654%/1.375%**.
- Target pressure changed **−0.770%**, peak-to-target distance changed **0 mm**,
  and target/global ratio changed **+0.000525**.
- All frozen baseline time-step limits passed; TR time-step sensitivity and
  formal convergence remain untested.

## Claim–evidence map

| Claim | Direct artifact | Status |
|---|---|---|
| PML16 TR chain completed without automatic rerun | `outputs/pub2_250khz_pml16_tr_20260811/chain_status.json` | supported |
| PML perturbation produced small field differences in this case | `outputs/pub2_250khz_pml16_tr_analysis_20260812/paired_pml_analysis.json` | supported |
| TR localization advantage persisted under PML16 | same paired analysis | supported, single case |
| PML evidence establishes formal convergence | none | not supported |
| Baseline CFL0.1 result | recovery field, analysis and independent package validation | supported for baseline only |
| Population generalization, quantitative pressure accuracy or safety | none | not supported |

## Limitations that must remain in the manuscript

The evidence is restricted to one anatomy, trajectory, frequency and source
configuration. One PML perturbation and one time-step perturbation cannot by
themselves establish formal convergence. No experimental ground truth is used,
and simulated pressure must not be interpreted as efficacy or clinical safety.
The uncalibrated binary material profile, threshold-only segmentation, coarse
source slice spacing and non-anatomical target further block subject-specific
accuracy or anatomical-localization claims.

## External 270 kHz measurement branch (not yet a Case079 validation)

An openly licensed UCL H115 free-field dataset (`10.5522/04/28025240.v2`) has
now been ingested as an independent method-validation branch. For qCW scans,
stored voltage traces were centrally cropped to approximately five complete
270-kHz cycles, fitted by least squares to sine, cosine and DC terms, and divided
by the interpolated hydrophone sensitivity (2.3400e-8 V/Pa; 9% stated amplitude
uncertainty). The calibrated axial peak was 0.4236 MPa at 49.006 mm; an
independent transverse scan at 39.998 mm yielded 0.3306 MPa and agreed with the
axial interpolation there to 0.0209%. This agreement checks data loading and
calibration consistency, not simulation accuracy.

The axial -6 dB region was left-censored because the far scan endpoint remained
at 57.6% of the peak. Therefore no complete axial focal depth is claimed. PW
broadband pressure also remains excluded pending a filter/window sensitivity
contract. Before the first propagation, a 10.98-PPW H115 homogeneous-water
model passed resource and geometry dry-runs. The subsequently executed results
are reported below; this branch cannot support successful experimental-validation
wording because the preregistered held-out endpoints did not all pass.

## External 270 kHz result — controlled nonpassing observation (2026-08-18)

One preregistered, homogeneous-water H115 propagation was completed using the
frozen effective-bowl model (0.50 mm spacing, 10.98 PPW, PML16, CFL0.10,
5,337 time steps). The guarded CPU process completed in 54.46 min with finite
non-zero artifacts. Independent package checks found maximum process-tree use
of 5.972 equivalent cores, 1.223 GiB working set and 18.167 GiB minimum free
memory; all operating gates passed.

The qCW axial peak was used only for one numerical amplitude scale. Held-out
axial shape passed its normalized-L2 criterion (3.780%) but peak position did
not (1.856 mm versus <=1.0 mm). The independent transverse plane had high
normalized correlation (0.9875), small peak-pressure (+1.689%) and location
(0 mm) errors, but failed normalized L2 (15.004% versus <=10%). A dated
2026-08-25 audit corrected raster-step inference in the line-width extractor;
the corrected y-width error is +5.989% and passes the frozen ±10% criterion.
Thus the frozen acceptance contract is
**not met**. This is retained as a useful falsification observation for the
simplified source model, not as a successful external validation, and no
automatic rerun or claim upgrade was made. The audited package is
`outputs/ucl_h115_water_validation_20260818/`.

## External 270 kHz grid sensitivity — dx0.50 versus dx0.30 (2026-08-23)

To test whether the failed measurement endpoints were primarily caused by the
0.50-mm discretization, one finer-grid calculation retained the same water,
effective-bowl geometry, excitation, 180-us duration and CFL0.10. Spatial
spacing was reduced to 0.30 mm (18.30 PPW); PML points increased from 16 to 27
to preserve approximately 8 mm physical PML thickness. The explicit full model
preserved the reference physical domain. The 335 x 268 x 268, 8,894-step run
completed in 6.41 h. Independent validation found a maximum 5.980 equivalent
cores, 5.095 GiB working set and 14.283 GiB minimum free memory.

After source-relative physical alignment and exclusion of the frozen 5-mm
nearfield, 4,377,600 common voxels gave a normalized correlation of 0.999881,
least-squares-scaled relative L2 of 1.310%, relative L-infinity of 2.170% of
the reference peak, +0.0307% peak-magnitude change and 0-mm discrete axial-peak
shift. Nevertheless, the measurement comparison did not improve: axial
peak-position error increased from 1.856 to 2.177 mm and transverse normalized L2
from 15.004% to 15.469%. Corrected y-width errors were +5.989% and +7.160%,
respectively, and both passed. Thus grid
refinement preserved the simulated field but did not repair the external
mismatch. Two grids cannot establish formal convergence; the next diagnostic
priority is the effective source representation and measurement alignment.

The reproducible figure and manifest are in
`paper/figures/ucl_h115_grid_sensitivity_corrected_20260825/`.

## External 270 kHz source-model sensitivity — nominal versus effective (2026-08-25)

One independently frozen dx0.50-mm candidate used the HDF5-documented nominal
64-mm radius and 64-mm outer diameter, with the two equal-area, in-phase rings
treated as an equal-amplitude union because per-ring acoustic calibration is
unavailable. The guarded run completed in 2,806 s. Maximum monitored CPU was
5.974 equivalent cores, maximum working set 1.220 GiB and minimum free memory
17.282 GiB.

Nominal geometry was materially worse than the paper-derived effective bowl:
axial peak-position error increased from 1.856 to 10.028 mm, axial normalized
L2 from 3.780% to 31.030%, and transverse normalized L2 from 15.004% to
118.286%. A secondary frozen sweep found +1.0 mm was the smallest descriptive
origin offset passing the axial peak gate for the effective bowl, but it cannot
replace the primary unshifted result or be used as a post-hoc registration
correction. Approximate 0.2-mm amplitude-domain
aperture averaging changed transverse L2 only to 15.039%. Package integrity,
device compliance and figure hashes passed; external validation did not.
