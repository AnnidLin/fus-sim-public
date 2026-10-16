from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
KWAVE_PYTHON = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")


@dataclass(frozen=True)
class PmlCandidate:
    pml_size: int
    pml_thickness_mm: float
    estimated_grid_size: tuple[int, int, int]
    estimated_voxel_count: int
    estimated_memory_mb: float
    relative_voxel_count: float
    role: str
    recommendation: str
    dry_run_output_dir: str
    future_run_dir: str
    dry_run_command: list[str]
    future_runner_command: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pml_size": self.pml_size,
            "pml_thickness_mm": self.pml_thickness_mm,
            "estimated_grid_size": list(self.estimated_grid_size),
            "estimated_voxel_count": self.estimated_voxel_count,
            "estimated_memory_mb": self.estimated_memory_mb,
            "relative_voxel_count": self.relative_voxel_count,
            "role": self.role,
            "recommendation": self.recommendation,
            "dry_run_output_dir": self.dry_run_output_dir,
            "future_run_dir": self.future_run_dir,
            "dry_run_command": self.dry_run_command,
            "future_runner_command": self.future_runner_command,
        }


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def nested(data: dict[str, Any] | None, keys: list[str], default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def input_paths() -> dict[str, Path]:
    return {
        "dx075_model_summary": PROJECT_ROOT / "outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/summary.json",
        "dx075_dry_run": PROJECT_ROOT
        / "outputs/ct_grid_convergence_plan/079_candidate_006/dx0p75_dry_run/quality_dry_run_summary.json",
        "dx075_execution_summary": PROJECT_ROOT
        / "outputs/ct_grid_convergence_plan/079_candidate_006/dx0p75_model_build_dry_run_summary.json",
        "freefield_quality": PROJECT_ROOT / "outputs/freefield_quality_report/freefield_quality_summary.json",
        "simulation_presets": PROJECT_ROOT / "simulation_presets.json",
    }


def load_inputs() -> dict[str, dict[str, Any] | None]:
    return {name: read_json(path) for name, path in input_paths().items()}


def command_text(command: list[str]) -> str:
    return " ".join(command)


def build_candidates(data: dict[str, dict[str, Any] | None], pml_values: list[int]) -> list[PmlCandidate]:
    dry = data["dx075_dry_run"]
    if dry is None:
        return []
    base_pml = int(nested(dry, ["simulation_quality", "pml_size"], 8))
    dx_mm = float(nested(dry, ["simulation_quality", "dx_mm"], 0.75))
    base_grid = tuple(int(v) for v in nested(dry, ["simulation_quality", "grid_size"], [69, 57, 47]))
    base_voxels = int(nested(dry, ["simulation_quality", "voxel_count"], 184851))
    base_memory = float(nested(dry, ["simulation_quality", "memory_estimate", "estimated_mb"], 4.7676))
    config = dry.get("config", {})
    model_path = str(config.get("model_path", "outputs\\ct_acoustic_model_3d_profile_hu300_dx0p75\\acoustic_model_3d.npz"))
    entry_plan_path = str(config.get("entry_plan_path", "outputs\\case_refinement_plan\\079\\candidate_006\\entry_plan.json"))
    sim_time_us = float(config.get("simulation_time_s", 55e-6)) * 1e6
    cycles = int(config.get("tone_burst_cycles", 8))
    quick_lateral_mm = float(config.get("quick_lateral_half_width_m", 0.017)) * 1e3
    quick_post_target_mm = float(config.get("quick_post_target_margin_m", 0.008)) * 1e3
    aperture_mm = float(config.get("aperture_diameter_m", 0.03)) * 1e3
    radius_mm = float(config.get("transducer_radius_m", 0.035)) * 1e3

    candidates: list[PmlCandidate] = []
    for pml in pml_values:
        delta = pml - base_pml
        grid = tuple(max(1, dim + 2 * delta) for dim in base_grid)
        voxels = grid[0] * grid[1] * grid[2]
        relative = voxels / base_voxels
        memory = base_memory * relative
        dry_dir = f"outputs\\ct_pml_boundary_review\\079_candidate_006_dx0p75\\pml{pml}_dry_run"
        future_dir = f"outputs\\ct_pml_boundary_runs\\079_candidate_006_dx0p75_pml{pml}_standard"
        dry_command = [
            str(KWAVE_PYTHON),
            "simulate_kwave_3d_focus.py",
            "--model",
            model_path,
            "--entry-plan",
            entry_plan_path,
            "--output-dir",
            dry_dir,
            "--preset",
            "standard",
            "--dry-run-quality",
            "--sim-time-us",
            f"{sim_time_us:g}",
            "--cycles",
            str(cycles),
            "--quick-lateral-mm",
            f"{quick_lateral_mm:g}",
            "--quick-post-target-mm",
            f"{quick_post_target_mm:g}",
            "--aperture-mm",
            f"{aperture_mm:g}",
            "--radius-mm",
            f"{radius_mm:g}",
            "--pml-size",
            str(pml),
        ]
        runner_command = [
            str(KWAVE_PYTHON),
            "run_kwave_command.py",
            "--script",
            "simulate_kwave_3d_focus.py",
            "--output-dir",
            future_dir,
            "--preset",
            "standard",
            "--model",
            model_path,
            "--entry-plan",
            entry_plan_path,
            "--sim-time-us",
            f"{sim_time_us:g}",
            "--cycles",
            str(cycles),
            "--quick-lateral-mm",
            f"{quick_lateral_mm:g}",
            "--quick-post-target-mm",
            f"{quick_post_target_mm:g}",
            "--aperture-mm",
            f"{aperture_mm:g}",
            "--radius-mm",
            f"{radius_mm:g}",
            "--pml-size",
            str(pml),
            "--execute",
            "--checkpoint-sec",
            "120",
            "--hard-stop-min",
            "30",
        ]
        if pml == base_pml:
            role = "existing_dx0p75_baseline"
            recommendation = "Use existing PML=8 dry-run as the baseline."
        elif pml == 12:
            role = "recommended_next_dry_run_quality"
            recommendation = "Execute dry-run-quality only, then inspect grid/memory/source mask before any pressure authorization."
        else:
            role = "risk_estimate_only"
            recommendation = "Keep as cost estimate until PML=12 dry-run-quality is reviewed."
        candidates.append(
            PmlCandidate(
                pml_size=pml,
                pml_thickness_mm=pml * dx_mm,
                estimated_grid_size=grid,
                estimated_voxel_count=voxels,
                estimated_memory_mb=memory,
                relative_voxel_count=relative,
                role=role,
                recommendation=recommendation,
                dry_run_output_dir=dry_dir,
                future_run_dir=future_dir,
                dry_run_command=dry_command,
                future_runner_command=runner_command,
            )
        )
    return sorted(candidates, key=lambda item: item.pml_size)


def build_summary(data: dict[str, dict[str, Any] | None], pml_values: list[int]) -> dict[str, Any]:
    candidates = build_candidates(data, pml_values)
    recommended = next((item for item in candidates if item.pml_size == 12), None)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "CT PML/boundary review plan only; no pressure simulation",
        "inputs": {
            "paths": {name: rel(path) for name, path in input_paths().items()},
            "exists": {name: payload is not None for name, payload in data.items()},
        },
        "decision": {
            "case_id": "079",
            "baseline_profile": "simple_hu300",
            "dx_mm": 0.75,
            "plan_ready": bool(candidates),
            "execution_authorized": False,
            "dry_run_quality_allowed": recommended is not None,
            "pressure_run_allowed": False,
            "paper_grade_ready": False,
            "next_recommended_artifact": "PML=12 dry-run-quality",
        },
        "baseline_pml8": {
            "grid_size": nested(data["dx075_dry_run"], ["simulation_quality", "grid_size"]),
            "pml_size": nested(data["dx075_dry_run"], ["simulation_quality", "pml_size"]),
            "pml_thickness_mm": float(nested(data["dx075_dry_run"], ["simulation_quality", "pml_size"], 8))
            * float(nested(data["dx075_dry_run"], ["simulation_quality", "dx_mm"], 0.75)),
            "memory_estimate_mb": nested(data["dx075_dry_run"], ["simulation_quality", "memory_estimate", "estimated_mb"]),
            "source_label_counts": nested(data["dx075_dry_run"], ["source", "source_label_counts"]),
        },
        "freefield_context": {
            "pml_boundary_changes": nested(data["freefield_quality"], ["pml_boundary_comparison", "changes"]),
            "interpretation": nested(data["freefield_quality"], ["pml_boundary_comparison", "interpretation"]),
            "boundary": "free-field PML stability is context only; CT-specific PML still needs review.",
        },
        "candidates": [candidate.to_dict() for candidate in candidates],
        "recommended_candidate": None if recommended is None else recommended.to_dict(),
        "guardrails": [
            "Run only PML=12 dry-run-quality at this stage.",
            "Do not run any pressure solve from this plan without explicit authorization.",
            "PML=16 remains a cost estimate until PML=12 is reviewed.",
            "Dry-run-quality cannot validate boundary reflections; it only checks metadata/cost/source mask.",
        ],
        "not_executed": [
            "k-Wave pressure simulation",
            "thermal simulation",
            "paper-grade preset run",
        ],
    }


