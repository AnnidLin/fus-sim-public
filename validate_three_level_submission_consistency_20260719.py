from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "outputs" / "acoustic_paper_submission_package_three_level_20260719"


def main() -> None:
    texts = {str(path.relative_to(PACKAGE)): path.read_text(encoding="utf-8") for path in PACKAGE.rglob("*.md")}
    joined = "\n".join(texts.values())
    forbidden = [
        "dx0.5 convergence check failed",
        "dx0.375 not run",
        "dx0.5 convergence not established",
        "Grid convergence at dx = 0.5 mm remains incomplete",
        "dx = 0.375 mm grid convergence remains open",
        "refined focus error was 5.472%",
    ]
    checks = {
        "no_stale_claims": not any(item in joined for item in forbidden),
        "all_docs_have_new_evidence": all(
            token in joined
            for token in ("4/6/8-PPW", "1.364% to 0.402% to 0.113%", "Supplementary Figure 7")
        ),
        "reviewer_response_updated": "How was numerical stability assessed" in joined,
        "point_design_marked_historical": "Historical Design, Executed" in texts["point_waveform_design\\point_waveform_design.md"],
    }
    failed = [name for name, value in checks.items() if not value]
    print(json.dumps({"status": "pass" if not failed else "fail", "checks": checks, "failed": failed}, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
