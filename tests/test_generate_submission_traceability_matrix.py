from pathlib import Path

from generate_submission_traceability_matrix import build


ROOT = Path(__file__).resolve().parents[1]


def test_submission_traceability_matrix_passes_on_retained_artifacts():
    report = build(ROOT)
    assert report["status"] == "passed"
    assert len(report["items"]) == 5
    assert all(report["checks"].values())
    assert "nonpassing" in report["claim_boundary"]
