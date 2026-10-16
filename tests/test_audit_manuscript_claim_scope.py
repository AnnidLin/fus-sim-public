from pathlib import Path

from audit_manuscript_claim_scope import build


ROOT = Path(__file__).resolve().parents[1]


def test_manuscript_claim_scope_is_bounded_and_reports_h115_failures():
    report = build(ROOT)
    assert report["status"] == "passed_claim_scope"
    assert report["submission_ready"] is False
    assert report["forbidden_positive_phrase_hits"] == []
    assert all(report["checks"].values())