def write_csv(path: Path, candidates: list[dict[str, Any]]) -> None:
    fieldnames = [
        "pml_size",
        "pml_thickness_mm",
        "estimated_grid_size",
        "estimated_voxel_count",
        "estimated_memory_mb",
        "relative_voxel_count",
        "role",
        "recommendation",
        "dry_run_output_dir",
        "future_run_dir",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for candidate in candidates:
            row = dict(candidate)
            row["estimated_grid_size"] = "x".join(str(v) for v in row["estimated_grid_size"])
            writer.writerow({key: row.get(key) for key in fieldnames})


def build_markdown(summary: dict[str, Any]) -> str:
    decision = summary["decision"]
    lines = [
        "# simple_hu300 CT PML/Boundary Review Plan",
        "",
        "> Scope: PML metadata and command templates. No pressure solve was executed by this plan.",
        "",
        "## Decision",
        "",
        f"- case: `{decision['case_id']}`",
        f"- dx: `{decision['dx_mm']}` mm",
        f"- plan ready: `{decision['plan_ready']}`",
        f"- dry-run-quality allowed: `{decision['dry_run_quality_allowed']}`",
        f"- pressure run allowed: `{decision['pressure_run_allowed']}`",
        f"- next recommended artifact: `{decision['next_recommended_artifact']}`",
        "",
        "## Candidate Estimates",
        "",
        "| PML | thickness mm | estimated grid | memory MB | rel voxels | role |",
        "| ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for candidate in summary["candidates"]:
        lines.append(
            f"| {candidate['pml_size']} | {candidate['pml_thickness_mm']:.3f} | "
            f"{'x'.join(str(v) for v in candidate['estimated_grid_size'])} | "
            f"{candidate['estimated_memory_mb']:.3f} | {candidate['relative_voxel_count']:.2f} | {candidate['role']} |"
        )
    recommended = summary["recommended_candidate"]
    if recommended:
        lines.extend(
            [
                "",
                "## Recommended Dry-run-quality Candidate",
                "",
                f"- PML: `{recommended['pml_size']}`",
                f"- output: `{recommended['dry_run_output_dir']}`",
                "",
                "Dry-run-quality command, not pressure:",
                "",
                "```powershell",
                command_text(recommended["dry_run_command"]),
                "```",
                "",
                "Future pressure runner template, blocked:",
                "",
                "```powershell",
                command_text(recommended["future_runner_command"]),
                "```",
            ]
        )
    lines.extend(["", "## Guardrails", ""])
    lines.extend(f"- {item}" for item in summary["guardrails"])
    lines.extend(["", "## Not Executed", ""])
    lines.extend(f"- {item}" for item in summary["not_executed"])
    lines.append("")
    return "\n".join(lines)


def write_command_files(output_dir: Path, summary: dict[str, Any]) -> None:
    recommended = summary["recommended_candidate"]
    if not recommended:
        return
    (output_dir / "recommended_pml12_dry_run_quality_command.ps1").write_text(
        "# Dry-run-quality only. Does not solve pressure.\n" + command_text(recommended["dry_run_command"]) + "\n",
        encoding="utf-8-sig",
    )
    (output_dir / "blocked_pml12_pressure_runner_command.ps1").write_text(
        "# BLOCKED. Do not run without explicit pressure authorization.\n"
        + command_text(recommended["future_runner_command"])
        + "\n",
        encoding="utf-8-sig",
    )


def write_gap_feedback(output_dir: Path, summary: dict[str, Any]) -> None:
    brief_dir = PROJECT_ROOT / "outputs/evidence_briefs/simple_hu300_ct_pml_boundary_review"
    brief_dir.mkdir(parents=True, exist_ok=True)
    feedback = {
        "module": "simple_hu300_ct_pml_boundary_review",
        "feedback_type": "post_execution_gap_feedback",
        "executed_scope": [
            "read dx0.75 PML=8 dry-run-quality summary",
            "generated CT PML/boundary review candidate plan",
            "generated PML=12 dry-run-quality and blocked pressure command templates",
        ],
        "outputs": {
            "report": rel(output_dir / "ct_pml_boundary_review_plan.md"),
            "summary": rel(output_dir / "ct_pml_boundary_review_plan.json"),
            "csv": rel(output_dir / "ct_pml_boundary_candidates.csv"),
        },
        "decision": summary["decision"],
        "not_executed": summary["not_executed"],
        "recommended_next_step": "Execute PML=12 dry-run-quality only, then inspect source mask and memory before any pressure authorization.",
    }
    (brief_dir / "gap_feedback.json").write_text(
        json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = "\n".join(
        [
            "# Gap Feedback：simple_hu300 CT PML/boundary review",
            "",
            "## Actual Execution",
            "",
            "- Read dx0.75 PML=8 dry-run-quality summary.",
            "- Generated CT PML/boundary review plan and command templates.",
            "",
            "## Outputs",
            "",
            f"- `{rel(output_dir / 'ct_pml_boundary_review_plan.md')}`",
            f"- `{rel(output_dir / 'ct_pml_boundary_review_plan.json')}`",
            f"- `{rel(output_dir / 'ct_pml_boundary_candidates.csv')}`",
            "",
            "## Decision",
            "",
            f"- dry-run-quality allowed: `{summary['decision']['dry_run_quality_allowed']}`",
            f"- pressure run allowed: `{summary['decision']['pressure_run_allowed']}`",
            f"- next recommended artifact: `{summary['decision']['next_recommended_artifact']}`",
            "",
            "## Not Executed",
            "",
            "- No k-Wave pressure simulation.",
            "- No thermal simulation.",
            "- No paper-grade preset run.",
            "",
        ]
    )
    (brief_dir / "gap_feedback.md").write_text(md, encoding="utf-8-sig")


def parse_pml_values(value: str) -> list[int]:
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate CT PML/boundary review plan for simple_hu300 dx0.75.")
    parser.add_argument("--pml-size", type=parse_pml_values, default=[8, 12, 16])
    parser.add_argument("--output-dir", default="outputs/simple_hu300_ct_pml_boundary_review/079_candidate_006_dx0p75")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = PROJECT_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    data = load_inputs()
    summary = build_summary(data, args.pml_size)
    (output_dir / "ct_pml_boundary_review_plan.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "ct_pml_boundary_review_plan.md").write_text(build_markdown(summary), encoding="utf-8-sig")
    write_csv(output_dir / "ct_pml_boundary_candidates.csv", summary["candidates"])
    write_command_files(output_dir, summary)
    write_gap_feedback(output_dir, summary)
    print(f"Wrote {output_dir / 'ct_pml_boundary_review_plan.md'}")
    print(f"Wrote {output_dir / 'ct_pml_boundary_review_plan.json'}")


if __name__ == "__main__":
    main()
