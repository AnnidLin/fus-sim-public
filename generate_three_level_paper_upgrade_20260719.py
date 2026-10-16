from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "outputs" / "acoustic_paper_submission_package_20260715"
CONVERGENCE = ROOT / "outputs" / "freefield_aperture_calibration" / "d60_grid_convergence_three_level_20260719" / "report.json"
SENSITIVITY = ROOT / "outputs" / "d60_pml_cfl_sensitivity_20260717" / "d60_pml_cfl_sensitivity.json"
EQUIVALENCE = ROOT / "outputs" / "a4b_standard_tr_confirmation_20260719" / "preset_equivalence" / "preset_equivalence_report.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "acoustic_paper_submission_package_three_level_20260719"


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"Expected exactly one manuscript block, found {text.count(old)}")
    return text.replace(old, new)


def convergence_rows(report: dict) -> list[dict]:
    rows = []
    for key in ("dx0p75", "dx0p5", "dx0p375"):
        level = report[key]
        rows.append(
            {
                "grid_spacing_mm": level["dx_mm"],
                "points_per_wavelength": 3.0 / level["dx_mm"],
                "global_peak_mpa": level["global_peak_mpa"],
                "target_to_global_ratio": level["target_to_global_peak_ratio"],
                "refined_focus_error_percent": level["refined_focus_error_percent"],
                "lateral_minus6db_mm": level["minus6db_lateral_equivalent_mm"],
                "axial_minus6db_mm": level["minus6db_axial_width_mm"],
                "runtime_s": level["runtime_s"],
            }
        )
    return rows


def write_table(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_figure(rows: list[dict], path: Path) -> None:
    dx = [row["grid_spacing_mm"] for row in rows]
    focus = [row["refined_focus_error_percent"] for row in rows]
    peak = [row["global_peak_mpa"] for row in rows]
    lateral = [row["lateral_minus6db_mm"] for row in rows]
    axial = [row["axial_minus6db_mm"] for row in rows]

    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.25), constrained_layout=True)
    colors = ["#1b6ca8", "#238b57", "#c65d21"]
    axes[0].plot(dx, focus, marker="o", color=colors[0], linewidth=2)
    axes[0].set(xlabel="Grid spacing (mm)", ylabel="Refined focus error (%)", title="Focal-position error")
    axes[1].plot(dx, peak, marker="o", color=colors[1], linewidth=2)
    axes[1].set(xlabel="Grid spacing (mm)", ylabel="Global peak (MPa)", title="Peak-pressure stability")
    axes[2].plot(dx, lateral, marker="o", color=colors[2], linewidth=2, label="Lateral")
    axes[2].plot(dx, axial, marker="s", color="#525b65", linewidth=2, label="Axial")
    axes[2].set(xlabel="Grid spacing (mm)", ylabel="-6 dB width (mm)", title="Focal dimensions")
    axes[2].legend(frameon=False)
    for ax in axes:
        ax.invert_xaxis()
        ax.grid(alpha=0.2)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220, facecolor="white")
    plt.close(fig)


