from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "outputs" / "acoustic_paper_submission_package_three_level_20260719"


def main() -> None:
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    report = json.loads((PACKAGE / "transcranial_boundary_evidence" / "hamming_hotspot_report.json").read_text(encoding="utf-8"))
    checks = {
        "negative_pilot": report["status"] == "negative_pilot_hamming_worsened_hotspot_dominance",
        "manifest_matches": manifest["hotspot_suppression_pilot"]["status"] == report["status"],
        "mapping_still_blocked": manifest["mapping_uncertainty_unlocked"] is False,
        "no_window_scan": manifest["hotspot_suppression_pilot"]["followup_fixed_window_scan_authorized"] is False,
        "readme_discloses": "Hamming pilot" in (PACKAGE / "transcranial_boundary_evidence" / "README.md").read_text(encoding="utf-8"),
    }
    failed = [name for name, passed in checks.items() if not passed]
    print(json.dumps({"status": "pass" if not failed else "fail", "checks": checks, "failed": failed}, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
