from pathlib import Path

from audit_submission_negative_results import build


ROOT = Path(__file__).resolve().parents[1]


def test_negative_results_and_limitations_are_retained():
    report = build(ROOT)
    assert report["status"] == "passed_negative_results_and_limitations_retained"
    assert report["submission_ready"] is False
    assert report["h115_failed_endpoint_count"] == 12
    assert report["effective_failed_endpoint_count"] == 4
    assert report["nominal_failed_endpoint_count"] == 8
    assert all(report["checks"].values())
