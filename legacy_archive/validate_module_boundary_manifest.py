from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = PROJECT_ROOT / "outputs/module_boundary_manifest/module_boundary_manifest.json"
OUT_JSON = PROJECT_ROOT / "outputs/module_boundary_manifest/module_boundary_manifest_validation.json"
OUT_MD = PROJECT_ROOT / "outputs/module_boundary_manifest/module_boundary_manifest_validation.md"


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: str) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": evidence})


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
    scripts = sorted(path.name for path in PROJECT_ROOT.glob("*.py"))
    entries = manifest.get("script_entries", [])
    entry_names = sorted(item.get("name") for item in entries)
    checks: list[dict[str, Any]] = []
    add(checks, "manifest.version", manifest.get("manifest_version") == "1.0.0", str(manifest.get("manifest_version")))
    add(checks, "manifest.module", manifest.get("module") == "module_boundary_manifest", str(manifest.get("module")))
    add(checks, "manifest.no_physical_move", manifest.get("physical_reorganization_allowed") is False, str(manifest.get("physical_reorganization_allowed")))
    add(checks, "scripts.all_root_classified", scripts == entry_names, f"root={len(scripts)}; entries={len(entry_names)}")
    unclassified = manifest.get("unclassified_scripts", [])
    add(checks, "scripts.no_unclassified", len(unclassified) == 0, str(unclassified))
    categories = {item.get("name"): item.get("category") for item in entries}
    bad_generators = {name: cat for name, cat in categories.items() if name.startswith("generate_") and cat not in {"governance_policy", "evidence_report_generator"}}
    add(checks, "generators.boundary", not bad_generators, str(bad_generators))
    bad_validators = {name: cat for name, cat in categories.items() if name.startswith("validate_") and cat != "validator"}
    add(checks, "validators.boundary", not bad_validators, str(bad_validators))
    bad_sim = {name: cat for name, cat in categories.items() if (name.startswith("simulate_") or name.startswith("run_") or name == "kwave_run_healthcheck.py") and cat != "simulation_runner"}
    add(checks, "simulation.boundary", not bad_sim, str(bad_sim))
    moved = [item.get("path") for item in entries if item.get("move_performed")]
    add(checks, "entries.no_moves", not moved, str(moved))
    failed = [item for item in checks if item["status"] != "pass"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module_boundary_manifest_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# Module Boundary Manifest Validation\n\n"
        f"- valid: `{result['module_boundary_manifest_valid']}`\n"
        f"- failed check count: `{result['failed_check_count']}`\n",
        encoding="utf-8",
    )
    print(json.dumps({"module_boundary_manifest_valid": result["module_boundary_manifest_valid"], "failed_check_count": len(failed)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
