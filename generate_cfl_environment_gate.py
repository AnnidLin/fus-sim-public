from __future__ import annotations

import importlib.metadata
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
MODULE = "cfl_environment_gate"
OUT_DIR = PROJECT_ROOT / "outputs" / MODULE
BRIEF_DIR = PROJECT_ROOT / "outputs" / "evidence_briefs" / MODULE


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


def paths() -> dict[str, Path]:
    run_dir = PROJECT_ROOT / "outputs/ct_standard_pressure_authorization/079_candidate_006_dx0p75_pml12_standard"
    return {
        "evidence_brief": BRIEF_DIR / "evidence_brief.json",
        "standard_pressure_execution": run_dir / "standard_pressure_execution_summary.json",
        "kwave_summary": run_dir / "summary.json",
        "runner_status": run_dir / "runner_status.json",
        "quality_dry_run": run_dir / "quality_dry_run_summary.json",
        "simulation_presets": PROJECT_ROOT / "simulation_presets.json",
        "environment_install_record": PROJECT_ROOT / "环境安装记录.md",
    }


def package_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def observe_current_environment() -> dict[str, Any]:
    packages = {
        "numpy": package_version("numpy"),
        "scipy": package_version("scipy"),
        "matplotlib": package_version("matplotlib"),
        "h5py": package_version("h5py"),
        "k-wave-python": package_version("k-wave-python"),
        "kwave": package_version("kwave"),
    }
    return {
        "observation_scope": "current_environment_only_not_historical_run_capture",
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "packages": {key: value for key, value in packages.items() if value is not None},
    }


def add_check(
    checks: list[dict[str, Any]],
    check_id: str,
    title: str,
    status: str,
    evidence: str,
    source: str,
    recommended_next: str,
    blocks_paper_grade: bool,
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "title": title,
            "status": status,
            "evidence": evidence,
            "source": source,
            "recommended_next": recommended_next,
            "blocks_paper_grade": blocks_paper_grade,
        }
    )


