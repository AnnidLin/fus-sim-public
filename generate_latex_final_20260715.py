from __future__ import annotations

import argparse
from pathlib import Path

OUTPUT_DIR = Path("outputs/manuscript_draft_20260715")
DRAFT_TEX = OUTPUT_DIR / "manuscript_draft.tex"
FINAL_TEX = OUTPUT_DIR / "latex_build_package" / "manuscript_final.tex"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    package_dir = args.output_dir / "latex_build_package"
    package_dir.mkdir(parents=True, exist_ok=True)

    tex = DRAFT_TEX.read_text(encoding="utf-8")
    tex = tex.replace(
        "\\title{Source-geometry calibration of a 60-mm aperture, 500~kHz focused ultrasound transducer in homogeneous free field for patient-specific transcranial simulation}",
        "\\title{Source-geometry calibration of a 60-mm aperture, 500~kHz focused ultrasound transducer in homogeneous free field for patient-specific transcranial simulation}\\thanks{Final draft --- ready for internal review. Fine-grid decision: Option A executed 2026-07-16 (dx0.5 corrected point-waveform rerun); Gate B outcome recorded in the corrected grid-convergence report.}",
    )
    # Insert data availability paragraph before Declarations
    data_availability = (
        "\\section*{Data and code availability}\n\n"
        "All simulation output summaries, parameter tables, figures, reproducibility manifests, and evidence registry entries used in this study are stored in the project repository under \\texttt{outputs/}. "
        "The simulation pipeline is implemented in Python using k-wave-python 0.6.1. "
        "Key scripts include \\texttt{simulate\\_kwave\\_3d\\_focus.py}, \\texttt{run\\_kwave\\_command.py}, and \\texttt{generate\\_manuscript\\_draft\\_20260715.py}. "
        "Raw CT data are not included because the present work reports homogeneous free-field simulations only.\n\n"
    )
    tex = tex.replace("\\section*{Declarations}", data_availability + "\\section*{Declarations}")

    final_path = package_dir / "manuscript_final.tex"
    final_path.write_text(tex, encoding="utf-8")

    instructions = """# LaTeX Build Instructions

1. Ensure you have a LaTeX distribution with `pdflatex` (e.g., TeX Live, MiKTeX).
2. Place the required figures in this directory:
   - `figure_1_source_correction.png` (copy from `../paper_skeleton_20260715/figure_1_package/`)
   - `supplementary_figure_*.png` (copy from `../d60_supplementary_figures_20260715/` and `../d60_supplementary_analysis_20260715/`)
3. Update the `\\includegraphics` commands in `manuscript_final.tex` with the correct figure filenames (currently no figures are included).
4. Run:
   ```bash
   pdflatex manuscript_final.tex
   pdflatex manuscript_final.tex
   ```
5. The bibliography is inline in the `thebibliography` environment; no separate BibTeX run is required.
"""
    (package_dir / "README.md").write_text(instructions, encoding="utf-8")

    print(f"Wrote {final_path}")


if __name__ == "__main__":
    main()
