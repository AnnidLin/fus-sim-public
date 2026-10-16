#!/usr/bin/env python3
"""D60 R78.330 dx0.75 free-field baseline — PML16 / CFL0.1 parameter sensitivity report.

Case: D60 R78.330 dx0.75 corrected free-field baseline (PML12/CFL0.2, kwave_ok 4757 s,
Gate B `gate_b_dx075_dx05_pass`).  Two sensitivity variants run with the same script
(simulate_source_array_focus_point_waveform.py), same entry plan
(outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_plan_20260714/entry_plan.json),
PML-outside mode (npz grids expected identical in shape to the baseline):

  - baseline : outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pointwave_20260714/run
  - PML16    : outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_pml16_pointwave_20260717/run
  - CFL0.1   : outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_cfl0p1_pointwave_20260717/run

PURE ANALYSIS ONLY: reads existing summary.json / runner_status.json / pressure_max_mpa.npz
artifacts and writes a Markdown + JSON report.  NEVER imports or runs k-Wave.

Metric semantics match the Gate B report
(outputs/freefield_aperture_calibration/d60_grid_convergence_corrected_20260716/
d60_grid_convergence_report.json): focus error / refined focus error / -6 dB widths /
focal displacement are recomputed from the NPZ fields with the SAME implementation
(`field_metrics` imported from generate_d60_grid_convergence_report.py, trilinear
subvoxel refinement, continuous half-peak widths at 0.25 voxel spacing).

Graceful degradation: a variant with missing summary.json is marked 未完成 and its
comparison is skipped; exit code stays 0 (the orchestrator re-runs this script after
the runs finish).  With all variants missing a baseline-only summary is still written.

Exit codes: 0 = report written (including degraded modes); 2 = baseline missing or
output write failure.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import numpy as np
except ImportError:  # pragma: no cover - numpy is present in kwave312, degrade anyway
    np = None

# Gate-B-identical metric computation (pure analysis: numpy/scipy only, no k-Wave).
try:
    from generate_d60_grid_convergence_report import field_metrics as gate_b_field_metrics
except Exception as exc:  # noqa: BLE001 - degrade to summary-only metrics
    gate_b_field_metrics = None
    _FIELD_METRICS_IMPORT_ERROR = exc
else:
    _FIELD_METRICS_IMPORT_ERROR = None

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
FF_ROOT = PROJECT_ROOT / "outputs" / "freefield_aperture_calibration"
BASELINE_RUN = FF_ROOT / "d60_r78p330_dx0p75_pointwave_20260714" / "run"
PML16_RUN = FF_ROOT / "d60_r78p330_dx0p75_pml16_pointwave_20260717" / "run"
CFL01_RUN = FF_ROOT / "d60_r78p330_dx0p75_cfl0p1_pointwave_20260717" / "run"
GATE_B_REPORT_JSON = FF_ROOT / "d60_grid_convergence_corrected_20260716" / "d60_grid_convergence_report.json"
ENTRY_PLAN = FF_ROOT / "d60_r78p330_dx0p75_plan_20260714" / "entry_plan.json"

OUT_DIR = PROJECT_ROOT / "outputs" / "d60_pml_cfl_sensitivity_20260717"
OUT_MD = OUT_DIR / "d60_pml_cfl_sensitivity_report.md"
OUT_JSON = OUT_DIR / "d60_pml_cfl_sensitivity.json"

VARIANTS = [
    {"key": "pml16", "label": "PML16 变体", "run_dir": PML16_RUN, "changed_param": "pml_size 12 → 16"},
    {"key": "cfl0p1", "label": "CFL0.1 变体", "run_dir": CFL01_RUN, "changed_param": "cfl 0.2 → 0.1"},
]

# Judgment thresholds (task-specified, Gate-B acceptance style)
THRESH_PEAK_CHANGE_PERCENT = 1.0       # stricter than Gate B grid gate (5%)
THRESH_WIDTH_CHANGE_PERCENT = 10.0     # Gate B lateral gate; cf. dx0.5 axial change 8.889%
THRESH_FOCUS_ERROR_DELTA_PP = 0.5      # absolute percentage-point change (refined)
FOCAL_DISPLACEMENT_GATE_MM = 1.0       # informational only (Gate B grid gate value)

CONCLUSION_DISCIPLINE = (
    "本报告全部结论为 **sensitivity observation（参数敏感性观察）级别**：仅刻画 PML 厚度与 "
    "CFL 数对 D60 R78.330 dx0.75 自由场基线数值结果的影响。不构成网格收敛性证明、不构成 "
    "paper-grade 声明、不授权 CT 压力外推（CT pressure remains unauthorized）、不构成任何"
    "临床安全或热安全结论。"
)

PML_BOUNDARY_NOTE = (
    "PML16 变体采用 PML-outside 模式：PML 厚度位于模型网格之外，不改变模型网格形状，"
    "因此全局峰在**模型网格上**的 boundary distance（global_boundary_distance_voxels）"
    "不随 PML 厚度变化；两 run 该值应完全一致（本报告将其列为一致性核对项而非敏感性指标）。"
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
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def fmt(value: float | None, nd: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:.{nd}f}"
    return str(value)


def fmt_sci(value: float | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:.4e}"
    return str(value)


def pct_change(variant: float | None, base: float | None) -> float | None:
    if variant is None or base is None or base == 0:
        return None
    return 100.0 * abs(variant - base) / abs(base)


def load_run(run_dir: Path, label: str) -> dict:
    """Load one run: summary.json presence gates availability; metrics Gate-B recomputed."""
    rec: dict = {
        "label": label,
        "run_dir": rel(run_dir),
        "status": "missing",
        "runner_status": None,
        "runtime_s": None,
        "config": None,
        "summary_metrics": None,
        "gate_b_metrics": None,
        "gate_b_metrics_error": None,
        "waveform_stats": None,
        "npz_path": rel(run_dir / "pressure_max_mpa.npz"),
    }
    summary = load_json(run_dir / "summary.json")
    if summary is None:
        return rec
    rec["status"] = "loaded"
    rec["config"] = summary.get("config") or {}
    pressure = summary.get("pressure") or {}
    rec["summary_metrics"] = {
        "global_peak_mpa": pressure.get("global_peak_mpa"),
        "global_peak_index_ijk": pressure.get("global_peak_index_ijk"),
        "target_pressure_mpa": pressure.get("target_pressure_mpa"),
        "target_window_peak_mpa": pressure.get("target_window_peak_mpa"),
        "target_window_peak_index_ijk": pressure.get("target_window_peak_index_ijk"),
        "target_to_global_peak_ratio": pressure.get("target_to_global_peak_ratio"),
        "global_peak_axial_from_source_mm": pressure.get("global_peak_axial_from_source_mm"),
        "global_peak_lateral_offset_mm": pressure.get("global_peak_lateral_offset_mm"),
        "metric_semantics_version": pressure.get("metric_semantics_version"),
    }
    rec["waveform_stats"] = summary.get("target_waveform_stats")
    runner = load_json(run_dir / "runner_status.json")
    if runner is not None:
        rec["runner_status"] = runner.get("status")
        rec["runtime_s"] = (runner.get("execution") or {}).get("runtime_s")
    if gate_b_field_metrics is not None and np is not None:
        try:
            rec["gate_b_metrics"] = gate_b_field_metrics(run_dir)
        except Exception as exc:  # noqa: BLE001 - npz missing/corrupt -> summary-only
            rec["gate_b_metrics_error"] = f"{type(exc).__name__}: {exc}"
    else:
        rec["gate_b_metrics_error"] = (
            f"field_metrics 导入失败: {_FIELD_METRICS_IMPORT_ERROR}" if gate_b_field_metrics is None else "numpy 不可用"
        )
    return rec


def to_jsonable(obj):
    """Recursively convert numpy scalars/arrays so json.dumps never fails."""
    if np is not None:
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return [to_jsonable(v) for v in obj.tolist()]
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    return obj


def field_diff(base_dir: Path, variant_dir: Path, base_peak: float | None) -> dict:
    """Voxel-wise field diff (grids expected identical shape, PML-outside mode)."""
    out = {
        "available": False,
        "note": None,
        "shape": None,
        "max_abs_delta_mpa": None,
        "max_abs_delta_over_baseline_peak": None,
        "p99_abs_delta_mpa": None,
        "max_delta_index_ijk": None,
    }
    if np is None:
        out["note"] = "numpy 不可用"
        return out
    b_path, v_path = base_dir / "pressure_max_mpa.npz", variant_dir / "pressure_max_mpa.npz"
    if not b_path.exists() or not v_path.exists():
        out["note"] = "pressure_max_mpa.npz 缺失（baseline 或变体）"
        return out
    try:
        with np.load(b_path) as b_data:
            base = np.asarray(b_data["pressure_max_mpa"], dtype=np.float64)
        with np.load(v_path) as v_data:
            var = np.asarray(v_data["pressure_max_mpa"], dtype=np.float64)
    except Exception as exc:  # noqa: BLE001
        out["note"] = f"NPZ 读取失败: {exc}"
        return out
    if base.shape != var.shape:
        out["note"] = f"网格形状不一致: baseline {base.shape} vs 变体 {var.shape}，跳过逐体素 diff"
        return out
    delta = np.abs(var - base)
    peak = float(base.max()) if base_peak is None else float(base_peak)
    flat_idx = int(np.argmax(delta))
    out.update(
        available=True,
        shape=[int(v) for v in base.shape],
        max_abs_delta_mpa=float(delta.max()),
        max_abs_delta_over_baseline_peak=(float(delta.max()) / peak if peak else None),
        p99_abs_delta_mpa=float(np.percentile(delta, 99)),
        max_delta_index_ijk=[int(v) for v in np.unravel_index(flat_idx, delta.shape)],
    )
    return out


def config_diff(base_cfg: dict, var_cfg: dict) -> list[dict]:
    rows = []
    for key in sorted(set(base_cfg) | set(var_cfg)):
        b, v = base_cfg.get(key), var_cfg.get(key)
        if b != v:
            b_s, v_s = str(b), str(v)
            for anchor in (str(PROJECT_ROOT), PROJECT_ROOT.as_posix()):
                b_s, v_s = b_s.replace(anchor, ""), v_s.replace(anchor, "")
            rows.append({"parameter": key, "baseline": b_s, "variant": v_s})
    return rows


def judge_variant(base: dict, var: dict) -> dict:
    """Gate-B-acceptance-style sensitivity judgment for one variant."""
    b_g, v_g = base.get("gate_b_metrics") or {}, var.get("gate_b_metrics") or {}
    j: dict = {"gates": {}, "verdict": None, "note": None}

    b_peak = (base["summary_metrics"] or {}).get("global_peak_mpa")
    v_peak = (var["summary_metrics"] or {}).get("global_peak_mpa")
    peak_change = pct_change(v_peak, b_peak)
    j["gates"]["peak_change"] = {
        "baseline_mpa": b_peak, "variant_mpa": v_peak,
        "change_percent": peak_change, "threshold_percent": THRESH_PEAK_CHANGE_PERCENT,
        "pass": None if peak_change is None else peak_change < THRESH_PEAK_CHANGE_PERCENT,
    }

    b_lat, v_lat = b_g.get("minus6db_lateral_equivalent_mm"), v_g.get("minus6db_lateral_equivalent_mm")
    b_ax, v_ax = b_g.get("minus6db_axial_width_mm"), v_g.get("minus6db_axial_width_mm")
    lat_change, ax_change = pct_change(v_lat, b_lat), pct_change(v_ax, b_ax)
    lat_pass = None if lat_change is None else lat_change < THRESH_WIDTH_CHANGE_PERCENT
    ax_pass = None if ax_change is None else ax_change < THRESH_WIDTH_CHANGE_PERCENT
    j["gates"]["width_change"] = {
        "lateral_equivalent": {"baseline_mm": b_lat, "variant_mm": v_lat,
                               "change_percent": lat_change, "pass": lat_pass},
        "axial": {"baseline_mm": b_ax, "variant_mm": v_ax,
                  "change_percent": ax_change, "pass": ax_pass},
        "threshold_percent": THRESH_WIDTH_CHANGE_PERCENT,
        "pass": None if (lat_pass is None or ax_pass is None) else bool(lat_pass and ax_pass),
    }

    b_fe, v_fe = b_g.get("refined_focus_error_percent"), v_g.get("refined_focus_error_percent")
    fe_delta = None if (b_fe is None or v_fe is None) else abs(v_fe - b_fe)
    b_fe_u, v_fe_u = b_g.get("focus_error_percent"), v_g.get("focus_error_percent")
    fe_delta_u = None if (b_fe_u is None or v_fe_u is None) else abs(v_fe_u - b_fe_u)
    j["gates"]["focus_error_change"] = {
        "baseline_refined_percent": b_fe, "variant_refined_percent": v_fe,
        "delta_percentage_points": fe_delta,
        "delta_percentage_points_unrefined": fe_delta_u,
        "threshold_percentage_points": THRESH_FOCUS_ERROR_DELTA_PP,
        "pass": None if fe_delta is None else fe_delta < THRESH_FOCUS_ERROR_DELTA_PP,
    }

    b_pk, v_pk = b_g.get("refined_peak_relative_to_source_mm"), v_g.get("refined_peak_relative_to_source_mm")
    displacement = None
    if b_pk is not None and v_pk is not None and np is not None:
        displacement = float(np.linalg.norm(np.asarray(v_pk, dtype=float) - np.asarray(b_pk, dtype=float)))
    j["focal_displacement_mm"] = displacement

    b_bd, v_bd = b_g.get("global_boundary_distance_voxels"), v_g.get("global_boundary_distance_voxels")
    j["boundary_distance_consistency"] = {
        "baseline_voxels": b_bd, "variant_voxels": v_bd,
        "consistent": None if (b_bd is None or v_bd is None) else bool(b_bd == v_bd),
        "note": "PML-outside 模式下 PML 厚度不改变模型网格上的 boundary distance（一致性核对，非门控）",
    }

    gate_vals = [g.get("pass") for g in j["gates"].values()]
    if any(v is None for v in gate_vals):
        j["verdict"] = "data_incomplete"
        j["note"] = "部分指标不可用（NPZ/复算缺失），无法完成全部门控"
    elif all(gate_vals):
        j["verdict"] = "sensitivity_pass"
    else:
        j["verdict"] = "sensitivity_flag"
    return j


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------
def render(ctx: dict) -> str:
    L: list[str] = []
    a = L.append
    base = ctx["baseline"]
    b_s = base["summary_metrics"] or {}
    b_g = base.get("gate_b_metrics") or {}
    b_w = base.get("waveform_stats") or {}

    a("# D60 R78.330 dx0.75 自由场基线 — PML16 / CFL0.1 参数敏感性对比报告")
    a("")
    a(f"- 生成时间（UTC）：{ctx['generated_at_utc']}")
    a(f"- 生成器：`{rel(Path(__file__))}`（纯分析脚本，未运行任何 k-Wave 仿真）")
    a("- 对象：D60 R78.330 dx0.75 corrected 自由场基线（PML12/CFL0.2，kwave_ok，已过 Gate B `gate_b_dx075_dx05_pass`）及其 PML16、CFL0.1 变体")
    a(f"- 同一 entry plan：`{rel(ENTRY_PLAN)}`；PML-outside 模式，NPZ 网格预期同形同尺寸")
    a("- 指标语义：与 Gate B 报告同集（`field_metrics` 同源复算：trilinear 亚体素精化、0.25 体素步长连续半峰宽；summary 直取字段另注）")
    a("")

    a("## ⚠️ 结论级别声明（阅读本报告前必读）")
    a("")
    a(f"> {CONCLUSION_DISCIPLINE}")
    a("")

    a("## 输入状态")
    a("")
    a("| 输入 | 状态 | 路径 |")
    a("| --- | --- | --- |")
    a(f"| 基线（PML12/CFL0.2）summary | 已加载 | `{rel(BASELINE_RUN / 'summary.json')}` |")
    for v in ctx["variants"]:
        st = "已加载" if v["status"] == "loaded" else "缺失（未完成）"
        a(f"| {v['label']} summary | {st} | `{v['run_dir']}/summary.json` |")
    a("")
    missing = [v for v in ctx["variants"] if v["status"] != "loaded"]
    if missing:
        names = "、".join(v["label"] for v in missing)
        a(f"> **降级模式：{names}未完成。** 相应对比列与判定已跳过；运行完成后重跑本脚本自动补齐（退出码保持 0）。")
        a("")

    # --- metrics table -----------------------------------------------------
    a("## 指标对比表（Gate B 同集语义）")
    a("")
    cols = ctx["variants"]
    a("| 指标 | 基线（PML12/CFL0.2） | " + " | ".join(v["label"] for v in cols) + " | 来源 |")
    a("| --- | --- | " + " | ".join("---" for _ in cols) + " | --- |")

    def row(name, getter, nd=4, sci=False, source="summary"):
        f = (lambda x: fmt_sci(x)) if sci else (lambda x: fmt(x, nd))
        cells = [f(getter(base))]
        for v in cols:
            cells.append("未完成" if v["status"] != "loaded" else f(getter(v)))
        a(f"| {name} | " + " | ".join(cells) + f" | {source} |")

    def s_get(key):
        return lambda r: ((r["summary_metrics"] or {}).get(key))

    def g_get(key):
        return lambda r: ((r.get("gate_b_metrics") or {}).get(key))

    def c_get(key):
        return lambda r: ((r.get("config") or {}).get(key))

    def w_get(key):
        return lambda r: ((r.get("waveform_stats") or {}).get(key))

    row("runner_status", lambda r: r.get("runner_status"), source="runner_status.json")
    row("runtime (s)", lambda r: r.get("runtime_s"), nd=1, source="runner_status.json")
    row("pml_size（变化参数）", c_get("pml_size"), nd=0, source="summary config")
    row("cfl（变化参数）", c_get("cfl"), nd=2, source="summary config")
    row("global_peak_mpa", s_get("global_peak_mpa"), source="summary pressure")
    row("target_pressure_mpa", s_get("target_pressure_mpa"), source="summary pressure")
    row("target_window_peak_mpa", s_get("target_window_peak_mpa"), source="summary pressure")
    row("target_to_global_peak_ratio", s_get("target_to_global_peak_ratio"), nd=5, source="summary pressure")
    row("focus_error (mm)", g_get("focus_error_mm"), nd=4, source="复算 (npz)")
    row("focus_error (%)", g_get("focus_error_percent"), nd=4, source="复算 (npz)")
    row("refined focus_error (mm)", g_get("refined_focus_error_mm"), nd=4, source="复算 (npz)")
    row("refined focus_error (%)", g_get("refined_focus_error_percent"), nd=4, source="复算 (npz)")
    row("−6 dB lateral width 1 (mm)", g_get("minus6db_lateral_width_1_mm"), nd=4, source="复算 (npz)")
    row("−6 dB lateral width 2 (mm)", g_get("minus6db_lateral_width_2_mm"), nd=4, source="复算 (npz)")
    row("−6 dB lateral equivalent (mm)", g_get("minus6db_lateral_equivalent_mm"), nd=4, source="复算 (npz)")
    row("−6 dB axial width (mm)", g_get("minus6db_axial_width_mm"), nd=4, source="复算 (npz)")
    row("focal displacement vs 基线 (mm)", lambda r: 0.0 if r is base else (r.get("judgment") or {}).get("focal_displacement_mm"), nd=4, source="复算 (npz)")
    row("global_boundary_distance_voxels", g_get("global_boundary_distance_voxels"), nd=0, source="复算 (npz)")
    row("waveform length (samples)", w_get("length"), nd=0, source="summary waveform")
    row("waveform max (Pa)", w_get("max_pa"), sci=True, source="summary waveform")
    row("waveform min (Pa)", w_get("min_pa"), sci=True, source="summary waveform")
    row("waveform rms (Pa)", w_get("rms_pa"), sci=True, source="summary waveform")
    a("")
    a("**来源列说明**：`summary` = 各 run `summary.json` 的 `pressure` / `target_waveform_stats` / `config` 块直取"
      "（`metric_semantics_version = " + str(b_s.get("metric_semantics_version")) + "`）；"
      "`复算` = 用 Gate B 报告同源实现（`generate_d60_grid_convergence_report.field_metrics`，"
      "trilinear 亚体素精化 + 0.25 体素步长连续半峰宽）从 `pressure_max_mpa.npz` 重新计算；"
      "focus error、−6 dB 宽度、focal displacement、boundary distance 不存于 summary.json，均为复算值。")
    a("")

    # --- field diff --------------------------------------------------------
    a("## 场值逐体素 diff（变体 − 基线，同形网格）")
    a("")
    any_diff = False
    a("| 变体 | max\\|Δp\\| (MPa) | max\\|Δp\\| / 基线峰 | 99 百分位 \\|Δp\\| (MPa) | max\\|Δp\\| 位置 (ijk) |")
    a("| --- | --- | --- | --- | --- |")
    for v in cols:
        d = v.get("field_diff") or {}
        if v["status"] != "loaded":
            a(f"| {v['label']} | 未完成 | — | — | — |")
        elif not d.get("available"):
            a(f"| {v['label']} | 不可用：{d.get('note')} | — | — | — |")
        else:
            any_diff = True
            ratio = d.get("max_abs_delta_over_baseline_peak")
            a(f"| {v['label']} | {fmt(d.get('max_abs_delta_mpa'), 6)} | "
              f"{('—' if ratio is None else f'{100.0 * ratio:.4f}%')} | "
              f"{fmt(d.get('p99_abs_delta_mpa'), 6)} | {d.get('max_delta_index_ijk')} |")
    a("")
    if not any_diff and all(v["status"] != "loaded" for v in cols):
        a("> 当前无可用变体，diff 表将在变体完成后自动填充。")
        a("")

    # --- judgments ---------------------------------------------------------
    a("## 判定（Gate B acceptance 风格）")
    a("")
    a("### 判定阈值表")
    a("")
    a("| 判定项 | 阈值 | 参照 |")
    a("| --- | --- | --- |")
    a(f"| global peak 变化 | < {THRESH_PEAK_CHANGE_PERCENT}% | 任务指定（严于 Gate B 网格门的 5%） |")
    a(f"| −6 dB 宽度变化（lateral equivalent 与 axial 分别判定） | < {THRESH_WIDTH_CHANGE_PERCENT}% | Gate B lateral 门 10%；dx0.5 gate 实测 axial 变化 8.889% 量级 |")
    a(f"| refined focus error 变化 | 绝对值 < {THRESH_FOCUS_ERROR_DELTA_PP} 个百分点 | 任务指定 |")
    a(f"| focal displacement | 记录项，不设门控 | Gate B 网格收敛门为 ≤ {FOCAL_DISPLACEMENT_GATE_MM} mm |")
    a("")
    for v in cols:
        a(f"### {v['label']}（{v['changed_param']}）")
        a("")
        if v["status"] != "loaded":
            a("- 未完成：summary.json 缺失，判定跳过。")
            a("")
            continue
        j = v.get("judgment") or {}
        gates = j.get("gates") or {}
        pc = gates.get("peak_change") or {}
        wc = gates.get("width_change") or {}
        fe = gates.get("focus_error_change") or {}
        bd = j.get("boundary_distance_consistency") or {}

        def mark(p):
            return {True: "✅ pass", False: "❌ fail", None: "— 数据不足"}[p]

        a(f"- peak change：{fmt(pc.get('change_percent'), 4)}%（门 {THRESH_PEAK_CHANGE_PERCENT}%）→ {mark(pc.get('pass'))}")
        lat, ax = wc.get("lateral_equivalent") or {}, wc.get("axial") or {}
        a(f"- width change：lateral {fmt(lat.get('change_percent'), 4)}% / axial {fmt(ax.get('change_percent'), 4)}%"
          f"（门 {THRESH_WIDTH_CHANGE_PERCENT}%）→ {mark(wc.get('pass'))}")
        a(f"- refined focus error 变化：{fmt(fe.get('delta_percentage_points'), 4)} 个百分点"
          f"（门 {THRESH_FOCUS_ERROR_DELTA_PP} pp；未 refined 变化 {fmt(fe.get('delta_percentage_points_unrefined'), 4)} pp，参考）"
          f"→ {mark(fe.get('pass'))}")
        a(f"- focal displacement：{fmt(j.get('focal_displacement_mm'), 4)} mm（记录项）")
        a(f"- boundary distance 一致性：baseline {bd.get('baseline_voxels')} vs 变体 {bd.get('variant_voxels')} 体素"
          f"（{'一致' if bd.get('consistent') else '不一致/未知'}；PML 不改变模型网格上的 boundary distance）")
        verdict = j.get("verdict")
        verdict_txt = {"sensitivity_pass": "**sensitivity_pass**",
                       "sensitivity_flag": "**sensitivity_flag**",
                       "data_incomplete": "**data_incomplete**（部分指标缺失）"}.get(verdict, "—")
        a(f"- **结论：{verdict_txt}**（sensitivity observation，非收敛性/paper-grade 声明）")
        a("")
        cd = v.get("config_diff") or []
        if cd:
            a("- config 差异（预期仅变化参数与时间步相关项）：")
            for r in cd:
                a(f"  - `{r['parameter']}`: 基线 {r['baseline']} → 变体 {r['variant']}")
            a("")

    a("## PML 与 boundary distance 注记")
    a("")
    a(f"> {PML_BOUNDARY_NOTE}")
    a("")

    a("## 结论（sensitivity observation 级别）")
    a("")
    a(f"- 基线（`{rel(BASELINE_RUN / 'summary.json')}`，复算自同目录 NPZ）：global peak "
      f"{fmt(b_s.get('global_peak_mpa'))} MPa，target/global {fmt(b_s.get('target_to_global_peak_ratio'), 5)}，"
      f"refined focus error {fmt(b_g.get('refined_focus_error_percent'))}%（{fmt(b_g.get('refined_focus_error_mm'))} mm），"
      f"−6 dB lateral {fmt(b_g.get('minus6db_lateral_equivalent_mm'), 3)} mm / axial {fmt(b_g.get('minus6db_axial_width_mm'), 3)} mm。")
    for v in cols:
        if v["status"] != "loaded":
            a(f"- {v['label']}：未完成，无判定。")
        else:
            j = v.get("judgment") or {}
            a(f"- {v['label']}（{v['changed_param']}）：{j.get('verdict')}；"
              f"peak 变化 {fmt(((j.get('gates') or {}).get('peak_change') or {}).get('change_percent'), 4)}%，"
              f"focal displacement {fmt(j.get('focal_displacement_mm'), 4)} mm。")
    a("")
    a(f"> {CONCLUSION_DISCIPLINE}")
    a("")

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

    limitations: list[str] = [
        "敏感性观察基于单次实现（single realization）对比，不构成网格收敛性证明；Gate B 的 dx0.375 更深层收敛仍未运行。",
        "focus error / −6 dB 宽度 / focal displacement / boundary distance 不存在于 summary.json，系用 Gate B 同源实现从 NPZ 复算；summary.json 直取字段已在报告标注。",
        "百分比变化的参考基准为本报告基线列（PML12/CFL0.2），与 Gate B 报告以 dx0.5 为参考不同。",
        "CFL0.1 变体 dt 减半、nt 加倍，target waveform 长度/统计与基线不直接等长可比（采样密度不同）。",
        "场值 diff 依赖两 run NPZ 同形（PML-outside 模式预期成立）；形状不一致时自动跳过并标注。",
    ]
    if gate_b_field_metrics is None:
        limitations.append(f"Gate B field_metrics 导入失败（{_FIELD_METRICS_IMPORT_ERROR}），复算指标整体缺失，仅剩 summary 直取字段。")

    baseline = load_run(BASELINE_RUN, "基线（PML12/CFL0.2）")
    if baseline["status"] != "loaded":
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        msg = (
            "# D60 PML/CFL 敏感性报告生成失败\n\n"
            f"基线输入缺失或不可解析：`{rel(BASELINE_RUN / 'summary.json')}`。\n"
            "无基线则敏感性对比无意义，脚本以退出码 2 结束。\n"
        )
        OUT_MD.write_text(msg, encoding="utf-8")
        OUT_JSON.write_text(
            json.dumps({"error": "baseline_missing", "path": rel(BASELINE_RUN / "summary.json")},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"ERROR: baseline summary missing: {BASELINE_RUN / 'summary.json'}", file=sys.stderr)
        return 2
    if baseline.get("gate_b_metrics_error"):
        limitations.append(f"基线复算指标不可用：{baseline['gate_b_metrics_error']}。")

    variants: list[dict] = []
    for spec in VARIANTS:
        rec = load_run(spec["run_dir"], spec["label"])
        rec["key"] = spec["key"]
        rec["changed_param"] = spec["changed_param"]
        if rec["status"] == "loaded":
            if rec.get("gate_b_metrics_error"):
                limitations.append(f"{spec['label']}复算指标不可用：{rec['gate_b_metrics_error']}。")
            rec["judgment"] = judge_variant(baseline, rec)
            rec["field_diff"] = field_diff(
                BASELINE_RUN, spec["run_dir"],
                ((baseline.get("gate_b_metrics") or {}).get("global_peak_mpa")
                 or (baseline["summary_metrics"] or {}).get("global_peak_mpa")),
            )
            rec["config_diff"] = config_diff(baseline.get("config") or {}, rec.get("config") or {})
        variants.append(rec)

    data_sources = [
        {"path": rel(BASELINE_RUN / "summary.json"), "used_for": "基线 pressure/config/target_waveform_stats 直取", "status": "已读取"},
        {"path": rel(BASELINE_RUN / "pressure_max_mpa.npz"), "used_for": "基线 Gate-B 同源复算（focus error/−6 dB/精化峰/boundary）", "status": "已读取" if baseline.get("gate_b_metrics") else "不可用"},
        {"path": rel(BASELINE_RUN / "runner_status.json"), "used_for": "基线 runner 状态与 runtime", "status": "已读取" if baseline.get("runner_status") else "缺失"},
        {"path": rel(GATE_B_REPORT_JSON), "used_for": "指标语义与 acceptance 风格基准（gate_b_dx075_dx05_pass）",
         "status": "已读取" if GATE_B_REPORT_JSON.exists() else "缺失"},
        {"path": rel(ENTRY_PLAN), "used_for": "三 run 共用 entry plan（一致性前提）", "status": "已读取" if ENTRY_PLAN.exists() else "缺失"},
    ]
    for v in variants:
        data_sources.append({"path": f"{v['run_dir']}/summary.json", "used_for": f"{v['label']} pressure/config/waveform 直取",
                             "status": "已读取" if v["status"] == "loaded" else "缺失（未完成）"})
        data_sources.append({"path": f"{v['run_dir']}/pressure_max_mpa.npz", "used_for": f"{v['label']} 复算指标与场值 diff",
                             "status": ("已读取" if v.get("gate_b_metrics") else "缺失/不可用") if v["status"] == "loaded" else "缺失（未完成）"})

    ctx = {
        "generated_at_utc": generated_at,
        "baseline": baseline,
        "variants": variants,
        "data_sources": data_sources,
        "limitations": limitations,
    }
    report_md = render(ctx)

    json_out = {
        "generated_at_utc": generated_at,
        "generator": rel(Path(__file__)),
        "case": "D60 R78.330 dx0.75 free-field baseline (PML12/CFL0.2, gate_b_dx075_dx05_pass) PML16/CFL0.1 sensitivity",
        "metric_semantics": {
            "focus_error/widths/displacement": "Gate-B-identical recomputation via generate_d60_grid_convergence_report.field_metrics (trilinear subvoxel refinement, 0.25-voxel continuous half-peak widths)",
            "percent_change_reference": "absolute change divided by THIS report's baseline (PML12/CFL0.2) value",
            "conclusion_level": "sensitivity_observation_only",
        },
        "thresholds": {
            "peak_change_percent": THRESH_PEAK_CHANGE_PERCENT,
            "width_change_percent": THRESH_WIDTH_CHANGE_PERCENT,
            "focus_error_delta_percentage_points": THRESH_FOCUS_ERROR_DELTA_PP,
            "focal_displacement_gate_mm_informational": FOCAL_DISPLACEMENT_GATE_MM,
        },
        "conclusion_discipline": CONCLUSION_DISCIPLINE,
        "pml_boundary_note": PML_BOUNDARY_NOTE,
        "baseline": baseline,
        "variants": [
            {k: v[k] for k in ("key", "label", "run_dir", "status", "runner_status", "runtime_s",
                               "changed_param", "summary_metrics", "gate_b_metrics",
                               "gate_b_metrics_error", "waveform_stats", "config_diff",
                               "field_diff", "judgment") if k in v}
            for v in variants
        ],
        "degraded_mode": any(v["status"] != "loaded" for v in variants),
        "data_sources": data_sources,
        "limitations": limitations,
    }

    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        OUT_MD.write_text(report_md, encoding="utf-8")
        OUT_JSON.write_text(json.dumps(to_jsonable(json_out), ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: failed to write outputs: {exc}", file=sys.stderr)
        return 2

    loaded = [v["label"] for v in variants if v["status"] == "loaded"]
    missing = [v["label"] for v in variants if v["status"] != "loaded"]
    mode = "FULL" if not missing else f"DEGRADED ({'、'.join(missing)}未完成)"
    print(f"[{mode}] report: {OUT_MD}")
    print(f"[{mode}] json:    {OUT_JSON}")
    b_s = baseline["summary_metrics"] or {}
    print(f"baseline: global_peak={b_s.get('global_peak_mpa')} MPa, "
          f"target/global={b_s.get('target_to_global_peak_ratio')}")
    if loaded:
        print(f"loaded variants: {loaded}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
