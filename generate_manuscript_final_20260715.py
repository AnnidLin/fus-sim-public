from __future__ import annotations

import argparse
from pathlib import Path

OUTPUT_DIR = Path("outputs/manuscript_draft_20260715")
DRAFT_PATH = OUTPUT_DIR / "manuscript_draft.md"
FINAL_PATH = OUTPUT_DIR / "manuscript_final.md"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    draft = DRAFT_PATH.read_text(encoding="utf-8")
    # Remove the draft title/status block and replace with final front matter
    lines = draft.splitlines()
    # Drop leading blank lines and the first title/status block
    start = 0
    for i, line in enumerate(lines):
        if line.startswith("## Abstract"):
            start = i
            break

    body = "\n".join(lines[start:])

    front = """# Manuscript Final Draft: Source-geometry calibration of a 60-mm aperture, 500 kHz focused ultrasound transducer in homogeneous free field

> Status: final draft — ready for internal review and LaTeX conversion
> Date: 2026-07-15
> Claim level: engineering validation; no clinical safety, paper-grade convergence, or transcranial efficacy claims
> Corresponding plan: `ACOUSTIC_CURRENT_PLAN_20260714.md`
> Fine-grid decision: Option A executed 2026-07-16 (dx0.5 corrected point-waveform rerun); Gate B outcome recorded in the corrected grid-convergence report

"""

    tail = """

## Data and code availability

All simulation output summaries, parameter tables, figures, reproducibility manifests, and evidence registry entries used in this study are stored in the project repository under `outputs/`. The simulation pipeline is implemented in Python using k-wave-python 0.6.1. Key scripts include `simulate_kwave_3d_focus.py`, `run_kwave_command.py`, and `generate_manuscript_draft_20260715.py`. Raw CT data are not included because the present work reports homogeneous free-field simulations only.
"""

    final = front + body + tail
    final_path = args.output_dir / "manuscript_final.md"
    final_path.write_text(final, encoding="utf-8")
    print(f"Wrote {final_path}")


if __name__ == "__main__":
    main()