def build_gate() -> dict[str, Any]:
    p = paths()
    inputs = {name: read_json(path) for name, path in p.items() if path.suffix == ".json"}
    standard = inputs["standard_pressure_execution"]
    summary = inputs["kwave_summary"]
    runner = inputs["runner_status"]
    presets = inputs["simulation_presets"]
    quality = nested(summary, ["simulation_quality"], {}) or nested(standard, ["simulation_quality"], {})
    runtime = nested(summary, ["runtime"], {})
    standard_preset = nested(presets, ["presets", "standard"], {})

    checks: list[dict[str, Any]] = []
    for name, path in p.items():
        if path.suffix == ".json":
            parsed = inputs.get(name) is not None
            add_check(
                checks,
                f"input.{name}",
                f"Input available: {name}",
                "pass" if parsed else "block",
                "JSON parsed" if parsed else "missing or unparsable",
                rel(path),
                "No action." if parsed else "Restore the required input before evaluating this gate.",
                not parsed,
            )
        else:
            exists = path.exists()
            add_check(
                checks,
                f"input.{name}",
                f"Input available: {name}",
                "pass" if exists else "warn",
                "file exists" if exists else "file missing",
                rel(path),
                "No action." if exists else "Restore or regenerate the environment install record.",
                False,
            )

    preset = nested(standard, ["preset"])
    cfl = nested(quality, ["cfl"])
    pml_size = nested(quality, ["pml_size"])
    ppw = nested(quality, ["ppw_min_sound_speed"])
    grid = nested(quality, ["grid_size"])
    dt_s = nested(quality, ["dt_s"], nested(runtime, ["dt_s"]))
    nt = nested(quality, ["nt"], nested(runtime, ["nt"]))
    backend = nested(quality, ["backend"], nested(runtime, ["backend"]))
    device = nested(quality, ["device"], nested(runtime, ["device"]))
    runtime_s = nested(quality, ["runtime_s"], nested(runtime, ["runtime_s"]))
    memory_mb = nested(quality, ["memory_estimate", "estimated_mb"], nested(quality, ["memory_estimate_mb"]))

    add_check(
        checks,
        "preset.standard",
        "Run preset is standard",
        "pass" if preset == "standard" else "block",
        f"preset={preset}",
        rel(p["standard_pressure_execution"]),
        "Use this as engineering evidence only; do not relabel as paper-grade.",
        preset != "standard",
    )
    add_check(
        checks,
        "cfl.value_present",
        "CFL value is recorded",
        "pass" if isinstance(cfl, (int, float)) else "block",
        f"cfl={cfl}",
        rel(p["kwave_summary"]),
        "Keep CFL in every future run summary.",
        not isinstance(cfl, (int, float)),
    )
    add_check(
        checks,
        "cfl.standard_value",
        "CFL matches current standard-run value",
        "pass" if cfl == 0.2 else "warn",
        f"cfl={cfl}; expected_current_standard=0.2",
        rel(p["kwave_summary"]),
        "If changing CFL, create a separate CFL sensitivity plan.",
        False,
    )
    add_check(
        checks,
        "pml.value_present",
        "PML size is recorded",
        "pass" if isinstance(pml_size, int) else "block",
        f"pml_size={pml_size}",
        rel(p["kwave_summary"]),
        "Keep PML size in every future run summary.",
        not isinstance(pml_size, int),
    )
    add_check(
        checks,
        "runtime.fields_present",
        "Runtime fields required by standard preset are present",
        "pass" if all(value is not None for value in [grid, dt_s, nt, runtime_s, backend, device, memory_mb]) else "warn",
        f"grid={grid}; dt_s={dt_s}; nt={nt}; runtime_s={runtime_s}; backend={backend}; device={device}; memory_mb={memory_mb}",
        rel(p["kwave_summary"]),
        "Fill any missing runtime fields before stronger interpretation.",
        False,
    )
    add_check(
        checks,
        "runner.discipline",
        "Runner discipline is recorded",
        "pass"
        if nested(runner, ["status"]) == "kwave_ok"
        and nested(runner, ["uses_start_process"]) is False
        and nested(runner, ["uses_powershell_job"]) is False
        else "block",
        f"status={nested(runner, ['status'])}; uses_start_process={nested(runner, ['uses_start_process'])}; uses_powershell_job={nested(runner, ['uses_powershell_job'])}",
        rel(p["runner_status"]),
        "Keep using runner-gated execution for any future pressure run.",
        nested(runner, ["status"]) != "kwave_ok",
    )

    required_standard = set(standard_preset.get("required_summary_fields", []))
    historical_environment_fields = {
        "backend": backend,
        "device": device,
        "runtime_s": runtime_s,
        "python_version": nested(summary, ["environment_record", "python_version"]),
        "kwave_python_version": nested(summary, ["environment_record", "kwave_python_version"]),
        "platform": nested(summary, ["environment_record", "platform"]),
    }
    missing_environment = [key for key, value in historical_environment_fields.items() if value in (None, "")]
    add_check(
        checks,
        "environment.historical_record",
        "Historical run environment record is partial",
        "warn" if missing_environment else "pass",
        f"missing_environment_fields={missing_environment}",
        rel(p["kwave_summary"]),
        "Record Python, package, platform, and hardware fields in future runner summaries.",
        False,
    )
    add_check(
        checks,
        "paper_grade.required_environment",
        "Paper-grade environment requirement remains blocked",
        "block",
        f"standard_required_fields={sorted(required_standard)}; missing_environment_fields={missing_environment}",
        rel(p["simulation_presets"]),
        "Do not claim paper-grade until environment record plus grid/PML/CFL sensitivity evidence exists.",
        True,
    )

    current_environment = observe_current_environment()
    blocking = [item for item in checks if item["blocks_paper_grade"]]
    status = "block" if blocking else "pass"
    return {
        "gate_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "module": MODULE,
        "scope": "read-only CFL and environment gate for current simple_hu300 standard pressure output",
        "inputs": {
            "paths": {name: rel(path) for name, path in p.items()},
            "missing": [name for name, path in p.items() if not path.exists()],
        },
        "decision": {
            "gate_status": status,
            "pressure_execution_allowed": False,
            "paper_grade_ready": False,
            "medical_or_safety_conclusion_allowed": False,
            "profile_promotion_allowed": False,
            "cfl_metadata_present": isinstance(cfl, (int, float)),
            "environment_record_status": "partial" if missing_environment else "complete",
            "recommended_next_action": "Record complete environment metadata and plan numerical sensitivity before any additional pressure run.",
        },
        "observed_run_quality": {
            "preset": preset,
            "cfl": cfl,
            "pml_size": pml_size,
            "ppw_min_sound_speed": ppw,
            "grid_size": grid,
            "dt_s": dt_s,
            "nt": nt,
            "backend": backend,
            "device": device,
            "runtime_s": runtime_s,
            "memory_estimate_mb": memory_mb,
        },
        "historical_environment_record": historical_environment_fields,
        "missing_environment_fields": missing_environment,
        "current_environment_observation": current_environment,
        "checks": checks,
        "blocked_claims": [
            "paper-grade reproduction",
            "validated pressure baseline",
            "medical or safety conclusion",
            "source-backed alpha pressure eligibility",
            "profile/default promotion",
        ],
        "not_executed": [
            "k-Wave simulation",
            "thermal simulation",
            "paper-grade run",
            "profile/default promotion",
        ],
    }


