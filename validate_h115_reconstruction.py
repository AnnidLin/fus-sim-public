"""Verify that a fresh H115 non-solver reconstruction matches accepted analyses."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PAIRS = (
    ("effective_dx0p5.json", "effective_dx0p5_coordinate_audit.json"),
    ("effective_dx0p3.json", "effective_dx0p3_coordinate_audit.json"),
    ("source_registration_sensitivity.json", "source_registration_sensitivity.json"),
)


def canonical(value: Any) -> Any:
    """Remove only explicitly volatile provenance timestamps."""
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items() if key != "generated_at_utc"}
    if isinstance(value, list):
        return [canonical(item) for item in value]
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pdf_without_creation_date(path: Path) -> bytes:
    """Normalize only the PDF creation timestamp emitted by Matplotlib."""
    return re.sub(rb"/CreationDate \(D:[^)]*\)", b"/CreationDate (normalized)", path.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recheck-dir", type=Path, required=True)
    parser.add_argument("--accepted-dir", type=Path, required=True)
    parser.add_argument("--recheck-grid-figure-dir", type=Path)
    parser.add_argument("--accepted-grid-figure-dir", type=Path)
    parser.add_argument("--recheck-source-figure-dir", type=Path)
    parser.add_argument("--accepted-source-figure-dir", type=Path)
    parser.add_argument("--recheck-tables-dir", type=Path)
    parser.add_argument("--accepted-tables-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    checks = []
    for recheck_name, accepted_name in PAIRS:
        recheck_path = args.recheck_dir / recheck_name
        accepted_path = args.accepted_dir / accepted_name
        recheck = json.loads(recheck_path.read_text(encoding="utf-8"))
        accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
        checks.append(
            {
                "recheck_file": recheck_path.as_posix(),
                "accepted_file": accepted_path.as_posix(),
                "exact_after_dropping_generated_at_utc": canonical(recheck) == canonical(accepted),
                "recheck_sha256": sha256(recheck_path),
                "accepted_sha256": sha256(accepted_path),
            }
        )

    derived_checks = []
    derived_dirs = (
        args.recheck_grid_figure_dir,
        args.accepted_grid_figure_dir,
        args.recheck_source_figure_dir,
        args.accepted_source_figure_dir,
        args.recheck_tables_dir,
        args.accepted_tables_dir,
    )
    if any(derived_dirs) and not all(derived_dirs):
        parser.error("all six derived-artifact directory arguments must be supplied together")
    if all(derived_dirs):
        for label, recheck_dir, accepted_dir, stem in (
            ("grid_png", args.recheck_grid_figure_dir, args.accepted_grid_figure_dir, "figure_ucl_h115_grid_sensitivity"),
            ("source_png", args.recheck_source_figure_dir, args.accepted_source_figure_dir, "figure_ucl_h115_source_registration"),
        ):
            recheck_png, accepted_png = recheck_dir / f"{stem}.png", accepted_dir / f"{stem}.png"
            recheck_pdf, accepted_pdf = recheck_dir / f"{stem}.pdf", accepted_dir / f"{stem}.pdf"
            derived_checks.extend(
                [
                    {"artifact": label, "rule": "exact_bytes", "passed": recheck_png.read_bytes() == accepted_png.read_bytes()},
                    {
                        "artifact": label.replace("png", "pdf"),
                        "rule": "exact_bytes_after_dropping_creation_date_only",
                        "passed": pdf_without_creation_date(recheck_pdf) == pdf_without_creation_date(accepted_pdf),
                    },
                ]
            )
        for name in ("h115_validation_endpoints", "h115_methods_parameters"):
            for suffix in ("json", "csv", "md"):
                recheck_path = args.recheck_tables_dir / f"{name}.{suffix}"
                accepted_path = args.accepted_tables_dir / f"{name}.{suffix}"
                if suffix == "json":
                    matched = canonical(json.loads(recheck_path.read_text(encoding="utf-8"))) == canonical(
                        json.loads(accepted_path.read_text(encoding="utf-8"))
                    )
                    rule = "exact_json_after_dropping_generated_at_utc_only"
                else:
                    matched = recheck_path.read_bytes() == accepted_path.read_bytes()
                    rule = "exact_bytes"
                derived_checks.append({"artifact": f"{name}.{suffix}", "rule": rule, "passed": matched})

    passed = all(check["exact_after_dropping_generated_at_utc"] for check in checks) and all(
        check["passed"] for check in derived_checks
    )
    report = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if passed else "failed",
        "comparison_rule": "Exact JSON equality after recursively dropping generated_at_utc only.",
        "checks": checks,
        "derived_checks": derived_checks,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"status": report["status"], "analysis_checks": len(checks), "derived_checks": len(derived_checks), "output": str(args.output)}
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
