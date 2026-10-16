from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "outputs" / "acoustic_paper_submission_package_three_level_20260719"


def main() -> None:
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    addendum = PACKAGE / "transcranial_boundary_evidence"
    report = json.loads((addendum / "heldout_tr_report.json").read_text(encoding="utf-8"))
    audit = json.loads((addendum / "generalization_audit.json").read_text(encoding="utf-8"))
    checks = {
        "seven_files": len(list(addendum.iterdir())) == 7,
        "heldout_hold": report["status"] == "confirmatory_hold" and report["n_pass"] == 1,
        "pooled_half": audit["pooled_pass_rate"] == 0.5,
        "manifest_blocks_mapping": manifest["mapping_uncertainty_unlocked"] is False,
        "claim_boundary_preserved": manifest["claim_level"] == "engineering free-field validation",
        "readme_discloses_hold": "held-out TR hold (1/3 pass)" in (PACKAGE / "README.md").read_text(encoding="utf-8"),
    }
    failed = [name for name, passed in checks.items() if not passed]
    print(json.dumps({"status": "pass" if not failed else "fail", "checks": checks, "failed": failed}, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
