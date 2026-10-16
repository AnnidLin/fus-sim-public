from pathlib import Path

from audit_author_material_consistency import build


ROOT = Path(__file__).resolve().parents[1]


def test_author_materials_cover_all_actions_and_retain_no_go():
    report = build(ROOT)
    assert report["status"] == "passed_author_material_consistency"
    assert report["submission_ready"] is False
    assert all(report["action_coverage"].values())
    assert all(report["checks"].values())
