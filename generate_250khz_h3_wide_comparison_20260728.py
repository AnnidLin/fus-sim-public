"""Cross-run comparison 2026-07-28: 250 kHz H3 superposition + NLM wide-domain confirmation.

Reads tonight's new runs plus prior quick-chain references and writes
outputs/cross_case_250khz_h3_wide_20260728/comparison_250khz_h3_wide.{json,md}.
Engineering-observation wording only; no claim-grade verdicts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs" / "cross_case_250khz_h3_wide_20260728"

RUNS = {
    "079_default_250khz_quick_baseline": "outputs/case079_kwave_quick_250khz_20260724/summary.json",
    "079_default_250khz_quick_tr": "outputs/case079_tr_250khz_20260724/summary.json",
    "nlm_250khz_quick_baseline": "outputs/nlm_kwave_quick_250khz_20260724/summary.json",
    "nlm_250khz_quick_tr": "outputs/nlm_tr_72m_250khz_20260724/summary.json",
    "h3_500khz_tr_prior": "outputs/a5_heldout_tr_confirmation_20260719/offset_y+12p5_z-15p0/tr/summary.json",
    "h3_250khz_baseline_new": "outputs/case079_h3_250khz_baseline_20260728/summary.json",
    "h3_250khz_tr_new": "outputs/case079_h3_tr_250khz_20260728/summary.json",
    "nlm_250khz_wide_tr_new": "outputs/nlm_tr_wide_250khz_20260728/summary.json",
    "nlm_250khz_wide_calibrate_new": "outputs/nlm_tr_wide_250khz_20260728/summary_calibrate.json",
}


def load_metrics(rel: str) -> dict | None:
    path = ROOT / rel
    if not path.exists():
        return None
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    p = d.get("pressure") or {}
    cfg = d.get("config") or {}
    m = d.get("model") or {}
    tw = p.get("target_window_peak_mpa")
    g = p.get("global_peak_mpa")
    tg = p.get("target_to_global_peak_ratio")
    if tg is None and tw and g:
        tg = tw / g
    return {
        "path": rel,
        "frequency_hz": cfg.get("frequency_hz"),
        "preset": cfg.get("preset"),
        "cycles": cfg.get("tone_burst_cycles"),
        "aperture_mm": (cfg.get("aperture_diameter_m") or 0) * 1000 or None,
        "radius_mm": (cfg.get("transducer_radius_m") or 0) * 1000 or None,
        "model_shape": m.get("model_shape") or d.get("model_shape"),
        "target_window_peak_mpa": tw,
        "global_peak_mpa": g,
        "t_over_g": tg,
        "global_peak_to_target_distance_mm": p.get("global_peak_to_target_distance_mm"),
    }


def pct_delta(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return (a - b) / b * 100.0


def main() -> int:
    metrics = {name: load_metrics(rel) for name, rel in RUNS.items()}
    missing = [n for n, m in metrics.items() if m is None]

    analyses: dict = {}

    h3b = metrics.get("h3_250khz_baseline_new")
    h3t = metrics.get("h3_250khz_tr_new")
    h3_500 = metrics.get("h3_500khz_tr_prior")
    dfb = metrics.get("079_default_250khz_quick_baseline")
    dft = metrics.get("079_default_250khz_quick_tr")
    if h3b and h3t:
        analyses["h3_250khz_tr_amplification"] = (
            h3t["t_over_g"] / h3b["t_over_g"] if h3b["t_over_g"] else None
        )
        analyses["h3_vs_default_entry_250khz_baseline_tg_delta_pct"] = pct_delta(
            h3b["t_over_g"], dfb and dfb["t_over_g"]
        )
        analyses["h3_vs_default_entry_250khz_tr_tg_delta_pct"] = pct_delta(
            h3t["t_over_g"], dft and dft["t_over_g"]
        )
        analyses["h3_tr_tg_250_vs_500_delta_pct"] = pct_delta(
            h3t["t_over_g"], h3_500 and h3_500["t_over_g"]
        )

    nq = metrics.get("nlm_250khz_quick_tr")
    nw = metrics.get("nlm_250khz_wide_tr_new")
    if nq and nw:
        delta = pct_delta(nw["t_over_g"], nq["t_over_g"])
        analyses["nlm_wide_vs_quick_tr_tg_delta_pct"] = delta
        analyses["nlm_wide_domain_reading"] = (
            "quick-crop protocol not domain-dominated"
            if delta is not None and abs(delta) <= 10.0
            else "domain extent materially changes t/g; protocol review required"
        )

    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "brief_id": "freq250_h3_wide_domain_20260728",
        "claim_level": "engineering_observation_screening",
        "metrics": metrics,
        "missing_inputs": missing,
        "analyses": analyses,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "comparison_250khz_h3_wide.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    lines = [
        "# 250 kHz H3 Superposition + Wide-Domain Confirmation (engineering observation)",
        "",
        f"- Generated (UTC): {result['generated_at_utc']}",
        f"- Claim level: {result['claim_level']}",
        f"- Missing inputs: {', '.join(missing) if missing else 'none'}",
        "",
        "## Run metrics",
        "",
        "| run | preset | shape | tw MPa | global MPa | t/g | peak-to-target mm |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, m in metrics.items():
        if not m:
            lines.append(f"| {name} | - | - | - | - | - | - |")
            continue
        shape = "x".join(str(v) for v in (m["model_shape"] or []))
        lines.append(
            "| {n} | {p} | {s} | {tw} | {g} | {tg} | {d} |".format(
                n=name,
                p=m["preset"],
                s=shape,
                tw=f"{m['target_window_peak_mpa']:.4f}" if m["target_window_peak_mpa"] else "-",
                g=f"{m['global_peak_mpa']:.4f}" if m["global_peak_mpa"] else "-",
                tg=f"{m['t_over_g']:.4f}" if m["t_over_g"] is not None else "-",
                d=f"{m['global_peak_to_target_distance_mm']:.1f}"
                if m["global_peak_to_target_distance_mm"] is not None
                else "-",
            )
        )
    lines += ["", "## Analyses", ""]
    for k, v in analyses.items():
        lines.append(f"- {k}: {v}")
    lines += [
        "",
        "Screening-level engineering observations only; no safety, dose, or clinical claims.",
    ]
    (OUT / "comparison_250khz_h3_wide.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"overall": "ok", "missing": missing, "analyses": list(analyses)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
