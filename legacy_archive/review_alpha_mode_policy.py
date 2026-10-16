from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parent
KWAVE_ROOT = Path(r"D:\AIprogram\python-envs\kwave312\Lib\site-packages\kwave")


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    path: Path
    patterns: tuple[str, ...]
    interpretation: str


EVIDENCE = (
    EvidenceItem(
        evidence_id="kwave_alpha_power_1_requires_no_dispersion_or_alternative",
        path=KWAVE_ROOT / "kmedium.py",
        patterns=("alpha_power != 1", "no_dispersion", "not valid for medium.alpha_power = 1"),
        interpretation="k-wave-python explicitly treats alpha_power=1 as invalid for the dispersion term unless alpha_mode=no_dispersion is used.",
    ),
    EvidenceItem(
        evidence_id="kwave_alpha_mode_allowed_values",
        path=KWAVE_ROOT / "kmedium.py",
        patterns=("no_absorption", "no_dispersion", "stokes"),
        interpretation="k-wave-python accepts alpha_mode values no_absorption, no_dispersion, and stokes.",
    ),
    EvidenceItem(
        evidence_id="prestus_mueller_alpha0_conversion",
        path=PROJECT_ROOT / "data" / "source_code_refs" / "PRESTUS_source" / "doc" / "doc_pseudoCT.md",
        patterns=("mueller", "alpha_0", "0.5^y"),
        interpretation="PRESTUS documents Mueller attenuation as alpha(f=500kHz) converted to alpha0 using alpha_power.",
    ),
    EvidenceItem(
        evidence_id="prestus_fit_alpha_power_route",
        path=PROJECT_ROOT / "data" / "source_code_refs" / "PRESTUS_source" / "functions" / "medium" / "medium_setup.m",
        patterns=("fit_alpha_power", "alpha_power_fixed = 2", "fitPowerLawParamsMulti"),
        interpretation="PRESTUS has a fitted fixed-alpha-power route, defaulting to alpha_power=2 when fit_alpha_power is enabled.",
    ),
    EvidenceItem(
        evidence_id="prestus_fit_power_law_helper",
        path=PROJECT_ROOT / "data" / "source_code_refs" / "PRESTUS_source" / "functions" / "medium" / "fitPowerLawParamsMulti.m",
        patterns=("single global", "alpha_power", "rescaled prefactor"),
        interpretation="PRESTUS describes rescaling alpha0 when the solver enforces a single reference alpha_power.",
    ),
    EvidenceItem(
        evidence_id="babelbrain_dispersion_correction_not_alpha_mode",
        path=PROJECT_ROOT / "data" / "source_code_refs" / "BabelBrain_source" / "TranscranialModeling" / "BabelIntegrationBASE.py",
        patterns=("bApplyCorrectionForDispersion", "DispersionCorrection", "ExpectedError"),
        interpretation="BabelBrain includes dispersion correction logic, but it is not direct evidence for kWaveMedium.alpha_mode=no_dispersion.",
    ),
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def find_line(text: str, pattern: str) -> int | None:
    for idx, line in enumerate(text.splitlines(), start=1):
        if pattern in line:
            return idx
    return None


def excerpt(text: str, pattern: str, radius: int = 2) -> str:
    lines = text.splitlines()
    line = find_line(text, pattern)
    if line is None:
        return ""
    start = max(1, line - radius)
    end = min(len(lines), line + radius)
    return "\n".join(f"{idx}: {lines[idx - 1]}" for idx in range(start, end + 1))


def audit_evidence() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in EVIDENCE:
        exists = item.path.exists()
        text = read_text(item.path) if exists else ""
        hits = []
        for pattern in item.patterns:
            line = find_line(text, pattern) if exists else None
            hits.append(
                {
                    "pattern": pattern,
                    "found": line is not None,
                    "line": line,
                    "excerpt": excerpt(text, pattern) if line is not None else "",
                }
            )
        rows.append(
            {
                "evidence_id": item.evidence_id,
                "path": str(item.path),
                "exists": exists,
                "all_patterns_found": all(hit["found"] for hit in hits),
                "interpretation": item.interpretation,
                "hits": hits,
            }
        )
    return rows


def read_profile(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_policy(evidence: list[dict[str, object]], profile: dict[str, object]) -> dict[str, object]:
    semantics = profile.get("alpha_semantics", {})
    alpha_power = semantics.get("alpha_power") if isinstance(semantics, dict) else None
    alpha_mode = semantics.get("alpha_mode") if isinstance(semantics, dict) else None
    has_kwave_no_dispersion_evidence = any(
        row["evidence_id"] == "kwave_alpha_power_1_requires_no_dispersion_or_alternative" and row["all_patterns_found"]
        for row in evidence
    )
    has_prestus_fit_route = any(
        row["evidence_id"] == "prestus_fit_alpha_power_route" and row["all_patterns_found"]
        for row in evidence
    )
    has_mueller_alpha0_evidence = any(
        row["evidence_id"] == "prestus_mueller_alpha0_conversion" and row["all_patterns_found"]
        for row in evidence
    )

    options = [
        {
            "option_id": "keep_blocked",
            "description": "Keep prestus_marsac_mueller_draft blocked for pressure.",
            "evidence_strength": "high",
            "pros": ["No implicit physics change.", "Preserves current traceability."],
            "cons": ["Does not produce a source-backed pressure comparison yet."],
            "recommended": True,
        },
        {
            "option_id": "experimental_no_dispersion_profile",
            "description": "Create a separate experimental profile with alpha_mode=no_dispersion for alpha_power=1.0.",
            "evidence_strength": "interface_supported_but_physics_review_needed" if has_kwave_no_dispersion_evidence else "insufficient",
            "pros": ["Matches k-wave-python documented workaround for alpha_power=1."],
            "cons": ["Suppresses dispersion; not automatically a literature-validated choice.", "Must not overwrite the current draft profile."],
            "recommended": False,
        },
        {
            "option_id": "prestus_fit_alpha_power_2_profile",
            "description": "Create a separate model-build-only profile following PRESTUS fit_alpha_power route with fixed alpha_power=2.",
            "evidence_strength": "source_supported_model_build_route" if has_prestus_fit_route else "insufficient",
            "pros": ["Closer to PRESTUS source strategy for solver-compatible single alpha_power.", "Avoids alpha_power=1 dispersion singularity."],
            "cons": ["Requires implementing/validating fitPowerLawParamsMulti-style rescaling; not a one-line parameter change."],
            "recommended": False,
        },
    ]

    pressure_allowed = False
    blockers = [
        "Current draft profile has alpha_mode unset.",
        "alpha_power=1.0 requires an explicit dispersion decision.",
        "No source-backed pressure run should start until a separate experimental profile or fitted-alpha-power route is reviewed.",
    ]
    if not has_mueller_alpha0_evidence:
        blockers.append("Could not confirm PRESTUS Mueller alpha0 conversion evidence.")
    return {
        "profile_id": profile.get("profile_id"),
        "profile_alpha_power": alpha_power,
        "profile_alpha_mode": alpha_mode,
        "has_kwave_no_dispersion_evidence": has_kwave_no_dispersion_evidence,
        "has_prestus_fit_route": has_prestus_fit_route,
        "has_mueller_alpha0_evidence": has_mueller_alpha0_evidence,
        "policy_options": options,
        "recommended_policy": "keep_blocked",
        "pressure_allowed_for_current_profile": pressure_allowed,
        "blockers": blockers,
        "next_engineering_action": "If continuing source-backed mapping, create a dry-run-only plan for either an experimental no_dispersion profile or a PRESTUS fit_alpha_power=2 model-build profile; do not run pressure.",
    }


def write_csv(path: Path, evidence: Iterable[dict[str, object]]) -> None:
    import csv

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["evidence_id", "path", "exists", "all_patterns_found", "interpretation", "patterns"])
        writer.writeheader()
        for row in evidence:
            writer.writerow(
                {
                    "evidence_id": row["evidence_id"],
                    "path": row["path"],
                    "exists": row["exists"],
                    "all_patterns_found": row["all_patterns_found"],
                    "interpretation": row["interpretation"],
                    "patterns": "; ".join(f"{hit['pattern']}@{hit['line'] if hit['line'] else 'missing'}" for hit in row["hits"]),
                }
            )


def markdown(payload: dict[str, object]) -> str:
    policy = payload["policy"]
    lines = [
        "# alpha_mode / no_dispersion 策略审查",
        "",
        "## 结论",
        "",
        f"- 当前 profile：`{policy['profile_id']}`",
        f"- 当前 `alpha_power`：`{policy['profile_alpha_power']}`",
        f"- 当前 `alpha_mode`：`{policy['profile_alpha_mode']}`",
        f"- 当前 profile 是否允许 pressure：`{policy['pressure_allowed_for_current_profile']}`",
        f"- 推荐策略：`{policy['recommended_policy']}`",
        "",
        "当前建议是继续阻断 `prestus_marsac_mueller_draft` 的 pressure simulation。`alpha_mode=no_dispersion` 是 k-wave-python 支持的规避路径，但不是自动物理真值；PRESTUS 还提供了 fixed alpha_power=2 的拟合路线，值得作为后续 model-build-only 方向比较。",
        "",
        "## 策略选项",
        "",
    ]
    for option in policy["policy_options"]:
        lines.append(f"### {option['option_id']}")
        lines.append("")
        lines.append(f"- 描述：{option['description']}")
        lines.append(f"- 证据强度：`{option['evidence_strength']}`")
        lines.append(f"- 推荐：`{option['recommended']}`")
        lines.append(f"- 优点：{'; '.join(option['pros'])}")
        lines.append(f"- 风险：{'; '.join(option['cons'])}")
        lines.append("")
    lines.extend(["## Blockers", ""])
    lines.extend(f"- {item}" for item in policy["blockers"])
    lines.extend(["", "## 证据清单", ""])
    for row in payload["evidence"]:
        lines.append(f"- `{row['evidence_id']}`: exists=`{row['exists']}`, all_patterns_found=`{row['all_patterns_found']}`")
        lines.append(f"  - {row['interpretation']}")
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "1. 若继续 source-backed mapping，优先新增一个 dry-run-only 的实验 profile 计划，而不是修改现有 draft。",
            "2. 两条候选路线：`experimental_no_dispersion_profile` 或 `prestus_fit_alpha_power_2_profile`。",
            "3. 任一路线都先做 model-build/dry-run，不直接跑 pressure。",
            "",
        ]
    )
    return "\n".join(lines)


