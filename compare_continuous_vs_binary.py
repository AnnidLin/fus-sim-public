from __future__ import annotations

import argparse
import json
from pathlib import Path
import numpy as np

# Ensure matplotlib runs headlessly
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent

def load_simulation_data(run_dir: Path, model_path: Path) -> dict[str, any]:
    npz_path = run_dir / "pressure_max_mpa.npz"
    summary_path = run_dir / "summary.json"
    
    if not npz_path.exists():
        raise FileNotFoundError(f"Missing simulation NPZ: {npz_path}")
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing simulation summary: {summary_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Missing input model: {model_path}")
        
    npz_data = np.load(npz_path)
    if "target_waveform" not in npz_data:
        raise ValueError(f"NPZ file does not contain 'target_waveform': {npz_path}. Was --record-target-waveform enabled?")
    
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    model_data = np.load(model_path)
    
    # Extract local c and rho at the focal point
    target_idx = model_data["target_index_ijk"]
    c_local = float(model_data["sound_speed"][tuple(target_idx)])
    rho_local = float(model_data["density"][tuple(target_idx)])
    alpha_local = float(model_data["alpha_coeff"][tuple(target_idx)])
    
    # dt_s
    dt_s = float(summary["runtime"]["dt_s"])
    waveform = npz_data["target_waveform"]  # in Pa
    
    pressure_max_mpa = npz_data["pressure_max_mpa"]
    dx_m = float(npz_data["dx_m"])
    target_ijk = npz_data["target_index_ijk"]
    effective_peak_ijk = np.array(summary["pressure"]["effective_peak_index_ijk"], dtype=int)
    
    return {
        "waveform": waveform,
        "c": c_local,
        "rho": rho_local,
        "alpha": alpha_local,
        "dt_s": dt_s,
        "pressure_max_mpa": pressure_max_mpa,
        "dx_m": dx_m,
        "target_ijk": target_ijk,
        "effective_peak_ijk": effective_peak_ijk,
        "summary": summary
    }

def compute_fwhm(pressure_max_mpa: np.ndarray, peak_idx: np.ndarray, dx_m: float) -> tuple[float, float, float]:
    """
    Computes FWHM along x, y, and z axes passing through peak_idx.
    FWHM is where pressure >= P_max / sqrt(2).
    """
    p_peak = pressure_max_mpa[tuple(peak_idx)]
    threshold = p_peak / np.sqrt(2.0)
    
    # X axis FWHM
    line_x = pressure_max_mpa[:, peak_idx[1], peak_idx[2]]
    inside_x = np.where(line_x >= threshold)[0]
    fwhm_x = (inside_x.max() - inside_x.min() + 1) * dx_m * 1000.0 if inside_x.size else 0.0
    
    # Y axis FWHM
    line_y = pressure_max_mpa[peak_idx[0], :, peak_idx[2]]
    inside_y = np.where(line_y >= threshold)[0]
    fwhm_y = (inside_y.max() - inside_y.min() + 1) * dx_m * 1000.0 if inside_y.size else 0.0
    
    # Z axis FWHM
    line_z = pressure_max_mpa[peak_idx[0], peak_idx[1], :]
    inside_z = np.where(line_z >= threshold)[0]
    fwhm_z = (inside_z.max() - inside_z.min() + 1) * dx_m * 1000.0 if inside_z.size else 0.0
    
    return fwhm_x, fwhm_y, fwhm_z

def main() -> None:
    parser = argparse.ArgumentParser(description="Compare focal pressure waveform and metrics of two simulations.")
    parser.add_argument(
        "--baseline-dir",
        default=str(PROJECT_ROOT / "outputs" / "ct_comparison_runs" / "079_binary_standard"),
        help="Path to baseline simulation run directory."
    )
    parser.add_argument(
        "--baseline-model",
        default=str(PROJECT_ROOT / "outputs" / "ct_acoustic_models_batch" / "079_bone300_dx1" / "acoustic_model_3d.npz"),
        help="Path to baseline acoustic model NPZ."
    )
    parser.add_argument(
        "--candidate-dir",
        default=str(PROJECT_ROOT / "outputs" / "ct_comparison_runs" / "079_continuous_standard"),
        help="Path to candidate simulation run directory."
    )
    parser.add_argument(
        "--candidate-model",
        default=str(PROJECT_ROOT / "outputs" / "ct_acoustic_model_3d_profile_continuous" / "acoustic_model_3d.npz"),
        help="Path to candidate acoustic model NPZ."
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "outputs" / "continuous_vs_binary_comparison"),
        help="Path to output comparison directory."
    )
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Loading baseline simulation data from {args.baseline_dir}...")
    binary = load_simulation_data(Path(args.baseline_dir), Path(args.baseline_model))
    
    print(f"Loading candidate simulation data from {args.candidate_dir}...")
    continuous = load_simulation_data(Path(args.candidate_dir), Path(args.candidate_model))
    
    # 1. Timesteps and time axes
    t_bin = np.arange(len(binary["waveform"])) * binary["dt_s"] * 1e6  # in us
    t_con = np.arange(len(continuous["waveform"])) * continuous["dt_s"] * 1e6  # in us
    
    p_bin = binary["waveform"] / 1e6  # in MPa
    p_con = continuous["waveform"] / 1e6  # in MPa
    
    # Truncate to match length for residual calculations
    min_len = min(len(p_bin), len(p_con))
    p_bin_tr = p_bin[:min_len]
    p_con_tr = p_con[:min_len]
    waveform_rmse_mpa = float(np.sqrt(np.mean((p_con_tr - p_bin_tr) ** 2)))
    
    # 2. Acoustic Intensity (plane-wave approximation)
    i_inst_bin = (binary["waveform"] ** 2) / (binary["rho"] * binary["c"]) / 1e4  # W/cm^2
    i_inst_con = (continuous["waveform"] ** 2) / (continuous["rho"] * continuous["c"]) / 1e4  # W/cm^2
    
    ita_bin = float(np.mean(i_inst_bin))
    ita_con = float(np.mean(i_inst_con))
    i_peak_bin = float(np.max(i_inst_bin))
    i_peak_con = float(np.max(i_inst_con))
    
    # 3. Particle Displacement
    u_bin = np.cumsum(binary["waveform"]) / (binary["rho"] * binary["c"]) * binary["dt_s"] * 1e9 # nm
    u_con = np.cumsum(continuous["waveform"]) / (continuous["rho"] * continuous["c"]) * continuous["dt_s"] * 1e9 # nm
    
    disp_peak_bin = float(np.max(np.abs(u_bin)))
    disp_peak_con = float(np.max(np.abs(u_con)))
    disp_p2p_bin = float(np.ptp(u_bin))
    disp_p2p_con = float(np.ptp(u_con))
    
    # 4. Focal Peak Pressures
    p_max_bin = float(np.max(p_bin))
    p_min_bin = float(np.min(p_bin))
    p_p2p_bin = p_max_bin - p_min_bin
    
    p_max_con = float(np.max(p_con))
    p_min_con = float(np.min(p_con))
    p_p2p_con = p_max_con - p_min_con
    
    # 5. FWHM and Focal Shift Calculations
    bin_fwhm_x, bin_fwhm_y, bin_fwhm_z = compute_fwhm(binary["pressure_max_mpa"], binary["effective_peak_ijk"], binary["dx_m"])
    con_fwhm_x, con_fwhm_y, con_fwhm_z = compute_fwhm(continuous["pressure_max_mpa"], continuous["effective_peak_ijk"], continuous["dx_m"])
    
    focal_shift_bin_mm = float(binary["summary"]["pressure"]["effective_peak_to_target_distance_mm"])
    focal_shift_con_mm = float(continuous["summary"]["pressure"]["effective_peak_to_target_distance_mm"])
    
    # Print metrics summary
    print("\n=== COMPARISON METRICS SUMMARY ===")
    print(f"Baseline model:  Local c={binary['c']:.1f} m/s, rho={binary['rho']:.1f} kg/m3")
    print(f"Candidate model: Local c={continuous['c']:.1f} m/s, rho={continuous['rho']:.1f} kg/m3")
    print("-------------------------------------------------")
    print(f"Peak positive pressure (MPa): Baseline={p_max_bin:.4f}, Candidate={p_max_con:.4f} (Diff: {(p_max_con - p_max_bin)/p_max_bin*100:+.2f}%)")
    print(f"Time-average Intensity I_ta (W/cm^2): Baseline={ita_bin:.4f}, Candidate={ita_con:.4f} (Diff: {(ita_con - ita_bin)/ita_bin*100:+.2f}%)")
    print(f"Waveform RMSE (MPa): {waveform_rmse_mpa:.4f}")
    print(f"Focal Shift (mm): Baseline={focal_shift_bin_mm:.3f}, Candidate={focal_shift_con_mm:.3f}")
    print(f"FWHM Axial X (mm): Baseline={bin_fwhm_x:.3f}, Candidate={con_fwhm_x:.3f}")
    print(f"FWHM Lateral Y/Z (mm): Baseline=({bin_fwhm_y:.3f}, {bin_fwhm_z:.3f}), Candidate=({con_fwhm_y:.3f}, {con_fwhm_z:.3f})")
    
    # 5. Plotting Pressure Waveform Comparison
    plt.figure(figsize=(10, 5))
    plt.plot(t_bin, p_bin, label='Baseline Model', color='#1f77b4', alpha=0.8)
    plt.plot(t_con, p_con, label='Candidate Model', color='#d62728', alpha=0.8, linestyle='--')
    plt.xlabel('Time ($\mu$s)')
    plt.ylabel('Pressure (MPa)')
    plt.title('Focal Point Pressure Waveform Comparison')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "pressure_waveform_comparison.png", dpi=300)
    plt.close()
    
    # 6. Plotting Displacement Comparison
    plt.figure(figsize=(10, 5))
    plt.plot(t_bin, u_bin, label='Baseline Model', color='#1f77b4', alpha=0.8)
    plt.plot(t_con, u_con, label='Candidate Model', color='#d62728', alpha=0.8, linestyle='--')
    plt.xlabel('Time ($\mu$s)')
    plt.ylabel('Particle Displacement (nm)')
    plt.title('Focal Point Particle Displacement Comparison')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "displacement_waveform_comparison.png", dpi=300)
    plt.close()
    
    # 7. Write Markdown Report
    report_path = output_dir / "comparison_report.md"
    
    report_content = f"""# Continuous vs Binary Skull Simulation Focal Comparison Report

This report compares the focal acoustic field metrics of the **Candidate Acoustic Model** ({continuous['summary']['mapping_profile']['profile_id'] if 'mapping_profile' in continuous['summary'] and continuous['summary']['mapping_profile'] else 'N/A'}) against the **Baseline Model** under standard simulation parameters.

## Focal Acoustic Metrics Summary

| Metric | Baseline Model | Candidate Model | Relative Difference |
| :--- | :---: | :---: | :---: |
| **Local Sound Speed ($c$)** | {binary['c']:.1f} m/s | {continuous['c']:.1f} m/s | {(continuous['c'] - binary['c'])/binary['c']*100:+.2f}% |
| **Local Density ($\\rho$)** | {binary['rho']:.1f} kg/m³ | {continuous['rho']:.1f} kg/m³ | {(continuous['rho'] - binary['rho'])/binary['rho']*100:+.2f}% |
| **Local Attenuation ($\\alpha$)** | {binary['alpha']:.3f} dB/MHz/cm | {continuous['alpha']:.3f} dB/MHz/cm | {(continuous['alpha'] - binary['alpha'])/binary['alpha']*100:+.2f}% |
| **Peak Positive Pressure ($p_+$)** | {p_max_bin:.4f} MPa | {p_max_con:.4f} MPa | {(p_max_con - p_max_bin)/p_max_bin*100:+.2f}% |
| **Peak Negative Pressure ($p_-$)** | {p_min_bin:.4f} MPa | {p_min_con:.4f} MPa | {(p_min_con - p_min_bin)/abs(p_min_bin)*100:+.2f}% |
| **Peak-to-Peak Pressure ($p_{{p2p}}$)** | {p_p2p_bin:.4f} MPa | {p_p2p_con:.4f} MPa | {(p_p2p_con - p_p2p_bin)/p_p2p_bin*100:+.2f}% |
| **Time-Average Intensity ($I_{{ta}}$)** | {ita_bin:.4f} W/cm² | {ita_con:.4f} W/cm² | {(ita_con - ita_bin)/ita_bin*100:+.2f}% |
| **Peak Instantaneous Intensity ($I_{{peak}}$)** | {i_peak_bin:.4f} W/cm² | {i_peak_con:.4f} W/cm² | {(i_peak_con - i_peak_bin)/i_peak_bin*100:+.2f}% |
| **Max Displacement ($|u|_{{max}}$)** | {disp_peak_bin:.2f} nm | {disp_peak_con:.2f} nm | {(disp_peak_con - disp_peak_bin)/disp_peak_bin*100:+.2f}% |
| **Peak-to-Peak Displacement ($u_{{p2p}}$)** | {disp_p2p_bin:.2f} nm | {disp_p2p_con:.2f} nm | {(disp_p2p_con - disp_p2p_bin)/disp_p2p_bin*100:+.2f}% |
| **Focal Shift (Effective vs Target)** | {focal_shift_bin_mm:.3f} mm | {focal_shift_con_mm:.3f} mm | {(focal_shift_con_mm - focal_shift_bin_mm):+.3f} mm |
| **FWHM - Axial X** | {bin_fwhm_x:.3f} mm | {con_fwhm_x:.3f} mm | {(con_fwhm_x - bin_fwhm_x)/bin_fwhm_x*100:+.2f}% |
| **FWHM - Lateral Y** | {bin_fwhm_y:.3f} mm | {con_fwhm_y:.3f} mm | {(con_fwhm_y - bin_fwhm_y)/bin_fwhm_y*100:+.2f}% |
| **FWHM - Lateral Z** | {bin_fwhm_z:.3f} mm | {con_fwhm_z:.3f} mm | {(con_fwhm_z - bin_fwhm_z)/bin_fwhm_z*100:+.2f}% |

### Waveform Residual Metrics
*   **Focal Waveform RMSE**: {waveform_rmse_mpa:.4f} MPa

## Visualizations

### 1. Focal Pressure Waveform Comparison
![Focal Pressure Waveform](pressure_waveform_comparison.png)

### 2. Particle Displacement Comparison
![Particle Displacement](displacement_waveform_comparison.png)

## Physical Findings and Interpretation

1. **Local Parameter Context**:
   - The baseline model assignments represent a uniform or simplified layer structure.
   - The continuous model applies linear interpolation or PRESTUS-style custom density/sound-speed mappings. At the focal voxel, the continuous skull property results in $c = {continuous['c']:.1f}$ m/s and $\\rho = {continuous['rho']:.1f}$ kg/m³, which represents a more realistic heterogeneous layer transition.

2. **Acoustic Transmittance & Focus**:
   - The peak positive pressure in the continuous model is **{p_max_con:.4f} MPa** compared to **{p_max_bin:.4f} MPa** in the baseline model (relative change of **{(p_max_con - p_max_bin)/p_max_bin*100:+.2f}%**).
   - The focal FWHM axial width has shifted from **{bin_fwhm_x:.3f} mm** to **{con_fwhm_x:.3f} mm** (change of **{(con_fwhm_x - bin_fwhm_x)/bin_fwhm_x*100:+.2f}%**).

3. **Mechanical Displacement**:
   - The peak-to-peak particle displacement shows a relative change of **{(disp_p2p_con - disp_p2p_bin)/disp_p2p_bin*100:+.2f}%**. Since displacement is estimated by integrating velocity $v(t) \\approx p(t) / (\\rho c)$, the changes in local density and sound speed scale the acoustic pressure differences, resulting in a physically consistent displacement profile.

---
*Report generated automatically.*
"""
    
    report_path.write_text(report_content, encoding="utf-8")
    print(f"Comparison report written successfully to {report_path}")

if __name__ == "__main__":
    main()
