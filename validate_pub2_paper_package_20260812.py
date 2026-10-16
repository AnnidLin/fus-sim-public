"""Validate the PUB.2 submission-preparation draft and figure provenance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIGURE_DIR = ROOT / "paper" / "figures" / "pub2_20260812"
DRAFT = ROOT / "paper" / "PUB2_MANUSCRIPT_DRAFT_V0_1_20260812.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    manifest_path = FIGURE_DIR / "figure_manifest.json"
    checks: dict[str, bool] = {
        "draft_exists": DRAFT.is_file(),
        "manifest_exists": manifest_path.is_file(),
    }
    if not all(checks.values()):
        print(json.dumps({"status": "failed", "checks": checks}))
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for relative, expected in manifest.get("sources", {}).items():
        path = ROOT / relative
        checks[f"source:{relative}"] = path.is_file() and sha256(path) == expected
    for relative, expected in manifest.get("outputs", {}).items():
        path = ROOT / relative
        checks[f"output:{relative}"] = path.is_file() and path.stat().st_size > 0 and sha256(path) == expected
    draft = DRAFT.read_text(encoding="utf-8")
    checks.update({
        "draft_has_abstract": "## Abstract" in draft,
        "draft_has_methods": "## Methods" in draft,
        "draft_has_results": "## Results" in draft,
        "draft_has_discussion": "## Discussion" in draft,
        "draft_has_claim_boundary": "do not establish numerical convergence" in draft,
        "draft_has_author_queries": "## Pre-submission author queries" in draft,
        "pressure_definition_recorded": manifest.get("pressure_definition") == "max(abs(p_max), abs(p_min)) / 1e6 MPa at each voxel",
    })
    status = "passed" if all(checks.values()) else "failed"
    print(json.dumps({"status": status, "check_count": len(checks), "failed": [key for key, value in checks.items() if not value]}))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
