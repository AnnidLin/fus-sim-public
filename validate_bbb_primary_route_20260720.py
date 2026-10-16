from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LIT = ROOT / "literature_tFUS_review"


def main() -> None:
    route = (LIT / "18_BBB个体化药物递送规划主线.md").read_text(encoding="utf-8")
    integrated = (LIT / "17_四篇本地论文整合与个体化治疗规划路线.md").read_text(encoding="utf-8")
    bbb_moc = (LIT / "MOC_BBB微泡与空化监测.md").read_text(encoding="utf-8")
    board = (LIT / "实验平台阶段看板.md").read_text(encoding="utf-8")
    todo = (ROOT / "AI_TODO.md").read_text(encoding="utf-8")
    han_note = (LIT / "notes" / "28_Han2015_transcranial_brain_tumor_HIFU_review.md").read_text(encoding="utf-8")
    brief = json.loads((ROOT / "outputs" / "evidence_briefs" / "bbb_personalized_drug_delivery_route" / "evidence_brief.json").read_text(encoding="utf-8"))
    registry_source = (ROOT / "generate_evidence_registry.py").read_text(encoding="utf-8")

    checks = {
        "primary_application_is_bbb_drug_delivery": "平台的首要应用明确为" in route and "BBB" in route and "药物" in route,
        "path_is_acoustic_not_euclidean": "最小声学代价路径" in route and "不代表超声传播最优" in route,
        "path_uses_skull_and_angle": all(term in route for term in ("颅骨的总长度", "入射角", "HU", "颅骨吸收")),
        "roi_coverage_is_required": "ROI 覆盖率" in route,
        "physical_array_is_required": "物理阵元" in route,
        "bbb_dose_is_multivariable": all(term in route for term in ("in-situ PNP", "MI", "burst length", "微泡协议")),
        "pcd_closed_loop_is_required": "PCD/AE 闭环" in route and "宽带声发射" in route,
        "drug_amount_is_not_claimed_from_acoustics": "仅凭声场不能直接预测" in route,
        "microbubble_dose_is_not_free_variable": "不是可以脱离产品" in route,
        "fixed_power_is_rejected": "固定输入功率" in route and "不是" in route,
        "clinical_dose_claim_blocked": "不输出临床处方" in route and "最佳 BBB 开放能量" in route,
        "four_paper_route_reframed": "首要应用是聚焦超声联合微泡开放 BBB" in integrated,
        "han_hifu_role_is_method_only": "HIFU 热消融剂量不是平台主目标" in han_note,
        "bbb_moc_is_primary": "BBB 开放与药物递送现为平台首要应用" in bbb_moc,
        "pan_mi_is_not_universal": "不是跨微泡、设备、物种或患者通用" in bbb_moc,
        "board_no_longer_deprioritizes_bbb": "不优先扩展 BBB" not in board and "P4 BBB 个体化升级" in board,
        "todo_has_application_anchor": "BBB Drug-Delivery Application Anchor" in todo,
        "brief_is_planning_only": brief["status"] == "planning_only",
        "bbb_pressure_not_authorized": brief["bbb_pressure_execution_authorized"] is False,
        "microbubble_recommendation_not_authorized": brief["microbubble_dose_recommendation_authorized"] is False,
        "registry_generator_tracks_brief": "bbb_personalized_route_brief" in registry_source,
        "patient_evidence_links_present": all(pmid in route for pmid in ("41395575", "38897294", "38531173")),
    }
    result = {
        "status": "pass" if all(checks.values()) else "fail",
        "passed": sum(checks.values()),
        "total": len(checks),
        "checks": checks,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
