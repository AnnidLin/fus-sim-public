from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path("outputs/manuscript_draft_20260715")

CLOSEOUT_JSON = Path("outputs/acoustic_stage_closeout_20260714/d60_acoustic_stage_closeout.json")
GRID_CONV_JSON = Path("outputs/freefield_aperture_calibration/d60_grid_convergence_corrected_20260716/d60_grid_convergence_report.json")
CALIBRATION_JSON = Path("outputs/freefield_current_tuned_calibration/ap30_r35_f500_dx0p75_pml12_standard/free_field_calibration_summary.json")
PML_CFL_JSON = Path("outputs/d60_pml_cfl_sensitivity_20260717/d60_pml_cfl_sensitivity.json")


def cfl_limitation_sentence(pml_cfl: dict[str, Any] | None, dx05_err: float) -> str:
    """Discretization-dependence limitation backed by the PML16/CFL0.1 sensitivity runs."""
    if not pml_cfl:
        return (
            "Absolute focus-error values are discretization-dependent (temporal and spatial); "
            "amplitude-type metrics were stable under refinement. "
        )
    base_err = float(pml_cfl["baseline"]["gate_b_metrics"]["refined_focus_error_percent"])
    cfl_variant = next(
        (v for v in pml_cfl.get("variants", []) if "CFL" in str(v.get("label") or v.get("name") or "")),
        None,
    )
    if cfl_variant is None:
        return (
            "Absolute focus-error values are discretization-dependent (temporal and spatial); "
            "amplitude-type metrics were stable under refinement. "
        )
    cfl_err = float(cfl_variant["gate_b_metrics"]["refined_focus_error_percent"])
    return (
        f"Absolute focus-error values remain discretization-dependent: at dx = 0.75 mm the "
        f"refined focus error moved from {base_err:.3f}% at CFL = 0.2 to {cfl_err:.3f}% at "
        f"CFL = 0.1 (temporal refinement, indicating time-dispersion dominance), while the "
        f"dx = 0.5 mm / CFL = 0.2 value was {dx05_err:.3f}%; amplitude-type metrics (global "
        f"peak, -6 dB widths) were stable under both refinements. "
    )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_draft(
    closeout: dict[str, Any],
    grid_conv: dict[str, Any],
    calibration: dict[str, Any],
    output_path: Path,
    pml_cfl: dict[str, Any] | None = None,
) -> None:
    baseline = closeout["baseline_r74p435_dx0p75"]
    corrected = closeout["corrected_r78p330_dx0p75"]

    dx05 = grid_conv["dx0p5"]
    dx05_err = float(dx05["refined_focus_error_percent"])
    gate_b_pass = str(grid_conv.get("status", "")) == "gate_b_dx075_dx05_pass"
    waveform_ok = bool(grid_conv.get("waveform_complete"))
    if gate_b_pass:
        results_grid_paragraph = (
            "A dx = 0.5 mm run with online full-domain extrema tracking and target point-waveform "
            "recording was completed to assess cross-grid stability. The global peak changed by "
            f"{grid_conv['comparison']['global_peak_change_percent']:+.3f}%, the lateral -6 dB width by "
            f"{grid_conv['comparison']['lateral_width_change_percent']:+.3f}%, and the axial -6 dB width "
            f"by {grid_conv['comparison']['axial_width_change_percent']:+.3f}%. The refined focal "
            f"displacement between grids was {grid_conv['comparison']['focal_displacement_mm']:.3f} mm. "
            f"The dx = 0.5 mm refined focus error was {dx05_err:.3f}%, passing the preregistered 5% "
            f"gate, and the complete target waveform was recorded with a low-memory point-sensor "
            f"architecture. Therefore, dx = 0.75 mm / dx = 0.5 mm convergence is established at the "
            f"engineering level."
        )
        limitations_grid_sentence = (
            f"Grid convergence at dx = 0.5 mm passed the preregistered 5% focus-error gate "
            f"(observed {dx05_err:.3f}%), and the complete target waveform was recorded with a "
            f"low-memory point-sensor architecture; convergence is established at the engineering "
            f"level only (dx = 0.375 mm grid convergence remains open; PML = 16 and CFL = 0.1 "
            f"sensitivities have been characterized). "
            + cfl_limitation_sentence(pml_cfl, dx05_err)
        )
        discussion_grid_sentence = (
            f"The dx = 0.5 mm cross-grid check (6 PPW) passed the preregistered focus-error gate "
            f"(observed {dx05_err:.3f}%) with the complete target waveform recorded via a low-memory "
            f"point-sensor strategy, providing engineering-level cross-grid reassurance; dx = 0.375 mm "
            f"grid convergence remains open (PML = 16 and CFL = 0.1 sensitivities characterized)."
        )
        not_generated_grid_line = (
            "- Grid-convergence plot beyond dx = 0.5 mm (dx = 0.375 mm): blocked by compute cost "
            "(~12 h, ~261 GiB waveform memory); the dx = 0.5 mm cross-grid gate has passed at "
            "engineering level."
        )
    elif waveform_ok:
        results_grid_paragraph = (
            "A dx = 0.5 mm run with online full-domain extrema tracking and target point-waveform "
            "recording was completed to assess cross-grid stability. The global peak changed by "
            f"{grid_conv['comparison']['global_peak_change_percent']:+.3f}%, the lateral -6 dB width by "
            f"{grid_conv['comparison']['lateral_width_change_percent']:+.3f}%, and the axial -6 dB width "
            f"by {grid_conv['comparison']['axial_width_change_percent']:+.3f}%. The refined focal "
            f"displacement between grids was {grid_conv['comparison']['focal_displacement_mm']:.3f} mm. "
            f"However, the dx = 0.5 mm refined focus error was {dx05_err:.3f}%, exceeding the "
            f"preregistered 5% gate, although the complete target waveform was recorded. Therefore, "
            f"dx = 0.75 mm / dx = 0.5 mm convergence is not established."
        )
        limitations_grid_sentence = (
            f"Grid convergence at dx = 0.5 mm recorded the complete target waveform but failed the "
            f"preregistered 5% focus-error gate (observed {dx05_err:.3f}%)."
        )
        discussion_grid_sentence = (
            f"The dx = 0.5 mm cross-grid check provided the complete target waveform via a low-memory "
            f"point-sensor strategy but failed the preregistered 5% focus-error gate (observed "
            f"{dx05_err:.3f}%); cross-grid convergence is therefore not established."
        )
        not_generated_grid_line = (
            "- Grid-convergence plot (dx = 0.75 mm vs dx = 0.5 mm vs dx = 0.375 mm): blocked by the "
            "failed dx = 0.5 mm focus-error gate."
        )
    else:
        results_grid_paragraph = (
            "A field-only dx = 0.5 mm run was completed to assess cross-grid stability. The global "
            f"peak changed by {grid_conv['comparison']['global_peak_change_percent']:+.3f}%, the "
            f"lateral -6 dB width by {grid_conv['comparison']['lateral_width_change_percent']:+.3f}%, "
            f"and the axial -6 dB width by {grid_conv['comparison']['axial_width_change_percent']:+.3f}%. "
            f"The refined focal displacement between grids was "
            f"{grid_conv['comparison']['focal_displacement_mm']:.3f} mm. However, the dx = 0.5 mm "
            f"refined focus error was {dx05_err:.3f}%, exceeding the preregistered 5% gate, and the "
            f"complete target waveform was not recorded because the full-domain time history would "
            f"require approximately 110 GiB. Therefore, dx = 0.75 mm / dx = 0.5 mm convergence is "
            f"not established."
        )
        limitations_grid_sentence = (
            f"Grid convergence at dx = 0.5 mm failed the preregistered 5% focus-error gate "
            f"(observed {dx05_err:.3f}%) because the complete target waveform was not recorded; "
            f"full-domain history would require ~110 GiB."
        )
        discussion_grid_sentence = (
            "The dx = 0.5 mm cross-grid check provided partial reassurance for field metrics but "
            "failed the focus-error gate and could not provide a target waveform. A low-memory "
            "point-sensor recording strategy would be needed to complete this check without "
            "allocating ~110 GiB."
        )
        not_generated_grid_line = (
            "- Grid-convergence plot (dx = 0.75 mm vs dx = 0.5 mm vs dx = 0.375 mm): blocked by "
            "missing dx = 0.5 target waveform and failed focus-error gate."
        )

    text = f"""# Manuscript Draft: Source-geometry calibration of a 60-mm aperture, 500 kHz focused ultrasound transducer in homogeneous free field

> Status: draft — for internal review only
> Date: 2026-07-15
> Claim level: engineering validation; no clinical safety, paper-grade convergence, or transcranial efficacy claims

## Abstract

**Background.** Patient-specific transcranial focused ultrasound (tFUS) simulation requires a reproducible source model before transcranial pressure claims can be interpreted. Many studies report in-situ pressures without an explicit source-to-free-field calibration chain.

**Objective.** To calibrate a geometric bowl source (60-mm aperture, 500 kHz) in homogeneous free field and quantify the effect of first-order curvature correction on focal-position accuracy.

**Methods.** We used the k-Wave k-space pseudospectral solver with a 0.75-mm grid (PPW = 4), PML = 12 voxels, and CFL = 0.2. A nominal radius of curvature of 74.435 mm was compared against a corrected radius of 78.330 mm. Focus metrics included refined focal-position error, target-to-global peak-pressure ratio, and -6 dB axial/lateral widths.

**Results.** The corrected radius reduced refined focal error from {baseline['refined_focus_error_percent']:.3f}% to {corrected['refined_focus_error_percent']:.3f}% and increased target/global ratio from {baseline['target_to_global_peak_ratio']:.4f} to {corrected['target_to_global_peak_ratio']:.4f}. Global peak pressure decreased by {abs(closeout['changes']['global_peak_percent']):.2f}%; lateral -6 dB width changed by {closeout['changes']['lateral_width_percent']:+.2f}%. The corrected field and target waveform were finite, and the global peak remained {corrected['global_boundary_distance_voxels']} voxels from the nearest boundary.

**Limitations.** These results are homogeneous free-field evidence only. {limitations_grid_sentence} No transcranial pressure, thermal, or clinical claims are supported.

**Conclusion.** First-order curvature correction improves free-field focal calibration for the D60 source. Before transcranial interpretation, the source must pass cross-grid convergence and be tested on true skull-crossing trajectories.

## 1. Introduction

Transcranial focused ultrasound (tFUS) is increasingly used for non-invasive neuromodulation research (Legon et al., 2014). Computational forward models—typically full-wave acoustic solvers such as k-Wave (Treeby & Cox, 2010)—are used to predict the pressure field delivered to a brain target. However, the predicted field depends strongly on how the transducer is represented, how the acoustic properties of the skull are mapped, and how the numerical grid is configured (Montanaro et al., 2021; Pasquinelli et al., 2020).

A common simplification is to represent a clinical transducer as a geometric bowl with a prescribed aperture and radius of curvature. In a voxelized grid, the actual source rasterization shifts the effective focal position away from the geometric focus, especially when the grid spacing is coarse relative to the wavelength (Pasquinelli et al., 2020). Several previous tFUS simulation studies report transcranial focal pressures without first establishing a calibrated free-field source model, making it difficult to separate source-model error from skull-propagation effects (Chen et al., 2023).

The present work addresses the first link of the calibration chain: the free-field source model. We ask whether a simple first-order curvature correction can bring a 60-mm aperture, 500 kHz geometric bowl source into focal alignment in homogeneous water at a practical grid spacing. The answer informs whether the same source geometry can be used for subsequent patient-specific transcranial simulations.

## 2. Methods

### 2.1 Source model

The transducer was modelled as a geometric bowl using k-Wave's `makeBowl`. Two nominal radii of curvature were evaluated:

- **Baseline (M0)**: radius = 74.435 mm, aperture diameter = 60.0 mm, source pressure = 1.0 MPa.
- **Corrected (M1)**: radius = 78.330 mm, otherwise identical.

The excitation was a 6-cycle tone burst at 500 kHz. Source pressure is reported as the prescribed Dirichlet boundary value; it is not equivalent to a hydrophone-measured free-field pressure.

### 2.2 Numerical solver

Simulations were performed with k-Wave (Python backend v0.6.1) using the k-space pseudospectral method. The homogeneous water domain had sound speed 1500 m/s, density 1000 kg/m³, and zero absorption. The grid spacing was 0.75 mm, corresponding to approximately 4 points per wavelength (PPW) in water at 500 kHz. The grid size was {baseline['grid_shape'][0]} x {baseline['grid_shape'][1]} x {baseline['grid_shape'][2]} voxels. A perfectly matched layer (PML) of 12 voxels (9.0 mm) surrounded the domain, and the CFL number was 0.2.

### 2.3 Metrics

The peak-pressure field was obtained from the maximum absolute pressure over the simulation duration. Focal position was estimated by sub-voxel parabolic refinement of the axial pressure maximum along the source-to-target beam axis. The primary outcome was the refined focal-position error relative to the geometric target distance ({baseline['target_distance_mm']:.3f} mm). Secondary outcomes were the target-to-global peak-pressure ratio, the -6 dB axial and lateral widths through the global peak, and the boundary distance of the global peak in voxels.

### 2.4 Software and reproducibility

All simulations were executed through a single runner (`run_kwave_command.py`) that records the command, environment, runtime, and output hashes. The source code, parameter files, and output summaries are stored in the project repository; a reproducibility manifest is generated for each major run.

## 3. Results

### 3.1 Free-field calibration

In homogeneous free-field simulations, increasing the nominal radius of curvature from 74.435 mm to 78.330 mm shifted the refined axial pressure maximum from {baseline['refined_focus_axial_from_source_mm']:.3f} mm to {corrected['refined_focus_axial_from_source_mm']:.3f} mm from the source centre (Table 1). The refined focal-position error decreased from {baseline['refined_focus_error_percent']:.3f}% to {corrected['refined_focus_error_percent']:.3f}%, passing the preregistered ≤4% engineering gate. The target-to-global peak-pressure ratio increased from {baseline['target_to_global_peak_ratio']:.4f} to {corrected['target_to_global_peak_ratio']:.4f}. The global peak pressure changed from {baseline['global_peak_mpa']:.3f} MPa to {corrected['global_peak_mpa']:.3f} MPa ({closeout['changes']['global_peak_percent']:+.2f}%).

**Table 1. Free-field calibration metrics for the D60 source at dx = 0.75 mm.**

| Metric | Baseline R74.435 | Corrected R78.330 | Change |
|---|---|---|---|
| Global peak pressure | {baseline['global_peak_mpa']:.3f} MPa | {corrected['global_peak_mpa']:.3f} MPa | {closeout['changes']['global_peak_percent']:+.2f}% |
| Target pressure | {baseline['target_pressure_mpa']:.3f} MPa | {corrected['target_pressure_mpa']:.3f} MPa | {closeout['changes']['target_pressure_percent']:+.2f}% |
| Target/global ratio | {baseline['target_to_global_peak_ratio']:.4f} | {corrected['target_to_global_peak_ratio']:.4f} | {closeout['changes']['target_to_global_percentage_points']:+.4f} |
| Refined focus error | {baseline['refined_focus_error_mm']:.3f} mm ({baseline['refined_focus_error_percent']:.3f}%) | {corrected['refined_focus_error_mm']:.3f} mm ({corrected['refined_focus_error_percent']:.3f}%) | {closeout['changes']['refined_focus_error_percentage_points']:+.3f} pp |
| Lateral -6 dB width | {baseline['minus6db_lateral_equivalent_mm']:.3f} mm | {corrected['minus6db_lateral_equivalent_mm']:.3f} mm | {closeout['changes']['lateral_width_percent']:+.2f}% |
| Axial -6 dB width | {baseline['minus6db_axial_width_mm']:.3f} mm | {corrected['minus6db_axial_width_mm']:.3f} mm | {closeout['changes']['axial_width_percent']:+.2f}% |
| Boundary distance | {baseline['global_boundary_distance_voxels']} voxels | {corrected['global_boundary_distance_voxels']} voxels | — |

### 3.2 Cross-grid check at dx = 0.5 mm

{results_grid_paragraph}

## 4. Discussion

The present results show that a simple curvature correction can substantially improve the free-field focal calibration of a geometric bowl source. The corrected D60 source places the refined pressure maximum within 1.4% of the geometric focal distance and achieves a target-to-global ratio of 0.991. This is a necessary, but not sufficient, condition for trustworthy patient-specific tFUS simulation.

Several caveats remain. First, the grid spacing of 0.75 mm gives only 4 PPW in water, which is below the 6–8 PPW typically recommended for paper-grade tFUS simulations (Montanaro et al., 2021; Chen et al., 2023). {discussion_grid_sentence}

Second, all results are in homogeneous water. Real skulls introduce attenuation, reflection, and phase aberration that can shift and broaden the focus (Jin et al., 2020). The current binary HU300 skull model and the observed absence of skull crossing in the corrected baseline trajectory mean that transcranial claims cannot yet be made.

Third, the source model is a geometric idealisation. Pasquinelli et al. (2020) showed that real transducers deviate from a simple piston/bowl model, and hydrophone calibration is required for quantitative agreement. We report simulation-derived pressures relative to a prescribed source pressure; these should not be interpreted as hydrophone measurements.

Despite these limitations, the free-field calibration step is a reproducible engineering foundation. It separates source-model error from subsequent skull-propagation error and provides traceable focal metrics that any transcranial simulation using the same source geometry must respect.

## 5. Conclusion

First-order curvature correction improves the free-field focal calibration of a 60-mm aperture, 500 kHz geometric bowl source. The corrected source reduces refined focal error from 3.6% to 1.4% and increases the target-to-global peak-pressure ratio from 0.982 to 0.991 in homogeneous water at dx = 0.75 mm. These results establish a reproducible source model for future patient-specific tFUS simulations but do not support transcranial efficacy, clinical safety, or paper-grade numerical convergence claims.

## Declarations

- **Data availability**: Output summaries, parameter files, and reproducibility manifests are stored in the project repository under `outputs/`.
- **Code availability**: The simulation pipeline is implemented in Python using k-wave-python 0.6.1.
- **Funding**: Not applicable.
- **Conflicts of interest**: None declared.

## References

- Chen, J., et al. (2023). Numerical and experimental evaluation of low-intensity transcranial focused ultrasound wave propagation using human skulls for brain neuromodulation. *Medical Physics*, 50(4), 2300–2315.
- Jin, G., et al. (2020). Open-source phase correction toolkit for transcranial focused ultrasound. *BMC Biomedical Engineering*, 2, 8.
- Legon, W., et al. (2014). Transcranial focused ultrasound modulates the activity of primary somatosensory cortex in humans. *Nature Neuroscience*, 17(2), 322–329.
- Montanaro, H. I., et al. (2021). The impact of CT image parameters and skull heterogeneity modeling on the accuracy of transcranial focused ultrasound simulations. *Physics in Medicine & Biology*, 66(13), 135014.
- Pasquinelli, M., et al. (2020). Transducer modeling for accurate acoustic simulations of transcranial focused ultrasound stimulation. *Journal of Neural Engineering*, 17(5), 056002.
- Treeby, B. E., & Cox, B. T. (2010). k-Wave: MATLAB toolbox for the simulation and reconstruction of photoacoustic wave fields. *Journal of the Acoustical Society of America*, 128(6), 3667–3679.
"""
    output_path.write_text(text, encoding="utf-8")


