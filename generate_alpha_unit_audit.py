from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


PROFILE_PATHS = [
    Path("acoustic_mapping_profiles/simple_hu300.json"),
    Path("acoustic_mapping_profiles/continuous_skull.json"),
    Path("acoustic_mapping_profiles/prestus_marsac_mueller_draft.json"),
]


SOURCE_SNIPPETS = [
    {
        "source_id": "PRESTUS_kplan_attenuation",
        "path": Path("data/source_code_refs/PRESTUS_source/functions/medium/medium_pct_attenuation.m"),
        "start": 37,
        "end": 50,
        "unit_semantics": "alpha_coeff=13.3 with alpha_power=1; intended to replicate k-Plan; comments say config alpha_coeff is dB/(MHz cm).",
        "classification": "alpha0_candidate_with_power_law",
        "confidence": "medium",
    },
    {
        "source_id": "PRESTUS_mueller_attenuation",
        "path": Path("data/source_code_refs/PRESTUS_source/functions/medium/medium_pct_attenuation.m"),
        "start": 52,
        "end": 68,
        "unit_semantics": "alpha_min/max are alpha(f) at 500 kHz in dB/cm; code converts to alpha0 by alpha_at_500kHz / 0.5^alpha_power.",
        "classification": "alpha_at_frequency_converted_to_alpha0",
        "confidence": "high_for_PRESTUS_code_medium_for_fus_sim",
    },
    {
        "source_id": "PRESTUS_aubry_attenuation",
        "path": Path("data/source_code_refs/PRESTUS_source/functions/medium/medium_pct_attenuation.m"),
        "start": 69,
        "end": 78,
        "unit_semantics": "alpha_min=0.2 and alpha_max=8 from Aubry route; alpha_power from config; units require source-paper audit.",
        "classification": "ambiguous_alpha_coeff_route",
        "confidence": "medium_low",
    },
    {
        "source_id": "BabelBrain_porosity_attenuation",
        "path": Path("data/source_code_refs/BabelBrain_source/TranscranialModeling/BabelIntegrationBASE.py"),
        "start": 473,
        "end": 492,
        "unit_semantics": "Returns attenuation in Np/m according to docstring; formula scales with frequency/1e6 and sqrt porosity.",
        "classification": "np_per_m_candidate",
        "confidence": "medium",
    },
    {
        "source_id": "BabelBrain_Webb_attenuation",
        "path": Path("data/source_code_refs/BabelBrain_source/TranscranialModeling/BabelIntegrationBASE.py"),
        "start": 494,
        "end": 533,
        "unit_semantics": "Uses Webb scanner/kernel coefficients: Alpha_0*(frequency/1e6)^Beta*exp(HU*c)*100; docstring says attenuation values Np/m x 100.",
        "classification": "scanner_specific_ambiguous_conversion",
        "confidence": "medium_low",
    },
]


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


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


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


def source_excerpt(path: Path, start: int, end: int) -> str:
    lines = read_lines(path)
    if not lines:
        return ""
    return "\n".join(f"{i}: {lines[i - 1]}" for i in range(start, min(end, len(lines)) + 1))