def upgraded_manuscript(text: str) -> str:
    text = text.replace("Date: 2026-07-15", "Date: 2026-07-19")
    text = text.replace(
        "Status: final draft — ready for internal review and LaTeX conversion",
        "Status: three-level numerical-evidence draft — ready for internal scientific review",
    )
    text = replace_once(
        text,
        "**Methods.** We used the k-Wave k-space pseudospectral solver with a 0.75-mm grid (PPW = 4), PML = 12 voxels, and CFL = 0.2. A nominal radius of curvature of 74.435 mm was compared against a corrected radius of 78.330 mm. Focus metrics included refined focal-position error, target-to-global peak-pressure ratio, and -6 dB axial/lateral widths.",
        "**Methods.** We used the k-Wave k-space pseudospectral solver to compare nominal and curvature-corrected bowl sources at 0.75-mm spacing. The corrected source was then evaluated at 0.75, 0.50, and 0.375 mm (4, 6, and 8 points per wavelength), with separate PML-thickness and CFL sensitivity runs. Focus metrics included refined focal-position error, target-to-global peak-pressure ratio, and -6 dB axial/lateral widths.",
    )
    text = replace_once(
        text,
        "**Results.** The corrected radius reduced refined focal error from 3.555% to 1.364% and increased target/global ratio from 0.9824 to 0.9910. Global peak pressure decreased by 5.09%; lateral -6 dB width changed by +3.92%. The corrected field and target waveform were finite, and the global peak remained 27 voxels from the nearest boundary.",
        "**Results.** The corrected radius reduced refined focal error from 3.555% to 1.364% and increased target/global ratio from 0.9824 to 0.9910 at 0.75 mm. Across 0.75, 0.50, and 0.375 mm, refined focal error decreased from 1.364% to 0.402% to 0.113%; adjacent-grid global-peak changes were 0.852% and 0.291%, and lateral-width changes were 0.643% and 1.235%. Increasing PML thickness from 12 to 16 voxels changed the peak by 0.0003%, whereas reducing CFL from 0.2 to 0.1 changed the peak by 0.0759% but shifted the refined focus by 1.111 mm.",
    )
    text = replace_once(
        text,
        "**Limitations.** These results are homogeneous free-field evidence only. Grid convergence at dx = 0.5 mm passed the preregistered 5% focus-error gate (observed 0.402%), and the complete target waveform was recorded with a low-memory point-sensor architecture; convergence is established at the engineering level only (dx = 0.375 mm grid convergence remains open; PML = 16 and CFL = 0.1 sensitivities have been characterized). Absolute focus-error values remain discretization-dependent: at dx = 0.75 mm the refined focus error moved from 1.364% at CFL = 0.2 to 0.116% at CFL = 0.1 (temporal refinement, indicating time-dispersion dominance), while the dx = 0.5 mm / CFL = 0.2 value was 0.402%; amplitude-type metrics (global peak, -6 dB widths) were stable under both refinements.  No transcranial pressure, thermal, or clinical claims are supported.",
        "**Limitations.** These results are homogeneous free-field evidence only. The three-grid comparison supports engineering-level numerical stability, not a formal asymptotic convergence order. The CFL sensitivity of focal position shows that absolute localization remains time-step dependent even though amplitude and width metrics were stable. No hydrophone validation, paper-grade heterogeneous-skull benchmark, thermal analysis, or clinical evidence is included.",
    )
    old_section = text[text.index("### 3.2 Cross-grid check at dx = 0.5 mm"):text.index("## 4. Discussion")]
    new_section = """### 3.2 Three-level grid convergence\n\nThe corrected source was evaluated at grid spacings of 0.75, 0.50, and 0.375 mm, corresponding to 4, 6, and 8 points per wavelength in water. Refined focal-position error decreased monotonically from 1.364% to 0.402% to 0.113%. For the 0.75-to-0.50-mm and 0.50-to-0.375-mm comparisons, global peak pressure changed by 0.852% and 0.291%, lateral -6 dB width changed by 0.643% and 1.235%, and refined focal displacement was 0.855 and 0.235 mm, respectively. All 12 registered Gate B checks passed. The observed adjacent-level focus-error ratios were 3.39 and 3.55; because the refinement factors differ, these ratios are reported descriptively and are not used to claim a formal order of convergence.\n\n### 3.3 PML and time-step sensitivity\n\nIncreasing PML thickness from 12 to 16 voxels produced a 0.0003% global-peak change, no measurable width change, and no refined focal displacement. Reducing CFL from 0.2 to 0.1 produced a 0.0759% peak change and unchanged -6 dB widths, but the refined focus moved by 1.111 mm and its error changed by 1.247 percentage points. Thus, amplitude and focal-width metrics were stable in these single-factor tests, while focal localization retained detectable time-step sensitivity.\n\n"""
    text = text.replace(old_section, new_section)
    text = replace_once(
        text,
        "Several caveats remain. First, the grid spacing of 0.75 mm gives only 4 PPW in water, which is below the 6–8 PPW typically recommended for paper-grade tFUS simulations (Montanaro et al., 2021; Chen et al., 2023). The dx = 0.5 mm cross-grid check (6 PPW) passed the preregistered focus-error gate (observed 0.402%) with the complete target waveform recorded via a low-memory point-sensor strategy, providing engineering-level cross-grid reassurance; dx = 0.375 mm grid convergence remains open (PML = 16 and CFL = 0.1 sensitivities characterized).",
        "Several caveats remain. First, the three-grid series spans 4, 6, and 8 PPW and passed all registered engineering checks, with monotonically decreasing focal error and sub-1% adjacent-grid peak changes. This strengthens numerical confidence beyond a two-grid comparison. It does not establish formal asymptotic convergence, and the CFL test shows that focal localization remains sensitive to time-step choice even when pressure amplitude and focal widths are stable.",
    )
    text = replace_once(
        text,
        "First-order curvature correction improves the free-field focal calibration of a 60-mm aperture, 500 kHz geometric bowl source. The corrected source reduces refined focal error from 3.6% to 1.4% and increases the target-to-global peak-pressure ratio from 0.982 to 0.991 in homogeneous water at dx = 0.75 mm. These results establish a reproducible source model for future patient-specific tFUS simulations but do not support transcranial efficacy, clinical safety, or paper-grade numerical convergence claims.",
        "First-order curvature correction improves the free-field focal calibration of a 60-mm aperture, 500 kHz geometric bowl source. Three grid levels from 4 to 8 PPW showed monotonic focal-error reduction and stable peak-pressure and lateral-width metrics, while the CFL sensitivity identified a remaining localization dependence. These results establish an engineering-validated source-model foundation for subsequent skull-crossing studies but do not support transcranial efficacy, thermal safety, or clinical claims.",
    )
    return text


