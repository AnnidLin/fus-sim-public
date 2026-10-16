from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
CONTROL = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "offset_y-10p0_z-02p5" / "tr"
HAMMING = ROOT / "outputs" / "a5_hotspot_suppression_hamming_20260720" / "offset_y-10p0_z-02p5" / "tr"
BRIEF = ROOT / "outputs" / "evidence_briefs" / "a5_hotspot_suppression_hamming"
OUTPUT = ROOT / "outputs" / "a5_hamming_hotspot_report_20260720"


def load_arm(path: Path) -> dict:
    summary = json.loads((path / "summary.json").read_text(encoding="utf-8"))
    with np.load(path / "pressure_max_mpa.npz") as data:
        pressure = np.asarray(data["pressure_max_mpa"])
        labels = np.asarray(data["labels"])
        global_index = np.unravel_index(int(np.argmax(pressure)), pressure.shape)
        skull_peak = float(np.max(pressure[labels == 2]))
        global_label = int(labels[global_index])
        finite = bool(np.all(np.isfinite(pressure)))
    target_peak = float(summary["pressure"]["target_window_peak_mpa"])
    return {
        "target_global": float(summary["pressure"]["target_to_global_peak_ratio"]),
        "target_window_mpa": target_peak,
        "global_mpa": float(summary["pressure"]["global_peak_mpa"]),
        "skull_peak_mpa": skull_peak,
        "skull_focus": skull_peak / target_peak,
        "peak_target_mm": float(summary["pressure"]["global_peak_to_target_distance_mm"]),
        "global_material": "skull" if global_label == 2 else ("soft_tissue" if global_label == 1 else "background"),
        "global_index_ijk": list(map(int, global_index)),
        "scale_factor": float(summary["time_reversal"]["scale_factor"]),
        "replay_max_abs_pa": float(summary["time_reversal"]["replay_max_abs_pa"]),
        "finite": finite,
        "source_label_counts": summary["source"]["source_label_counts"],
        "source_points": int(summary["source"]["source_points"]),
    }


def gates(arm: dict) -> dict:
    return {
        "target_global": arm["target_global"] >= 0.90,
        "global_not_skull": arm["global_material"] != "skull",
        "skull_focus": arm["skull_focus"] <= 1.25,
        "peak_target": arm["peak_target_mm"] <= 10.0,
        "finite": arm["finite"],
        "source_safe": arm["source_label_counts"] == {"0": arm["source_points"]},
    }


def pct(new: float, old: float) -> float:
    return (new / old - 1.0) * 100.0


def main() -> None:
    control = load_arm(CONTROL)
    hamming = load_arm(HAMMING)
    control_checks = gates(control)
    hamming_checks = gates(hamming)
    report = {
        "status": "negative_pilot_hamming_worsened_hotspot_dominance",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol": "outputs/evidence_briefs/a5_hotspot_suppression_hamming/evidence_brief.md",
        "trajectory": "offset_y-10p0_z-02p5",
        "control": {**control, "checks": control_checks, "pass": all(control_checks.values())},
        "hamming": {**hamming, "checks": hamming_checks, "pass": all(hamming_checks.values())},
        "changes": {
            "target_global_percent": pct(hamming["target_global"], control["target_global"]),
            "target_window_percent": pct(hamming["target_window_mpa"], control["target_window_mpa"]),
            "global_peak_percent": pct(hamming["global_mpa"], control["global_mpa"]),
            "skull_peak_percent": pct(hamming["skull_peak_mpa"], control["skull_peak_mpa"]),
            "skull_focus_percent": pct(hamming["skull_focus"], control["skull_focus"]),
            "scale_factor_percent": pct(hamming["scale_factor"], control["scale_factor"]),
        },
        "a5_original_verdict_preserved": "confirmatory_hold",
        "followup_window_or_parameter_scan_authorized": False,
        "decision": "Reject fixed Hamming apodization for this route. Next work must use an explicit skull-hotspot-constrained objective; do not test another fixed window within this packet.",
        "claim_boundary": "post-study single-trajectory engineering pilot",
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "hamming_hotspot_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    metrics = ["target_global", "skull_focus", "peak_target_mm"]
    titles = ["Target/global", "Skull/focus", "Peak-target distance (mm)"]
    thresholds = [0.90, 1.25, 10.0]
    fig, axes = plt.subplots(1, 3, figsize=(8.8, 3.1), constrained_layout=True)
    for ax, metric, title, threshold in zip(axes, metrics, titles, thresholds):
        ax.bar(["Control", "Hamming"], [control[metric], hamming[metric]], color=["#4c78a8", "#d55e00"])
        ax.axhline(threshold, color="#b42318", linestyle="--", linewidth=1.2)
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.2)
        ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(OUTPUT / "hamming_hotspot_comparison.png", dpi=220, facecolor="white")
    plt.close(fig)

    lines = [
        "# Hamming Hotspot-Suppression Pilot",
        "",
        f"- Status: `{report['status']}`",
        "- Exactly one refocus executed; no parameter scan.",
        "",
        "| Metric | Unweighted H1 | Hamming | Change |",
        "|---|---:|---:|---:|",
        f"| target/global | {control['target_global']:.3f} | {hamming['target_global']:.3f} | {report['changes']['target_global_percent']:+.1f}% |",
        f"| target-window peak (MPa) | {control['target_window_mpa']:.3f} | {hamming['target_window_mpa']:.3f} | {report['changes']['target_window_percent']:+.1f}% |",
        f"| skull peak (MPa) | {control['skull_peak_mpa']:.3f} | {hamming['skull_peak_mpa']:.3f} | {report['changes']['skull_peak_percent']:+.1f}% |",
        f"| skull/focus | {control['skull_focus']:.3f} | {hamming['skull_focus']:.3f} | {report['changes']['skull_focus_percent']:+.1f}% |",
        f"| peak-target distance (mm) | {control['peak_target_mm']:.2f} | {hamming['peak_target_mm']:.2f} | - |",
        "",
        "Hamming weighting reduced the target-window peak while increasing the remote skull peak under the frozen max-amplitude replay normalization. Target/global and skull/focus both worsened, and the global peak remained in skull approximately 56 mm from target.",
        "",
        "Decision: reject fixed Hamming apodization for this route. Do not test another fixed window in this packet; the next method must explicitly constrain skull/global-hotspot energy.",
        "",
        "The original A5 `confirmatory_hold` remains unchanged. This pilot does not unlock mapping, thermal, or clinical claims.",
    ]
    (OUTPUT / "hamming_hotspot_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    feedback = {
        "status": report["status"],
        "pressure_runs_executed": 1,
        "deviations": [],
        "followup_authorized": False,
        "decision": report["decision"],
    }
    (BRIEF / "gap_feedback.json").write_text(json.dumps(feedback, indent=2) + "\n", encoding="utf-8")
    (BRIEF / "gap_feedback.md").write_text(
        "# Gap Feedback: Hamming Hotspot-Suppression Pilot\n\n"
        f"- Status: `{report['status']}`\n"
        "- Pressure runs: 1/1 authorized refocus completed `kwave_ok`.\n"
        "- Deviations: none.\n"
        "- Result: target/global and skull/focus worsened; remote skull peak persisted.\n"
        "- Decision: reject fixed Hamming apodization; no additional window or parameter scan authorized.\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], "control_pass": report["control"]["pass"], "hamming_pass": report["hamming"]["pass"]}))


if __name__ == "__main__":
    main()
