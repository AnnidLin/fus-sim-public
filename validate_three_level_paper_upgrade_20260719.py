from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "outputs" / "acoustic_paper_submission_package_three_level_20260719"


def main() -> None:
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    manuscript = (PACKAGE / "manuscript" / "manuscript_final.md").read_text(encoding="utf-8")
    mapping = (PACKAGE / "submission_documents" / "reference_figure_mapping.md").read_text(encoding="utf-8")
    with (PACKAGE / "tables" / "supplementary_table_4_three_level_convergence.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    checks = {
        "manifest_status": manifest["status"] == "three_level_paper_evidence_package",
        "three_grid_rows": len(rows) == 3,
        "grid_spacings": [round(float(row["grid_spacing_mm"]), 3) for row in rows] == [0.75, 0.5, 0.375],
        "manuscript_has_three_level_result": "1.364% to 0.402% to 0.113%" in manuscript,
        "manuscript_has_cfl_flag": "shifted the refined focus by 1.111 mm" in manuscript,
        "mapping_updated": "Supplementary Figure 7" in mapping,
        "stale_dx0375_removed": "dx0.375 not run" not in manuscript + mapping,
        "stale_open_removed": "dx = 0.375 mm grid convergence remains open" not in manuscript + mapping,
        "no_stale_latex": not (PACKAGE / "manuscript" / "manuscript_final.tex").exists(),
        "figure_exists": (PACKAGE / "supplementary_figures" / "supplementary_figure_7_three_level_convergence.png").stat().st_size > 50_000,
        "claim_boundary": manifest["ct_pressure_authorized"] is False and "engineering free-field validation" in manifest["claim_level"],
    }
    failed = [name for name, passed in checks.items() if not passed]
    print(json.dumps({"status": "pass" if not failed else "fail", "checks": checks, "failed": failed}, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
