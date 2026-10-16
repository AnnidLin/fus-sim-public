from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
KWAVE_PYTHON = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")


@dataclass(frozen=True)
class Candidate:
    dx_mm: float
    full_shape: tuple[int, int, int]
    required_max_shape: int
    crop_grid_size: tuple[int, int, int]
    nt_estimate: int
    ppw_min_sound_speed: float
    memory_estimate_mb: float
    relative_voxel_count: float
    relative_work: float
    risk_level: str
    role: str
    recommendation: str
    model_output_dir: str
    dry_run_output_dir: str
    future_run_dir: str
    model_build_command: list[str]
    dry_run_command: list[str]
    future_runner_command: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dx_mm": self.dx_mm,
            "full_shape": list(self.full_shape),
            "required_max_shape": self.required_max_shape,
            "crop_grid_size": list(self.crop_grid_size),
            "nt_estimate": self.nt_estimate,
            "ppw_min_sound_speed": self.ppw_min_sound_speed,
            "memory_estimate_mb": self.memory_estimate_mb,
            "relative_voxel_count": self.relative_voxel_count,
            "relative_work": self.relative_work,
            "risk_level": self.risk_level,
            "role": self.role,
            "recommendation": self.recommendation,
            "model_output_dir": self.model_output_dir,
            "dry_run_output_dir": self.dry_run_output_dir,
            "future_run_dir": self.future_run_dir,
            "model_build_command": self.model_build_command,
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
        "paper_grade_readiness": PROJECT_ROOT
        / "outputs/simple_hu300_paper_grade_readiness/079_candidate_006/paper_grade_readiness_summary.json",
        "baseline_reentry": PROJECT_ROOT
        / "outputs/simple_hu300_baseline_reentry/079_candidate_006/baseline_reentry_summary.json",
        "hu300_model_summary": PROJECT_ROOT / "outputs/ct_acoustic_model_3d_profile_hu300/summary.json",
        "standard_review_plan": PROJECT_ROOT / "outputs/ct_standard_review_plan/079_candidate_006/ct_standard_review_plan.json",
        "standard_review_dry_run": PROJECT_ROOT
        / "outputs/ct_standard_review_plan/079_candidate_006/quality_dry_run/quality_dry_run_summary.json",
        "simulation_presets": PROJECT_ROOT / "simulation_presets.json",
    }


def load_inputs() -> dict[str, dict[str, Any] | None]:
    return {name: read_json(path) for name, path in input_paths().items()}


def risk_level(relative_work: float, memory_mb: float, full_shape: tuple[int, int, int]) -> str:
    if max(full_shape) >= 400 or relative_work >= 12 or memory_mb >= 80:
        return "very_high"
    if max(full_shape) >= 300 or relative_work >= 5 or memory_mb >= 30:
        return "high"
    if relative_work >= 2.5 or memory_mb >= 12:
        return "medium"
    return "low"


def dx_tag(dx_mm: float) -> str:
    return str(dx_mm).replace(".", "p").rstrip("0").rstrip("p")


def command_text(command: list[str]) -> str:
    return " ".join(command)


