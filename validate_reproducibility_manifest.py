from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = PROJECT_ROOT / "outputs/reproducibility_manifest/case_079_reproducibility_manifest.json"
OUT_JSON = PROJECT_ROOT / "outputs/reproducibility_manifest/case_079_reproducibility_manifest_validation.json"
OUT_MD = PROJECT_ROOT / "outputs/reproducibility_manifest/case_079_reproducibility_manifest_validation.md"


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: str) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": evidence})


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
    checks: list[dict[str, Any]] = []

    add(checks, "manifest.case", manifest.get("case_id") == "079", str(manifest.get("case_id")))
    add(checks, "manifest.planned_packets", bool(manifest.get("planned_packets")), "planned packet count")
    statuses = {packet.get("status") for packet in manifest.get("planned_packets", [])}
    add(
        checks,
        "manifest.separates_planned",
        bool(statuses.intersection({"planned", "completed", "awaiting_user_authorization"})),
        str(sorted(statuses)),
    )
    add(checks, "manifest.invalidated_present", bool(manifest.get("invalidated_runs")), str(manifest.get("invalidated_runs")))
    add(checks, "manifest.blocked_present", bool(manifest.get("blocked_runs")), str(manifest.get("blocked_runs")))
    p1_complete = any(
        packet.get("packet_id") == "P1_correct_entry_plan_dx0p75" and packet.get("status") == "completed"
        for packet in manifest.get("planned_packets", [])
    )
    p2_complete = any(
        packet.get("packet_id") == "P2_corrected_dx0p75_standard_pressure" and packet.get("status") == "completed"
        for packet in manifest.get("planned_packets", [])
    )
    p4_complete = any(
        packet.get("packet_id") == "P4_corrected_pennes_thermal" and packet.get("status") == "completed"
        for packet in manifest.get("planned_packets", [])
    )
    p5_complete = any(
        packet.get("packet_id") == "P5_final_reproducibility_package" and packet.get("status") == "completed"
        for packet in manifest.get("planned_packets", [])
    )
    expected_next = (
        "P6b_post_skull_beam_axis_profile_and_interface_audit"
        if p5_complete
        else "P5_final_reproducibility_package"
        if p4_complete
        else "P4_corrected_pennes_thermal"
        if p2_complete
        else "P2_corrected_dx0p75_standard_pressure"
        if p1_complete
        else "P1_correct_entry_plan_dx0p75"
    )
    add(checks, "manifest.next_packet", manifest.get("immediate_next_packet") == expected_next, str(manifest.get("immediate_next_packet")))
    pressure_like_packets = [
        packet
        for packet in manifest.get("planned_packets", [])
        if "pressure" in packet.get("packet_id", "").lower() or "thermal" in packet.get("packet_id", "").lower()
    ]
    missing_gates = [
        packet.get("packet_id")
        for packet in pressure_like_packets
        if not packet.get("required_gates") or packet.get("authorization") != "required"
    ]
    add(checks, "manifest.real_runs_have_gates", not missing_gates, str(missing_gates))
    forbidden_executed = set(manifest.get("not_executed_by_manifest", []))
    expected_not_executed = set()
    if not p4_complete:
        expected_not_executed.add("thermal simulation")
    if not p2_complete:
        expected_not_executed.add("pressure simulation")
    else:
        expected_not_executed.add("additional pressure simulation beyond P2")
    add(
        checks,
        "manifest.no_execution_by_manifest",
        expected_not_executed.issubset(forbidden_executed),
        str(sorted(forbidden_executed)),
    )

    failed = [item for item in checks if item["status"] != "pass"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# Reproducibility Manifest Validation\n\n"
        f"- manifest valid: `{result['manifest_valid']}`\n"
        f"- failed check count: `{result['failed_check_count']}`\n",
        encoding="utf-8",
    )
    print(json.dumps({"manifest_valid": result["manifest_valid"], "failed_check_count": len(failed)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