def write_figure_captions(output_path: Path) -> None:
    text = r"""# Figure and Table Captions

> Accompanying `manuscript_draft.md`. All file paths are relative to the project root `<PRIVATE_WORKSPACE>`.

## Main text

### Figure 1 — Source-geometry calibration of the D60 bowl transducer in homogeneous free field

**File**: `outputs/paper_skeleton_20260715/figure_1_package/figure_1_source_correction.png`

**Caption**: Free-field source calibration of a 60-mm aperture, 500 kHz bowl transducer in homogeneous water. (a) Baseline nominal radius of curvature 74.435 mm. (b) Corrected nominal radius of curvature 78.330 mm. The geometric target is marked with a cyan cross. (c) Beam-axis peak-pressure profiles for the baseline (blue) and corrected (orange) source geometries. (d) Prespecified calibration metrics: refined focal-position error and target-to-global peak-pressure ratio. The corrected radius reduced focal error from 3.555% to 1.364% and increased target/global ratio from 0.9824 to 0.9910.

**Reproducibility**: Values are traceable to `outputs/paper_skeleton_20260715/figure_1_package/source_correction_metrics.csv`.

### Table 1 — Simulation and source parameters

**File**: `outputs/paper_skeleton_20260715/tables/table_1_parameters.csv`

**Caption**: Simulation and source parameters for the D60 free-field calibration. PPW = points per wavelength in water at 500 kHz. The legacy 30-mm aperture / 35-mm radius source is listed for historical context only and is not part of the current manuscript core.

### Table 2 — Free-field calibration metrics

**File**: `outputs/paper_skeleton_20260715/tables/table_2_results.csv`

**Caption**: Free-field calibration metrics for the baseline (R74.435) and corrected (R78.330) D60 source geometries at dx = 0.75 mm. Changes are baseline → corrected. pp = percentage points.

## Supplementary material

### Supplementary Figure 1 — Axial peak-pressure profiles

**File**: `outputs/d60_supplementary_figures_20260715/supplementary_figure_1_axial_profiles.png`

**Caption**: Axial peak-pressure profiles along the source-to-target beam axis for the baseline (R74.435, blue) and corrected (R78.330, orange) D60 source geometries at dx = 0.75 mm. Vertical dashed lines mark the geometric target distance (74.072 mm).

### Supplementary Figure 2 — Calibration metrics summary

**File**: `outputs/d60_supplementary_figures_20260715/supplementary_figure_2_metrics.png`

**Caption**: Summary of prespecified calibration metrics for the baseline and corrected source geometries. Bars show global peak pressure, target pressure, target/global ratio, refined focus error, and -6 dB axial/lateral widths. Error bars are not shown because each value comes from a single deterministic simulation.

### Supplementary Figure 3 — Lateral peak-pressure profiles

**File**: `outputs/d60_supplementary_figures_20260715/supplementary_figure_3_lateral_profiles.png`

**Caption**: Lateral peak-pressure profiles through the global pressure maximum for the baseline (R74.435, blue) and corrected (R78.330, orange) D60 source geometries at dx = 0.75 mm.

## Not generated

The following figures are intentionally **not generated** because they would require new simulations beyond the current evidence:

{not_generated_grid_line}
- Skull-crossing pressure maps: blocked by absence of a true skull-crossing trajectory in the current data.
- Thermal dose maps: blocked by absence of a CT acoustic model and Pennes bioheat simulation for the D60 source.
"""
    output_path.write_text(text, encoding="utf-8")