def build_candidates(data: dict[str, dict[str, Any] | None], dx_values: list[float]) -> list[Candidate]:
    model_summary = data["hu300_model_summary"]
    dry = data["standard_review_dry_run"]
    plan = data["standard_review_plan"]
    if model_summary is None or dry is None or plan is None:
        return []

    original_shape = nested(model_summary, ["source", "original_shape_xyz"], [512, 512, 40])
    original_spacing = nested(model_summary, ["source", "original_spacing_mm_xyz"], [0.390625, 0.390625, 5.0])
    physical_mm = [float(s) * float(sp) for s, sp in zip(original_shape, original_spacing)]
    baseline_dx = float(nested(dry, ["simulation_quality", "dx_mm"], 1.0))
    baseline_crop = tuple(int(v) for v in nested(dry, ["simulation_quality", "grid_size"], [66, 45, 35]))
    baseline_nt = int(nested(dry, ["simulation_quality", "nt"], 770))
    baseline_memory = float(nested(dry, ["simulation_quality", "memory_estimate", "estimated_mb"], 2.68))
    sound_speed_min = float(nested(dry, ["simulation_quality", "sound_speed_min_m_s"], 1500.0))
    frequency_hz = float(nested(dry, ["simulation_quality", "frequency_hz"], 500000.0))
    candidate_config = plan.get("candidate_config", {})
    entry_plan_path = str(plan.get("entry_plan_path", "outputs\\case_refinement_plan\\079\\candidate_006\\entry_plan.json"))
    sim_time_us = float(candidate_config.get("sim_time_us", 55.0))
    cycles = int(candidate_config.get("cycles", 8))
    quick_lateral_mm = float(candidate_config.get("quick_lateral_mm", 17.0))
    quick_post_target_mm = float(candidate_config.get("quick_post_target_mm", 8.0))
    aperture_mm = float(candidate_config.get("aperture_mm", 30.0))
    radius_mm = float(candidate_config.get("radius_mm", 35.0))

    baseline_voxels = math.prod(baseline_crop)
    baseline_work = baseline_voxels * baseline_nt
    candidates: list[Candidate] = []
    for dx in dx_values:
        scale = 1.0 if abs(dx - baseline_dx) < 1e-3 else baseline_dx / dx
        full_shape = tuple(max(1, int(round(size / dx))) for size in physical_mm)
        required_max_shape = max(full_shape)
        crop_grid = tuple(max(1, int(math.ceil(v * scale))) for v in baseline_crop)
        nt_estimate = int(math.ceil(baseline_nt * scale))
        ppw = sound_speed_min / (frequency_hz * dx * 1e-3)
        voxels = math.prod(crop_grid)
        relative_voxel = voxels / baseline_voxels
        relative_work = (voxels * nt_estimate) / baseline_work
        memory_mb = baseline_memory * relative_voxel
        risk = risk_level(relative_work, memory_mb, full_shape)
        tag = dx_tag(dx)
        model_dir = f"outputs\\ct_acoustic_model_3d_profile_hu300_dx{tag}"
        dry_dir = f"outputs\\ct_grid_convergence_plan\\079_candidate_006\\dx{tag}_dry_run"
        future_dir = f"outputs\\ct_grid_convergence_runs\\079_candidate_006_dx{tag}_standard"
        model_command = [
            str(KWAVE_PYTHON),
            "build_ct_acoustic_model.py",
            "--nifti-file",
            "data\\raw_ct\\079.nii",
            "--output-dir",
            model_dir,
            "--mapping-profile",
            "acoustic_mapping_profiles\\simple_hu300.json",
            "--target-dx-mm",
            f"{dx:g}",
            "--max-shape",
            str(required_max_shape),
        ]
        model_path = f"{model_dir}\\acoustic_model_3d.npz"
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
            "--execute",
            "--checkpoint-sec",
            "120",
            "--hard-stop-min",
            "30",
        ]
        if abs(dx - baseline_dx) < 1e-3:
            role = "existing_baseline"
            recommendation = "Use existing standard-review dry-run; do not rebuild unless validating reproducibility."
        elif abs(dx - 0.75) < 1e-9:
            role = "recommended_next_model_build_and_dry_run"
            recommendation = "Build model and run dry-run-quality only before any pressure run authorization."
        else:
            role = "risk_estimate_only"
            recommendation = "Do not execute until dx=0.75 model-build/dry-run and standard-run results are reviewed."
        candidates.append(
            Candidate(
                dx_mm=dx,
                full_shape=full_shape,
                required_max_shape=required_max_shape,
                crop_grid_size=crop_grid,
                nt_estimate=nt_estimate,
                ppw_min_sound_speed=ppw,
                memory_estimate_mb=memory_mb,
                relative_voxel_count=relative_voxel,
                relative_work=relative_work,
                risk_level=risk,
                role=role,
                recommendation=recommendation,
                model_output_dir=model_dir,
                dry_run_output_dir=dry_dir,
                future_run_dir=future_dir,
                model_build_command=model_command,
                dry_run_command=dry_command,
                future_runner_command=runner_command,
            )
        )
    return sorted(candidates, key=lambda c: c.dx_mm, reverse=True)