def gap_feedback(payload: dict[str, object]) -> dict[str, object]:
    return {
        "feedback_type": "post_execution_gap_feedback",
        "module": "alpha_mode_policy_review",
        "execution_scope": "read_only_policy_review_no_kwave",
        "outputs": [
            "outputs/alpha_mode_policy_review/policy_review.md",
            "outputs/alpha_mode_policy_review/policy_review.json",
            "outputs/alpha_mode_policy_review/evidence_inventory.csv",
        ],
        "policy": payload["policy"],
        "pressure_run_allowed": False,
        "next_action": payload["policy"]["next_engineering_action"],
    }


def gap_markdown(payload: dict[str, object]) -> str:
    policy = payload["policy"]
    return "\n".join(
        [
            "# alpha_mode_policy_review gap feedback",
            "",
            "## 本轮执行范围",
            "",
            "- 只读策略审查。",
            "- 未运行 k-Wave。",
            "- 未修改现有 draft profile 的 alpha_mode。",
            "",
            "## 结果",
            "",
            f"- 推荐策略：`{policy['recommended_policy']}`",
            f"- 当前 profile pressure allowed：`{policy['pressure_allowed_for_current_profile']}`",
            "",
            "## 下一步",
            "",
            policy["next_engineering_action"],
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review alpha_mode/no_dispersion policy without running k-Wave.")
    parser.add_argument("--profile", default="acoustic_mapping_profiles/prestus_marsac_mueller_draft.json")
    parser.add_argument("--output-dir", default="outputs/alpha_mode_policy_review")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    profile = read_profile(PROJECT_ROOT / args.profile)
    evidence = audit_evidence()
    policy = build_policy(evidence, profile)
    payload = {
        "review_type": "alpha_mode_policy_review",
        "execution_scope": "read_only_no_kwave",
        "profile_path": str(PROJECT_ROOT / args.profile),
        "evidence": evidence,
        "policy": policy,
    }
    (output_dir / "policy_review.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "policy_review.md").write_text(markdown(payload), encoding="utf-8-sig")
    write_csv(output_dir / "evidence_inventory.csv", evidence)

    evidence_dir = PROJECT_ROOT / "outputs" / "evidence_briefs" / "alpha_mode_policy_review"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    feedback = gap_feedback(payload)
    (evidence_dir / "gap_feedback.json").write_text(json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8")
    (evidence_dir / "gap_feedback.md").write_text(gap_markdown(payload), encoding="utf-8-sig")


if __name__ == "__main__":
    main()
