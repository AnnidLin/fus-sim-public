from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "outputs" / "acoustic_paper_submission_package_three_level_20260719"


def replace_required(text: str, old: str, new: str, name: str) -> str:
    if old not in text:
        raise ValueError(f"Expected stale statement missing in {name}: {old[:70]}")
    return text.replace(old, new)


def update(name: str, changes: list[tuple[str, str]]) -> None:
    path = PACKAGE / "submission_documents" / name
    text = path.read_text(encoding="utf-8")
    for old, new in changes:
        text = replace_required(text, old, new, name)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    update("cover_letter.md", [(
        "Grid convergence at dx = 0.5 mm remains incomplete (failed the preregistered 5% focus-error gate) and is explicitly discussed as a limitation, together with the absence of hydrophone validation and skull-crossing data.",
        "The completed 4/6/8-PPW series passed all 12 registered engineering checks; we report this as engineering-level numerical evidence rather than a formal asymptotic convergence claim. Remaining limitations include CFL-dependent focal localization, no hydrophone validation, and no paper-grade heterogeneous-skull benchmark.",
    )])
    update("one_page_summary.md", [
        ("- Grid spacing is 4 PPW; dx0.5 convergence check failed the 5% focus-error gate.", "- A completed 4/6/8-PPW series passed all 12 engineering checks: refined focal error 1.364% -> 0.402% -> 0.113%, with adjacent-grid peak changes below 1%."),
        ("If grid convergence is required, implement the low-memory point-waveform design (`outputs/point_waveform_design_20260715/`) and re-run dx0.5. CT pressure remains blocked until a skull-crossing trajectory exists.", "The free-field numerical ladder is complete at the engineering-evidence level. The next manuscript-critical gap is a preregistered heterogeneous-skull validation design; the existing A4 quick hold remains unchanged, and duplicate label-only pressure reruns are prohibited."),
    ])
    update("response_to_reviewers_template.md", [
        ("**Likely comment**: The grid spacing is only 4 PPW and the dx0.5 convergence check failed. Why should the reader trust the dx0.75 results?", "**Likely comment**: How was numerical stability assessed across spatial and temporal discretization choices?"),
        ("> We agree that 4 PPW is below the 6–8 PPW often recommended for paper-grade tFUS simulations. The manuscript now explicitly states this as a limitation. The dx0.75 results are presented as an engineering calibration step, not as a converged solution. We attempted a dx0.5 cross-grid check; the refined focus error was 5.472%, exceeding our preregistered 5% gate, and the full-domain target waveform could not be recorded because it would require ~110 GiB. A low-memory point-sensor recording design is provided in `outputs/point_waveform_design_20260715/` and can be implemented if the editor/reviewers consider it essential.", "> We evaluated the corrected source at 0.75, 0.50, and 0.375 mm (4, 6, and 8 PPW). Refined focal error decreased from 1.364% to 0.402% to 0.113%; adjacent-grid global-peak changes were 0.852% and 0.291%, and all 12 registered engineering checks passed. PML16 was stable, while CFL0.1 shifted the refined focus by 1.111 mm despite stable amplitude and width metrics. We therefore claim engineering-level numerical stability, not a formal asymptotic convergence order."),
        ("- Update numbers if the dx0.5 point-waveform run is completed (Option A).", "- Confirm that all quoted values match Supplementary Table 4 and the PML/CFL sensitivity report."),
        ("Any clinical interpretation would require grid convergence, skull-crossing validation, thermal modelling, and regulatory/ethical review—none of which are presented here.", "Any clinical interpretation would require heterogeneous-skull validation, thermal modelling, experimental validation, and regulatory/ethical review—none of which are presented here."),
    ])
    update("title_and_metadata.md", [(
        "Grid convergence at dx = 0.5 mm remains incomplete and is explicitly discussed as a limitation.",
        "A three-level 4/6/8-PPW comparison supports engineering-level numerical stability; formal asymptotic convergence and heterogeneous-skull validation remain outside the claim boundary.",
    )])
    update("author_checklist.md", [
        ("- [ ] The dx = 0.5 mm numbers come from `outputs/freefield_aperture_calibration/d60_grid_convergence_corrected_20260716/d60_grid_convergence_report.json`.", "- [ ] The 0.75/0.50/0.375-mm numbers match `outputs/freefield_aperture_calibration/d60_grid_convergence_three_level_20260719/report.json`."),
        ("- [ ] Any convergence wording matches the corrected Gate B report status: `gate_b_dx075_dx05_pass` permits engineering-level convergence language only; paper-grade numerical convergence remains unclaimed in all cases.", "- [ ] Convergence wording matches `three_level_convergence_pass`: engineering-level three-grid evidence only; no formal asymptotic order or heterogeneous-skull convergence claim."),
        ("- [x] Fine-grid decision gate resolved 2026-07-16: Option A chosen and executed (dx0.5 corrected point-waveform rerun); outcome is recorded in the corrected Gate B report — verify it before circulation.", "- [x] Fine-grid ladder completed 2026-07-19 through dx0.375; all 12 registered engineering checks passed and the target waveform chain is finite."),
    ])
    update("data_availability_statement.md", [(
        "`outputs/freefield_aperture_calibration/d60_grid_convergence_20260713/d60_grid_convergence_report.json`",
        "`outputs/freefield_aperture_calibration/d60_grid_convergence_three_level_20260719/report.json`",
    )])

    design = PACKAGE / "point_waveform_design" / "point_waveform_design.md"
    text = design.read_text(encoding="utf-8")
    text = replace_required(text, "# Target-Only Point-Waveform Recording Design", "# Target-Only Point-Waveform Recording Design (Historical Design, Executed)", design.name)
    text = replace_required(text, "6. Execute the D60 dx0.5 field run if not already present, then the waveform-only run.", "6. Historical instruction: execute the D60 dx0.5 field run, then the waveform-only run. This chain completed successfully on 2026-07-17.", design.name)
    text = replace_required(text, "- A finite target waveform for the dx0.5 grid, enabling the Gate B cross-grid convergence check to proceed.", "- Achieved: a finite 1500-sample target waveform for the dx0.5 grid enabled Gate B and the subsequent three-level convergence check.", design.name)
    design.write_text(text, encoding="utf-8")
    print("submission_docs_upgraded=true")


if __name__ == "__main__":
    main()
