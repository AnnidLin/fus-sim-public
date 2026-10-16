from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
PLAN_PATH = PROJECT_ROOT / "outputs/p3_numerical_sensitivity_plan/079_candidate_006_dx0p75/p3_numerical_sensitivity_plan.json"
OUT_JSON = PROJECT_ROOT / "outputs/p3_numerical_sensitivity_plan/079_candidate_006_dx0p75/p3_numerical_sensitivity_plan_validation.json"
OUT_MD = PROJECT_ROOT / "outputs/p3_numerical_sensitivity_plan/079_candidate_006_dx0p75/p3_numerical_sensitivity_plan_validation.md"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: str) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": evidence})


def command_tokens(packet: dict[str, Any]) -> list[str]:
    raw = packet.get("planned_runner_command_without_execute", [])
    return [str(item) for item in raw] if isinstance(raw, list) else []


def main() -> None:
    plan = read_json(PLAN_PATH)
    checks: list[dict[str, Any]] = []
    packets = plan.get("packets", [])
    packet_ids = [item.get("packet_id") for item in packets if isinstance(item, dict)]
    command_packets = [item for item in packets if isinstance(item, dict) and item.get("planned_runner_command_without_execute")]

    add(checks, "plan.exists", PLAN_PATH.exists(), rel(PLAN_PATH))
    add(checks, "baseline.kwave_ok", plan.get("baseline", {}).get("runner_status") == "kwave_ok", str(plan.get("baseline", {}).get("runner_status")))
    add(checks, "packets.unique_ids", len(packet_ids) == len(set(packet_ids)), str(packet_ids))
    add(checks, "packets.has_p3a", "P3a_pml16_boundary_sensitivity_authorization" in packet_ids, str(packet_ids))
    add(checks, "packets.has_p3b", "P3b_cfl0p1_timestep_sensitivity_authorization" in packet_ids, str(packet_ids))
    p3a_packet = next(
        (
            item
            for item in packets
            if isinstance(item, dict) and item.get("packet_id") == "P3a_pml16_boundary_sensitivity_authorization"
        ),
        {},
    )
    p3b_packet = next(
        (
            item
            for item in packets
            if isinstance(item, dict) and item.get("packet_id") == "P3b_cfl0p1_timestep_sensitivity_authorization"
        ),
        {},
    )
    p3a_completed = p3a_packet.get("status") == "completed"
    p3b_completed = p3b_packet.get("status") == "completed"
    p3c_packet = next(
        (item for item in packets if isinstance(item, dict) and item.get("packet_id") == "P3c_corrected_dx0p5_grid_sensitivity_prerequisite"),
        {},
    )
    p3c_completed = p3c_packet.get("status") == "completed"
    expected_next = (
        "P5_final_reproducibility_package"
        if p3c_completed
        else "P3c_corrected_dx0p5_grid_sensitivity_prerequisite"
        if p3b_completed
        else
        "P3b_cfl0p1_timestep_sensitivity_authorization"
        if p3a_completed
        else "P3a_pml16_boundary_sensitivity_authorization"
    )
    add(
        checks,
        "plan.immediate_next_matches_state",
        plan.get("immediate_next_packet") == expected_next,
        str(plan.get("immediate_next_packet")),
    )
    add(
        checks,
        "packets.p3a_authorization_state",
        any(
            item.get("packet_id") == "P3a_pml16_boundary_sensitivity_authorization"
            and item.get("status") in {"awaiting_user_authorization", "completed"}
            and item.get("authorization") == "required_before_execute"
            for item in packets
            if isinstance(item, dict)
        ),
        "P3a status/authorization",
    )
    add(
        checks,
        "packets.p3b_state",
        p3b_packet.get("status")
        in {"blocked_until_P3a_review", "awaiting_user_authorization", "completed"},
        str(p3b_packet.get("status")),
    )
    add(
        checks,
        "packets.p3c_state",
        p3c_packet.get("status")
        in {"completed", "planned_coordinate_chain_prerequisite", "blocked_until_dx0p75_sensitivity_review", "blocked_until_dx0p5_corrected_entry_plan"},
        str(p3c_packet.get("status")),
    )
    unauthorized_execute = [
        item.get("packet_id")
        for item in command_packets
        if "--execute" in command_tokens(item) or item.get("authorization") != "required_before_execute"
    ]
    add(checks, "commands.no_execute_flag", not unauthorized_execute, str(unauthorized_execute))
    duplicate_outputs = []
    output_dirs = [item.get("output_dir") for item in command_packets]
    for output_dir in output_dirs:
        if output_dirs.count(output_dir) > 1:
            duplicate_outputs.append(output_dir)
    add(checks, "commands.unique_output_dirs", not duplicate_outputs, str(duplicate_outputs))
    pressure_conflicts = [
        item.get("packet_id")
        for item in command_packets
        if item.get("status") != "completed"
        and (PROJECT_ROOT / str(item.get("output_dir", "")) / "pressure_max_mpa.npz").exists()
    ]
    add(checks, "commands.no_pressure_conflicts", not pressure_conflicts, str(pressure_conflicts))
    not_executed = set(plan.get("not_executed", []))
    expected_not_executed = {"thermal simulation"}
    expected_not_executed.add(
        "additional pressure simulation beyond P3b"
        if p3b_completed
        else "additional pressure simulation beyond P3a"
        if p3a_completed
        else "additional pressure simulation"
    )
    add(checks, "plan.no_unplanned_run_executed", expected_not_executed.issubset(not_executed), str(sorted(not_executed)))
    blocked_claims = set(plan.get("claim_boundary", {}).get("blocked_claims", []))
    add(
        checks,
        "claims.blocked",
        {
            "additional pressure simulation has been authorized",
            "additional pressure simulation has been run",
            "thermal simulation",
            "numerical convergence claim",
            "medical or safety conclusion",
        }.issubset(blocked_claims),
        str(sorted(blocked_claims)),
    )

    failed = [item for item in checks if item["status"] != "pass"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plan_path": rel(PLAN_PATH),
        "plan_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# P3 Numerical Sensitivity Plan Validation\n\n"
        f"- plan valid: `{result['plan_valid']}`\n"
        f"- failed check count: `{result['failed_check_count']}`\n",
        encoding="utf-8",
    )
    print(json.dumps({"plan_valid": result["plan_valid"], "failed_check_count": result["failed_check_count"]}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
