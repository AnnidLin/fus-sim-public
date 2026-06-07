from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def no_dispersion_profile(base: dict[str, object]) -> dict[str, object]:
    profile = copy.deepcopy(base)
    profile["profile_id"] = "prestus_marsac_mueller_no_dispersion_experimental"
    profile["description"] = (
        "Experimental dry-run-only profile derived from prestus_marsac_mueller_draft. "
        "It sets alpha_mode=no_dispersion for alpha_power=1.0, following the k-wave-python interface workaround. "
        "This is not a validated physical baseline and must not be used for pressure conclusions."
    )
    semantics = profile.setdefault("alpha_semantics", {})
    semantics["alpha_mode"] = "no_dispersion"
    semantics["status"] = "experimental_dry_run_only_no_pressure"
    semantics["pressure_allowed"] = False
    semantics["policy_source"] = "outputs/alpha_mode_policy_review/policy_review.md"
    semantics.setdefault("notes", [])
    semantics["notes"].append("alpha_mode=no_dispersion is an experimental solver-interface choice, not a validated physics conclusion.")
    profile["review_status"] = "experimental_dry_run_only_do_not_use_as_default"
    profile["notes"] = [
        "Do not place this profile in the default baseline route.",
        "Model-build-only validation may be considered after user approval.",
        "Pressure simulation remains blocked until a separate evidence brief and dry-run quality gate pass.",
    ]
    return profile


def fit_alpha_power_2_plan_profile(base: dict[str, object]) -> dict[str, object]:
    profile = copy.deepcopy(base)
    profile["profile_id"] = "prestus_fit_alpha_power_2_plan_only"
    profile["description"] = (
        "Plan-only profile draft for migrating PRESTUS fit_alpha_power behavior. "
        "This profile is not directly buildable until fitPowerLawParamsMulti-style alpha0 rescaling is implemented and validated."
    )
    profile["mapping_type"] = "plan_only_prestus_fit_alpha_power_2_requires_formula_migration"
    mapping = profile.setdefault("source_backed_mapping", {})
    attenuation = mapping.setdefault("attenuation", {})
    attenuation["algorithm"] = "prestus_fit_alpha_power_2_plan_only"
    attenuation["formula"] = (
        "Requires fitPowerLawParamsMulti(a0, y, c0, f_ref, y_ref=2) migration. "
        "Do not implement by simply setting alpha_power=2 without rescaling alpha_coeff."
    )
    attenuation["source_locator"] = "data/source_code_refs/PRESTUS_source/functions/medium/fitPowerLawParamsMulti.m:1-90"
    attenuation["unit_risk"] = "blocked_until_formula_migrated"
    semantics = profile.setdefault("alpha_semantics", {})
    semantics["alpha_power"] = 2.0
    semantics["alpha_mode"] = None
    semantics["alpha_coeff_kind"] = "fit_alpha_power_2_prefactor_plan_only"
    semantics["status"] = "plan_only_requires_fitPowerLawParamsMulti_migration"
    semantics["pressure_allowed"] = False
    semantics["policy_source"] = "outputs/alpha_mode_policy_review/policy_review.md"
    semantics["notes"] = [
        "This route follows the PRESTUS idea of fitting attenuation to a fixed alpha_power=2.",
        "The required alpha0 rescaling formula is not implemented in fus-sim yet.",
        "Do not run build_ct_acoustic_model.py with this profile until mapping_type support is explicitly added.",
    ]
    profile["review_status"] = "plan_only_do_not_build_do_not_use_as_default"
    profile["notes"] = [
        "This is a planning artifact, not an executable acoustic mapping profile.",
        "The next engineering step would be formula migration and model-build-only validation.",
        "Pressure simulation is blocked.",
    ]
    return profile


def build_plan(output_dir: Path, no_dispersion_path: Path, fit_path: Path) -> dict[str, object]:
    return {
        "plan_type": "source_backed_alpha_profile_options",
        "execution_scope": "profile_drafts_and_plan_only_no_model_build_no_kwave",
        "pressure_allowed": False,
        "options": [
            {
                "option_id": "experimental_no_dispersion_profile",
                "profile_draft": str(no_dispersion_path),
                "status": "experimental_dry_run_only",
                "buildable_by_current_build_script": True,
                "pressure_allowed": False,
                "recommended_next_step": "Optional: user-authorized model-build-only validation in an isolated output directory.",
                "risk": "Suppresses dispersion; not a validated physics baseline.",
            },
            {
                "option_id": "prestus_fit_alpha_power_2_profile",
                "profile_draft": str(fit_path),
                "status": "plan_only_requires_formula_migration",
                "buildable_by_current_build_script": False,
                "pressure_allowed": False,
                "recommended_next_step": "Migrate fitPowerLawParamsMulti-style formula, then run model-build-only validation.",
                "risk": "Incorrect if implemented by only setting alpha_power=2 without alpha_coeff rescaling.",
            },
        ],
        "recommended_policy": "Do not run pressure. If continuing, choose exactly one model-build-only path after user confirmation.",
        "recommended_first_path": "experimental_no_dispersion_profile for isolated model-build-only validation, or fit_alpha_power_2 only after formula migration.",
    }


