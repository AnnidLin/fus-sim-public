from pathlib import Path

from audit_repository_entry_docs import build


ROOT = Path(__file__).resolve().parents[1]


def test_repository_entry_docs_match_current_boundaries():
    report = build(ROOT)
    assert report["status"] == "passed_entry_document_boundaries"
    assert report["submission_ready"] is False
    assert report["test_file_count"] >= 100
    assert all(report["checks"].values())