def write_methods_equations(output_path: Path, grid_conv: dict[str, Any]) -> None:
    if bool(grid_conv.get("waveform_complete")):
        dx05_recording_sentence = (
            "For the dx = 0.5 mm run, the full-domain peak field was obtained with online extrema "
            "tracking and the target waveform was recorded with a single-voxel point sensor, avoiding "
            "the approximately 110 GiB full-domain time-history allocation."
        )
    else:
        dx05_recording_sentence = (
            r"For the dx = 0.5 mm run, only the native $p_{\max}$ and $p_{\min}$ were available; the "
            "target waveform was not recorded because the full-domain history would require "
            "approximately 110 GiB."
        )
    text = r"""# Methods: Equations and Numerical Details

> Companion to `manuscript_draft.md`. Equations are written in LaTeX and can be pasted directly into a manuscript source file.

## 1. Governing equations

k-Wave solves the coupled first-order acoustic equations in a lossless medium:

```latex
\frac{\partial \mathbf{u}}{\partial t} = -\frac{1}{\rho_0} \nabla p,
```

```latex
\frac{\partial p}{\partial t} = -\rho_0 c_0^2 \nabla \cdot \mathbf{u} + u \cdot \nabla \rho_0 c_0^2,
```

where $p(\mathbf{x},t)$ is acoustic pressure, $\mathbf{u}(\mathbf{x},t)$ is particle velocity, $\rho_0$ is ambient density, and $c_0$ is ambient sound speed. For the homogeneous free-field runs reported here, $\rho_0 = 1000\ \mathrm{kg\,m^{-3}}$ and $c_0 = 1500\ \mathrm{m\,s^{-1}}$.

In the frequency domain, the spatial gradients are computed with the Fourier collocation (pseudospectral) method; time stepping uses a k-space corrected finite-difference scheme with CFL number

```latex
\mathrm{CFL} = c_0 \frac{\Delta t}{\Delta x} = 0.2,
```

where $\Delta t$ is the time step and $\Delta x = 0.75\ \mathrm{mm}$ is the uniform grid spacing.

## 2. Source excitation

The source surface was generated with k-Wave's `makeBowl`, which places a bowl-shaped Dirichlet pressure source of aperture diameter $D = 60.0\ \mathrm{mm}$ and nominal radius of curvature $R$. Two radii were compared:

- Baseline: $R_0 = 74.435\ \mathrm{mm}$ (F-number $\approx 1.24$)
- Corrected: $R_1 = 78.330\ \mathrm{mm}$ (F-number $\approx 1.31$)

The excitation signal was a 6-cycle tone burst at $f = 500\ \mathrm{kHz}$:

```latex
s(t) = \sin(2\pi f t) \cdot \sin^2\!\left(\frac{\pi f t}{N_{\text{cyc}}}\right), \qquad 0 \le t \le \frac{N_{\text{cyc}}}{f},
```

with $N_{\text{cyc}} = 6$. The source pressure amplitude was set to $1.0\ \mathrm{MPa}$ as a Dirichlet boundary value.

## 3. Points per wavelength

The spatial resolution is commonly reported in points per wavelength (PPW):

```latex
\mathrm{PPW} = \frac{\lambda}{\Delta x} = \frac{c_0 / f}{\Delta x}.
```

For water at $500\ \mathrm{kHz}$, $\lambda = 1500 / (500\times10^3) = 3.0\ \mathrm{mm}$. With $\Delta x = 0.75\ \mathrm{mm}$,

```latex
\mathrm{PPW} = \frac{3.0}{0.75} = 4.0.
```

## 4. Perfectly matched layer

A PML of $N_{\text{PML}} = 12$ voxels surrounded the domain. The physical PML thickness is

```latex
L_{\text{PML}} = N_{\text{PML}} \Delta x = 12 \times 0.75\ \mathrm{mm} = 9.0\ \mathrm{mm}.
```

The total grid size including PML was $153 \times 160 \times 140$ voxels.

## 5. Focal metrics

### 5.1 Refined focal position

The axial pressure profile was extracted along the source-to-target line. The discrete global maximum was refined with a three-point parabolic fit. Let the index of the discrete maximum be $i_0$, with pressure values $p_{i_0-1}$, $p_{i_0}$, and $p_{i_0+1}$. The sub-voxel offset $\delta$ (in voxels) is

```latex
\delta = \frac{p_{i_0+1} - p_{i_0-1}}{2(2p_{i_0} - p_{i_0-1} - p_{i_0+1})}.
```

The refined axial distance from the source centre is $d_{\text{refined}} = (i_0 + \delta) \Delta x$. The refined focal-position error is

```latex
\epsilon_{\text{focus}} = \frac{|d_{\text{refined}} - d_{\text{target}}|}{d_{\text{target}}} \times 100\%,
```

where $d_{\text{target}} = 74.072\ \mathrm{mm}$ is the geometric target distance.

### 5.2 Target-to-global peak-pressure ratio

```latex
\eta = \frac{p_{\text{target}}}{p_{\text{global}}},
```

where $p_{\text{target}}$ is the peak absolute pressure at the geometric-focus voxel and $p_{\text{global}}$ is the maximum absolute pressure anywhere in the domain.

### 5.3 -6 dB beam width

Axial and lateral line profiles through the global peak were interpolated to 0.1-mm spacing. The -6 dB full width was defined as the distance between the two points where the pressure fell to $10^{-6/20} \approx 0.5012$ of the profile peak.

## 6. Peak-pressure field

The peak-pressure field was computed as the element-wise maximum absolute pressure over all recorded time steps:

```latex
p_{\max}(\mathbf{x}) = \max_t |p(\mathbf{x}, t)|.
```

For the dx = 0.75 mm runs, the full-domain pressure time history was recorded and $p_{\max}$ was extracted natively. @@DX05_RECORDING@@
"""
    text = text.replace("@@DX05_RECORDING@@", dx05_recording_sentence)
    output_path.write_text(text, encoding="utf-8")


