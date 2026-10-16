from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "outputs" / "nlm_public_case_readiness_20260723"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(artifacts: dict[str, dict]) -> dict:
    intake = artifacts["intake"]
    registration = artifacts["registration"]
    native = artifacts["native_t2"]
    model = artifacts["affine_model"]
    proxy = artifacts["proxy"]
    entry = artifacts["entry"]
    checks = {
        "ct_geometry_valid": intake["checks"]["ct_geometry_valid"] is True,
        "t2_geometry_valid": intake["checks"]["t2_geometry_valid"] is True,
        "registration_quantitative_gate_pass": registration["quantitative_checks"]["quantitative_gate_pass"] is True,
        "codex_registration_visual_review_pass": registration["codex_visual_review"] == "pass",
        "native_t2_matches_ct_grid": native["checks"]["shape_matches_ct"] is True and native["checks"]["affine_matches_ct"] is True,
        "affine_acoustic_model_ready": model["world_mapping"]["status"] == "available" and all(model["checks"].values()),
        "proxy_coordinate_transfer_ready": proxy["proxy_coordinate_transfer_ready"] is True and proxy["center_inside_mask"] is True,
        "entry_target_is_soft_tissue": entry["target_label"] == 1,
        "entry_crosses_skull": entry["has_skull_crossing"] is True and entry["entry_label"] == 2,
        "source_is_background": entry["source_center_label"] == 0,
    }
    automated_pipeline_ready = all(checks.values())
    expert_qc = registration["expert_human_visual_qc_pass"] is True
    registered_anatomy = proxy["registered_anatomical_roi_ready"] is True
    engineering_blockers = [
        "hardware_geometry_missing",
        "kwave_dry_run_not_executed",
    ]
    anatomical_blockers = [
        blocker
        for blocker, blocked in (
            ("expert_human_registration_qc_missing", not expert_qc),
            ("registered_anatomical_roi_missing", not registered_anatomy),
        )
        if blocked
    ]
    return {
        "readiness_version": "1.1.0",
        "case_id": "nlm_additional_head_72m",
        "subject_semantics": intake["subject_semantics"],
        "checks": checks,
        "automated_public_data_pipeline_ready": automated_pipeline_ready,
        "engineering_sandbox_input_ready": automated_pipeline_ready,
        "expert_required_for_engineering_sandbox": False,
        "expert_human_registration_qc_ready": expert_qc,
        "registered_anatomical_roi_ready": registered_anatomy,
        "simulation_execution_ready": False,
        "status": (
            "engineering_sandbox_input_ready_simulation_gates_pending"
            if automated_pipeline_ready
            else "public_pipeline_onboarding_incomplete"
        ),
        "gate_tracks": {
            "engineering_sandbox": {
                "input_ready": automated_pipeline_ready,
                "simulation_ready": False,
                "blockers": engineering_blockers,
                "post_execution_pending": ["pressure_and_exposure_metrics_not_computed"],
            },
            "registered_anatomical_or_clinical": {
                "ready": automated_pipeline_ready and expert_qc and registered_anatomy,
                "blockers": anatomical_blockers,
            },
        },
        "blockers": engineering_blockers,
        "pressure_executed": False,
        "clinical_safety_claim": False,
        "claim_boundary": (
            "expert_independent_public_postmortem_engineering_sandbox_"
            "not_anatomical_or_clinical_validation"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit end-to-end NLM public-case pipeline readiness without simulation.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    paths = {
        "intake": ROOT / "outputs/nlm_public_case_intake_20260722/intake_report.json",
        "registration": ROOT / "outputs/nlm_ct_t2_registration_20260722/registration_qc_report.json",
        "native_t2": ROOT / "outputs/nlm_ct_t2_native_resample_20260723/native_resample_report.json",
        "affine_model": ROOT / "outputs/nlm_ct_acoustic_model_affine_simple_hu300_dx0p75_20260723/affine_model_build_report.json",
        "proxy": ROOT / "outputs/nlm_proxy_acoustic_grid_20260723/proxy_transfer_report.json",
        "entry": ROOT / "outputs/nlm_ct_entry_plan_left_x_20260723/entry_plan.json",
    }
    result = evaluate({name: load(path) for name, path in paths.items()})
    result["artifacts"] = {name: str(path.relative_to(ROOT)) for name, path in paths.items()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "public_case_readiness.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# NLM Public Case Readiness",
        "",
        f"- Status: `{result['status']}`",
        f"- Automated pipeline ready: `{str(result['automated_public_data_pipeline_ready']).lower()}`",
        f"- Engineering sandbox input ready: `{str(result['engineering_sandbox_input_ready']).lower()}`",
        "- Expert required for engineering sandbox: `false`",
        f"- Expert registration QC: `{str(result['expert_human_registration_qc_ready']).lower()}`",
        f"- Registered anatomy: `{str(result['registered_anatomical_roi_ready']).lower()}`",
        "- Claim boundary: expert-independent public postmortem engineering sandbox only; no anatomical, clinical, or pressure claim.",
        "",
        "## Engineering simulation blockers",
        "",
        *[f"- `{item}`" for item in result["blockers"]],
        "",
        "## Anatomical or clinical-only blockers",
        "",
        *[
            f"- `{item}`"
            for item in result["gate_tracks"]["registered_anatomical_or_clinical"]["blockers"]
        ],
    ]
    (args.output_dir / "public_case_readiness.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
