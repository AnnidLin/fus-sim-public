from pathlib import Path

from generate_dependency_license_inventory import build


ROOT = Path(__file__).resolve().parents[1]


def test_dependency_inventory_retains_project_licence_blocker():
    report = build(ROOT)
    assert report["status"] == "conditional_project_licence_missing"
    assert report["dependency_count"] == 29
    assert report["project_licence_author_decision_required"] is True
    assert all(item["version_matches"] for item in report["dependencies"])
