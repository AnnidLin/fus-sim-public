from pathlib import Path

from audit_reviewer_reproduction_path import build


ROOT = Path(__file__).resolve().parents[1]


def test_reviewer_reproduction_path_is_non_solver_and_bounded():
    report = build(ROOT)
    assert report["status"] == "passed_non_solver_reviewer_path"
    assert report["submission_ready"] is False
    assert report["command_script_count"] == 7
    assert all(report["checks"].values())
