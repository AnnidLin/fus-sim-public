from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "outputs" / "acoustic_paper_submission_package_three_level_20260719"
SOURCE = ROOT / "outputs" / "a5_hamming_hotspot_report_20260720"


def main() -> None:
    destination = PACKAGE / "transcranial_boundary_evidence"
    names = ["hamming_hotspot_report.json", "hamming_hotspot_report.md", "hamming_hotspot_comparison.png"]
    for name in names:
        shutil.copy2(SOURCE / name, destination / name)
    manifest_path = PACKAGE / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["hotspot_suppression_pilot"] = {
        "status": "negative_pilot_hamming_worsened_hotspot_dominance",
        "report": "transcranial_boundary_evidence/hamming_hotspot_report.json",
        "followup_fixed_window_scan_authorized": False,
    }
    manifest["transcranial_boundary_evidence"] = [str(path.relative_to(PACKAGE)).replace("\\", "/") for path in sorted(destination.iterdir())]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    readme_path = destination / "README.md"
    text = readme_path.read_text(encoding="utf-8")
    note = (
        "\n## Hamming pilot\n\nA single post-study Hamming-weighted refocus worsened target/global "
        "(0.915 to 0.554) and skull/focus (1.076 to 1.774). Fixed aperture-window scanning is rejected; "
        "future work requires an explicit skull-hotspot-constrained objective.\n"
    )
    if "## Hamming pilot" not in text:
        readme_path.write_text(text.rstrip() + "\n" + note, encoding="utf-8")
    print(json.dumps({"status": "attached", "files": names}))


if __name__ == "__main__":
    main()
