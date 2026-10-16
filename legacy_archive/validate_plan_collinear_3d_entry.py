from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np

ROOT = Path(__file__).resolve().parent
PLAN_DIR = ROOT / "outputs/collinear_entry_planning/079_candidate_006_dx0p75"
REPORT_PATH = PLAN_DIR / "collinear_entry_plan.json"
OUT_JSON = PLAN_DIR / "validation.json"
OUT_MD = PLAN_DIR / "validation.md"

def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: Any) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": str(evidence)})

def main() -> None:
    print("Validating collinear entry plan...")
    checks: list[dict[str, Any]] = []
    
    json_exists = REPORT_PATH.exists()
    axial_exists = (PLAN_DIR / "entry_layout_axial.png").exists()
    coronal_exists = (PLAN_DIR / "entry_layout_coronal.png").exists()
    
    add(checks, "files.json_exists", json_exists, json_exists)
    add(checks, "files.axial_exists", axial_exists, axial_exists)
    add(checks, "files.coronal_exists", coronal_exists, coronal_exists)
    
    if not json_exists:
        print("Missing collinear_entry_plan.json!")
        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "plan_valid": False,
            "failed_check_count": 1,
            "checks": checks,
            "failed_checks": [{"check_id": "files.json_exists", "status": "fail", "evidence": "False"}]
        }
        OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        OUT_MD.write_text("# Collinear Entry Plan Validation\n\n- plan valid: `False`\n- failed check count: `1`\n", encoding="utf-8")
        raise SystemExit(1)
        
    plan = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    
    # Coordinates
    source = np.array(plan["source_center_index_ijk"])
    entry = np.array(plan["entry_index_ijk"])
    target = np.array(plan["target_index_ijk"])
    
    # Vector collinearity checks
    vec_se = entry - source
    vec_st = target - source
    norm_se = np.linalg.norm(vec_se)
    norm_st = np.linalg.norm(vec_st)
    
    cos_sim = float(np.dot(vec_se, vec_st) / (norm_se * norm_st)) if norm_se > 0 and norm_st > 0 else 0.0
    
    add(checks, "collinear.cos_similarity", cos_sim > 0.99, cos_sim)
    add(checks, "collinear.has_skull_crossing", plan.get("has_skull_crossing") is True, plan.get("has_skull_crossing"))
    add(checks, "collinear.skull_path_length_mm", plan.get("skull_path_length_mm", 0.0) > 0.0, plan.get("skull_path_length_mm"))
    add(checks, "safety.source_label", plan.get("source_center_label") == 0, plan.get("source_center_label"))
    add(checks, "safety.entry_label", plan.get("entry_label") == 2, plan.get("entry_label"))
    add(checks, "safety.target_label", plan.get("target_label") == 1, plan.get("target_label"))
    
    failed = [item for item in checks if item["status"] == "fail"]
    
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plan_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed
    }
    
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(f"# Collinear Entry Plan Validation\n\n- plan valid: `{result['plan_valid']}`\n- failed check count: `{len(failed)}`\n", encoding="utf-8")
    
    print(json.dumps({"plan_valid": result["plan_valid"], "failed_check_count": len(failed)}))
    
    if failed:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
