from pathlib import Path

from audit_figure_table_captions import build


ROOT = Path(__file__).resolve().parents[1]


def test_figure_and_table_caption_semantics_match_manifests():
    report = build(ROOT)
    assert report["status"] == "passed_caption_semantics"
    assert report["artifact_group_count"] == 5
    assert report["submission_ready"] is False
    assert all(report["checks"].values())
