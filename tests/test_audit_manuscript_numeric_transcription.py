from pathlib import Path

from audit_manuscript_numeric_transcription import build


ROOT = Path(__file__).resolve().parents[1]


def test_manuscript_numeric_transcription_matches_sources():
    report = build(ROOT)
    assert report["status"] == "passed_numeric_transcription"
    assert report["submission_ready"] is False
    assert all(report["checks"].values())
