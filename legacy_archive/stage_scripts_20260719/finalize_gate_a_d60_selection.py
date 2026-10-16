from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SELECTION = PROJECT_ROOT / "outputs/paper_gate_a_d60_trajectory_selection_079/gate_a_d60_trajectory_selection.json"
FEEDBACK_JSON = PROJECT_ROOT / "outputs/evidence_briefs/paper_gate_a_d60_trajectory_selection/gap_feedback.json"
FEEDBACK_MD = PROJECT_ROOT / "outputs/evidence_briefs/paper_gate_a_d60_trajectory_selection/gap_feedback.md"


def main() -> None:
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    selected = selection["selected"]
    if len(selected) != 3:
        raise ValueError(f"Expected three D60 selections, found {len(selected)}")
    if not all(item.get("background_only") and item.get("hard_gate_pass") for item in selected):
        raise ValueError("Cannot close D60 Gate A: a selected source mask failed a machine gate")

    review = {
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewer": "Codex delegated gross-anatomy visual review via Windows desktop screenshots",
        "views": ["axial", "coronal"],
        "result": "pass",
        "findings": [
            "all three paths enter through one lateral skull segment",
            "paths remain visibly superior to the orbit and sinonasal region",
            "no visible skull-base or open-cavity crossing",
        ],
        "boundary": "label model and two-plane gross review do not replace segmented eye/sinus labels or expert clinical planning",
    }
    selection["status"] = "gate_a_d60_closed"
    selection["gross_anatomy_visual_review"] = review
    selection["pressure_execution_authorized"] = False
    selection["next"] = "complete D60 dx0.5 free-field convergence before any CT pressure"
    SELECTION.write_text(json.dumps(selection, indent=2), encoding="utf-8")

    feedback = json.loads(FEEDBACK_JSON.read_text(encoding="utf-8"))
    feedback["status"] = "gate_a_d60_closed"
    feedback["visual_review_complete"] = True
    feedback["visual_review_result"] = "pass"
    feedback["visual_review_blocker"] = None
    feedback["pressure_execution_authorized"] = False
    feedback["next"] = "plan D60 dx0.5 free-field convergence"
    FEEDBACK_JSON.write_text(json.dumps(feedback, indent=2), encoding="utf-8")

    text = FEEDBACK_MD.read_text(encoding="utf-8")
    text = text.replace(
        "Status: `machine_gates_pass_visual_review_pending`.",
        "Status: `gate_a_d60_closed`.",
    )
    text = text.replace(
        "The D60 geometry is not formally closed and does not authorize CT pressure. Resume with visual review of the three generated PNGs; only after closure may the D60 dx0.5 free-field convergence stage be planned.",
        "Delegated axial/coronal gross-anatomy review passed for all three paths: each enters through one lateral skull segment, remains visibly above the orbit/sinonasal region, and does not visibly cross the skull base or an open cavity. This closes D60 Gate A for engineering planning, but does not replace dedicated eye/sinus segmentation or expert clinical planning. CT pressure remains unauthorized until D60 free-field convergence closes.",
    )
    FEEDBACK_MD.write_text(text, encoding="utf-8")
    print(json.dumps({"status": selection["status"], "selected": [item["candidate_id"] for item in selected]}))


if __name__ == "__main__":
    main()
