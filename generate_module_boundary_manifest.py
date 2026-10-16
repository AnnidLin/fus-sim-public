from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "outputs/module_boundary_manifest"
BRIEF_DIR = PROJECT_ROOT / "outputs/evidence_briefs/module_boundary_manifest"

CATEGORIES = {
    "governance_policy": "Evidence/governance contracts, registries, ledgers, gates, claim policy, and maturity policy.",
    "evidence_report_generator": "Report or evidence-summary generators that read existing artifacts.",
    "validator": "Validation scripts for schema, contracts, run ledger, cases, or model build outputs.",
    "model_build": "Scripts that build or import acoustic/CT/material models.",
    "simulation_runner": "Scripts that run or orchestrate k-Wave, free-field, thermal, or pipeline simulations.",
    "analysis_compare": "Post-processing, comparison, auditing, plotting, and analysis scripts.",
    "planning_scan": "Planning, scanning, target/entry selection, download preparation, and candidate shortlisting scripts.",
    "utility_io": "Utility readers/searchers or source-download helpers.",
}

GOVERNANCE_GENERATORS = {
    "generate_evidence_registry.py",
    "generate_profile_preset_run_contract.py",
    "generate_gate_state_machine.py",
    "generate_run_ledger.py",
    "generate_maturity_model.py",
    "generate_claim_policy.py",
    "generate_module_boundary_manifest.py",
    "generate_cfl_environment_gate.py",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def classify(path: Path) -> tuple[str, str]:
    name = path.name
    if name in GOVERNANCE_GENERATORS or name.startswith("validate_") or name in {
        "evaluate_profile_promotion_gate.py",
        "review_alpha_mode_policy.py",
        "generate_module_evidence_brief.py",
    }:
        if name.startswith("validate_"):
            return "validator", "validate_* governance or output validation script"
        return "governance_policy", "explicit governance generator/evaluator"
    if name.startswith("generate_") or name.startswith("summarize_"):
        return "evidence_report_generator", "generate_* report/evidence artifact script"
    if name.startswith("build_") or name.startswith("batch_build_") or name.startswith("prepare_public") or name.startswith("prepare_visible"):
        return "model_build", "model/import/build preparation script"
    if name.startswith("simulate_") or name.startswith("run_") or name == "kwave_run_healthcheck.py":
        return "simulation_runner", "simulation or runner entry point"
    if (
        name.startswith("compare_")
        or name.startswith("analyze_")
        or name.startswith("audit_")
        or name.startswith("plot_")
        or name.startswith("estimate_")
        or name.startswith("evaluate_")
        or name.startswith("check_")
    ):
        return "analysis_compare", "analysis, audit, comparison, or plotting script"
    if name.startswith("plan_") or name.startswith("scan_") or name.startswith("select_") or name.startswith("shortlist_") or name.startswith("catalog_") or name.startswith("inventory_") or name.startswith("prepare_") or name.startswith("review_"):
        return "planning_scan", "planning, review, scan, or preparation script"
    if name in {
        "read_pdf.py",
        "search_pdf.py",
        "download_source_code_refs.py",
        "write_tcia_download_guide.py",
        "map_mri_to_ct_coordinates.py",
        "extract_source_code_formulas.py",
        "simulation_quality.py",
    }:
        return "utility_io", "utility or I/O helper"
    return "unclassified", "no current classification rule"


def build_manifest() -> dict[str, Any]:
    scripts = sorted(PROJECT_ROOT.glob("*.py"))
    entries = []
    for script in scripts:
        category, reason = classify(script)
        entries.append(
            {
                "path": rel(script),
                "name": script.name,
                "category": category,
                "classification_reason": reason,
                "move_performed": False,
            }
        )
    unclassified = [item["path"] for item in entries if item["category"] == "unclassified"]
    grouped: dict[str, list[str]] = {category: [] for category in CATEGORIES}
    for item in entries:
        if item["category"] in grouped:
            grouped[item["category"]].append(item["path"])
    return {
        "manifest_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": "module_boundary_manifest",
        "scope": "read-only current root script boundary manifest",
        "physical_reorganization_allowed": False,
        "physical_reorganization_block_reason": "Moving files would require a separate evidence-briefed cleanup with import/test audit.",
        "categories": CATEGORIES,
        "grouped_scripts": grouped,
        "script_entries": entries,
        "unclassified_scripts": unclassified,
        "proposed_future_layout": {
            "scripts/evidence/": ["evidence_report_generator", "governance evidence generators"],
            "scripts/gates/": ["gate evaluators and validators"],
            "scripts/model_build/": ["CT/model build and import scripts"],
            "scripts/runners/": ["k-Wave, free-field, thermal, and runner entry points"],
            "scripts/reports/": ["case/report/plot/compare scripts"],
            "scripts/planning/": ["entry, target, download, and scan planners"],
        },
        "required_followup_before_physical_move": [
            "create separate cleanup evidence brief",
            "map imports and command references",
            "add compatibility wrappers or update documented commands",
            "run validators after move",
        ],
        "not_executed": [
            "file move",
            "import rewrite",
            "k-Wave simulation",
            "thermal simulation",
        ],
    }


def markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Module Boundary Manifest",
        "",
        f"- manifest version: `{manifest['manifest_version']}`",
        f"- physical reorganization allowed: `{manifest['physical_reorganization_allowed']}`",
        f"- unclassified scripts: `{len(manifest['unclassified_scripts'])}`",
        "",
        "## Categories",
        "",
    ]
    for category, description in manifest["categories"].items():
        lines.append(f"- `{category}`: {description}")
    lines.extend(["", "## Grouped Scripts", ""])
    for category, scripts in manifest["grouped_scripts"].items():
        lines.append(f"### {category}")
        if scripts:
            lines.extend(f"- `{script}`" for script in scripts)
        else:
            lines.append("- none")
        lines.append("")
    lines.extend(["## Future Layout", ""])
    for folder, roles in manifest["proposed_future_layout"].items():
        lines.append(f"- `{folder}`: {', '.join(roles)}")
    lines.extend(["", "## Not Executed", ""])
    lines.extend(f"- {item}" for item in manifest["not_executed"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    manifest_path = OUT_DIR / "module_boundary_manifest.json"
    report_path = OUT_DIR / "module_boundary_manifest.md"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(markdown(manifest), encoding="utf-8")
    feedback = {
        "module": "module_boundary_manifest",
        "feedback_type": "post_execution_gap_feedback",
        "executed_scope": [
            "scanned root-level Python scripts",
            "classified scripts into module-boundary categories",
            "kept physical reorganization blocked",
        ],
        "outputs": {
            "manifest": rel(manifest_path),
            "report": rel(report_path),
        },
        "decision": {
            "module_boundary_manifest_status": "v1_complete",
            "physical_reorganization_allowed": False,
            "unclassified_script_count": len(manifest["unclassified_scripts"]),
        },
        "not_executed": manifest["not_executed"],
        "recommended_next_step": "Proceed to item 8: M2 baseline hardening program.",
    }
    (BRIEF_DIR / "gap_feedback.json").write_text(json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8")
    (BRIEF_DIR / "gap_feedback.md").write_text(
        "# Gap Feedback: Module Boundary Manifest\n\n"
        "## Decision\n\n"
        "- module boundary manifest status: `v1_complete`\n"
        f"- physical reorganization allowed: `{manifest['physical_reorganization_allowed']}`\n"
        f"- unclassified script count: `{len(manifest['unclassified_scripts'])}`\n\n"
        "## Outputs\n\n"
        f"- `{rel(manifest_path)}`\n"
        f"- `{rel(report_path)}`\n\n"
        "## Not Executed\n\n"
        "- No file move.\n"
        "- No import rewrite.\n"
        "- No k-Wave simulation.\n"
        "- No thermal simulation.\n",
        encoding="utf-8",
    )
    print(f"Wrote {rel(manifest_path)}")


if __name__ == "__main__":
    main()