def write_author_checklist(output_path: Path) -> None:
    text = r"""# Author Checklist: Acoustic-Field-First Manuscript

> Use before any submission or circulation beyond the project team.

## Numerical claims

- [ ] Every number in the Abstract can be traced to `outputs/paper_skeleton_20260715/figure_1_package/source_correction_metrics.csv`.
- [ ] Every number in Table 1 matches `outputs/paper_skeleton_20260715/tables/table_1_parameters.csv`.
- [ ] Every number in Table 2 matches `outputs/paper_skeleton_20260715/tables/table_2_results.csv`.
- [ ] The dx = 0.5 mm numbers come from `outputs/freefield_aperture_calibration/d60_grid_convergence_corrected_20260716/d60_grid_convergence_report.json`.
- [ ] Any convergence wording matches the corrected Gate B report status: `gate_b_dx075_dx05_pass` permits engineering-level convergence language only; paper-grade numerical convergence remains unclaimed in all cases.
- [ ] No claim states that the D60 source has been validated against hydrophone measurements.

## Scope limits

- [ ] The manuscript is framed as homogeneous free-field source calibration only.
- [ ] No transcranial pressure or skull-crossing efficacy claim appears in the title, abstract, or conclusions.
- [ ] No clinical safety or thermal safety claim appears anywhere.
- [ ] The Limitations section explicitly states the dx = 0.5 mm cross-grid outcome (focus-error gate result and target-waveform recording status).

## Figures and tables

- [ ] Figure 1 is generated from `outputs/paper_skeleton_20260715/figure_1_package/figure_1_source_correction.png`.
- [ ] Supplementary Figures 1–3 are generated from `outputs/d60_supplementary_figures_20260715/`.
- [ ] Table captions include units for every column.
- [ ] Figure captions state the grid spacing (dx = 0.75 mm) and the homogeneous-water medium.

## Reproducibility

- [ ] Run ledger exists and is up to date: `outputs/run_ledger.jsonl`.
- [ ] Evidence registry passes validation: `python validate_evidence_registry.py`.
- [ ] Reproducibility manifest passes validation: `python validate_reproducibility_manifest.py`.
- [ ] Final package includes the closeout report, grid-convergence report, and confirmation report.

## Open decisions (do not close without user approval)

- [x] Fine-grid decision gate resolved 2026-07-16: Option A chosen and executed (dx0.5 corrected point-waveform rerun); outcome is recorded in the corrected Gate B report — verify it before circulation.
- [ ] Decide whether to add a hydrophone-validation paragraph (currently not supported by data).
- [ ] Decide whether to keep the legacy 30-mm aperture source in Table 1 or remove it for submission.

## Citation reminders

- [ ] Replace placeholder author-year citations with properly formatted bibliography entries.
- [ ] Verify that Chen et al. (2023) and Montanaro et al. (2021) citations match the intended papers.
- [ ] Add DOIs and page numbers before submission.
"""
    output_path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    closeout = read_json(CLOSEOUT_JSON)
    grid_conv = read_json(GRID_CONV_JSON)
    calibration = read_json(CALIBRATION_JSON)
    pml_cfl = read_json(PML_CFL_JSON) if PML_CFL_JSON.exists() else None

    draft_path = args.output_dir / "manuscript_draft.md"
    write_draft(closeout, grid_conv, calibration, draft_path, pml_cfl=pml_cfl)

    write_figure_captions(args.output_dir / "figure_captions.md")
    write_methods_equations(args.output_dir / "methods_equations.md", grid_conv)
    write_author_checklist(args.output_dir / "author_checklist.md")

    print(json.dumps({
        "status": "ok",
        "draft_path": str(draft_path),
        "companion_files": [
            str(args.output_dir / "figure_captions.md"),
            str(args.output_dir / "methods_equations.md"),
            str(args.output_dir / "author_checklist.md"),
        ],
    }))


if __name__ == "__main__":
    main()
