from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")

STEPS = [
    ("grid convergence (corrected)", "generate_d60_grid_convergence_report_corrected.py"),
    ("reference paper gap matrix", "generate_reference_paper_gap_matrix.py"),
    ("paper skeleton", "generate_paper_skeleton_20260715.py"),
    ("fine grid decision gate", "generate_fine_grid_decision_gate_20260715.py"),
    ("supplementary figures", "generate_d60_supplementary_figures_20260715.py"),
    ("supplementary analysis", "generate_d60_supplementary_analysis_20260715.py"),
    ("manuscript draft", "generate_manuscript_draft_20260715.py"),
    ("manuscript final", "generate_manuscript_final_20260715.py"),
    ("latex final", "generate_latex_final_20260715.py"),
    ("submission package", "generate_acoustic_paper_submission_package_20260715.py"),
]


def run_script(script: str) -> dict[str, object]:
    command = [str(PYTHON_EXE), str(PROJECT_ROOT / script)]
    result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    return {
        "script": script,
        "returncode": result.returncode,
        "stdout": result.stdout.strip().splitlines()[-3:] if result.stdout else [],
        "stderr": result.stderr.strip()[-500:] if result.stderr else "",
    }


def main() -> None:
    results = []
    for name, script in STEPS:
        print(f"Running {name}...", flush=True)
        info = run_script(script)
        results.append(info)
        if info["returncode"] != 0:
            print(f"FAILED: {script}", flush=True)
            break

    # Run validators
    validators = [
        "validate_evidence_registry.py",
        "validate_reproducibility_manifest.py",
        "validate_final_reproducibility_package.py",
    ]
    for validator in validators:
        result = subprocess.run(
            [str(PYTHON_EXE), str(PROJECT_ROOT / validator)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        results.append({
            "script": validator,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
        })

    summary_path = PROJECT_ROOT / "outputs" / "overnight_work_summary_20260715" / "regeneration_after_dx05_summary.json"
    summary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Summary written to {summary_path}")


if __name__ == "__main__":
    main()
