from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parent
KWAVE_ROOT = Path(r"D:\AIprogram\python-envs\kwave312\Lib\site-packages\kwave")


@dataclass(frozen=True)
class SourceCheck:
    source_id: str
    path: Path
    patterns: tuple[str, ...]
    role: str


CHECKS = (
    SourceCheck(
        source_id="simulate_kwave_3d_focus_medium",
        path=PROJECT_ROOT / "simulate_kwave_3d_focus.py",
        patterns=("kWaveMedium", "alpha_coeff=model.alpha_coeff", "alpha_power=np.array(actual_alpha_power)"),
        role="3D CT pressure script medium construction",
    ),
    SourceCheck(
        source_id="simulate_kwave_3d_focus_npz",
        path=PROJECT_ROOT / "simulate_kwave_3d_focus.py",
        patterns=('"alpha_power" in data.files', "model.alpha_power", "config.alpha_power"),
        role="3D CT model alpha_power load and fallback",
    ),
    SourceCheck(
        source_id="simulate_freefield_transducer",
        path=PROJECT_ROOT / "simulate_freefield_transducer.py",
        patterns=("alpha_power", "medium_properties", "KWave3DConfig"),
        role="free-field homogeneous medium alpha_power plumbing",
    ),
    SourceCheck(
        source_id="build_ct_acoustic_model_metadata",
        path=PROJECT_ROOT / "build_ct_acoustic_model.py",
        patterns=("alpha_semantics_metadata", "alpha_semantics_npz_fields", '"alpha_power"'),
        role="CT model alpha semantics metadata and NPZ fields",
    ),
    SourceCheck(
        source_id="kwave_kmedium_contract",
        path=KWAVE_ROOT / "kmedium.py",
        patterns=("alpha_coeff: np.array = None", "alpha_power: np.array = None", "dB/(MHz^y cm)"),
        role="k-wave-python medium interface contract",
    ),
    SourceCheck(
        source_id="kwave_absorption_variables",
        path=KWAVE_ROOT / "kWaveSimulation_helper" / "create_absorption_variables.py",
        patterns=("db2neper(medium.alpha_coeff, medium.alpha_power)", "medium.alpha_power"),
        role="k-wave-python absorption variable conversion",
    ),
    SourceCheck(
        source_id="kwave_python_solver",
        path=KWAVE_ROOT / "solvers" / "kspace_solver.py",
        patterns=("alpha_power", "alpha_np", "alpha_coeff"),
        role="Python solver absorption path",
    ),
    SourceCheck(
        source_id="kwave_cpp_solver_export",
        path=KWAVE_ROOT / "solvers" / "cpp_simulation.py",
        patterns=('"alpha_coeff"', '"alpha_power"', "np.float32(medium.alpha_power)"),
        role="C++ solver input export path",
    ),
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def line_number_for(text: str, pattern: str) -> int | None:
    for idx, line in enumerate(text.splitlines(), start=1):
        if pattern in line:
            return idx
    return None


def excerpt_for(text: str, pattern: str, radius: int = 2) -> str:
    lines = text.splitlines()
    lineno = line_number_for(text, pattern)
    if lineno is None:
        return ""
    start = max(1, lineno - radius)
    end = min(len(lines), lineno + radius)
    return "\n".join(f"{i}: {lines[i - 1]}" for i in range(start, end + 1))


def audit_sources() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for check in CHECKS:
        exists = check.path.exists()
        text = read_text(check.path) if exists else ""
        pattern_hits = []
        for pattern in check.patterns:
            lineno = line_number_for(text, pattern) if exists else None
            pattern_hits.append(
                {
                    "pattern": pattern,
                    "found": lineno is not None,
                    "line": lineno,
                    "excerpt": excerpt_for(text, pattern) if lineno is not None else "",
                }
            )
        results.append(
            {
                "source_id": check.source_id,
                "path": str(check.path),
                "exists": exists,
                "role": check.role,
                "all_patterns_found": all(hit["found"] for hit in pattern_hits),
                "pattern_hits": pattern_hits,
            }
        )
    return results


def load_json_if_exists(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_npz_metadata(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    import numpy as np

    data = np.load(path, allow_pickle=True)
    keys = set(data.files)
    fields = {}
    for key in ["alpha_power", "alpha_unit_semantics", "alpha_coeff_kind", "alpha_source_route", "alpha_semantics_status"]:
        if key in keys:
            value = data[key]
            try:
                fields[key] = value.item()
            except ValueError:
                fields[key] = value.tolist()
    return {
        "path": str(path),
        "exists": True,
        "has_alpha_power": "alpha_power" in keys,
        "alpha_fields": fields,
    }


def assess_interface(source_results: list[dict[str, object]], profile: dict[str, object] | None, npz_meta: dict[str, object]) -> dict[str, object]:
    found = {item["source_id"]: item["all_patterns_found"] for item in source_results}
    script_passes_alpha_power = bool(found.get("simulate_kwave_3d_focus_medium") and found.get("simulate_kwave_3d_focus_npz"))
    kwave_contract_ok = bool(found.get("kwave_kmedium_contract") and found.get("kwave_absorption_variables"))
    solver_paths_reference_alpha_power = bool(found.get("kwave_python_solver") and found.get("kwave_cpp_solver_export"))
    profile_alpha_status = None
    profile_alpha_power = None
    if profile:
        semantics = profile.get("alpha_semantics", {})
        if isinstance(semantics, dict):
            profile_alpha_status = semantics.get("status")
            profile_alpha_power = semantics.get("alpha_power")
    npz_alpha_power = npz_meta.get("alpha_fields", {}).get("alpha_power") if npz_meta.get("exists") else None

    blockers: list[str] = []
    warnings: list[str] = []
    if not script_passes_alpha_power:
        blockers.append("simulate_kwave_3d_focus.py does not clearly load and pass alpha_power.")
    if not kwave_contract_ok:
        blockers.append("Could not confirm k-wave-python alpha_coeff/alpha_power interface contract.")
    if profile_alpha_power == 1.0:
        warnings.append("alpha_power=1.0 can be problematic with power-law dispersion unless alpha_mode/no_dispersion semantics are reviewed.")
    if profile_alpha_status and "review_pending" in str(profile_alpha_status):
        warnings.append("Profile alpha semantics remain review_pending; pressure use should stay blocked until a patch/review decision.")
    if npz_meta.get("exists") and npz_alpha_power is None:
        blockers.append("Validated NPZ exists but alpha_power metadata was not found.")

    recommendation = "do_not_run_draft_pressure_yet"
    if script_passes_alpha_power and kwave_contract_ok and solver_paths_reference_alpha_power and not blockers:
        recommendation = "interface_plumbing_present_but_alpha_mode_review_needed"

    return {
        "script_passes_alpha_power": script_passes_alpha_power,
        "kwave_contract_ok": kwave_contract_ok,
        "solver_paths_reference_alpha_power": solver_paths_reference_alpha_power,
        "profile_alpha_power": profile_alpha_power,
        "profile_alpha_status": profile_alpha_status,
        "npz_alpha_power": npz_alpha_power,
        "blockers": blockers,
        "warnings": warnings,
        "recommendation": recommendation,
        "pressure_allowed_for_prestus_marsac_mueller_draft": False,
    }


def write_csv(path: Path, source_results: Iterable[dict[str, object]]) -> None:
    import csv

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source_id", "path", "role", "exists", "all_patterns_found", "patterns"])
        writer.writeheader()
        for item in source_results:
            writer.writerow(
                {
                    "source_id": item["source_id"],
                    "path": item["path"],
                    "role": item["role"],
                    "exists": item["exists"],
                    "all_patterns_found": item["all_patterns_found"],
                    "patterns": "; ".join(
                        f"{hit['pattern']}@{hit['line'] if hit['line'] is not None else 'missing'}"
                        for hit in item["pattern_hits"]
                    ),
                }
            )


def markdown_report(payload: dict[str, object]) -> str:
    assessment = payload["assessment"]
    lines = [
        "# k-Wave alpha_power 接口审计报告",
        "",
        "## 结论",
        "",
        f"- 3D CT 脚本是否读取并传递 alpha_power：`{assessment['script_passes_alpha_power']}`",
        f"- k-wave-python 接口契约是否确认：`{assessment['kwave_contract_ok']}`",
        f"- solver 路径是否引用 alpha_power：`{assessment['solver_paths_reference_alpha_power']}`",
        f"- draft profile 当前建议：`{assessment['recommendation']}`",
        f"- 是否允许 `prestus_marsac_mueller_draft` 进入压力仿真：`{assessment['pressure_allowed_for_prestus_marsac_mueller_draft']}`",
        "",
        "## 关键解释",
        "",
        "- 当前平台的 3D CT 脚本已经具备 alpha_power plumbing：模型 NPZ 有 `alpha_power` 时优先使用，否则回退到脚本默认值。",
        "- k-wave-python 的 `kWaveMedium` 注释把 `alpha_coeff` 定义为 `dB/(MHz^y cm)`，并要求吸收介质同时定义 `alpha_coeff` 和 `alpha_power`。",
        "- 这只证明接口链路存在，不等于 PRESTUS draft attenuation 已通过物理验证。",
        "- `alpha_power=1.0` 仍需要额外审查 `alpha_mode` / dispersion 处理；在确认前不应启动 draft profile 压力仿真。",
        "",
        "## Blockers",
        "",
    ]
    blockers = assessment["blockers"]
    if blockers:
        lines.extend(f"- {item}" for item in blockers)
    else:
        lines.append("- 暂未发现接口级 blocker。")
    lines.extend(["", "## Warnings", ""])
    warnings = assessment["warnings"]
    if warnings:
        lines.extend(f"- {item}" for item in warnings)
    else:
        lines.append("- 暂无 warning。")
    lines.extend(["", "## 源码检查清单", ""])
    for item in payload["source_checks"]:
        lines.append(f"- `{item['source_id']}`: exists=`{item['exists']}`, all_patterns_found=`{item['all_patterns_found']}`")
        lines.append(f"  - path: `{item['path']}`")
    lines.extend(
        [
            "",
            "## 下一步建议",
            "",
            "1. 不运行 `prestus_marsac_mueller_draft` pressure simulation。",
            "2. 新增一个最小补丁计划：在 `simulate_kwave_3d_focus.py` 的 medium 构建处把 `alpha_mode` 也做成 profile/NPZ 可控，至少支持对 alpha_power=1 的 `no_dispersion` 审查路径。",
            "3. 补一个 dry-run/summary 字段，明确每次运行的 `alpha_coeff_kind`、`alpha_power`、`alpha_mode` 和 `alpha_semantics_status`。",
            "4. 完成补丁和 dry-run 后，再决定是否做 model-build-only 对照；压力仿真仍需用户单独授权。",
        ]
    )
    return "\n".join(lines) + "\n"


def gap_feedback_markdown(payload: dict[str, object]) -> str:
    assessment = payload["assessment"]
    lines = [
        "# kwave_alpha_power_interface_audit gap feedback",
        "",
        "## 本轮执行范围",
        "",
        "- 只读审计：读取项目脚本、mapping profile、已有 NPZ metadata 和本地 k-wave-python 源码。",
        "- 未运行 k-Wave。",
        "- 未生成 `pressure_max_mpa.npz` 或 `acoustic_model_3d.npz`。",
        "",
        "## 实际发现",
        "",
        f"- `script_passes_alpha_power`: `{assessment['script_passes_alpha_power']}`",
        f"- `kwave_contract_ok`: `{assessment['kwave_contract_ok']}`",
        f"- `solver_paths_reference_alpha_power`: `{assessment['solver_paths_reference_alpha_power']}`",
        f"- `profile_alpha_power`: `{assessment['profile_alpha_power']}`",
        f"- `profile_alpha_status`: `{assessment['profile_alpha_status']}`",
        "",
        "## 偏差与风险",
        "",
    ]
    warnings = assessment["warnings"]
    if warnings:
        lines.extend(f"- {item}" for item in warnings)
    else:
        lines.append("- 未发现新增 warning。")
    lines.extend(
        [
            "",
            "## 调节后的下一步",
            "",
            "- 不跑 draft pressure。",
            "- 先补 `alpha_mode` / alpha semantics 的 profile、NPZ、dry-run 和 summary 字段。",
            "- 后续任何 pressure 对照仍需单独 evidence brief、dry-run quality、runner 和用户授权。",
            "",
        ]
    )
    return "\n".join(lines)


def write_gap_feedback(payload: dict[str, object]) -> None:
    evidence_dir = PROJECT_ROOT / "outputs" / "evidence_briefs" / "kwave_alpha_power_interface_audit"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    feedback = {
        "feedback_type": "post_execution_gap_feedback",
        "module": "kwave_alpha_power_interface_audit",
        "execution_scope": payload["execution_scope"],
        "outputs": [
            "outputs/kwave_alpha_power_interface_audit/interface_audit_report.md",
            "outputs/kwave_alpha_power_interface_audit/interface_audit_report.json",
            "outputs/kwave_alpha_power_interface_audit/source_inventory.csv",
            "outputs/kwave_alpha_power_interface_audit/recommended_patch_plan.md",
        ],
        "assessment": payload["assessment"],
        "next_action": "Add alpha_mode/alpha semantics propagation to dry-run and summary before any draft pressure run.",
        "pressure_run_allowed": False,
    }
    (evidence_dir / "gap_feedback.json").write_text(json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8")
    (evidence_dir / "gap_feedback.md").write_text(gap_feedback_markdown(payload), encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit alpha_coeff/alpha_power interface semantics without running k-Wave.")
    parser.add_argument("--output-dir", default="outputs/kwave_alpha_power_interface_audit")
    parser.add_argument("--profile", default="acoustic_mapping_profiles/prestus_marsac_mueller_draft.json")
    parser.add_argument(
        "--model",
        default="outputs/alpha_semantics_metadata_validation/079_prestus_marsac_mueller_draft/acoustic_model_3d.npz",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    profile_path = PROJECT_ROOT / args.profile
    model_path = PROJECT_ROOT / args.model
    profile = load_json_if_exists(profile_path)
    npz_meta = load_npz_metadata(model_path)
    source_results = audit_sources()
    assessment = assess_interface(source_results, profile, npz_meta)

    payload = {
        "audit_type": "kwave_alpha_power_interface_audit",
        "execution_scope": "read_only_no_kwave",
        "profile_path": str(profile_path),
        "model_path": str(model_path),
        "profile_loaded": profile is not None,
        "model_metadata": npz_meta,
        "source_checks": source_results,
        "assessment": assessment,
    }

    (output_dir / "interface_audit_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "interface_audit_report.md").write_text(markdown_report(payload), encoding="utf-8-sig")
    write_csv(output_dir / "source_inventory.csv", source_results)
    write_gap_feedback(payload)

    patch_plan = "\n".join(
        [
            "# alpha_power / alpha_mode 后续补丁计划",
            "",
            "本文件是接口审计后的建议，不代表已经修改仿真物理。",
            "",
            "1. 在 mapping profile 中增加可选 `alpha_mode` 语义字段，默认保持空值。",
            "2. 在 CT acoustic model NPZ 中写入 `alpha_mode`、`alpha_coeff_kind`、`alpha_semantics_status`。",
            "3. 在 `simulate_kwave_3d_focus.py` 中读取这些字段，并在 `summary.json` 明确记录。",
            "4. 对 `alpha_power=1.0` 的 profile，只有在 evidence brief 或源码证据支持时才允许 `alpha_mode=no_dispersion`。",
            "5. 完成补丁后先跑 dry-run quality/metadata，不直接跑 pressure。",
            "",
        ]
    )
    (output_dir / "recommended_patch_plan.md").write_text(patch_plan, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
