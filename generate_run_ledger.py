from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
LEDGER_PATH = PROJECT_ROOT / "outputs" / "run_ledger.jsonl"
SUMMARY_PATH = PROJECT_ROOT / "outputs" / "run_ledger_summary.json"
REPORT_PATH = PROJECT_ROOT / "outputs" / "run_ledger_summary.md"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def nested(data: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def build_entries() -> list[dict[str, Any]]:
    run_path = PROJECT_ROOT / "outputs/ct_standard_pressure_authorization/079_candidate_006_dx0p75_pml12_standard/standard_pressure_execution_summary.json"
    run = read_json(run_path)
    output_dir = PROJECT_ROOT / str(run["output_dir"])
    return [
        {
            "ledger_version": "1.0.0",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "run_id": "079_candidate_006_simple_hu300_dx075_pml12_standard_2026-06-02",
            "case_id": str(run["case_id"]),
            "candidate_id": str(run["candidate_id"]),
            "profile": str(run["mapping_profile"]),
            "preset": str(run["preset"]),
            "output_dir": run["output_dir"],
            "runner_status": nested(run, ["runner", "status"]),
            "runtime_s": float(nested(run, ["runner", "runtime_s"], 0.0)),
            "pressure_generated": bool(nested(run, ["runner", "core_output_exists", "pressure"], False)),
            "summary_generated": bool(nested(run, ["runner", "core_output_exists", "summary"], False)),
            "claim_level": "standard_engineering_pressure_output",
            "authorization": "explicit user authorization in Codex thread before run_kwave_command.py --execute",
            "command_route": "run_kwave_command.py --execute",
            "pressure_path": rel(output_dir / "pressure_max_mpa.npz"),
            "summary_path": rel(output_dir / "summary.json"),
            "execution_summary_path": rel(run_path),
            "blocked_claims": [
                "validated pressure baseline",
                "paper-grade reproduction",
                "medical/safety conclusion",
                "profile/default promotion"
            ]
        }
    ]


def main() -> None:
    entries = build_entries()
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in entries) + "\n", encoding="utf-8")
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ledger_version": "1.0.0",
        "ledger_path": rel(LEDGER_PATH),
        "entry_count": len(entries),
        "claim_levels": sorted({item["claim_level"] for item in entries}),
        "pressure_run_count": sum(1 for item in entries if item["pressure_generated"]),
        "paper_grade_run_count": sum(1 for item in entries if item["claim_level"] == "paper_grade_candidate"),
        "medical_or_safety_conclusion_allowed": False
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT_PATH.write_text(
        "# Run Ledger Summary\n\n"
        f"- entry count: `{summary['entry_count']}`\n"
        f"- pressure run count: `{summary['pressure_run_count']}`\n"
        f"- paper-grade run count: `{summary['paper_grade_run_count']}`\n"
        f"- claim levels: `{summary['claim_levels']}`\n",
        encoding="utf-8",
    )
    print(f"Wrote {rel(LEDGER_PATH)}")
    print(f"Wrote {rel(SUMMARY_PATH)}")


if __name__ == "__main__":
    main()
