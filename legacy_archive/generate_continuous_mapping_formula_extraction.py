from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

SEARCH_TERMS = (
    "HU",
    "CT",
    "continuous",
    "skull",
    "density",
    "sound",
    "attenuation",
    "PRESTUS",
    "BabelBrain",
    "Aubry",
    "Darmani",
    "Mueller",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("/", "\\")
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8-sig")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def text_matches(row: dict[str, str]) -> bool:
    text = " ".join(str(v) for v in row.values()).lower()
    return any(term.lower() in text for term in SEARCH_TERMS)


def add_matrix_rows(rows: list[dict[str, Any]], source_path: Path, matrix_rows: list[dict[str, str]], source_kind: str) -> None:
    for idx, row in enumerate(matrix_rows, start=1):
        if not text_matches(row):
            continue
        if source_kind == "paper":
            source_id = row.get("paper_id") or row.get("title") or f"paper_row_{idx}"
            evidence_level = row.get("evidence_level", "")
            role = row.get("parameter_name", "")
            note = row.get("notes", "")
        else:
            source_id = row.get("tool_id") or row.get("name") or f"tool_row_{idx}"
            evidence_level = row.get("evidence_level", "")
            role = row.get("what_to_learn", "")
            note = row.get("risk_or_limit", "")
        rows.append(
            {
                "source_id": source_id,
                "source_type": source_kind,
                "locator": f"{rel(source_path)} row {idx}",
                "formula_parameter": "unspecified_or_context",
                "evidence_level": evidence_level or "local_matrix_entry",
                "evidence_status": "direction_or_context_only",
                "extractable_formula": "no",
                "summary": role,
                "risk_or_gap": note or "No exact formula extracted from this matrix row.",
                "recommended_next_action": "Use as locator; review primary paper/code before adopting numeric formulas.",
            }
        )


def add_document_mentions(rows: list[dict[str, Any]], path: Path, source_id: str, source_type: str) -> None:
    text = read_text(path)
    if not text:
        return
    matched_terms = [term for term in SEARCH_TERMS if term.lower() in text.lower()]
    if not matched_terms:
        return
    rows.append(
        {
            "source_id": source_id,
            "source_type": source_type,
            "locator": rel(path),
            "formula_parameter": "multiple",
            "evidence_level": "local_report_or_brief",
            "evidence_status": "secondary_summary_only",
            "extractable_formula": "no",
            "summary": f"Mentions: {', '.join(matched_terms[:10])}",
            "risk_or_gap": "Useful for orientation but not sufficient as primary formula evidence.",
            "recommended_next_action": "Trace cited papers/tools to exact equations or source functions.",
        }
    )


def current_implementation_rows(audit: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not audit:
        return []
    formula = audit.get("implemented_formula_summary", {})
    cont = audit.get("continuous_mapping_config", {})
    rows = []
    for param, key in (
        ("sound_speed_m_s", "sound_speed_range_m_s"),
        ("density_kg_m3", "density_range_kg_m3"),
        ("alpha_db_mhz_cm", "alpha_range_db_mhz_cm"),
    ):
        rows.append(
            {
                "source_id": "fus_sim_current_implementation",
                "source_type": "local_code",
                "locator": audit.get("builder_path", "build_ct_acoustic_model.py"),
                "formula_parameter": param,
                "evidence_level": "implemented_but_not_source_verified",
                "evidence_status": "exploratory_implementation",
                "extractable_formula": "yes_current_code_only",
                "summary": f"Skull-only linear interpolation after HU clamp; range={cont.get(key)}.",
                "risk_or_gap": "Formula source, units, and HU clamp convention remain unverified.",
                "recommended_next_action": "Compare against PRESTUS/BabelBrain/source paper equations before validation.",
            }
        )
    rows.append(
        {
            "source_id": "fus_sim_current_implementation",
            "source_type": "local_code",
            "locator": audit.get("builder_path", "build_ct_acoustic_model.py"),
            "formula_parameter": "hu_clamp",
            "evidence_level": "implemented_but_not_source_verified",
            "evidence_status": "exploratory_implementation",
            "extractable_formula": "yes_current_code_only",
            "summary": f"HU is clipped to {cont.get('hu_min')}..{cont.get('hu_max')} for skull-labeled voxels.",
            "risk_or_gap": "hu_max is not locked to a primary source.",
            "recommended_next_action": "Audit paper/code HU_max or normalization convention.",
        }
    )
    rows.append(
        {
            "source_id": "fus_sim_current_implementation",
            "source_type": "local_code",
            "locator": audit.get("builder_path", "build_ct_acoustic_model.py"),
            "formula_parameter": "skull_mask_scope",
            "evidence_level": "engineering_assumption",
            "evidence_status": "needs_model_build_validation",
            "extractable_formula": "yes_current_code_only",
            "summary": "Continuous mapping is applied only inside label 2 skull voxels; background and soft tissue remain fixed.",
            "risk_or_gap": "Needs model-build-only validation of labels, property distributions, and source/entry path properties.",
            "recommended_next_action": "Run model-build-only validation after formula source review.",
        }
    )
    return rows


def parameter_status(rows: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    statuses = {
        "sound_speed_m_s": {
            "status": "direction_supported_formula_unverified",
            "reason": "Current code has a linear interpolation, but no primary source or public code function has been audited.",
        },
        "density_kg_m3": {
            "status": "direction_supported_formula_unverified",
            "reason": "Current code has a linear interpolation, but the density mapping source remains unverified.",
        },
        "alpha_db_mhz_cm": {
            "status": "high_risk_units_unverified",
            "reason": "Attenuation mapping depends on units and frequency exponent; local evidence is insufficient.",
        },
        "hu_clamp": {
            "status": "unverified",
            "reason": "hu_min/hu_max are implemented in profile but not locked to source evidence.",
        },
        "skull_mask_scope": {
            "status": "engineering_assumption_pending_validation",
            "reason": "Skull-only mapping is a sensible platform design but still needs build-only validation.",
        },
    }
    return statuses


def make_report(report: dict[str, Any]) -> str:
    statuses = report["parameter_status"]
    return f"""# Continuous CT-HU Mapping 公式来源抽取报告

## 结论

本地证据仍不足以把 `continuous_skull` 升级为 validated baseline。当前只能确认：

1. PRESTUS/BabelBrain 等工具支持“CT/pseudo-CT 到异质声学模型”的方向；
2. fus-sim 已经实现了一个 skull-only 线性插值公式；
3. 但声速、密度、衰减、HU clamp 的精确来源和单位仍未锁定。

因此，当前 formula 状态是：**exploratory implementation, source formula unverified**。

## 参数状态

| 参数 | 状态 | 原因 |
| --- | --- | --- |
| sound_speed_m_s | {statuses['sound_speed_m_s']['status']} | {statuses['sound_speed_m_s']['reason']} |
| density_kg_m3 | {statuses['density_kg_m3']['status']} | {statuses['density_kg_m3']['reason']} |
| alpha_db_mhz_cm | {statuses['alpha_db_mhz_cm']['status']} | {statuses['alpha_db_mhz_cm']['reason']} |
| hu_clamp | {statuses['hu_clamp']['status']} | {statuses['hu_clamp']['reason']} |
| skull_mask_scope | {statuses['skull_mask_scope']['status']} | {statuses['skull_mask_scope']['reason']} |

## 当前 fus-sim 实现

当前代码公式可以被描述为：

```text
labels = threshold(HU)
skull_mask = labels == 2
HU_clipped = clip(HU, hu_min, hu_max)
t = (HU_clipped - hu_min) / (hu_max - hu_min)
property = range_min + t * (range_max - range_min)
```

该公式只代表当前实现，不代表已经被论文或公开代码验证。

## 本地证据源数量

- 公式来源矩阵记录数：{len(report['formula_source_matrix'])}
- 已确认 primary formula source：0
- 可立即作为默认公式的来源：0

## 关键缺口

- PRESTUS CT/pseudo-CT 到声学属性的具体源码函数尚未抽取。
- BabelBrain 的材料映射或报告字段尚未做 line-level 审查。
- Darmani/Mueller 等论文的公式、单位和适用范围尚未转录成 profile。
- attenuation 的单位和频率指数仍是最高风险项。

## 下一步建议

下一步不要跑 pressure。应选择以下二者之一：

1. 联网或本地下载公开代码后，抽取 PRESTUS/BabelBrain 中的 CT-to-acoustic 函数；
2. 在不跑 k-Wave 的前提下，做 model-build-only validation，比较 profile 生成的 label/property 分布、颅骨路径属性和 summary schema。
"""


def make_missing_checklist(report: dict[str, Any]) -> str:
    return """# Continuous Mapping Missing Evidence Checklist

## 必须补齐

- [ ] PRESTUS 源码中 CT/pseudo-CT 到 sound speed 的函数定位。
- [ ] PRESTUS 源码中 CT/pseudo-CT 到 density 的函数定位。
- [ ] PRESTUS 或论文中的 attenuation 公式、单位和频率指数。
- [ ] BabelBrain 是否使用 CT HU、density map 或 tissue class 映射材料属性。
- [ ] HU clamp 或 normalization 的来源，包括 HU_max。
- [ ] 当前 `continuous_skull.json` 中 `2200-3200 m/s`、`1500-2200 kg/m3`、`4-12 dB/MHz/cm` 的来源表。
- [ ] profile notes 与当前 builder 实现状态一致性修复。
- [ ] model-build-only validation：不跑声场，只比较 property volume 分布和颅骨路径属性。

## 完成前禁止

- [ ] 禁止把 `continuous_skull` 设置为默认 profile。
- [ ] 禁止继续用 continuous profile 做新的 CT pressure 对照。
- [ ] 禁止把既有 0.3% waveform difference 写成 validated physical conclusion。
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract local evidence for continuous CT-HU mapping formulas.")
    parser.add_argument("--output-dir", default="outputs/ct_hu_mapping_formula_extraction")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    paper_path = ROOT / "paper_parameter_matrix.csv"
    tool_path = ROOT / "tool_code_matrix.csv"
    alignment_path = ROOT / "parameter_alignment_report.md"
    route_path = ROOT / "reproduction_route_calibration.md"
    old_brief_path = ROOT / "outputs/evidence_briefs/ct_hu_continuous_mapping/evidence_brief.md"
    formula_review_path = ROOT / "outputs/ct_hu_mapping_audit/continuous_mapping_formula_review.md"
    audit_path = ROOT / "outputs/ct_hu_mapping_reconciliation/implemented_formula_audit.json"

    rows: list[dict[str, Any]] = []
    add_matrix_rows(rows, paper_path, read_csv(paper_path), "paper")
    add_matrix_rows(rows, tool_path, read_csv(tool_path), "tool")
    add_document_mentions(rows, alignment_path, "parameter_alignment_report", "local_report")
    add_document_mentions(rows, route_path, "reproduction_route_calibration", "local_report")
    add_document_mentions(rows, old_brief_path, "ct_hu_continuous_mapping_brief", "old_evidence_brief")
    add_document_mentions(rows, formula_review_path, "continuous_mapping_formula_review", "local_audit")
    rows.extend(current_implementation_rows(read_json(audit_path)))

    report = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "formula_source_unverified",
        "scope": "local evidence extraction only; no web lookup, no downloads, no model rebuild, no k-Wave",
        "formula_source_matrix": rows,
        "parameter_status": parameter_status(rows),
        "primary_formula_source_count": 0,
        "validated_default_ready": False,
        "recommended_next_actions": [
            "Extract PRESTUS/BabelBrain source functions with line-level locators.",
            "Audit attenuation units and frequency exponent.",
            "Run model-build-only validation after formula evidence is improved.",
        ],
    }

    write_csv(out_dir / "formula_source_matrix.csv", rows)
    write_json(out_dir / "formula_source_matrix.json", rows)
    write_json(out_dir / "formula_extraction_report.json", report)
    write_md(out_dir / "formula_extraction_report.md", make_report(report))
    write_md(out_dir / "missing_evidence_checklist.md", make_missing_checklist(report))

    print(f"Wrote continuous mapping formula extraction package to {rel(out_dir)}")


if __name__ == "__main__":
    main()
