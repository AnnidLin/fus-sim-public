from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
MODULE = "profile_preset_run_contract"
OUT_DIR = PROJECT_ROOT / "outputs" / MODULE


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def nested(data: dict[str, Any] | None, keys: list[str], default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def paths() -> dict[str, Path]:
    return {
        "profile": PROJECT_ROOT / "acoustic_mapping_profiles/simple_hu300.json",
        "presets": PROJECT_ROOT / "simulation_presets.json",
        "standard_run": PROJECT_ROOT
        / "outputs/ct_standard_pressure_authorization/079_candidate_006_dx0p75_pml12_standard/standard_pressure_execution_summary.json",
        "post_pressure_readiness": PROJECT_ROOT
        / "outputs/simple_hu300_post_pressure_readiness/079_candidate_006/post_pressure_readiness_summary.json",
        "registry": PROJECT_ROOT / "outputs/evidence_registry/evidence_registry.json",
    }


def build_contract() -> dict[str, Any]:
    p = paths()
    profile = read_json(p["profile"])
    presets = read_json(p["presets"])
    run = read_json(p["standard_run"])
    readiness = read_json(p["post_pressure_readiness"])
    registry = read_json(p["registry"])

    profile_id = nested(profile, ["profile_id"], "unknown")
    profile_review_status = nested(profile, ["review_status"], "unknown")
    preset_level = nested(run, ["simulation_quality", "preset"], nested(run, ["preset"], "unknown"))
    is_paper_grade = nested(run, ["simulation_quality", "is_paper_grade"], False)
    run_completed = nested(run, ["decision", "standard_pressure_run_completed"], False)
    paper_ready = nested(readiness, ["decision", "paper_grade_ready"], False)

    return {
        "contract_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": MODULE,
        "inputs": {name: rel(path) for name, path in p.items()},
        "profile": {
            "profile_id": profile_id,
            "profile_status": (
                "baseline_compatible_not_validated"
                if profile_review_status == "baseline_compatible"
                else f"{profile_review_status}_not_validated"
            ),
            "profile_review_status_source": rel(p["profile"]),
            "validated_pressure_baseline": False,
            "profile_promotion_allowed": False,
            "default_profile_change_allowed": False,
        },
        "preset": {
            "preset_level": preset_level,
            "quality_level": nested(run, ["simulation_quality", "preset"], preset_level),
            "is_paper_grade": bool(is_paper_grade),
            "preset_policy_source": rel(p["presets"]),
            "preset_does_not_define_profile_status": True,
            "preset_does_not_define_claim_level": True,
        },
        "run": {
            "run_id": "079_candidate_006_simple_hu300_dx075_pml12_standard_2026-06-02",
            "run_completed": bool(run_completed),
            "run_claim_level": "standard_engineering_pressure_output",
            "run_claim_level_reason": "runner-gated standard pressure output exists, but paper-grade/profile gates remain blocked",
            "output_dir": nested(run, ["output_dir"]),
            "pressure_generated": nested(run, ["runner", "core_output_exists", "pressure"], False),
            "summary_generated": nested(run, ["runner", "core_output_exists", "summary"], False),
        },
        "separation_policy": {
            "profile_success_does_not_upgrade_preset": True,
            "preset_success_does_not_upgrade_profile": True,
            "run_success_does_not_upgrade_profile": True,
            "run_success_does_not_upgrade_paper_grade": True,
            "paper_grade_requires_separate_gate": True,
            "profile_promotion_requires_separate_gate": True,
        },
        "claim_policy": {
            "allowed_claims": [
                "simple_hu300 is a reproducible engineering baseline profile",
                "the 079 candidate_006 dx0.75 PML12 standard run completed",
                "the run is standard engineering pressure output",
            ],
            "blocked_claims": [
                "validated pressure baseline",
                "paper-grade reproduction",
                "medical or safety conclusion",
                "default profile promotion",
                "source-backed alpha pressure eligibility",
            ],
            "paper_grade_ready": bool(paper_ready),
            "medical_or_safety_conclusion_allowed": False,
            "profile_promotion_allowed": False,
            "default_profile_change_allowed": False,
        },
        "conformance_target": {
            "registry_version": nested(registry, ["registry_version"]),
            "registry_path": rel(p["registry"]),
            "expected_profile_status": "baseline_compatible_not_validated",
            "expected_preset_level": "standard",
            "expected_run_claim_level": "standard_engineering_pressure_output",
        },
    }


def write_outputs(contract: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "profile_preset_run_contract.json"
    md_path = OUT_DIR / "profile_preset_run_contract.md"
    json_path.write_text(json.dumps(contract, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Profile / Preset / Run Separation Contract",
        "",
        f"- contract version: `{contract['contract_version']}`",
        f"- profile status: `{contract['profile']['profile_status']}`",
        f"- preset level: `{contract['preset']['preset_level']}`",
        f"- run claim level: `{contract['run']['run_claim_level']}`",
        "",
        "## Separation Policy",
        "",
    ]
    for key, value in contract["separation_policy"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Blocked Claims", ""])
    lines.extend(f"- {item}" for item in contract["claim_policy"]["blocked_claims"])
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    contract = build_contract()
    write_outputs(contract)
    print(f"Wrote {rel(OUT_DIR / 'profile_preset_run_contract.json')}")
    print(f"Wrote {rel(OUT_DIR / 'profile_preset_run_contract.md')}")


if __name__ == "__main__":
    main()