def upgraded_mapping(text: str) -> str:
    text = text.replace(
        "| Grid convergence vs PPW | — | Not generated | dx0.5 failed focus-error gate; dx0.375 not run. |",
        "| Grid convergence vs PPW | Supplementary Figure 7; Supplementary Table 4 | Generated | Three levels: 4, 6, and 8 PPW; all 12 engineering checks passed. |",
    )
    text = text.replace(
        "| Convergence / accuracy plots | — | Not generated | dx0.5 convergence not established. |",
        "| Convergence / accuracy plots | Supplementary Figure 7 | Generated | Three-level engineering convergence observation; no formal order claimed. |",
    )
    text = text.replace(
        "- **Generated figures**: Figure 1, Supplementary Figures 1–3, Tables 1–2.\n- **Missing for full paper**: grid-convergence figure, skull-crossing pressure maps, hydrophone comparison, thermal dose maps.\n- **Path forward**: Option A (dx0.5 point waveform) would enable the grid-convergence figure. CT pressure remains blocked by geometry, not just compute.",
        "- **Generated figures**: Figure 1, Supplementary Figures 1–7, Tables 1–2, and Supplementary Tables 3–4.\n- **Numerical evidence added**: three-level 4/6/8-PPW comparison plus PML16 and CFL0.1 sensitivity observations.\n- **Missing for a complete transcranial paper**: heterogeneous skull benchmark, hydrophone comparison, and thermal-dose evidence. The current A4 trajectory screen remains exploratory and does not unlock those claims.",
    )
    if "dx0.375 not run" in text or "dx0.5 convergence not established" in text:
        raise ValueError("Stale convergence statement remains in mapping")
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SOURCE, out)

    convergence = json.loads(CONVERGENCE.read_text(encoding="utf-8"))
    sensitivity = json.loads(SENSITIVITY.read_text(encoding="utf-8"))
    equivalence = json.loads(EQUIVALENCE.read_text(encoding="utf-8"))
    if convergence["status"] != "three_level_convergence_pass":
        raise ValueError("Three-level convergence gate is not passed")
    if not equivalence["numerically_equivalent"]:
        raise ValueError("A4b no-run decision is not supported")

    rows = convergence_rows(convergence)
    write_table(rows, out / "tables" / "supplementary_table_4_three_level_convergence.csv")
    write_figure(rows, out / "supplementary_figures" / "supplementary_figure_7_three_level_convergence.png")

    manuscript_path = out / "manuscript" / "manuscript_final.md"
    manuscript_path.write_text(upgraded_manuscript(manuscript_path.read_text(encoding="utf-8")), encoding="utf-8")
    mapping_path = out / "submission_documents" / "reference_figure_mapping.md"
    mapping_path.write_text(upgraded_mapping(mapping_path.read_text(encoding="utf-8")), encoding="utf-8")

    (out / "manuscript" / "manuscript_final.tex").unlink(missing_ok=True)
    (out / "manuscript" / "LATEX_REGENERATION_REQUIRED.md").write_text(
        "# LaTeX regeneration required\n\nThe Markdown manuscript is canonical. The 2026-07-15 LaTeX file was removed because it does not contain the three-level evidence. Regenerate LaTeX only after scientific review of the revised Markdown.\n",
        encoding="utf-8",
    )
    (out / "README.md").write_text(
        "# Acoustic Paper Evidence Package (Three-Level Upgrade, 2026-07-19)\n\n"
        "This package preserves the 2026-07-15 submission package and adds the completed 4/6/8-PPW convergence evidence, PML/CFL sensitivity interpretation, Supplementary Figure 7, and Supplementary Table 4.\n\n"
        "The canonical manuscript is `manuscript/manuscript_final.md`. Claims remain limited to engineering free-field validation. A4b pressure reruns were not performed because a fresh fingerprint audit proved them numerically identical to retained A4 runs.\n",
        encoding="utf-8",
    )

    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "three_level_paper_evidence_package",
            "source_package": str(SOURCE.relative_to(ROOT)),
            "evidence": {
                "three_level_convergence": str(CONVERGENCE.relative_to(ROOT)),
                "pml_cfl_sensitivity": str(SENSITIVITY.relative_to(ROOT)),
                "a4b_equivalence_audit": str(EQUIVALENCE.relative_to(ROOT)),
            },
            "claim_level": "engineering free-field validation",
            "ct_pressure_authorized": False,
            "latex_status": "regeneration_required_after_scientific_review",
        }
    )
    manifest["manuscript"] = ["manuscript/manuscript_final.md"]
    manifest["tables"].append("tables/supplementary_table_4_three_level_convergence.csv")
    manifest["supplementary_figures"].append("supplementary_figures/supplementary_figure_7_three_level_convergence.png")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    summary = {
        "status": "ok",
        "output_dir": str(out.relative_to(ROOT)),
        "grid_levels": len(rows),
        "sensitivity_verdicts": {item["key"]: item["judgment"]["verdict"] for item in sensitivity["variants"]},
        "a4b_pressure_run": "not_run_evidence_redundant",
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