def profile_alpha_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile_path in PROFILE_PATHS:
        profile = read_json(ROOT / profile_path)
        if not profile:
            rows.append(
                {
                    "source_id": profile_path.stem,
                    "source_type": "fus_sim_profile",
                    "locator": rel(ROOT / profile_path),
                    "alpha_value_or_range": "missing",
                    "alpha_power": "",
                    "unit_semantics": "profile_missing",
                    "classification": "missing",
                    "confidence": "none",
                    "pressure_use_status": "blocked",
                    "notes": "Profile file was not found.",
                }
            )
            continue
        alpha_value = profile.get("materials", {}).get("skull", {}).get("alpha_db_mhz_cm")
        alpha_power = ""
        mapping_type = profile.get("mapping_type")
        unit_semantics = "Stored as alpha_db_mhz_cm in fus-sim material profile."
        classification = "fus_sim_alpha_coeff_without_explicit_power"
        confidence = "low_medium"
        notes = "No alpha_power field is stored in the acoustic model NPZ."
        if mapping_type == "continuous_skull":
            cont = profile.get("continuous_mapping", {})
            alpha_value = cont.get("alpha_range_db_mhz_cm")
            unit_semantics = "Linear alpha range stored as dB/MHz/cm; no alpha_power in model output."
            classification = "linear_alpha_coeff_range_unverified"
        if mapping_type == "prestus_marsac_mueller":
            att = profile.get("source_backed_mapping", {}).get("attenuation", {})
            alpha_value = [
                att.get("alpha_min_db_cm_at_500khz"),
                att.get("alpha_max_db_cm_at_500khz"),
                "converted_to_alpha0",
            ]
            alpha_power = att.get("alpha_power")
            unit_semantics = att.get("output_unit_assumption", "")
            classification = "alpha_at_500khz_to_alpha0_draft"
            confidence = "medium_for_PRESTUS_logic_low_for_fus_sim_default"
            notes = att.get("unit_risk", "")
        rows.append(
            {
                "source_id": profile.get("profile_id", profile_path.stem),
                "source_type": "fus_sim_profile",
                "locator": rel(ROOT / profile_path),
                "alpha_value_or_range": json.dumps(alpha_value, ensure_ascii=False),
                "alpha_power": alpha_power,
                "unit_semantics": unit_semantics,
                "classification": classification,
                "confidence": confidence,
                "pressure_use_status": "blocked" if "draft" in str(profile.get("review_status", "")) or "review_pending" in str(profile.get("review_status", "")) else "usable_with_existing_caution",
                "notes": notes,
            }
        )
    return rows


def source_alpha_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in SOURCE_SNIPPETS:
        path = ROOT / item["path"]
        rows.append(
            {
                "source_id": item["source_id"],
                "source_type": "public_source_code",
                "locator": f"{rel(path)}:{item['start']}-{item['end']}",
                "alpha_value_or_range": extract_numbers(source_excerpt(path, item["start"], item["end"])),
                "alpha_power": extract_alpha_power(source_excerpt(path, item["start"], item["end"])),
                "unit_semantics": item["unit_semantics"],
                "classification": item["classification"],
                "confidence": item["confidence"],
                "pressure_use_status": "reference_only_requires_translation",
                "notes": source_excerpt(path, item["start"], item["end"])[:1200],
            }
        )
    return rows


def extract_numbers(text: str) -> str:
    nums = re.findall(r"[-+]?\d+(?:\.\d+)?", text)
    return ", ".join(nums[:20])


def extract_alpha_power(text: str) -> str:
    if "alpha_power" not in text and "Beta" not in text:
        return ""
    lines = [line.strip() for line in text.splitlines() if "alpha_power" in line or "Beta" in line]
    return " | ".join(lines[:5])


def local_output_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    paths = [
        Path("outputs/entry_path_property_profiles/079_candidate_006/entry_path_property_summary.json"),
        Path("outputs/ct_mapping_model_build_validation/prestus_marsac_mueller_079/model_build_validation.json"),
    ]
    for path in paths:
        data = read_json(ROOT / path)
        if not data:
            continue
        if "model_summaries" in data:
            for model, summary in data["model_summaries"].items():
                rows.append(
                    {
                        "source_id": f"{path.stem}_{model}",
                        "source_type": "fus_sim_output_summary",
                        "locator": rel(ROOT / path),
                        "alpha_value_or_range": json.dumps(summary.get("alpha_skull"), ensure_ascii=False),
                        "alpha_power": "",
                        "unit_semantics": "Observed path-level alpha_coeff values from model arrays; unit inherited from model profile, not independently validated.",
                        "classification": "observed_alpha_coeff_range",
                        "confidence": "range_high_unit_low",
                        "pressure_use_status": "diagnostic_only",
                        "notes": "Path profile values are not pressure results.",
                    }
                )
        if "candidate" in data:
            cand = data["candidate"]
            rows.append(
                {
                    "source_id": f"{path.stem}_candidate_model",
                    "source_type": "fus_sim_output_summary",
                    "locator": rel(ROOT / path),
                    "alpha_value_or_range": json.dumps(cand.get("alpha_skull"), ensure_ascii=False),
                    "alpha_power": "",
                    "unit_semantics": "Observed model-level skull alpha_coeff values from candidate model arrays.",
                    "classification": "observed_alpha_coeff_range",
                    "confidence": "range_high_unit_low",
                    "pressure_use_status": "diagnostic_only",
                    "notes": "Model-build validation only.",
                }
            )
    return rows


