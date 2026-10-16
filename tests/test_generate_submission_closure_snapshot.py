from datetime import datetime
from pathlib import Path

from generate_submission_closure_snapshot import build


ROOT = Path(__file__).resolve().parents[1]


def test_preclose_snapshot_is_bounded_and_not_complete():
    report = build(ROOT, datetime.fromisoformat("2026-08-29T04:42:01+08:00"))
    assert report["status"] == "preclose_passed_pending_time_and_author_actions"
    assert report["work_window_reached"] is False
    assert report["closure_complete"] is False
    assert report["submission_ready"] is False
    assert report["solver_authorized"] is False
    assert report["h115_external_comparison"] == "nonpassing"
    assert all(report["checks"].values())