def markdown(plan: dict[str, object]) -> str:
    lines = [
        "# Source-backed Alpha Profile 方案对照",
        "",
        "## 结论",
        "",
        "- 本轮只生成 profile 草案和计划。",
        "- 未重建 CT 模型。",
        "- 未运行 k-Wave。",
        "- 未放行 pressure simulation。",
        "",
        f"- 推荐策略：{plan['recommended_policy']}",
        "",
        "## 候选路线",
        "",
    ]
    for option in plan["options"]:
        lines.append(f"### {option['option_id']}")
        lines.append("")
        lines.append(f"- 草案路径：`{option['profile_draft']}`")
        lines.append(f"- 状态：`{option['status']}`")
        lines.append(f"- 当前 build 脚本是否可直接构建：`{option['buildable_by_current_build_script']}`")
        lines.append(f"- 是否允许 pressure：`{option['pressure_allowed']}`")
        lines.append(f"- 推荐下一步：{option['recommended_next_step']}")
        lines.append(f"- 主要风险：{option['risk']}")
        lines.append("")
    lines.extend(
        [
            "## 下一步建议",
            "",
            "1. 若希望进度更快，可先选择 `experimental_no_dispersion_profile` 做 isolated model-build-only validation；仍不跑 pressure。",
            "2. 若希望更贴近 PRESTUS source，应先迁移 `fitPowerLawParamsMulti` 公式，再做 model-build-only validation。",
            "3. 任一路线进入 pressure 前，都需要新的 evidence brief、dry-run quality、runner 和用户明确授权。",
            "",
        ]
    )
    return "\n".join(lines)


def command_template(no_dispersion_path: Path, output_dir: Path) -> str:
    return "\n".join(
        [
            "# 本文件只给出后续人工确认后的命令模板；当前脚本不会自动执行这些命令。",
            "# 方案 A：no_dispersion 草案的 isolated model-build-only validation。",
            "D:\\AIprogram\\python-envs\\kwave312\\Scripts\\python.exe build_ct_acoustic_model.py --nifti-file data\\raw_ct\\079.nii --target-dx-mm 1.0 --target-index 93,121,63 --mapping-profile "
            + str(no_dispersion_path)
            + " --output-dir outputs\\ct_acoustic_model_3d_profile_no_dispersion_experimental",
            "",
            "# 方案 B：fit_alpha_power_2 目前不可执行；必须先迁移 fitPowerLawParamsMulti 公式。",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create source-backed alpha profile option drafts without running model build or k-Wave.")
    parser.add_argument("--base-profile", default="acoustic_mapping_profiles/prestus_marsac_mueller_draft.json")
    parser.add_argument("--output-dir", default="outputs/source_backed_alpha_profile_options")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    drafts_dir = output_dir / "profile_drafts"
    output_dir.mkdir(parents=True, exist_ok=True)
    base_path = PROJECT_ROOT / args.base_profile
    base = load_json(base_path)

    no_dispersion = no_dispersion_profile(base)
    fit_alpha = fit_alpha_power_2_plan_profile(base)
    no_dispersion_path = drafts_dir / "prestus_marsac_mueller_no_dispersion_experimental.json"
    fit_path = drafts_dir / "prestus_fit_alpha_power_2_plan_only.json"
    write_json(no_dispersion_path, no_dispersion)
    write_json(fit_path, fit_alpha)

    plan = build_plan(output_dir, no_dispersion_path, fit_path)
    plan["base_profile"] = str(base_path)
    write_json(output_dir / "profile_option_plan.json", plan)
    (output_dir / "profile_option_report.md").write_text(markdown(plan), encoding="utf-8-sig")
    (output_dir / "recommended_commands.ps1").write_text(command_template(no_dispersion_path, output_dir), encoding="utf-8-sig")

    evidence_dir = PROJECT_ROOT / "outputs" / "evidence_briefs" / "source_backed_alpha_profile_options"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    feedback = {
        "feedback_type": "post_execution_gap_feedback",
        "module": "source_backed_alpha_profile_options",
        "execution_scope": "profile_drafts_and_plan_only",
        "outputs": [
            "outputs/source_backed_alpha_profile_options/profile_option_report.md",
            "outputs/source_backed_alpha_profile_options/profile_option_plan.json",
            "outputs/source_backed_alpha_profile_options/profile_drafts/prestus_marsac_mueller_no_dispersion_experimental.json",
            "outputs/source_backed_alpha_profile_options/profile_drafts/prestus_fit_alpha_power_2_plan_only.json",
        ],
        "pressure_allowed": False,
        "model_build_executed": False,
        "kwave_executed": False,
        "recommended_next_step": plan["recommended_policy"],
    }
    write_json(evidence_dir / "gap_feedback.json", feedback)
    (evidence_dir / "gap_feedback.md").write_text(
        "# source_backed_alpha_profile_options gap feedback\n\n"
        "本轮只生成 profile 草案和计划；未重建模型，未运行 k-Wave，未放行 pressure。\n",
        encoding="utf-8-sig",
    )


if __name__ == "__main__":
    main()
