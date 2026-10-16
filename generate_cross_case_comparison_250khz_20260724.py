"""250 kHz cross-case comparison: NLM 72m vs Case 079, baseline vs TR.

Reads the 250 kHz quick baselines (2026-07-24) and tonight's 250 kHz TR runs,
with 500 kHz counterparts as frequency reference. Screening-level engineering
observation only; no dose/safety claims.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "outputs" / "cross_case_comparison_250khz_20260724"

RUNS = {
    "nlm_250_quick": "outputs/nlm_kwave_quick_250khz_20260724/focus_metrics.json",
    "nlm_250_tr": "outputs/nlm_tr_72m_250khz_20260724/focus_metrics.json",
    "case079_250_quick": "outputs/case079_kwave_quick_250khz_20260724/focus_metrics.json",
    "case079_250_tr": "outputs/case079_tr_250khz_20260724/focus_metrics.json",
    "nlm_500_quick": "outputs/nlm_kwave_quick_20260724/focus_metrics.json",
    "nlm_500_tr": "outputs/nlm_tr_72m_20260724/focus_metrics.json",
    "case079_500_tr": "outputs/time_reversal_079_y+5_z0/focus_metrics.json",
}

KEYS = ("global_peak_mpa", "target_window_peak_mpa", "target_to_global_peak_ratio")


def load_metrics(rel: str) -> dict | None:
    path = PROJECT_ROOT / rel
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    flat: dict = {}

    def walk(d: dict, pre: str = "") -> None:
        for k, v in d.items():
            if isinstance(v, dict):
                walk(v, pre + k + ".")
            elif isinstance(v, (int, float)):
                flat[pre + k] = float(v)

    walk(data)
    return {k: flat.get(k) for k in KEYS if k in flat}


def pair_delta(base: dict, tr: dict) -> dict:
    out = {}
    for k in KEYS:
        b, t = base.get(k), tr.get(k)
        if b is None or t is None:
            continue
        out[k] = {"baseline": b, "tr": t, "ratio": (t / b) if b else None}
    return out


def main() -> None:
    metrics = {name: load_metrics(rel) for name, rel in RUNS.items()}
    missing = [name for name, m in metrics.items() if m is None]

    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "250 kHz cross-case (NLM 72m, Case 079) baseline vs time-reversal comparison",
        "claim_policy": "screening-level engineering observation only; no dose/safety claims",
        "missing_inputs": missing,
        "metrics": metrics,
        "comparisons": {},
    }

    for case, b_key, t_key in (
        ("nlm_72m_250khz", "nlm_250_quick", "nlm_250_tr"),
        ("case079_250khz", "case079_250_quick", "case079_250_tr"),
        ("nlm_72m_500khz", "nlm_500_quick", "nlm_500_tr"),
    ):
        b, t = metrics.get(b_key), metrics.get(t_key)
        if b and t:
            result["comparisons"][case] = pair_delta(b, t)

    freq = {}
    for case, q250, q500 in (
        ("nlm_72m", "nlm_250_quick", "nlm_500_quick"),
    ):
        a, b = metrics.get(q250), metrics.get(q500)
        if a and b:
            freq[case] = {
                "t_g_250khz": a["target_to_global_peak_ratio"],
                "t_g_500khz": b["target_to_global_peak_ratio"],
                "t_g_ratio_250_over_500": a["target_to_global_peak_ratio"] / b["target_to_global_peak_ratio"],
                "global_peak_250khz_mpa": a["global_peak_mpa"],
                "global_peak_500khz_mpa": b["global_peak_mpa"],
            }
    result["frequency_dimension"] = freq

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "cross_case_comparison_250khz_report.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# 250 kHz Cross-Case Comparison (NLM 72m vs Case 079)",
        "",
        f"- Generated (UTC): {result['generated_at_utc']}",
        f"- Claim policy: {result['claim_policy']}",
        "",
        "## Inputs",
    ]
    for name in RUNS:
        m = metrics.get(name)
        if m is None:
            lines.append(f"- {name}: MISSING")
        else:
            lines.append(
                f"- {name}: t/g {m['target_to_global_peak_ratio']:.4f}, "
                f"global peak {m['global_peak_mpa']:.3f} MPa, "
                f"target-window {m['target_window_peak_mpa']:.3f} MPa")
    lines += ["", "## Baseline -> TR deltas"]
    for case, comp in result["comparisons"].items():
        tg = comp.get("target_to_global_peak_ratio", {})
        pk = comp.get("global_peak_mpa", {})
        tw = comp.get("target_window_peak_mpa", {})
        lines.append(
            f"- {case}: t/g {tg.get('baseline'):.4f} -> {tg.get('tr'):.4f} "
            f"({tg.get('ratio'):.2f}x); global peak {pk.get('baseline'):.3f} -> {pk.get('tr'):.3f} MPa; "
            f"target-window {tw.get('baseline'):.3f} -> {tw.get('tr'):.3f} MPa")
    if freq:
        lines += ["", "## Frequency dimension (quick baselines)"]
        for case, f in freq.items():
            lines.append(
                f"- {case}: t/g 250 kHz {f['t_g_250khz']:.4f} vs 500 kHz {f['t_g_500khz']:.4f} "
                f"({f['t_g_ratio_250_over_500']:.2f}x); global peak {f['global_peak_250khz_mpa']:.3f} vs "
                f"{f['global_peak_500khz_mpa']:.3f} MPa")
    lines += ["", "Screening-level engineering observation only; no paper-grade convergence, dose, or clinical safety claim."]
    (OUT_DIR / "cross_case_comparison_250khz_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "ok", "missing": missing, "out": str(OUT_DIR.relative_to(PROJECT_ROOT))}))


if __name__ == "__main__":
    main()
