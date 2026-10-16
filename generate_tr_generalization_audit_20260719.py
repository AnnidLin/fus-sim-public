from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
A4 = ROOT / "outputs" / "a4_quick_screen_20260718" / "a4_quick_screen_report.json"
A5 = ROOT / "outputs" / "a5_heldout_tr_confirmation_20260719" / "heldout_tr_report.json"
OUTPUT = ROOT / "outputs" / "tr_generalization_audit_20260719"


def gate(row: dict) -> tuple[bool, list[str]]:
    failed = []
    if row["target_global"] < 0.90:
        failed.append("target_global")
    if row["global_peak_material"].startswith("skull"):
        failed.append("global_peak_material")
    if row["skull_focus"] > 1.25:
        failed.append("skull_focus")
    if row["peak_target_mm"] > 10.0:
        failed.append("peak_target_distance")
    return not failed, failed


def main() -> None:
    a4 = json.loads(A4.read_text(encoding="utf-8"))
    a5 = json.loads(A5.read_text(encoding="utf-8"))
    rows = []
    for item in a4["trajectories"]:
        row = {
            "cohort": "A4 development (post hoc absolute audit)",
            "trajectory": item["traj"],
            "target_global": float(item["tr"]["t_g"]),
            "skull_focus": float(item["skull_focus_ratio"]),
            "global_peak_material": item["tr"]["npz"]["global_peak_material"],
            "peak_target_mm": float(item["tr"]["pressure"]["global_peak_to_target_distance_mm"]),
        }
        row["absolute_gate_pass"], row["failed_gates"] = gate(row)
        rows.append(row)
    for item in a5["trajectories"]:
        row = {
            "cohort": "A5 held-out (preregistered)",
            "trajectory": item["trajectory"],
            "target_global": float(item["pressure"]["target_to_global_peak_ratio"]),
            "skull_focus": float(item["skull_focus_ratio"]),
            "global_peak_material": item["material"]["global_peak_material"],
            "peak_target_mm": float(item["pressure"]["global_peak_to_target_distance_mm"]),
        }
        row["absolute_gate_pass"], row["failed_gates"] = gate(row)
        rows.append(row)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "trajectory_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["cohort", "trajectory", "target_global", "skull_focus", "global_peak_material", "peak_target_mm", "absolute_gate_pass", "failed_gates"])
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "failed_gates": ";".join(row["failed_gates"])})

    dev = rows[:3]
    held = rows[3:]
    dev_rate = sum(row["absolute_gate_pass"] for row in dev) / 3
    held_rate = sum(row["absolute_gate_pass"] for row in held) / 3
    report = {
        "status": "heldout_generalization_gap_detected",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "development_absolute_gate_status": "post_hoc_not_original_a4_verdict",
        "original_a4_verdict_preserved": "hold",
        "development_pass_rate": dev_rate,
        "heldout_pass_rate": held_rate,
        "generalization_gap_percentage_points": (held_rate - dev_rate) * 100,
        "pooled_pass_rate": sum(row["absolute_gate_pass"] for row in rows) / len(rows),
        "rows": rows,
        "failure_pattern": "Three failed trajectories retained high target-window ratios but placed the global peak in skull approximately 57 mm from target.",
        "decision": "Do not unlock mapping or thermal expansion. The next method must explicitly suppress skull/global hotspots rather than optimize target-only focusing.",
        "claim_boundary": "descriptive six-trajectory single-case engineering audit; no inferential statistics or clinical claim",
    }
    (OUTPUT / "generalization_audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    labels = [f"D{i+1}" for i in range(3)] + [f"H{i+1}" for i in range(3)]
    colors = ["#4c78a8"] * 3 + ["#e07a2d"] * 3
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.3), constrained_layout=True)
    panels = [
        ("target_global", 0.90, "Target/global", "higher is better"),
        ("skull_focus", 1.25, "Skull/focus", "lower is better"),
        ("peak_target_mm", 10.0, "Peak-target distance (mm)", "lower is better"),
    ]
    for ax, (key, threshold, title, subtitle) in zip(axes[:3], panels):
        values = [row[key] for row in rows]
        ax.bar(labels, values, color=colors)
        ax.axhline(threshold, color="#b42318", linestyle="--", linewidth=1.2)
        ax.set_title(title)
        ax.set_xlabel(subtitle)
        ax.grid(axis="y", alpha=0.2)
    axes[3].bar(["Development", "Held-out"], [dev_rate * 100, held_rate * 100], color=["#4c78a8", "#e07a2d"])
    axes[3].set(ylabel="Pass rate (%)", ylim=(0, 100), title="Absolute-gate transfer")
    axes[3].grid(axis="y", alpha=0.2)
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(OUTPUT / "tr_generalization_audit.png", dpi=220, facecolor="white")
    plt.close(fig)

    lines = [
        "# TR Generalization Audit",
        "",
        f"- Development absolute-gate pass rate: {dev_rate * 100:.1f}% (post hoc; original A4 remains hold)",
        f"- Held-out preregistered pass rate: {held_rate * 100:.1f}%",
        f"- Descriptive transfer gap: {(held_rate - dev_rate) * 100:.1f} percentage points",
        f"- Pooled: {sum(row['absolute_gate_pass'] for row in rows)}/6 trajectories",
        "",
        "The repeated failure mode is a strong target-window focus accompanied by a more intense remote skull peak approximately 57 mm from the target. Target-only TR focusing therefore does not generalize reliably across the frozen Case 079 trajectory set.",
        "",
        "Decision: do not unlock mapping or thermal expansion. The next acoustic method must include an explicit skull/global-hotspot suppression objective.",
        "",
        "This is a descriptive single-case engineering audit. No inferential, clinical, or multi-subject generalization claim is supported.",
    ]
    (OUTPUT / "generalization_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "development_pass": sum(r["absolute_gate_pass"] for r in dev), "heldout_pass": sum(r["absolute_gate_pass"] for r in held)}))


if __name__ == "__main__":
    main()
