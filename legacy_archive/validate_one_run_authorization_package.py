from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
PACKAGE_PATH = PROJECT_ROOT / "outputs/one_run_authorization_package/079_candidate_006/one_run_authorization_package.json"
OUT_JSON = PROJECT_ROOT / "outputs/one_run_authorization_package/079_candidate_006/one_run_authorization_package_validation.json"
EXPECTED_GRID_DX0P5_HARD_STOP_MIN = 75


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: str) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": evidence})


def main() -> None:
    package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8-sig"))
    checks: list[dict[str, Any]] = []
    decision = package.get("decision", {})
    candidates = package.get("candidates", [])
    recommended = package.get("recommended_candidate")
    context = package.get("completed_context", {})
    resolution_gate = context.get("entry_plan_resolution_gate", {})
    resolution_blocked = resolution_gate.get("status") == "block"
    add(checks, "module", package.get("module") == "one_run_authorization_package", str(package.get("module")))
    add(checks, "package.ready_or_resolution_blocked", (decision.get("package_ready") is True) or resolution_blocked, str(decision))
    add(checks, "pressure.blocked", decision.get("pressure_execution_allowed_now") is False, str(decision))
    add(checks, "authorization.required", decision.get("requires_explicit_user_authorization") is True, str(decision))
    if resolution_blocked:
        add(checks, "resolution_gate.blocks", decision.get("package_ready") is False and recommended is None, str(resolution_gate))
    else:
        add(checks, "recommended.exists", isinstance(recommended, dict), str(recommended))
        add(checks, "recommended.one", decision.get("recommended_candidate_id") == recommended.get("candidate_id"), str(decision))
        add(checks, "candidates.nonempty", len(candidates) >= 1, f"count={len(candidates)}")
        add(
            checks,
            "recommended.grid",
            recommended.get("candidate_id") == "grid_dx0p5_pressure_comparison",
            str(recommended.get("candidate_id")),
        )
    add(
        checks,
        "context.cfl_pml_complete",
        context.get("numerical_sensitivity_status") == "cfl_and_pml_context_present",
        str(context),
    )
    output_dir = None if recommended is None else recommended.get("output_dir")
    pressure_exists = bool(output_dir) and (PROJECT_ROOT / output_dir / "pressure_max_mpa.npz").exists()
    runner_status_path = PROJECT_ROOT / output_dir / "runner_status.json" if output_dir else None
    completed_authorized_output = False
    if runner_status_path and runner_status_path.exists():
        runner_status = json.loads(runner_status_path.read_text(encoding="utf-8-sig"))
        completed_authorized_output = (
            runner_status.get("status") == "kwave_ok"
            and bool(runner_status.get("execute"))
            and runner_status.get("output_dir") == output_dir
        )
    add(
        checks,
        "output.no_conflict_or_completed_authorized",
        (not pressure_exists) or completed_authorized_output,
        str({"output_dir": output_dir, "pressure_exists": pressure_exists, "completed_authorized_output": completed_authorized_output}),
    )
    add(
        checks,
        "budget.hard_stop_expected",
        package.get("run_budget", {}).get("hard_stop_min") == EXPECTED_GRID_DX0P5_HARD_STOP_MIN,
        str(package.get("run_budget")),
    )
    command = [] if recommended is None else recommended.get("command") or []
    command_hard_stop = None
    if "--hard-stop-min" in command:
        index = command.index("--hard-stop-min")
        if index + 1 < len(command):
            command_hard_stop = int(command[index + 1])
    add(
        checks,
        "command.hard_stop_matches_budget_or_resolution_blocked",
        resolution_blocked or command_hard_stop == package.get("run_budget", {}).get("hard_stop_min"),
        str(command),
    )
    command_pml_size = None
    if "--pml-size" in command:
        index = command.index("--pml-size")
        if index + 1 < len(command):
            command_pml_size = int(command[index + 1])
    add(checks, "command.pml_size_standard_or_resolution_blocked", resolution_blocked or command_pml_size == 12, str(command))
    command_cfl = None
    if "--cfl" in command:
        index = command.index("--cfl")
        if index + 1 < len(command):
            command_cfl = float(command[index + 1])
    add(checks, "command.cfl_standard_or_resolution_blocked", resolution_blocked or command_cfl == 0.2, str(command))
    not_executed = set(package.get("not_executed", []))
    add(checks, "not_executed.no_pressure", "k-Wave pressure simulation" in not_executed, str(sorted(not_executed)))
    failed = [item for item in checks if item["status"] != "pass"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "one_run_authorization_package_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"one_run_authorization_package_valid": result["one_run_authorization_package_valid"], "failed_check_count": len(failed)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
