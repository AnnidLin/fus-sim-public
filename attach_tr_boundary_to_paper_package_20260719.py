from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "outputs" / "acoustic_paper_submission_package_three_level_20260719"
AUDIT = ROOT / "outputs" / "tr_generalization_audit_20260719"
HELDOUT = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719"


def main() -> None:
    destination = PACKAGE / "transcranial_boundary_evidence"
    destination.mkdir(parents=True, exist_ok=True)
    files = {
        AUDIT / "tr_generalization_audit.png": destination / "tr_generalization_audit.png",
        AUDIT / "trajectory_metrics.csv": destination / "trajectory_metrics.csv",
        AUDIT / "generalization_audit.json": destination / "generalization_audit.json",
        AUDIT / "generalization_audit.md": destination / "generalization_audit.md",
        HELDOUT / "heldout_tr_report.json": destination / "heldout_tr_report.json",
        HELDOUT / "heldout_tr_report.md": destination / "heldout_tr_report.md",
    }
    for source, target in files.items():
        shutil.copy2(source, target)
    (destination / "README.md").write_text(
        "# Transcranial Boundary Evidence\n\n"
        "This addendum is deliberately separate from the homogeneous free-field manuscript claim. A preregistered held-out Case 079 TR test passed all absolute gates on 1/3 trajectories; the original A4 verdict remains hold. Across development and held-out sets, 3/6 trajectories passed the same descriptive absolute criteria.\n\n"
        "The repeated failure mode was a strong target-window focus accompanied by a larger remote skull peak approximately 57 mm from target. These data block mapping and thermal expansion and motivate a skull-hotspot suppression objective. They do not constitute a paper-grade heterogeneous-skull benchmark or a clinical claim.\n",
        encoding="utf-8",
    )

    manifest_path = PACKAGE / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["transcranial_boundary_evidence"] = [str(path.relative_to(PACKAGE)).replace("\\", "/") for path in sorted(destination.iterdir())]
    manifest["evidence"].update(
        {
            "a5_heldout_tr": "outputs/a5_heldout_tr_confirmation_20260719/heldout_tr_report.json",
            "tr_generalization_audit": "outputs/tr_generalization_audit_20260719/generalization_audit.json",
        }
    )
    manifest["transcranial_boundary_status"] = "confirmatory_hold_1_of_3"
    manifest["mapping_uncertainty_unlocked"] = False
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    readme_path = PACKAGE / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    note = "\n## Transcranial boundary addendum\n\n`transcranial_boundary_evidence/` records a preregistered held-out TR hold (1/3 pass) and the descriptive 3/6 development-plus-held-out audit. It is included to expose the current generalization limit, not to expand the manuscript claim.\n"
    if "## Transcranial boundary addendum" not in readme:
        readme_path.write_text(readme.rstrip() + "\n" + note, encoding="utf-8")
    print(json.dumps({"status": "attached", "files": len(files) + 1}))


if __name__ == "__main__":
    main()
