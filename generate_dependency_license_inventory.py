"""Inventory pinned dependency licence metadata and archive exclusions."""
from __future__ import annotations

import argparse
import csv
import json
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path


def licence_summary(metadata) -> str | None:
    expression = metadata.get("License-Expression")
    if expression:
        return expression.strip()
    classifiers = [value for value in metadata.get_all("Classifier", []) if value.startswith("License ::")]
    if classifiers:
        return "; ".join(value.split(" :: ")[-1] for value in classifiers)
    value = metadata.get("License")
    if not value:
        return None
    first = next((line.strip() for line in value.splitlines() if line.strip()), "")
    return first[:160] or None


def build(root: Path) -> dict:
    requirements = []
    for raw in (root / "requirements-kwave312.txt").read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip():
            continue
        name, expected = raw.strip().split("==", 1)
        try:
            dist = distribution(name)
            metadata = dist.metadata
            installed = dist.version
            requirements.append({
                "name": name,
                "expected_version": expected,
                "installed_version": installed,
                "version_matches": installed == expected,
                "licence_summary": licence_summary(metadata),
                "project_url": metadata.get("Home-page") or metadata.get("Project-URL"),
                "installed": True,
            })
        except PackageNotFoundError:
            requirements.append({"name": name, "expected_version": expected, "installed_version": None, "version_matches": False, "licence_summary": None, "project_url": None, "installed": False})
    spec = json.loads((root / "paper/submission_archive_spec_20260829.json").read_text(encoding="utf-8-sig"))
    prohibited = set(spec["prohibited_inclusions"])
    excluded = {item["path"] for item in spec["excluded"]}
    root_licences = [path.name for path in root.iterdir() if path.is_file() and path.name.upper().startswith(("LICENSE", "COPYING"))]
    checks = {
        "29_exactly_pinned_dependencies": len(requirements) == 29,
        "all_pinned_dependencies_installed": all(item["installed"] for item in requirements),
        "all_installed_versions_match": all(item["version_matches"] for item in requirements),
        "all_dependencies_have_licence_metadata": all(bool(item["licence_summary"]) for item in requirements),
        "root_project_licence_absent": not root_licences,
        "raw_ct_prefix_prohibited": "data/raw_ct" in prohibited,
        "third_party_source_prefix_prohibited": "data/source_code_refs" in prohibited,
        "ucl_intake_prefix_prohibited": "outputs/ucl_270khz_freefield_intake_20260812" in prohibited,
        "raw_ct_explicitly_excluded": "data/raw_ct/079.nii" in excluded,
        "reconstructable_anatomy_explicitly_excluded": "CT-derived voxel property volumes and masks" in excluded,
        "large_pressure_fields_explicitly_excluded": "pressure_max_mpa.npz and full solver fields" in excluded,
        "private_records_explicitly_excluded": "credentials, signed agreements and private ethics records" in excluded,
    }
    passing_except_expected_project_gap = all(value for key, value in checks.items() if key != "root_project_licence_absent") and checks["root_project_licence_absent"]
    return {
        "schema_version": "1.0",
        "status": "conditional_project_licence_missing" if passing_except_expected_project_gap else "failed",
        "project_licence": None,
        "project_licence_author_decision_required": True,
        "dependencies": requirements,
        "dependency_count": len(requirements),
        "archive_prohibited_prefixes": spec["prohibited_inclusions"],
        "archive_exclusions": spec["excluded"],
        "checks": checks,
        "claim_boundary": "Installed-package metadata is an inventory aid, not legal advice; the copyright holder must choose the project licence and approve the final notices before release.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.root.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "dependency_licence_inventory.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (args.output_dir / "dependency_licence_inventory.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(report["dependencies"][0]))
        writer.writeheader()
        writer.writerows(report["dependencies"])
    lines = ["# Dependency licence and exclusion inventory", "", f"- status: `{report['status']}`", f"- pinned dependencies: `{report['dependency_count']}`", "- project licence: unresolved author decision", "", "| Package | Version | Licence metadata |", "|---|---:|---|"]
    lines += [f"| {item['name']} | {item['installed_version']} | {item['licence_summary']} |" for item in report["dependencies"]]
    lines += ["", "## Archive exclusions", ""] + [f"- `{item['path']}` — {item['reason']}" for item in report["archive_exclusions"]] + ["", report["claim_boundary"], ""]
    (args.output_dir / "dependency_licence_inventory.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": report["status"], "failed": [key for key, value in report["checks"].items() if not value]}))
    return 0 if report["status"].startswith("conditional") else 1


if __name__ == "__main__":
    raise SystemExit(main())
