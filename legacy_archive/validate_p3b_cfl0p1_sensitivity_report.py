from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
REPORT_PATH = PROJECT_ROOT / "outputs/p3b_cfl0p1_sensitivity_analysis/079_candidate_006_dx0p75/p3b_cfl0p1_sensitivity_report.json"
OUT_JSON = PROJECT_ROOT / "outputs/p3b_cfl0p1_sensitivity_analysis/079_candidate_006_dx0p75/p3b_cfl0p1_sensitivity_report_validation.json"
OUT_MD = PROJECT_ROOT / "outputs/p3b_cfl0p1_sensitivity_analysis/079_candidate_006_dx0p75/p3b_cfl0p1_sensitivity_report_validation.md"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def add(checks: list[dict[str, Any]], check_id: str, passed: bool, evidence: str) -> None:
    checks.append({"check_id": check_id, "status": "pass" if passed else "fail", "evidence": evidence})


def main() -> None:
    report = read_json(REPORT_PATH)
    checks: list[dict[str, Any]] = []
    p3b_dir = PROJECT_ROOT / report["p3b"]["output_dir"]
    threshold_checks = report.get("threshold_checks", {})
    failed_thresholds = [
        name for name, payload in threshold_checks.items() if isinstance(payload, dict) and payload.get("status") != "pass"
    ]

    add(checks, "report.exists", REPORT_PATH.exists(), rel(REPORT_PATH))
    add(checks, "baseline.kwave_ok", report.get("baseline", {}).get("runner_status") == "kwave_ok", str(report.get("baseline", {}).get("runner_status")))
    add(checks, "p3b.kwave_ok", report.get("p3b", {}).get("runner_status") == "kwave_ok", str(report.get("p3b", {}).get("runner_status")))
    add(checks, "p3b.pml12", report.get("p3b", {}).get("pml_size") == 12, str(report.get("p3b", {}).get("pml_size")))
    add(checks, "p3b.cfl01", float(report.get("p3b", {}).get("cfl", -1)) == 0.1, str(report.get("p3b", {}).get("cfl")))
    add(checks, "p3b.outputs_exist", all((p3b_dir / name).exists() for name in ["runner_status.json", "summary.json", "focus_metrics.json", "pressure_max_mpa.npz"]), rel(p3b_dir))
    add(checks, "thresholds.pass", not failed_thresholds, str(failed_thresholds))
    add(
        checks,
        "decision.next_packet",
        report.get("decision", {}).get("recommended_next_packet")
        in {"P3c_corrected_dx0p5_grid_sensitivity_prerequisite", "pause_for_p3b_timestep_analysis"},
        str(report.get("decision", {}).get("recommended_next_packet")),
    )
    blocked_claims = set(report.get("blocked_claims", []))
    add(
        checks,
        "claims.blocked",
        {
            "validated pressure baseline",
            "paper-grade reproduction",
            "medical or safety conclusion",
            "numerical convergence claim",
        }.issubset(blocked_claims),
        str(sorted(blocked_claims)),
    )

    failed = [item for item in checks if item["status"] != "pass"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_path": rel(REPORT_PATH),
        "report_valid": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
        "failed_checks": failed,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# P3b CFL0.1 Sensitivity Report Validation\n\n"
        f"- report valid: `{result['report_valid']}`\n"
        f"- failed check count: `{result['failed_check_count']}`\n",
        encoding="utf-8",
    )
    print(json.dumps({"report_valid": result["report_valid"], "failed_check_count": result["failed_check_count"]}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