def markdown(gate: dict[str, Any]) -> str:
    q = gate["observed_run_quality"]
    lines = [
        "# CFL / Environment Gate",
        "",
        f"- gate status: `{gate['decision']['gate_status']}`",
        f"- pressure execution allowed: `{gate['decision']['pressure_execution_allowed']}`",
        f"- paper-grade ready: `{gate['decision']['paper_grade_ready']}`",
        f"- environment record status: `{gate['decision']['environment_record_status']}`",
        "",
        "## Observed Run Quality",
        "",
        f"- preset: `{q['preset']}`",
        f"- CFL: `{q['cfl']}`",
        f"- PML size: `{q['pml_size']}`",
        f"- PPW min sound speed: `{q['ppw_min_sound_speed']}`",
        f"- grid size: `{q['grid_size']}`",
        f"- backend/device: `{q['backend']}` / `{q['device']}`",
        f"- runtime seconds: `{q['runtime_s']}`",
        "",
        "## Missing Environment Fields",
        "",
    ]
    if gate["missing_environment_fields"]:
        lines.extend(f"- `{item}`" for item in gate["missing_environment_fields"])
    else:
        lines.append("- none")
    lines.extend(["", "## Checks", "", "| Status | Check | Evidence |", "|---|---|---|"])
    for item in gate["checks"]:
        evidence = str(item["evidence"]).replace("\n", " ")
        if len(evidence) > 180:
            evidence = evidence[:177] + "..."
        lines.append(f"| `{item['status']}` | `{item['check_id']}` | {evidence} |")
    lines.extend(["", "## Not Executed", ""])
    lines.extend(f"- {item}" for item in gate["not_executed"])
    lines.append("")
    return "\n".join(lines)


def write_outputs(gate: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    gate_json = OUT_DIR / "cfl_environment_gate.json"
    gate_md = OUT_DIR / "cfl_environment_gate.md"
    gate_json.write_text(json.dumps(gate, indent=2, ensure_ascii=False), encoding="utf-8")
    gate_md.write_text(markdown(gate), encoding="utf-8")

    feedback = {
        "module": MODULE,
        "feedback_type": "post_execution_gap_feedback",
        "executed_scope": [
            "read existing standard pressure run summaries",
            "checked CFL/PML/runtime metadata",
            "recorded current environment observation without claiming historical equivalence",
            "kept pressure and paper-grade claims blocked",
        ],
        "outputs": {
            "gate_json": rel(gate_json),
            "gate_md": rel(gate_md),
        },
        "decision": gate["decision"],
        "warnings": [
            "Historical environment record is partial.",
            "Current environment observation is not a complete historical run capture.",
        ],
        "not_executed": gate["not_executed"],
        "recommended_next_step": gate["decision"]["recommended_next_action"],
    }
    (BRIEF_DIR / "gap_feedback.json").write_text(json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8")
    (BRIEF_DIR / "gap_feedback.md").write_text(
        "# Gap Feedback: CFL / Environment Gate\n\n"
        "## Decision\n\n"
        f"- gate status: `{gate['decision']['gate_status']}`\n"
        f"- pressure execution allowed: `{gate['decision']['pressure_execution_allowed']}`\n"
        f"- paper-grade ready: `{gate['decision']['paper_grade_ready']}`\n"
        f"- environment record status: `{gate['decision']['environment_record_status']}`\n\n"
        "## Outputs\n\n"
        f"- `{rel(gate_json)}`\n"
        f"- `{rel(gate_md)}`\n\n"
        "## Warnings\n\n"
        "- Historical environment record is partial.\n"
        "- Current environment observation is not a complete historical run capture.\n\n"
        "## Not Executed\n\n"
        "- No k-Wave simulation.\n"
        "- No thermal simulation.\n"
        "- No paper-grade run.\n"
        "- No profile/default promotion.\n",
        encoding="utf-8",
    )


def main() -> None:
    gate = build_gate()
    write_outputs(gate)
    print(f"Wrote {rel(OUT_DIR / 'cfl_environment_gate.json')}")
    print(f"Wrote {rel(OUT_DIR / 'cfl_environment_gate.md')}")


if __name__ == "__main__":
    main()
