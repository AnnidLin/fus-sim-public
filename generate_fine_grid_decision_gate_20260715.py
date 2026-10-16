from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path("outputs/fine_grid_decision_gate_20260715")

GRID_CONV_JSON = Path("outputs/freefield_aperture_calibration/d60_grid_convergence_20260713/d60_grid_convergence_report.json")
CONFIRMATION_JSON = Path("outputs/freefield_aperture_calibration/d60_r78p330_dx0p75_confirmation_20260714/d60_r78p330_confirmation_report.json")
FOCUS_BIAS_JSON = Path("outputs/freefield_aperture_calibration/d60_gate_b_focus_bias_audit_20260714/d60_gate_b_focus_bias_audit.json")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def estimate_memory(grid_shape: list[int], nt: int, dtype_bytes: int = 8) -> float:
    """Estimate full-domain time-history memory in GiB."""
    voxels = grid_shape[0] * grid_shape[1] * grid_shape[2]
    return voxels * nt * dtype_bytes / (1024 ** 3)


def build_analysis(grid_conv: dict[str, Any], confirmation: dict[str, Any], focus_bias: dict[str, Any]) -> dict[str, Any]:
    dx075 = grid_conv["dx0p75"]
    dx05 = grid_conv["dx0p5"]

    # Estimate nt for dx0.5 based on runtime scaling and dx0.75 nt=unknown; use a placeholder ratio.
    # From the confirmation report, dx0.75 runtime ~4757 s. dx0.5 runtime 12127 s.
    runtime_ratio = dx05["runtime_s"] / dx075["runtime_s"]

    # Estimate memory for dx0.5 full-domain history using grid shape and a typical nt.
    # The failure report stated ~110 GiB for [218,228,198] x 1500 float64.
    dx05_waveform_memory_gib = estimate_memory(dx05["grid_shape"], nt=1500)

    # Estimate dx0.375 grid: roughly 1.5x dx0.5 dimensions.
    dx0375_shape = [int(round(x * 4 / 3)) for x in dx05["grid_shape"]]
    dx0375_voxels = dx0375_shape[0] * dx0375_shape[1] * dx0375_shape[2]
    dx0375_runtime_estimate_h = (dx0375_voxels / (dx05["grid_shape"][0] * dx05["grid_shape"][1] * dx05["grid_shape"][2])) * runtime_ratio * (dx075["runtime_s"] / 3600) * 1.5
    dx0375_memory_gib = estimate_memory(dx0375_shape, nt=1500)

    # Decision criteria from ACOUSTIC_CURRENT_PLAN_20260714.md P3.
    criteria = {
        "indispensable_for_submission": {
            "question": "Does the paper gap matrix prove dx0.5 is the only irreplaceable near-term gap?",
            "answer": False,
            "reason": "The gap matrix shows 4 currently-unachievable gaps (true skull crossing, focus quality, mapping, hydrophone) that are more fundamental than grid resolution. A manuscript can be written with dx0.75-only free-field evidence if framed as engineering calibration.",
        },
        "speedup_or_checkpoint": {
            "question": "Is there a clear speedup or checkpoint scheme to avoid another 3+ hour run with no output?",
            "answer": False,
            "reason": "dx0.5 field-only run already completed in ~3.4 h. The blocker is target-waveform recording, which requires either a separate low-memory point-sensor run (~11.7 KiB target-only history) or a backend change. No implementation exists yet.",
        },
        "user_re_authorization": {
            "question": "Would the user explicitly re-authorize a new dx0.5 run?",
            "answer": "unknown",
            "reason": "Requires human decision. The current plan stops simulations automatically.",
        },
    }

    all_criteria_for_resumption = all(
        c["answer"] is True for c in criteria.values()
    )

    options = [
        {
            "option_id": "A_resume_dx05_with_target_pointwave",
            "label": "Resume dx0.5 with target-only point waveform",
            "description": "Run dx0.5 field-only again (if needed) and add a separate target-only sensor recording to avoid 110 GiB full-domain history.",
            "pros": ["Completes Gate B cross-grid convergence", "Keeps PPW=6 field metrics", "Low memory for waveform (~12 KiB)"],
            "cons": ["Requires new k-Wave run (~3.4 h)", "Needs implementation of point-waveform runner path", "Still only free-field evidence"],
            "estimated_time_h": 3.5,
            "estimated_memory_gib": 0.05,
            "recommended": True,
        },
        {
            "option_id": "B_jump_to_dx0375",
            "label": "Skip dx0.5 and run dx0.375 (8 PPW)",
            "description": "Run a finer grid directly to approximate paper-grade PPW.",
            "pros": ["Higher PPW (~8)", "Stronger paper-grade position"],
            "cons": [f"Estimated runtime ~{dx0375_runtime_estimate_h:.1f} h", f"Estimated waveform memory ~{dx0375_memory_gib:.1f} GiB", "No prior dx0.5 checkpoint"],
            "estimated_time_h": round(dx0375_runtime_estimate_h, 1),
            "estimated_memory_gib": round(dx0375_memory_gib, 1),
            "recommended": False,
        },
        {
            "option_id": "C_declare_non_convergence",
            "label": "Declare non-convergence and keep dx0.75 as engineering evidence",
            "description": "Write the manuscript with dx0.75-only free-field calibration and explicitly state that grid convergence was not established.",
            "pros": ["No new compute", "Honest limitation statement", "Aligns with current plan's stop condition"],
            "cons": ["Cannot claim paper-grade numerical convergence", "May be a reviewer concern"],
            "estimated_time_h": 0.0,
            "estimated_memory_gib": 0.0,
            "recommended": False,
        },
    ]

    recommendation = (
        "Option C is the default under the current plan because not all resumption criteria are met. "
        "If the user decides grid convergence is indispensable, Option A is the least expensive path; "
        "Option B should only be attempted after Option A succeeds."
    )

    return {
        "status": "decision_gate_prepared_no_simulation_run",
        "scope": "D60 free-field source calibration cross-grid convergence",
        "dx075": {
            "grid_shape": dx075["grid_shape"],
            "dx_mm": dx075["dx_mm"],
            "ppw": 4.0,
            "refined_focus_error_percent": dx075["refined_focus_error_percent"],
            "runtime_s": dx075["runtime_s"],
        },
        "dx05": {
            "grid_shape": dx05["grid_shape"],
            "dx_mm": dx05["dx_mm"],
            "ppw": 6.0,
            "refined_focus_error_percent": dx05["refined_focus_error_percent"],
            "global_peak_change_percent": grid_conv["comparison"]["global_peak_change_percent"],
            "lateral_width_change_percent": grid_conv["comparison"]["lateral_width_change_percent"],
            "axial_width_change_percent": grid_conv["comparison"]["axial_width_change_percent"],
            "focal_displacement_mm": grid_conv["comparison"]["focal_displacement_mm"],
            "runtime_s": dx05["runtime_s"],
            "waveform_complete": grid_conv["waveform_complete"],
            "estimated_full_domain_history_gib": round(dx05_waveform_memory_gib, 1),
        },
        "dx0375_estimate": {
            "grid_shape": dx0375_shape,
            "estimated_runtime_h": round(dx0375_runtime_estimate_h, 1),
            "estimated_full_domain_history_gib": round(dx0375_memory_gib, 1),
        },
        "gate_b_acceptance": grid_conv["acceptance"],
        "resumption_criteria": criteria,
        "all_criteria_for_resumption_met": all_criteria_for_resumption,
        "options": options,
        "recommendation": recommendation,
        "next_action": "Present this decision gate to the user. Default is Option C (declare non-convergence) unless the user explicitly authorizes Option A or B.",
    }