def make_report(data: dict[str, Any]) -> str:
    rows = data["matrix"]
    high_risk = [row for row in rows if "attenuation" in row["source_id"].lower() or "alpha" in row["classification"].lower()]
    bullets = "\n".join(
        f"- `{row['source_id']}` `{row['classification']}` confidence=`{row['confidence']}` status=`{row['pressure_use_status']}`"
        for row in high_risk[:20]
    )
    return f"""# Alpha Unit Audit Report

## 结论

当前不应使用 `prestus_marsac_mueller_draft` 进行 pressure simulation。理由是 attenuation 的数值来源已经比之前清楚，但单位语义还没有完全闭环到 fus-sim/k-Wave Python 的 `alpha_coeff` 和 `alpha_power` 输入。

当前状态：**blocked_for_pressure_until_alpha_semantics_resolved**。

## 核心发现

{bullets}

## 关键解释

- PRESTUS `mueller` route 先得到 500 kHz 下的 `alpha(f)`，再通过 `alpha(f) / 0.5^alpha_power` 转换为 `alpha0`。
- PRESTUS `k-plan` route 用固定 `alpha_coeff=13.3` 和 `alpha_power=1` 作为 k-Plan 复现目标。
- BabelBrain 的 porosity route 明确返回 `Np/m`；Webb route 还涉及 scanner/kernel 参数和 `*100`，不应直接混入 fus-sim profile。
- fus-sim 当前 CT model NPZ 只保存 `alpha_coeff`，没有保存 `alpha_power`，summary 也没有明确 alpha 是 `alpha(f)` 还是 `alpha0`。

## 对当前 draft profile 的影响

`prestus_marsac_mueller_draft` 的路径 alpha 约 `17.3`，这个值来自 Mueller-style 500 kHz alpha 转 alpha0 的草案。它可能是合理的 PRESTUS-style alpha0，也可能和当前 k-Wave Python 使用方式存在语义错配。没有完成审计前，不应跑 pressure。

## 下一步

1. 审查 `simulate_kwave_3d_focus.py` / `kWaveMedium` 是否传入 `alpha_power`，以及默认 alpha_power 是多少。
2. 如果需要支持 source-backed attenuation，CT 模型 summary/NPZ 应显式记录 `alpha_power` 或 profile-level alpha semantics。
3. 在 pressure 前先做 alpha-only profile normalization 设计，而不是继续调入射或跑 k-Wave。
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit attenuation unit semantics without running simulations.")
    parser.add_argument("--output-dir", default="outputs/alpha_unit_audit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = profile_alpha_rows() + source_alpha_rows() + local_output_rows()
    data = {
        "generated_at": now_iso(),
        "scope": "alpha unit audit only; no model rebuild and no k-Wave",
        "status": "blocked_for_pressure_until_alpha_semantics_resolved",
        "matrix": rows,
        "key_decisions": [
            "Do not run prestus_marsac_mueller_draft pressure simulation yet.",
            "Do not compare alpha values across sources without unit semantics.",
            "Add alpha_power/alpha semantics to model summary before source-backed pressure use.",
        ],
    }
    write_csv(out_dir / "alpha_unit_matrix.csv", rows)
    write_json(out_dir / "alpha_unit_matrix.json", rows)
    write_json(out_dir / "alpha_unit_audit_report.json", data)
    write_md(out_dir / "alpha_unit_audit_report.md", make_report(data))
    print(f"Wrote alpha unit audit to {rel(out_dir)}")


if __name__ == "__main__":
    main()
