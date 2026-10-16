from pathlib import Path

from validate_submission_status_consistency import build


ROOT = Path(__file__).resolve().parents[1]


def test_current_submission_status_is_consistent():
    report = build(ROOT)
    assert report["status"] == "passed"
    assert not report["failed_checks"]
    assert report["checks"]["preflight_not_submission_ready"]
