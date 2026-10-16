from pathlib import Path

from generate_submission_inventory import build


ROOT = Path(__file__).resolve().parents[1]


def test_submission_inventory_is_complete_but_not_ready():
    report = build(ROOT)
    assert report["status"] == "passed_inventory_author_inputs_pending"
    assert report["submission_ready"] is False
    assert report["target_journal"] is None
    assert report["archive_file_count"] == 136
    assert all(report["checks"].values())
