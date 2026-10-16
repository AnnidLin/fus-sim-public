from pathlib import Path

from audit_abstract_author_queries import build


ROOT = Path(__file__).resolve().parents[1]


def test_abstract_and_author_queries_are_bounded_and_owned():
    report = build(ROOT)
    assert report["status"] == "passed_abstract_and_author_query_mapping"
    assert report["abstract_word_count"] <= 250
    assert report["query_count"] == 6
    assert report["submission_ready"] is False
    assert all(report["checks"].values())
