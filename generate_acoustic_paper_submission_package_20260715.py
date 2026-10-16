from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "outputs" / "acoustic_paper_submission_package_20260715"

MANUSCRIPT_DIR = PROJECT_ROOT / "outputs" / "manuscript_draft_20260715"
SKELETON_DIR = PROJECT_ROOT / "outputs" / "paper_skeleton_20260715"
SUPP_FIG_DIR = PROJECT_ROOT / "outputs" / "d60_supplementary_figures_20260715"
SUPP_ANALYSIS_DIR = PROJECT_ROOT / "outputs" / "d60_supplementary_analysis_20260715"
POINT_WAVE_DESIGN = PROJECT_ROOT / "outputs" / "point_waveform_design_20260715" / "point_waveform_design.md"


def copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    out = args.output_dir
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    # Manuscript
    manuscript_dir = out / "manuscript"
    copy(MANUSCRIPT_DIR / "manuscript_final.md", manuscript_dir / "manuscript_final.md")
    copy(MANUSCRIPT_DIR / "latex_build_package" / "manuscript_final.tex", manuscript_dir / "manuscript_final.tex")

    # Tables
    tables_dir = out / "tables"
    copy(SKELETON_DIR / "tables" / "table_1_parameters.csv", tables_dir / "table_1_parameters.csv")
    copy(SKELETON_DIR / "tables" / "table_2_results.csv", tables_dir / "table_2_results.csv")
    copy(SKELETON_DIR / "figure_1_package" / "source_correction_metrics.csv", tables_dir / "source_correction_metrics.csv")
    copy(SUPP_ANALYSIS_DIR / "supplementary_table_3_focal_volume.csv", tables_dir / "supplementary_table_3_focal_volume.csv")

    # Figures
    figures_dir = out / "figures"
    copy(SKELETON_DIR / "figure_1_package" / "figure_1_source_correction.png", figures_dir / "figure_1_source_correction.png")

    # Supplementary figures
    supp_dir = out / "supplementary_figures"
    for fig in SUPP_FIG_DIR.glob("*.png"):
        copy(fig, supp_dir / fig.name)
    for fig in SUPP_ANALYSIS_DIR.glob("supplementary_figure_*.png"):
        copy(fig, supp_dir / fig.name)

    # Submission documents
    docs_dir = out / "submission_documents"
    for name in [
        "cover_letter.md",
        "highlights.md",
        "data_availability_statement.md",
        "author_contributions.md",
        "conflicts_of_interest.md",
        "author_checklist.md",
        "one_page_summary.md",
        "title_and_metadata.md",
        "reference_figure_mapping.md",
        "response_to_reviewers_template.md",
    ]:
        copy(MANUSCRIPT_DIR / name, docs_dir / name)

    # Point waveform design for reviewers
    design_dir = out / "point_waveform_design"
    copy(POINT_WAVE_DESIGN, design_dir / "point_waveform_design.md")

    # Top-level README
    readme = f"""# Acoustic Paper Submission Package (2026-07-15)

Self-contained package for the D60 free-field source-calibration manuscript.

## Contents

- `manuscript/` — final Markdown and LaTeX manuscripts.
- `tables/` — parameter, results, and focal-volume CSVs.
- `figures/` — main Figure 1.
- `supplementary_figures/` — Supplementary Figures 1–6.
- `submission_documents/` — cover letter, highlights, data availability, author contributions, conflicts, checklist, one-page summary, title options, reference mapping, reviewer response template.
- `point_waveform_design/` — low-memory dx0.5 waveform recording design.

## How to build the PDF

See `manuscript/manuscript_final.tex` and the instructions embedded in `manuscript/README.md` (created below).

## Scope statement

This package supports only the engineering free-field calibration claim. It does not support transcranial efficacy, clinical safety, thermal safety, or paper-grade numerical convergence.
"""
    (out / "README.md").write_text(readme, encoding="utf-8")

    (out / "manuscript" / "README.md").write_text(
        "# Manuscript Build Notes\n\n"
        "- `manuscript_final.md` is the canonical Markdown draft.\n"
        "- `manuscript_final.tex` is the LaTeX version.\n"
        "- To compile: copy the figures from `../figures/` and `../supplementary_figures/` into this directory and run `pdflatex manuscript_final.tex` twice.\n"
        "- Figures are not automatically embedded in the .tex; add `\\includegraphics` blocks as needed before submission.\n",
        encoding="utf-8",
    )

    manifest = {
        "output_dir": str(out.relative_to(PROJECT_ROOT)),
        "manuscript": ["manuscript/manuscript_final.md", "manuscript/manuscript_final.tex"],
        "tables": [f"tables/{p.name}" for p in tables_dir.glob("*.csv")],
        "figures": [f"figures/{p.name}" for p in figures_dir.glob("*.png")],
        "supplementary_figures": [f"supplementary_figures/{p.name}" for p in supp_dir.glob("*.png")],
        "submission_documents": [f"submission_documents/{p.name}" for p in docs_dir.glob("*.md")],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps({"status": "ok", "output_dir": str(out.relative_to(PROJECT_ROOT))}))


if __name__ == "__main__":
    main()
