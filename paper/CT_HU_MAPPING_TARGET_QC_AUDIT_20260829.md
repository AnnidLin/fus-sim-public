# CT-HU mapping, target and QC audit

Trace: `TRACE-20260829-001`

## Bottom line

The reported Case079 simulations are reproducible under an explicitly defined
binary engineering model, but the exact combined mapping is not presently backed
by a matching primary-source formula or calibration. The manuscript can report
the mapping as a frozen historical engineering profile and can cite the primary
literature to explain why continuous, scanner-specific calibration matters. It
cannot describe the mapping as validated or literature-derived. No default was
changed in this audit.

## Exact implemented model

Let `H` be the resampled CT value in HU. The label is

```text
background, H < -500
soft tissue, -500 <= H < 300
skull,      H >= 300
```

The assigned property triplets `(c, rho, alpha0)` are:

| Label | c (m/s) | rho (kg/m3) | alpha0 |
|---|---:|---:|---:|
| Background/coupling | 1500 | 1000 | 0.002 |
| Soft tissue/brain | 1540 | 1040 | 0.6 |
| Skull | 2800 | 1900 | 8.0 |

For the frozen binary profile, stored metadata interprets `alpha0` with
`alpha_power=1.5` and units `dB/(MHz^1.5 cm)`. These semantics are inferred for
backward compatibility, not source-calibrated.

Implementation locators:

- `build_ct_acoustic_model.py:394-406`
- `build_ct_acoustic_model.py:573-607`
- `acoustic_mapping_profiles/simple_hu300.json`

## Source-to-claim assessment

| Source | What it supports | What it does not support here |
|---|---|---|
| Marsac et al., 2017, DOI [10.1080/02656736.2017.1295322](https://doi.org/10.1080/02656736.2017.1295322) | CT-informed heterogeneous speed-of-sound modelling can improve transcranial focusing; experimentally optimized relation at 1 MHz | The exact binary threshold or constant values in `simple_hu300`; accuracy at 250 kHz in Case079 |
| Webb et al., 2018, DOI [10.1109/TUFFC.2018.2827899](https://doi.org/10.1109/TUFFC.2018.2827899) | HU-to-velocity relationships depend on photon energy, reconstruction method and kernel; scanner-specific calibration matters | A universal HU-to-velocity conversion or the `simple_hu300` constants |
| [PRESTUS](https://github.com/Donders-Institute/PRESTUS) / Zenodo [10.5281/zenodo.15095860](https://doi.org/10.5281/zenodo.15095860) | An auditable implementation route for continuous mapping and k-Wave integration | Direct validation of the frozen Case079 mapping; PRESTUS draft routes are materially different |
| Local threshold sensitivity | Engineering sensitivity to HU threshold in this one CT | Anatomical skull segmentation accuracy without a reference mask |

The project profile's `evidence_source` text mentions a Gao baseline context and
threshold comparison. That is contextual provenance, not a matching formula or
experimental validation. It must not be upgraded to a direct citation claim.

## Target and imaging-QC audit

### Target

- Historical `target_020=[93,121,63]` was recovered as an engineering candidate.
- The current planning contract explicitly labels the target ROI
  `synthetic_not_anatomical`.
- No independent anatomical label, clinician selection rule or registered MRI
  target supports it.
- Manuscript status: **engineering demonstration target only**.

### Case079 segmentation

- Current skull segmentation is a first-pass threshold model (`HU >= 300`).
- Historical 250/300/400/500/700-HU comparisons exist, but no ground-truth skull
  mask, Dice/Hausdorff score or expert visual sign-off was found.
- The original slice thickness is 5 mm before isotropic resampling; resampling
  does not create new anatomical resolution.
- Manuscript status: reproducible rule, **not validated segmentation**.

### Registration

- No Case079 CT-to-anatomical-image registration is documented.
- The NLM public proxy has separate research registration evidence and cannot be
  transferred to Case079.
- The NLM records also retain an audit trail: the base `registration_report.json`
  reports an earlier quantitative failure, while the later
  `registration_qc_report.json` documents the corrected mask semantics and a
  quantitative pass, with expert visual QC still false. Manuscript entry points
  must cite the later QC amendment together with the retained limitation.

## Manuscript-safe Methods text

> For the Case079 engineering demonstration, CT values were resampled to the
> simulation grid and segmented by fixed thresholds: values below -500 HU were
> assigned to the coupling/background class, values from -500 to below 300 HU to
> soft tissue, and values at or above 300 HU to skull. Each class received a
> constant acoustic property triplet; the skull values were 2800 m/s,
> 1900 kg/m3 and an attenuation prefactor of 8.0 dB/(MHz^1.5 cm) with power 1.5.
> This frozen binary profile was retained for matched numerical comparisons and
> was not treated as a validated subject-specific acoustic calibration. The
> target was an engineering geometric candidate rather than an anatomically
> registered clinical target.

## Required limitations

1. The exact binary property set lacks direct primary-source calibration.
2. HU-to-acoustic relationships are scanner/reconstruction dependent.
3. Case079 has coarse 5-mm source slice spacing, threshold-only segmentation,
   no reference mask and no expert segmentation sign-off.
4. The target is neither anatomically registered nor clinically selected.
5. Numerical sensitivity does not substitute for material or anatomical
   validation.

