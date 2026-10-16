from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LIT = ROOT / "literature_tFUS_review"
PDF = Path(r"<LOCAL_REFERENCE_DATA>\科研项目\经颅脑肿瘤HIFU治疗技术的研究现状_韩珍珍.pdf")
EXPECTED_SHA256 = "5EC5F2A0A982DB7AA59806382374DF7AE7D60CD7684F5B244ADB7462FF87A618"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> None:
    note = (LIT / "notes" / "28_Han2015_transcranial_brain_tumor_HIFU_review.md").read_text(encoding="utf-8")
    synthesis = (LIT / "17_四篇本地论文整合与个体化治疗规划路线.md").read_text(encoding="utf-8")
    ai_index = (LIT / "AI_LITERATURE_INDEX.md").read_text(encoding="utf-8")
    board = (LIT / "实验平台阶段看板.md").read_text(encoding="utf-8")
    alignment = (ROOT / "outputs" / "evidence_briefs" / "dual_point_hotspot_constrained_tr" / "literature_alignment_20260720.md").read_text(encoding="utf-8")
    addendum = json.loads((ROOT / "outputs" / "reference_paper_gap_matrix_20260715" / "han2015_hifu_addendum_20260720.json").read_text(encoding="utf-8"))

    csv_paths = [ROOT / "paper_parameter_matrix.csv", LIT / "structured" / "paper_parameter_matrix.csv"]
    csv_rows = []
    for path in csv_paths:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            csv_rows.append(list(csv.DictReader(handle)))
    han_rows = [row for row in csv_rows[0] if row["paper_id"] == "Han2015_local_review"]
    structured = json.loads((LIT / "structured" / "paper_parameter_matrix.json").read_text(encoding="utf-8"))
    han_json = [item for item in structured if item["paper_id"] == "Han2015_local_review"]

    checks = {
        "source_pdf_exists": PDF.is_file(),
        "source_pdf_hash_exact": PDF.is_file() and sha256(PDF) == EXPECTED_SHA256,
        "note_marks_2015_review_boundary": "文章发表于 2015 年" in note and "叙述性综述" in note,
        "note_separates_four_mechanisms": all(term in note for term in ("热消融", "神经调控", "BBB", "溶栓")),
        "leduc_primary_doi_present": "10.1299/jbse.7.43" in note and "10.1299/jbse.7.43" in alignment,
        "mcdannold_primary_doi_present": "10.1227/01.NEU.0000360379.95800.2F" in note,
        "individualized_objective_present": "患者特异性治疗规划" in note and "个体化照射计划" in synthesis,
        "roi_gap_present": "ROI" in synthesis and "覆盖" in synthesis and "体素掩膜" in synthesis,
        "physical_element_gap_present": "物理阵元" in synthesis,
        "dose_not_mixed": "不能共用一个“最佳强度”阈值" in synthesis,
        "dual_point_nonexecution_boundary": "does not authorize hotspot calibration pressure" in alignment,
        "ai_index_has_note_twice": ai_index.count("notes/28_Han2015_transcranial_brain_tumor_HIFU_review.md") == 2,
        "board_is_current": "同步至 2026-07-22" in board and "双点热点约束 TR" in board,
        "csv_copies_identical": csv_paths[0].read_bytes() == csv_paths[1].read_bytes(),
        "csv_has_eight_han_rows": len(han_rows) == 8,
        "csv_no_duplicate_parameter_names": len({row["parameter_name"] for row in han_rows}) == 8,
        "json_has_one_han_entry": len(han_json) == 1,
        "addendum_has_eight_gaps": len(addendum["gap_items"]) == 8,
        "addendum_blocks_clinical_claim": "does not establish clinical HIFU dose" in addendum["claim_boundary"],
    }
    result = {"status": "pass" if all(checks.values()) else "fail", "passed": sum(checks.values()), "total": len(checks), "checks": checks}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

