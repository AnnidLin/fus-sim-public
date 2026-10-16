#!/usr/bin/env python3
"""Time-reversal (TR) vs baseline vs heuristic phase-correction comparison report.

Case 079 (+5, 0) thick-skull geometry, ap30/r35, 500 kHz, dx0.75, PML12, CFL0.2.

PURE ANALYSIS ONLY: this script reads existing summary JSON / NPZ artifacts and
writes a Markdown + JSON comparison report.  It NEVER imports or runs k-Wave.

Inputs (priority order):
  1. TR refocus  : outputs/time_reversal_079_y+5_z0/summary.json
                   (missing -> degraded report: "TR refocus 未完成", exit code 0;
                   the orchestrator re-runs this script after refocus completes)
  2. TR calibrate: outputs/time_reversal_079_y+5_z0/summary_calibrate.json
  3. Baseline    : outputs/thick_skull_candidate_runs/
                   079_offset_y+005_z+000_ap30_r35_dx0p75_pml12_standard_pressure_20260710/
                   summary.json   (tone-burst, no correction)
  4. Heuristic   : outputs/radius_matched_phase_control_079/
                   radius_matched_phase_control_report.json
                   (r74.435 + 15x15 acoustic-path-integral; falls back to the
                   AI_TODO.md item 2.7 second-hand record when the JSON is absent)

Outputs:
  outputs/time_reversal_comparison_20260717/time_reversal_comparison_report.md
  outputs/time_reversal_comparison_20260717/time_reversal_comparison.json

Exit codes: 0 = report written (including degraded TR-missing mode);
            2 = baseline input missing or output write failure.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import numpy as np
except ImportError:  # pragma: no cover - numpy is present in kwave312, degrade anyway
    np = None

PROJECT_ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Input paths
# ---------------------------------------------------------------------------
TR_DIR = PROJECT_ROOT / "outputs" / "time_reversal_079_y+5_z0"
TR_REFOCUS_SUMMARY = TR_DIR / "summary.json"
TR_CALIBRATE_SUMMARY = TR_DIR / "summary_calibrate.json"
TR_NPZ = TR_DIR / "pressure_max_mpa.npz"

BASELINE_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "thick_skull_candidate_runs"
    / "079_offset_y+005_z+000_ap30_r35_dx0p75_pml12_standard_pressure_20260710"
)
BASELINE_SUMMARY = BASELINE_DIR / "summary.json"
BASELINE_NPZ = BASELINE_DIR / "pressure_max_mpa.npz"

HEURISTIC_JSON = (
    PROJECT_ROOT
    / "outputs"
    / "radius_matched_phase_control_079"
    / "radius_matched_phase_control_report.json"
)
AI_TODO_MD = PROJECT_ROOT / "AI_TODO.md"
TR_EVIDENCE_BRIEF = PROJECT_ROOT / "outputs" / "evidence_briefs" / "time_reversal_a3" / "evidence_brief.md"

OUT_DIR = PROJECT_ROOT / "outputs" / "time_reversal_comparison_20260717"
OUT_MD = OUT_DIR / "time_reversal_comparison_report.md"
OUT_JSON = OUT_DIR / "time_reversal_comparison.json"

MATERIAL_LABEL_NAMES = {0: "background (label 0)", 1: "soft_tissue (label 1)", 2: "skull (label 2)"}
SKULL_LABEL = 2

NORMALIZATION_CAVEAT = (
    "TR refocus 回放信号已按 max(abs) = 1 MPa 归一化（normalize_source=true, "
    "source_pressure_pa=1e6）。TR 的绝对 MPa 与 tone-burst baseline 的绝对 MPa "
    "驱动机制不同（点源标定 + 全场时间反转回放 vs 8-cycle tone-burst 正向辐射），"
    "**不可直接比较绝对幅值**。本报告的跨方法结论仅基于缩放不变量：峰值位置、"
    "target/global 比值、峰值间距、材料归属与波束轴几何。绝对 MPa 列仅作同方法"
    "内部参考。"
)

CONCLUSION_DISCIPLINE = (
    "本报告全部结论为 **engineering 观察级别**（engineering_validation_not_full_"
    "reproduction）。不构成临床安全、热安全、MItc 合规、paper-grade 收敛或 "
    "profile promotion 结论；禁止据此做任何安全外推。"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def rel(path: Path) -> str:
    """Repo-relative POSIX path for traceability in the report."""
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def fmt_mpa(value: float | None) -> str:
    return "—" if value is None else f"{value:.4f}"


def fmt_ratio(value: float | None) -> str:
    return "—" if value is None else f"{value:.4f}"


def fmt_mm(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def fmt_ijk(idx) -> str:
    if idx is None:
        return "—"
    return "[" + ", ".join(str(int(v)) for v in idx) + "]"


def extract_focus_metrics(pressure: dict | None) -> dict:
    """Normalize a compute_focus_metrics pressure block (semantics v2.0.0)."""
    pressure = pressure or {}
    keys = [
        "target_window_peak_mpa",
        "target_window_peak_index_ijk",
        "global_peak_mpa",
        "global_peak_index_ijk",
        "global_peak_to_target_distance_mm",
        "target_to_global_peak_ratio",
        "effective_peak_mpa",
        "effective_peak_index_ijk",
        "effective_peak_to_target_distance_mm",
        "beam_axis_effective_peak_mpa",
        "beam_axis_effective_peak_to_target_distance_mm",
        "beam_axis_effective_peak_axial_from_source_mm",
        "beam_axis_effective_peak_lateral_offset_mm",
        "target_window_peak_axial_shortfall_to_target_mm",
        "metric_semantics_version",
    ]
    return {k: pressure.get(k) for k in keys}


def analyze_npz(npz_path: Path, pressure_metrics: dict) -> dict:
    """Material-label analysis from pressure_max_mpa.npz (skull hotspot etc.)."""
    result = {
        "npz_path": rel(npz_path),
        "available": False,
        "note": None,
        "skull_peak_mpa": None,
        "global_peak_material": None,
        "target_window_peak_material": None,
    }
    if np is None:
        result["note"] = "numpy 不可用，跳过 NPZ 材料分析"
        return result
    if not npz_path.exists():
        result["note"] = "pressure_max_mpa.npz 不存在，跳过材料分析"
        return result
    try:
        data = np.load(npz_path)
        pressure = np.asarray(data["pressure_max_mpa"], dtype=np.float64)
        labels = np.asarray(data["labels"])
    except Exception as exc:  # noqa: BLE001 - report must never crash on IO
        result["note"] = f"NPZ 读取失败: {exc}"
        return result
    if pressure.shape != labels.shape or not np.any(labels == SKULL_LABEL):
        result["note"] = "labels 缺失或不含 skull (label 2)，无法做颅骨热点分析"
        return result
    result["available"] = True
    result["skull_peak_mpa"] = float(np.max(pressure[labels == SKULL_LABEL]))

    def _material_at(idx) -> str | None:
        if idx is None:
            return None
        ijk = tuple(int(v) for v in idx)
        if any(v < 0 or v >= labels.shape[d] for d, v in enumerate(ijk)):
            return None
        return MATERIAL_LABEL_NAMES.get(int(labels[ijk]), f"unknown ({int(labels[ijk])})")

    result["global_peak_material"] = _material_at(pressure_metrics.get("global_peak_index_ijk"))
    result["target_window_peak_material"] = _material_at(pressure_metrics.get("target_window_peak_index_ijk"))
    return result


def find_ai_todo_record() -> dict:
    """Locate the AI_TODO.md item 2.7 second-hand record (line number + text)."""
    record = {"path": rel(AI_TODO_MD), "line_number": None, "text": None}
    if not AI_TODO_MD.exists():
        return record
    try:
        lines = AI_TODO_MD.read_text(encoding="utf-8").splitlines()
    except OSError:
        return record
    for i, line in enumerate(lines, start=1):
        if "19.67" in line and "2.7" in line:
            record["line_number"] = i
            record["text"] = line.strip()
            break
    if record["line_number"] is None:
        for i, line in enumerate(lines, start=1):
            if "19.67" in line:
                record["line_number"] = i
                record["text"] = line.strip()
                break
    return record


def extract_heuristic() -> dict:
    """Heuristic r74.435 + 15x15 path-integral phase-correction results."""
    out = {
        "status": "missing",
        "source_kind": None,
        "source_path": None,
        "candidate": None,
        "configuration": None,
        "reference": None,
        "candidate_result": None,
        "relative_result": None,
        "acceptance": None,
        "ai_todo_record": None,
    }
    data = load_json(HEURISTIC_JSON)
    if data is not None:
        out.update(
            status="primary_json",
            source_kind="一手 JSON（apodization recovery / radius-matched phase-control 报告）",
            source_path=rel(HEURISTIC_JSON),
            candidate=data.get("candidate"),
            configuration=data.get("configuration"),
            reference=data.get("reference"),
            candidate_result=data.get("candidate_result"),
            relative_result=data.get("relative_result"),
            acceptance=data.get("acceptance"),
        )
        return out
    todo = find_ai_todo_record()
    out["ai_todo_record"] = todo
    if todo.get("line_number") is not None:
        out.update(
            status="secondhand_ai_todo",
            source_kind="二手记载（AI_TODO.md 2.7 行，未找到精确 JSON）",
            source_path=f"{todo['path']}:L{todo['line_number']}",
        )
    return out


def config_alignment(baseline_cfg: dict, tr_cfg: dict | None) -> list[dict]:
    """Check geometry/numerics alignment between baseline and TR configs."""
    if not tr_cfg:
        return []
    rows = []
    checks = [
        ("model_path", "声学模型"),
        ("entry_plan_path", "entry plan"),
        ("frequency_hz", "频率"),
        ("transducer_radius_m", "换能器曲率半径"),
        ("aperture_diameter_m", "孔径"),
        ("cfl", "CFL"),
        ("pml_size", "PML"),
        ("quick_mode", "quick 裁剪"),
        ("quick_lateral_half_width_m", "quick 横向半宽"),
        ("quick_post_target_margin_m", "quick 目标后余量"),
        ("nearfield_exclusion_m", "近场排除"),
        ("alpha_power", "alpha_power"),
    ]
    for key, label in checks:
        b, t = baseline_cfg.get(key), tr_cfg.get(key)
        if b is None and t is None:
            continue
        b_s = None if b is None else str(b).replace(str(PROJECT_ROOT), "").replace(PROJECT_ROOT.as_posix(), "")
        t_s = None if t is None else str(t).replace(str(PROJECT_ROOT), "").replace(PROJECT_ROOT.as_posix(), "")
        rows.append({"parameter": label, "baseline": b_s, "tr": t_s, "aligned": b == t})
    rows.append(
        {
            "parameter": "tone_burst_cycles",
            "baseline": str(baseline_cfg.get("tone_burst_cycles")),
            "tr": str(tr_cfg.get("tone_burst_cycles")),
            "aligned": baseline_cfg.get("tone_burst_cycles") == tr_cfg.get("tone_burst_cycles"),
        }
    )
    return rows


# ---------------------------------------------------------------------------
# Judgments (only when TR refocus is available)
# ---------------------------------------------------------------------------
def build_judgments(baseline: dict, tr: dict) -> dict:
    b_m, t_m = baseline["metrics"], tr["metrics"]
    b_npz, t_npz = baseline["npz"], tr["npz"]

    j: dict = {}

    # 1) Did TR move the global peak from skull toward the target?
    b_dist = b_m.get("global_peak_to_target_distance_mm")
    t_dist = t_m.get("global_peak_to_target_distance_mm")
    b_mat = b_npz.get("global_peak_material")
    t_mat = t_npz.get("global_peak_material")
    moved = None
    if t_dist is not None and b_dist is not None:
        dist_reduced = t_dist < b_dist
        left_skull = t_mat is not None and "skull" not in str(t_mat) and (b_mat is None or "skull" in str(b_mat))
        if left_skull and dist_reduced:
            moved = "是：全局峰已离开颅骨材料且距目标更近"
        elif dist_reduced:
            moved = "部分：全局峰距目标更近，但材料归属未变或未知"
        elif left_skull:
            moved = "部分：全局峰已离开颅骨材料，但距离未缩短"
        else:
            moved = "否：全局峰位置未明显改善"
    j["global_peak_moved_from_skull_toward_target"] = {
        "verdict": moved,
        "baseline_global_peak_to_target_mm": b_dist,
        "tr_global_peak_to_target_mm": t_dist,
        "baseline_global_peak_material": b_mat,
        "tr_global_peak_material": t_mat,
    }

    # 2) target/global improvement factor vs baseline (scale-invariant)
    b_r = b_m.get("target_to_global_peak_ratio")
    t_r = t_m.get("target_to_global_peak_ratio")
    factor = None
    if b_r and t_r is not None:
        factor = t_r / b_r
    j["target_global_improvement_factor_vs_baseline"] = {
        "baseline_ratio": b_r,
        "tr_ratio": t_r,
        "improvement_factor": factor,
    }

    # 3) Does the skull hotspot still exceed the focus?
    skull = t_npz.get("skull_peak_mpa")
    focus = t_m.get("target_window_peak_mpa")
    exceeds = None
    if skull is not None and focus is not None:
        exceeds = bool(skull > focus)
    j["skull_hotspot_still_exceeds_focus"] = {
        "verdict": None if exceeds is None else ("是：颅骨热点仍超过焦点" if exceeds else "否：焦点不低于颅骨热点"),
        "tr_skull_peak_mpa": skull,
        "tr_target_window_peak_mpa": focus,
        "note": "同一 TR 场内部比较，归一化不影响该判定" if exceeds is not None else "TR NPZ labels 不可用，无法判定",
    }

    # Baseline skull context for the same question
    b_skull = b_npz.get("skull_peak_mpa")
    b_focus = b_m.get("target_window_peak_mpa")
    j["baseline_skull_hotspot_exceeds_focus"] = {
        "baseline_skull_peak_mpa": b_skull,
        "baseline_target_window_peak_mpa": b_focus,
        "exceeds": None if (b_skull is None or b_focus is None) else bool(b_skull > b_focus),
    }
    return j


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------
def render_report(ctx: dict) -> str:
    L: list[str] = []
    a = L.append

    a("# Case 079 (+5,0) 厚颅骨聚焦校正对比报告：baseline vs 启发式相位校正 vs 全波形时间反转（TR）")
    a("")
    a(f"- 生成时间（UTC）：{ctx['generated_at_utc']}")
    a(f"- 生成器：`{rel(Path(__file__))}`（纯分析脚本，未运行任何 k-Wave 仿真）")
    a("- 几何/数值配置：Case 079 entry offset (+5, 0) mm，ap30/r35，500 kHz，dx 0.75 mm，PML12，CFL0.2")
    a("- 度量语义：`compute_focus_metrics`，`metric_semantics_version = 2.0.0`（target-window 半径 3 格点；effective/beam-axis 峰均含 10 mm 近场排除）")
    a("")

    a("## ⚠️ 归一化声明（阅读本报告前必读）")
    a("")
    a(f"> {NORMALIZATION_CAVEAT}")
    a("")

    a("## 输入状态")
    a("")
    st = ctx["input_status"]
    a("| 输入 | 状态 | 路径 |")
    a("| --- | --- | --- |")
    a(f"| TR refocus summary | {st['tr_refocus']} | `{rel(TR_REFOCUS_SUMMARY)}` |")
    a(f"| TR calibrate summary | {st['tr_calibrate']} | `{rel(TR_CALIBRATE_SUMMARY)}` |")
    a(f"| 无校正 baseline summary | {st['baseline']} | `{rel(BASELINE_SUMMARY)}` |")
    a(f"| 启发式相位校正 | {st['heuristic']} | `{ctx['heuristic']['source_path'] or '—'}` |")
    a("")
    if st["tr_refocus"] != "已加载":
        a("> **降级模式：TR refocus 未完成。** 本报告当前仅输出 baseline 与启发式校正部分；"
          "TR 列与判定节在 refocus 完成、重跑本脚本后自动生成。")
        a("")

    # --- comparison table -------------------------------------------------
    a("## 对比表（核心指标）")
    a("")
    b_m = ctx["baseline"]["metrics"]
    h = ctx["heuristic"]
    h_c = (h.get("candidate_result") or {})
    t_m = (ctx["time_reversal"] or {}).get("metrics") or {}
    tr_missing = ctx["time_reversal"] is None

    def trv(key, fmt):
        if tr_missing:
            return "待 TR refocus"
        return fmt(t_m.get(key))

    a("| 指标 | 无校正 baseline | 启发式相位校正（r74.435 + 15×15 path-integral） | TR 全波形时间反转 |")
    a("| --- | --- | --- | --- |")
    a(f"| target_window_peak (MPa) | {fmt_mpa(b_m.get('target_window_peak_mpa'))} | "
      f"{fmt_mpa(h_c.get('target_window_mpa'))} | {trv('target_window_peak_mpa', fmt_mpa)} |")
    a(f"| global_peak (MPa) | {fmt_mpa(b_m.get('global_peak_mpa'))} | "
      f"{fmt_mpa(h_c.get('global_mpa'))} | {trv('global_peak_mpa', fmt_mpa)} |")
    a(f"| target/global 比值 | {fmt_ratio(b_m.get('target_to_global_peak_ratio'))} | "
      f"{fmt_ratio(h_c.get('target_to_global'))} | {trv('target_to_global_peak_ratio', fmt_ratio)} |")
    a(f"| effective peak 距目标 (mm) | {fmt_mm(b_m.get('effective_peak_to_target_distance_mm'))} | "
      f"—（报告未含；仅有 beam-axis 值） | {trv('effective_peak_to_target_distance_mm', fmt_mm)} |")
    a(f"| 全局峰距目标 (mm) | {fmt_mm(b_m.get('global_peak_to_target_distance_mm'))} | "
      f"—（报告未含） | {trv('global_peak_to_target_distance_mm', fmt_mm)} |")
    a(f"| beam-axis effective peak 距目标 (mm) | {fmt_mm(b_m.get('beam_axis_effective_peak_to_target_distance_mm'))} | "
      f"{fmt_mm(h_c.get('beam_axis_effective_peak_to_target_distance_mm'))} | "
      f"{trv('beam_axis_effective_peak_to_target_distance_mm', fmt_mm)} |")
    a(f"| beam-axis effective peak 轴向位置 (mm, 自源心) | {fmt_mm(b_m.get('beam_axis_effective_peak_axial_from_source_mm'))} | "
      f"— | {trv('beam_axis_effective_peak_axial_from_source_mm', fmt_mm)} |")
    a(f"| beam-axis effective peak 横向偏移 (mm) | {fmt_mm(b_m.get('beam_axis_effective_peak_lateral_offset_mm'))} | "
      f"— | {trv('beam_axis_effective_peak_lateral_offset_mm', fmt_mm)} |")
    a(f"| target-window 峰距目标 (mm) | {fmt_mm(b_m.get('target_window_peak_axial_shortfall_to_target_mm'))}（轴向短欠） | "
      f"{fmt_mm(h_c.get('target_window_peak_to_target_distance_mm'))}（欧氏） | "
      f"{trv('target_window_peak_axial_shortfall_to_target_mm', fmt_mm)}（轴向短欠） |")
    b_npz, t_npz = ctx["baseline"]["npz"], (ctx["time_reversal"] or {}).get("npz") or {}
    a(f"| 全局峰材料归属 | {b_npz.get('global_peak_material') or '—'} | "
      f"skull (label 2)（报告记载） | "
      f"{'待 TR refocus' if tr_missing else (t_npz.get('global_peak_material') or '—')} |")
    a(f"| 颅骨区峰值 (MPa, NPZ labels==2) | {fmt_mpa(b_npz.get('skull_peak_mpa'))} | "
      f"—（NPZ 未随报告发布） | "
      f"{'待 TR refocus' if tr_missing else fmt_mpa(t_npz.get('skull_peak_mpa'))} |")
    a("| metric 语义版本 | " + str(b_m.get("metric_semantics_version") or "—") + " | "
      "报告自带口径（见注） | " + ("待 TR refocus" if tr_missing else str(t_m.get("metric_semantics_version") or "—")) + " |")
    a("")
    a("**列来源**：baseline 列 ← `" + rel(BASELINE_SUMMARY) + "`（pressure 块）与 `" + rel(BASELINE_NPZ) + "`；")
    a("启发式列 ← `" + (h["source_path"] or "—") + "`（candidate_result 块）；")
    a("TR 列 ← `" + rel(TR_REFOCUS_SUMMARY) + "`（pressure 块）与 `" + rel(TR_NPZ) + "`。")
    a("")
    a("**口径注意**：启发式校正列来自 `preset=quick`、曲率半径 r74.435 mm（radius-matched）的源阵列运行，"
      "与 baseline/TR 的 r35 / standard 几何**不完全同配置**；其百分比改善是相对其自带 r74.435 单碗参考 "
      f"（target_window {fmt_mpa((h.get('reference') or {}).get('target_window_mpa'))} MPa，"
      f"global {fmt_mpa((h.get('reference') or {}).get('global_mpa'))} MPa，"
      f"target/global {fmt_ratio((h.get('reference') or {}).get('target_to_global'))}），"
      "不是相对本表 baseline 列。跨列比较应集中在比值与位置类缩放不变量上。")
    a("")

    # --- heuristic block --------------------------------------------------
    a("## 启发式相位校正（历史结果）")
    a("")
    if h["status"] == "primary_json":
        rr = h.get("relative_result") or {}
        acc = h.get("acceptance") or {}
        cfg = h.get("configuration") or {}
        a(f"- 候选：`{h.get('candidate')}`；preset={cfg.get('preset')}，阵列 {cfg.get('array_elements')}，"
          f"活跃 patch {cfg.get('active_patches')}，相位模型 `{cfg.get('phase_model')}`，半径 {cfg.get('radius_mm')} mm。")
        a(f"- 颅骨热点降低：{rr.get('global_reduction_percent', 0.0):.2f}%（门控 ≥20%："
          f"{'通过' if acc.get('global_reduction_at_least_20_percent_pass') else '未过'}）")
        a(f"- 目标保留：{(rr.get('target_window_retention') or 0.0) * 100:.2f}%（门控 ≥80%："
          f"{'通过' if acc.get('target_window_retention_at_least_80_percent_pass') else '未过'}）")
        a(f"- target/global 改善：{rr.get('target_global_improvement_percent', 0.0):.2f}%（门控 ≥25%："
          f"{'通过' if acc.get('target_global_improvement_at_least_25_percent_pass') else '未过'}）")
        a(f"- 综合门控：**未通过**（overall_pass={acc.get('overall_pass')}）；原报告决策：reject and stop，"
          "quick engineering negative screen，不授权后续参数点。")
        a(f"- 来源（一手 JSON）：`{h['source_path']}`")
    elif h["status"] == "secondhand_ai_todo":
        rec = h["ai_todo_record"]
        a(f"- **二手记载**（未找到精确 JSON）：`{rec['path']}` L{rec['line_number']}（AI_TODO 2.7）：")
        a(f"  > {rec['text']}")
        a("- 要点：r74.435 + 15×15 path-integral 校正后热点降 19.67%、目标保留 93.90%，未过 20%/25% 门控。")
    else:
        a("- 未找到启发式校正的一手 JSON，也未能在 AI_TODO.md 定位 19.67% 记载；本节留空。")
    a("")

    # --- TR sections ------------------------------------------------------
    a("## TR 全波形时间反转")
    a("")
    cal = ctx["tr_calibrate"]
    if cal is not None:
        stats = cal.get("calibration_signal_stats") or {}
        a("### Calibrate 段（点源标定）")
        a("")
        a(f"- 记录点数（碗面 mask）：{stats.get('n_points', '—')}；nt_recorded={stats.get('nt_recorded', '—')}；"
          f"dt={stats.get('dt_s', 0.0):.3e} s；时长 {stats.get('duration_us', 0.0):.2f} µs")
        a(f"- 信号统计：max_abs={stats.get('max_abs_pa', 0.0):.4e} Pa，max={stats.get('max_pa', 0.0):.4e} Pa，"
          f"min={stats.get('min_pa', 0.0):.4e} Pa，rms={stats.get('rms_pa', 0.0):.4e} Pa")
        a(f"- 来源：`{rel(TR_CALIBRATE_SUMMARY)}`")
        a("")
    else:
        a("### Calibrate 段")
        a("")
        a(f"- 未找到 `{rel(TR_CALIBRATE_SUMMARY)}`（calibrate 未完成或未写出）。")
        a("")

    if tr_missing:
        a("### Refocus 段")
        a("")
        a("- **TR refocus 未完成**：`" + rel(TR_REFOCUS_SUMMARY) + "` 不存在。"
          "refocus 完成后重跑本脚本即可补齐 TR 列、判定节与结论。")
        a("")
    else:
        tr = ctx["time_reversal"]
        tr_meta = tr["summary"].get("time_reversal") or {}
        align = tr["summary"].get("time_alignment") or {}
        a("### Refocus 段（时间反转回放）")
        a("")
        a(f"- 归一化：normalize_source={tr_meta.get('normalize_source')}；记录信号 max_abs="
          f"{tr_meta.get('recorded_max_abs_pa', 0.0):.4e} Pa → 回放 max_abs={tr_meta.get('replay_max_abs_pa', 0.0):.4e} Pa；"
          f"scale_factor={tr_meta.get('scale_factor', 0.0):.4e}（归一化目标 1 MPa）。")
        a(f"- 时间对齐：nt_recorded={tr_meta.get('nt_recorded')}，预期聚焦时刻 "
          f"{tr_meta.get('expected_focus_time_us', 0.0):.2f} µs；策略 `{align.get('policy')}`，"
          f"nt_final={align.get('nt_final')}，尾部零填充 {align.get('replay_zero_padding_samples')} 采样。")
        a(f"- mask 一致性校验：`{tr_meta.get('mask_consistency_check')}`")
        a("")

        a("### 配置对齐检查（baseline vs TR）")
        a("")
        rows = ctx["config_alignment"]
        if rows:
            a("| 参数 | baseline | TR | 一致 |")
            a("| --- | --- | --- | --- |")
            for r in rows:
                a(f"| {r['parameter']} | {r['baseline']} | {r['tr']} | {'✅' if r['aligned'] else '⚠️ 不同'} |")
            a("")
            a("注：tone_burst_cycles 不同属预期（TR calibrate 用短脉冲标定，baseline 用 8-cycle tone-burst 驱动）；"
              "其余几何/数值参数应对齐。")
            a("")

        a("### 判定")
        a("")
        j = ctx["judgments"]
        j1 = j["global_peak_moved_from_skull_toward_target"]
        a(f"1. **TR 是否把全局峰从颅骨移向目标？** {j1['verdict'] or '数据不足，无法判定'}。"
          f"（baseline 全局峰距目标 {fmt_mm(j1['baseline_global_peak_to_target_mm'])} mm、材料 {j1['baseline_global_peak_material'] or '—'}；"
          f"TR 全局峰距目标 {fmt_mm(j1['tr_global_peak_to_target_mm'])} mm、材料 {j1['tr_global_peak_material'] or '—'}）")
        j2 = j["target_global_improvement_factor_vs_baseline"]
        factor_txt = "—" if j2["improvement_factor"] is None else f"{j2['improvement_factor']:.2f}×"
        a(f"2. **target/global 相对 baseline 提升倍数**：{factor_txt}"
          f"（baseline {fmt_ratio(j2['baseline_ratio'])} → TR {fmt_ratio(j2['tr_ratio'])}；比值为缩放不变量，"
          "不受 TR 归一化影响）。")
        j3 = j["skull_hotspot_still_exceeds_focus"]
        a(f"3. **颅骨热点是否仍超过焦点？** {j3['verdict'] or '数据不足，无法判定'}"
          f"（TR 颅骨区峰值 {fmt_mpa(j3['tr_skull_peak_mpa'])} MPa vs target-window 峰 {fmt_mpa(j3['tr_target_window_peak_mpa'])} MPa，"
          "同场内部比较）。")
        j0 = j["baseline_skull_hotspot_exceeds_focus"]
        if j0["exceeds"] is not None:
            a(f"   - 对照 baseline：颅骨区峰值 {fmt_mpa(j0['baseline_skull_peak_mpa'])} MPa vs target-window "
              f"{fmt_mpa(j0['baseline_target_window_peak_mpa'])} MPa → "
              f"{'颅骨热点超过焦点' if j0['exceeds'] else '焦点不低于颅骨热点'}。")
        a("")

    # --- conclusion -------------------------------------------------------
    a("## 结论（engineering 观察级别）")
    a("")
    if tr_missing:
        a("- TR refocus 尚未完成，本报告暂不下 TR 相关结论。")
        a(f"- 既有事实（baseline，`{rel(BASELINE_SUMMARY)}`）：target-window 峰 "
          f"{fmt_mpa(b_m.get('target_window_peak_mpa'))} MPa，全局（颅骨）峰 {fmt_mpa(b_m.get('global_peak_mpa'))} MPa，"
          f"target/global {fmt_ratio(b_m.get('target_to_global_peak_ratio'))}，"
          f"全局峰距目标 {fmt_mm(b_m.get('global_peak_to_target_distance_mm'))} mm——无校正时聚焦目标失败。")
        if h["status"] == "primary_json":
            rr = h.get("relative_result") or {}
            a(f"- 启发式相位校正历史结果（`{h['source_path']}`）：热点降 {rr.get('global_reduction_percent', 0.0):.2f}%、"
              f"目标保留 {(rr.get('target_window_retention') or 0.0) * 100:.2f}%、target/global 改善 "
              f"{rr.get('target_global_improvement_percent', 0.0):.2f}%，未过 20%/25% 预注册门控（quick 级负向筛查）。")
        a("- 待 TR refocus 完成并重跑本脚本后，将给出「TR 是否把全局峰从颅骨移向目标」「target/global 提升倍数」"
          "「颅骨热点是否仍超过焦点」三项判定。")
    else:
        j = ctx["judgments"]
        j1 = j["global_peak_moved_from_skull_toward_target"]
        j2 = j["target_global_improvement_factor_vs_baseline"]
        j3 = j["skull_hotspot_still_exceeds_focus"]
        a(f"- 全局峰迁移：{j1['verdict'] or '无法判定'}。")
        factor_txt = "—" if j2["improvement_factor"] is None else f"{j2['improvement_factor']:.2f}×"
        a(f"- target/global：baseline {fmt_ratio(j2['baseline_ratio'])} → TR {fmt_ratio(j2['tr_ratio'])}，"
          f"提升 {factor_txt}。")
        a(f"- 颅骨热点 vs 焦点：{j3['verdict'] or '无法判定'}。")
        a("- 与启发式校正的历史门控结果并读，可估计启发式方法与 TR 参考方法之间的距离；"
          "注意启发式列配置（r74.435/quick）与本报告 baseline/TR 列（r35/standard）不同，比较限于缩放不变量。")
    a("")
    a(f"> {CONCLUSION_DISCIPLINE}")
    a("")

    # --- sources ----------------------------------------------------------
    a("## 数据来源清单")
    a("")
    a("| # | 路径 | 用途 | 状态 |")
    a("| --- | --- | --- | --- |")
    for i, s in enumerate(ctx["data_sources"], start=1):
        a(f"| {i} | `{s['path']}` | {s['used_for']} | {s['status']} |")
    a("")

    a("## 已知限制")
    a("")
    for item in ctx["limitations"]:
        a(f"- {item}")
    a("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    baseline_summary = load_json(BASELINE_SUMMARY)
    tr_summary = load_json(TR_REFOCUS_SUMMARY)
    cal_summary = load_json(TR_CALIBRATE_SUMMARY)
    heuristic = extract_heuristic()

    limitations: list[str] = [
        "TR 绝对 MPa 经 max(abs)=1 MPa 归一化，不可与 tone-burst baseline 绝对幅值直接比较；跨方法结论仅用缩放不变量。",
        "启发式校正列为 r74.435/quick preset 配置，与 baseline/TR 的 r35/standard 几何不同配置；其百分比相对其自带 r74.435 单碗参考。",
        "对比基于单次实现（single realization），无网格收敛/参数敏感性支撑；不构成 paper-grade 证据。",
        "NPZ 材料归属分析依赖 pressure_max_mpa.npz 内 labels（0=background, 1=soft_tissue, 2=skull）；labels 缺失时相关判定降级为「无法判定」。",
    ]

    if baseline_summary is None:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        msg = (
            "# TR 对比报告生成失败\n\n"
            f"baseline 输入缺失或不可解析：`{rel(BASELINE_SUMMARY)}`。\n"
            "无 baseline 则对比无意义，脚本以退出码 2 结束。\n"
        )
        OUT_MD.write_text(msg, encoding="utf-8")
        OUT_JSON.write_text(
            json.dumps({"error": "baseline_missing", "path": rel(BASELINE_SUMMARY)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"ERROR: baseline summary missing: {BASELINE_SUMMARY}", file=sys.stderr)
        return 2

    baseline_metrics = extract_focus_metrics(baseline_summary.get("pressure"))
    baseline_npz = analyze_npz(BASELINE_NPZ, baseline_metrics)
    if not baseline_npz["available"]:
        limitations.append(f"baseline NPZ 材料分析不可用：{baseline_npz['note']}。")

    if heuristic["status"] == "secondhand_ai_todo":
        limitations.append("启发式校正数值来自 AI_TODO.md 2.7 二手记载，未经一手 JSON 复核。")
    elif heuristic["status"] == "missing":
        limitations.append("启发式校正数据完全缺失（一手 JSON 与 AI_TODO 记载均未找到）。")

    time_reversal_ctx = None
    judgments = None
    config_rows: list[dict] = []
    if tr_summary is not None:
        tr_metrics = extract_focus_metrics(tr_summary.get("pressure"))
        tr_npz = analyze_npz(TR_NPZ, tr_metrics)
        if not tr_npz["available"]:
            limitations.append(f"TR NPZ 材料分析不可用：{tr_npz['note']}。")
        time_reversal_ctx = {"summary": tr_summary, "metrics": tr_metrics, "npz": tr_npz}
        judgments = build_judgments(
            {"metrics": baseline_metrics, "npz": baseline_npz},
            {"metrics": tr_metrics, "npz": tr_npz},
        )
        config_rows = config_alignment(
            baseline_summary.get("config") or {}, tr_summary.get("config") or {}
        )
    else:
        limitations.append("TR refocus summary.json 尚不存在：当前为降级报告，仅含 baseline 与启发式部分（退出码 0）。")

    input_status = {
        "tr_refocus": "已加载" if tr_summary is not None else "缺失（TR refocus 未完成）",
        "tr_calibrate": "已加载" if cal_summary is not None else "缺失",
        "baseline": "已加载",
        "heuristic": {
            "primary_json": "已加载（一手 JSON）",
            "secondhand_ai_todo": "二手记载（AI_TODO.md 2.7）",
            "missing": "缺失",
        }[heuristic["status"]],
    }

    data_sources = [
        {"path": rel(TR_REFOCUS_SUMMARY), "used_for": "TR refocus 焦点指标（pressure 块）、归一化因子、nt 对齐",
         "status": "已读取" if tr_summary is not None else "缺失"},
        {"path": rel(TR_CALIBRATE_SUMMARY), "used_for": "TR calibrate 信号统计（n_points/max_abs/rms/dt/nt）",
         "status": "已读取" if cal_summary is not None else "缺失"},
        {"path": rel(TR_NPZ), "used_for": "TR 全场压力 + labels：全局峰材料归属、颅骨区峰值",
         "status": "已读取" if (time_reversal_ctx and time_reversal_ctx["npz"]["available"]) else "缺失/不可用"},
        {"path": rel(BASELINE_SUMMARY), "used_for": "无校正 baseline 焦点指标（pressure 块，semantics v2.0.0）", "status": "已读取"},
        {"path": rel(BASELINE_NPZ), "used_for": "baseline 全场压力 + labels：全局峰材料归属、颅骨区峰值",
         "status": "已读取" if baseline_npz["available"] else "不可用"},
        {"path": heuristic["source_path"] or rel(HEURISTIC_JSON),
         "used_for": "启发式 r74.435 + 15×15 path-integral 校正结果（热点 −19.67%、目标保留 93.90%、门控判定）",
         "status": input_status["heuristic"]},
        {"path": rel(AI_TODO_MD) + " L79（item 2.7）", "used_for": "启发式结果的治理记载/门控状态交叉印证", "status": "参考"},
        {"path": rel(TR_EVIDENCE_BRIEF), "used_for": "TR 实验设计背景与结论级别声明（A.3 evidence brief）",
         "status": "已读取" if TR_EVIDENCE_BRIEF.exists() else "缺失"},
    ]

    ctx = {
        "generated_at_utc": generated_at,
        "input_status": input_status,
        "baseline": {"metrics": baseline_metrics, "npz": baseline_npz},
        "heuristic": heuristic,
        "tr_calibrate": cal_summary,
        "time_reversal": time_reversal_ctx,
        "judgments": judgments,
        "config_alignment": config_rows,
        "data_sources": data_sources,
        "limitations": limitations,
    }

    report_md = render_report(ctx)

    # JSON mirror (numbers traceable; no numpy types)
    json_out = {
        "generated_at_utc": generated_at,
        "generator": rel(Path(__file__)),
        "case": "079 (+5,0) thick-skull, ap30/r35, 500 kHz, dx0.75, PML12, CFL0.2",
        "metric_semantics_version": "2.0.0",
        "normalization_caveat": NORMALIZATION_CAVEAT,
        "conclusion_discipline": CONCLUSION_DISCIPLINE,
        "input_status": input_status,
        "degraded_mode": tr_summary is None,
        "baseline": {
            "source": rel(BASELINE_SUMMARY),
            "metrics": baseline_metrics,
            "npz_analysis": baseline_npz,
        },
        "heuristic_phase_correction": heuristic,
        "tr_calibrate": None
        if cal_summary is None
        else {"source": rel(TR_CALIBRATE_SUMMARY), "calibration_signal_stats": cal_summary.get("calibration_signal_stats")},
        "time_reversal": None
        if time_reversal_ctx is None
        else {
            "source": rel(TR_REFOCUS_SUMMARY),
            "metrics": time_reversal_ctx["metrics"],
            "npz_analysis": time_reversal_ctx["npz"],
            "time_reversal_meta": time_reversal_ctx["summary"].get("time_reversal"),
            "time_alignment": time_reversal_ctx["summary"].get("time_alignment"),
        },
        "config_alignment": config_rows,
        "judgments": judgments,
        "data_sources": data_sources,
        "limitations": limitations,
    }

    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        OUT_MD.write_text(report_md, encoding="utf-8")
        OUT_JSON.write_text(json.dumps(json_out, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: failed to write outputs: {exc}", file=sys.stderr)
        return 2

    mode = "DEGRADED (TR refocus 未完成)" if tr_summary is None else "FULL"
    print(f"[{mode}] report: {OUT_MD}")
    print(f"[{mode}] json:    {OUT_JSON}")
    print(f"baseline: target_window={baseline_metrics.get('target_window_peak_mpa')} MPa, "
          f"global={baseline_metrics.get('global_peak_mpa')} MPa, "
          f"ratio={baseline_metrics.get('target_to_global_peak_ratio')}")
    if heuristic["status"] == "primary_json":
        rr = heuristic.get("relative_result") or {}
        print(f"heuristic: hotspot_reduction={rr.get('global_reduction_percent'):.2f}%, "
              f"target_retention={(rr.get('target_window_retention') or 0.0) * 100:.2f}%")
    if judgments is not None:
        j2 = judgments["target_global_improvement_factor_vs_baseline"]
        print(f"TR target/global improvement factor: {j2['improvement_factor']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
