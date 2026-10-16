from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
AUDIT_DIR = ROOT / "outputs/p6b_post_skull_beam_axis_audit/079_candidate_006_dx0p75"
REPORT_PATH = AUDIT_DIR / "beam_axis_profile.json"
OUT_JSON = AUDIT_DIR / "beam_axis_profile_validation.json"
OUT_MD = AUDIT_DIR / "beam_axis_profile_validation.md"

def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: Any) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": str(evidence)})

def main() -> None:
    print("Validating P6b audit results...")
    
    # Check file existence
    checks: list[dict[str, Any]] = []
    
    json_exists = (AUDIT_DIR / "beam_axis_profile.json").exists()
    md_exists = (AUDIT_DIR / "beam_axis_profile.md").exists()
    png_exists = (AUDIT_DIR / "beam_axis_profile.png").exists()
    
    add(checks, "files.json_exists", json_exists, json_exists)
    add(checks, "files.md_exists", md_exists, md_exists)
    add(checks, "files.png_exists", png_exists, png_exists)
    
    if not json_exists:
        print("Missing beam_axis_profile.json report!")
        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "audit_valid": False,
            "failed_check_count": 1,
            "checks": checks,
            "failed_checks": [{"check_id": "files.json_exists", "status": "fail", "evidence": "False"}]
        }
        OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        OUT_MD.write_text("# P6b Audit Validation\n\n- audit valid: `False`\n- failed check count: `1`\n", encoding="utf-8")
        raise SystemExit(1)
        
    audit = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    crossing = audit.get("actual_beam_path_skull_crossing", {})
    decision = audit.get("decision", {})
    
    add(checks, "audit.case", audit.get("case_id") == "079", audit.get("case_id"))
    add(checks, "audit.candidate", audit.get("candidate_id") == "candidate_006", audit.get("candidate_id"))
    add(checks, "beam_axis.zero_bone_crossing", crossing.get("skull_voxels_crossed") == 0, crossing.get("skull_voxels_crossed"))
    add(checks, "beam_axis.max_hu_below_threshold", crossing.get("max_hu_along_beam_path", 999.0) < 300.0, crossing.get("max_hu_along_beam_path"))
    add(checks, "decision.pressure_blocked", decision.get("pressure_execution_authorized") is False, decision.get("pressure_execution_authorized"))
    
    failed = [item for item in checks if item["status"] == "fail"]
    
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audit_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed
    }
    
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(f"# P6b Audit Validation\n\n- audit valid: `{result['audit_valid']}`\n- failed check count: `{len(failed)}`\n", encoding="utf-8")
    
    print(json.dumps({"audit_valid": result["audit_valid"], "failed_check_count": len(failed)}))
    
    if failed:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