def build_summary(data: dict[str, dict[str, Any] | None], dx_values: list[float]) -> dict[str, Any]:
    paths = {name: rel(path) for name, path in input_paths().items()}
    exists = {name: payload is not None for name, payload in data.items()}
    candidates = build_candidates(data, dx_values)
    recommended = next((item for item in candidates if item.role == "recommended_next_model_build_and_dry_run"), None)
    blockers = []
    if not all(exists.values()):
        blockers.append("missing_required_input")
    paper_ready = nested(data["paper_grade_readiness"], ["decision", "paper_grade_ready"], False)
    if paper_ready:
        blockers.append("unexpected_paper_grade_ready_true_reassess_before_planning")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "CT grid convergence plan only; no CT rebuild; no k-Wave; no pressure output",
        "inputs": {"paths": paths, "exists": exists},
        "decision": {
            "case_id": "079",
            "baseline_profile": "simple_hu300",
            "plan_ready": len(candidates) > 0 and not blockers,
            "execution_authorized": False,
            "next_recommended_artifact": "dx0.75 model-build-only plus dry-run-quality",
            "pressure_run_allowed": False,
            "paper_grade_ready": False,
            "blockers": blockers,
        },
        "baseline_reference": {
            "dx_mm": nested(data["standard_review_dry_run"], ["simulation_quality", "dx_mm"]),
            "grid_size": nested(data["standard_review_dry_run"], ["simulation_quality", "grid_size"]),
            "nt": nested(data["standard_review_dry_run"], ["simulation_quality", "nt"]),
            "ppw_min_sound_speed": nested(data["standard_review_dry_run"], ["simulation_quality", "ppw_min_sound_speed"]),
            "memory_estimate_mb": nested(
                data["standard_review_dry_run"], ["simulation_quality", "memory_estimate", "estimated_mb"]
            ),
        },
        "candidates": [candidate.to_dict() for candidate in candidates],
        "recommended_candidate": None if recommended is None else recommended.to_dict(),
        "guardrails": [
            "Do not execute pressure runs from this plan.",
            "First create the dx=0.75 CT acoustic model as model-build-only evidence.",
            "Then run dry-run-quality for dx=0.75 and inspect source mask, PPW, PML, CFL, grid size, nt, memory estimate.",
            "Only after those pass should a single dx=0.75 standard pressure run be considered for explicit user authorization.",
            "dx=0.5 remains risk-estimate only until dx=0.75 is reviewed.",
        ],
        "not_executed": [
            "CT model rebuild",
            "k-Wave dry-run-quality execution",
            "k-Wave pressure simulation",
            "thermal simulation",
        ],
    }


