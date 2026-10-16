from pathlib import Path

from validate_submission_archive_integrity import build


ROOT = Path(__file__).resolve().parents[1]


def test_submission_archive_is_bitwise_valid_but_release_blocked():
    report = build(ROOT)
    assert report["status"] == "passed_archive_integrity_blocked_release"
    assert report["archive_ready"] is False
    assert report["file_count"] == 136
    assert not report["mismatches"]
    assert all(report["checks"].values())