def write_report(analysis: dict[str, Any], path: Path) -> None:
    lines = [
        "# Fine-Grid Resumption Decision Gate (2026-07-15)",
        "",
        "> Scope: decide whether to resume dx0.5/dx0.375 free-field simulations for the D60 source calibration manuscript. No simulation was run.",
        "",
        "## Current evidence",
        "",
        f"- dx0.75: grid {analysis['dx075']['grid_shape']}, dx={analysis['dx075']['dx_mm']:.3f} mm, PPW={analysis['dx075']['ppw']}, refined focus error={analysis['dx075']['refined_focus_error_percent']:.3f}%, runtime={analysis['dx075']['runtime_s']/60:.1f} min.",
        f"- dx0.5: grid {analysis['dx05']['grid_shape']}, dx={analysis['dx05']['dx_mm']:.3f} mm, PPW={analysis['dx05']['ppw']}, refined focus error={analysis['dx05']['refined_focus_error_percent']:.3f}%.",
        f"- dx0.5 vs dx0.75 field metrics: global peak change {analysis['dx05']['global_peak_change_percent']:+.3f}%; lateral width change {analysis['dx05']['lateral_width_change_percent']:+.3f}%; axial width change {analysis['dx05']['axial_width_change_percent']:+.3f}%; focal displacement {analysis['dx05']['focal_displacement_mm']:.3f} mm.",
        f"- dx0.5 runtime: {analysis['dx05']['runtime_s']/3600:.2f} h.",
        f"- dx0.5 target waveform recorded: {analysis['dx05']['waveform_complete']}.",
        f"- Estimated full-domain time-history memory for dx0.5: {analysis['dx05']['estimated_full_domain_history_gib']:.1f} GiB.",
        "",
        "## Gate B acceptance",
        "",
        "| Check | Passed |",
        "|---|---|",
    ]
    for key, value in analysis["gate_b_acceptance"].items():
        lines.append(f"| {key} | {value} |")

    lines.extend([
        "",
        "## Resumption criteria (from ACOUSTIC_CURRENT_PLAN_20260714.md P3)",
        "",
        "| Criterion | Met? | Reason |",
        "|---|---|---|",
    ])
    for key, item in analysis["resumption_criteria"].items():
        lines.append(f"| {item['question']} | {item['answer']} | {item['reason']} |")

    lines.extend([
        "",
        f"**All criteria met for resumption**: {analysis['all_criteria_for_resumption_met']}",
        "",
        "## Options",
        "",
    ])
    for opt in analysis["options"]:
        rec = "(Recommended)" if opt["recommended"] else ""
        lines.extend([
            f"### {opt['option_id']} {rec}: {opt['label']}",
            "",
            opt["description"],
            "",
            f"- Estimated time: {opt['estimated_time_h']} h",
            f"- Estimated waveform memory: {opt['estimated_memory_gib']} GiB",
            f"- Pros: {'; '.join(opt['pros'])}",
            f"- Cons: {'; '.join(opt['cons'])}",
            "",
        ])

    lines.extend([
        "## Recommendation",
        "",
        analysis["recommendation"],
        "",
        "## Next action",
        "",
        analysis["next_action"],
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    grid_conv = read_json(GRID_CONV_JSON)
    confirmation = read_json(CONFIRMATION_JSON)
    focus_bias = read_json(FOCUS_BIAS_JSON)

    analysis = build_analysis(grid_conv, confirmation, focus_bias)
    (args.output_dir / "fine_grid_decision_gate.json").write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_report(analysis, args.output_dir / "fine_grid_decision_gate_report.md")

    print(json.dumps({"status": analysis["status"], "output_dir": str(args.output_dir), "recommendation": analysis["recommendation"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