def write_csv(path: Path, candidates: list[dict[str, Any]]) -> None:
    fieldnames = [
        "dx_mm",
        "full_shape",
        "required_max_shape",
        "crop_grid_size",
        "nt_estimate",
        "ppw_min_sound_speed",
        "memory_estimate_mb",
        "relative_voxel_count",
        "relative_work",
        "risk_level",
        "role",
        "recommendation",
        "model_output_dir",
        "dry_run_output_dir",
        "future_run_dir",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for candidate in candidates:
            row = dict(candidate)
            row["full_shape"] = "x".join(str(v) for v in row["full_shape"])
            row["crop_grid_size"] = "x".join(str(v) for v in row["crop_grid_size"])
            writer.writerow({key: row.get(key) for key in fieldnames})


def build_markdown(summary: dict[str, Any]) -> str:
    decision = summary["decision"]
    lines = [
        "# simple_hu300 CT Grid-convergence Plan",
        "",
        "> Scope: read-only estimates and command templates. No CT rebuild, dry-run-quality execution, k-Wave pressure run, or thermal run was executed.",
        "",
        "## Decision",
        "",
        f"- case: `{decision['case_id']}`",
        f"- baseline profile: `{decision['baseline_profile']}`",
        f"- plan ready: `{decision['plan_ready']}`",
        f"- execution authorized: `{decision['execution_authorized']}`",
        f"- pressure run allowed: `{decision['pressure_run_allowed']}`",
        f"- paper-grade ready: `{decision['paper_grade_ready']}`",
        f"- next recommended artifact: `{decision['next_recommended_artifact']}`",
        "",
        "## Candidate Estimates",
        "",
        "| dx mm | full shape | max-shape | crop grid | nt | PPW | memory MB | rel work | risk | role |",
        "| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for candidate in summary["candidates"]:
        lines.append(
            f"| {candidate['dx_mm']:.3f} | {'x'.join(str(v) for v in candidate['full_shape'])} | "
            f"{candidate['required_max_shape']} | {'x'.join(str(v) for v in candidate['crop_grid_size'])} | "
            f"{candidate['nt_estimate']} | {candidate['ppw_min_sound_speed']:.3f} | "
            f"{candidate['memory_estimate_mb']:.3f} | {candidate['relative_work']:.2f} | "
            f"{candidate['risk_level']} | {candidate['role']} |"
        )

    recommended = summary["recommended_candidate"]
    if recommended:
        lines.extend(
            [
                "",
                "## Recommended Next Artifact",
                "",
                f"- dx: `{recommended['dx_mm']}` mm",
                f"- action: `{recommended['recommendation']}`",
                f"- model output: `{recommended['model_output_dir']}`",
                f"- dry-run output: `{recommended['dry_run_output_dir']}`",
                "",
                "Model-build command template, not executed:",
                "",
                "```powershell",
                command_text(recommended["model_build_command"]),
                "```",
                "",
                "Dry-run-quality command template, not executed:",
                "",
                "```powershell",
                command_text(recommended["dry_run_command"]),
                "```",
                "",
                "Future pressure runner template, blocked until explicit authorization:",
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
    (output_dir / "recommended_model_build_command.ps1").write_text(
        "# Template only. Requires explicit decision before execution.\n"
        + command_text(recommended["model_build_command"])
        + "\n",
        encoding="utf-8-sig",
    )
    (output_dir / "recommended_dry_run_quality_command.ps1").write_text(
        "# Template only. Run only after model-build artifact exists.\n"
        + command_text(recommended["dry_run_command"])
        + "\n",
        encoding="utf-8-sig",
    )
    (output_dir / "blocked_future_pressure_runner_command.ps1").write_text(
        "# BLOCKED. Do not run without explicit user authorization after model-build and dry-run-quality pass.\n"
        + command_text(recommended["future_runner_command"])
        + "\n",
        encoding="utf-8-sig",
    )


def write_gap_feedback(output_dir: Path, summary: dict[str, Any]) -> None:
    brief_dir = PROJECT_ROOT / "outputs/evidence_briefs/simple_hu300_ct_grid_convergence_plan"
    brief_dir.mkdir(parents=True, exist_ok=True)
    feedback = {
        "module": "simple_hu300_ct_grid_convergence_plan",
        "feedback_type": "post_execution_gap_feedback",
        "executed_scope": [
            "read paper-grade readiness and baseline re-entry summaries",
            "estimated CT grid convergence candidates from existing dx=1.0 dry-run metadata",
            "generated model-build, dry-run-quality, and blocked future runner command templates",
        ],
        "outputs": {
            "report": rel(output_dir / "ct_grid_convergence_plan.md"),
            "summary": rel(output_dir / "ct_grid_convergence_plan.json"),
            "csv": rel(output_dir / "ct_grid_convergence_candidates.csv"),
        },
        "decision": summary["decision"],
        "not_executed": summary["not_executed"],
        "remaining_gaps": [
            "dx=0.75 CT model has not been built.",
            "dx=0.75 dry-run-quality has not been executed.",
            "No CT grid convergence pressure comparison exists.",
        ],
        "recommended_next_step": "If continuing without pressure, build the dx=0.75 simple_hu300 CT model and run dry-run-quality only; do not run pressure yet.",
    }
    (brief_dir / "gap_feedback.json").write_text(
        json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = "\n".join(
        [
            "# Gap Feedback：simple_hu300 CT grid convergence plan",
            "",
            "## Actual Execution",
            "",
            "- Read existing `simple_hu300` baseline and paper-grade readiness artifacts.",
            "- Estimated CT grid-convergence candidate costs from the current dx=1.0 standard dry-run.",
            "- Generated command templates only.",
            "",
            "## Outputs",
            "",
            f"- `{rel(output_dir / 'ct_grid_convergence_plan.md')}`",
            f"- `{rel(output_dir / 'ct_grid_convergence_plan.json')}`",
            f"- `{rel(output_dir / 'ct_grid_convergence_candidates.csv')}`",
            "",
            "## Decision",
            "",
            f"- plan ready: `{summary['decision']['plan_ready']}`",
            f"- pressure run allowed: `{summary['decision']['pressure_run_allowed']}`",
            f"- next recommended artifact: `{summary['decision']['next_recommended_artifact']}`",
            "",
            "## Not Executed",
            "",
            "- No CT model rebuild.",
            "- No k-Wave dry-run-quality execution.",
            "- No k-Wave pressure simulation.",
            "- No thermal simulation.",
            "",
        ]
    )
    (brief_dir / "gap_feedback.md").write_text(md, encoding="utf-8-sig")


def parse_dx_values(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a read-only CT grid-convergence plan for simple_hu300.")
    parser.add_argument("--dx-mm", type=parse_dx_values, default=[1.0, 0.75, 0.5])
    parser.add_argument("--output-dir", default="outputs/simple_hu300_ct_grid_convergence_plan/079_candidate_006")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = PROJECT_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    data = load_inputs()
    summary = build_summary(data, args.dx_mm)
    (output_dir / "ct_grid_convergence_plan.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "ct_grid_convergence_plan.md").write_text(build_markdown(summary), encoding="utf-8-sig")
    write_csv(output_dir / "ct_grid_convergence_candidates.csv", summary["candidates"])
    write_command_files(output_dir, summary)
    write_gap_feedback(output_dir, summary)
    print(f"Wrote {output_dir / 'ct_grid_convergence_plan.md'}")
    print(f"Wrote {output_dir / 'ct_grid_convergence_plan.json'}")


if __name__ == "__main__":
    main()
