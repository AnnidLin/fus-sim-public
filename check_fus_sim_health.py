#!/usr/bin/env python3
"""Quick health check for fus-sim project state.

Run this to verify environment, validators, and key outputs without manually
checking each one. Safe to run any time (read-only except for validator JSON writes).
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = Path("D:/AIprogram/python-envs/kwave312/Scripts/python.exe")


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def section(title):
    print(f"\n{'=' * 60}")
    print(title)
    print('=' * 60)


def check(name, condition, detail=""):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {name}")
    if detail:
        print(f"       {detail}")
    return condition


def main():
    all_ok = True

    section("Environment")
    all_ok &= check(
        "k-Wave Python interpreter exists",
        PY.exists(),
        str(PY) if PY.exists() else "missing",
    )
    if PY.exists():
        r = run([str(PY), "-c", "import kwave; print(kwave.__version__)"], cwd=ROOT)
        all_ok &= check(
            "k-Wave importable",
            r.returncode == 0,
            r.stdout.strip() if r.returncode == 0 else r.stderr.strip(),
        )

    section("Validators")
    validators = [
        "validate_run_ledger.py",
        "validate_evidence_registry.py",
        "validate_reproducibility_manifest.py",
        "validate_final_reproducibility_package.py",
    ]
    for v in validators:
        script = ROOT / v
        if not script.exists():
            all_ok &= check(v, False, "script not found")
            continue
        r = run([str(PY), str(script)], cwd=ROOT)
        try:
            result = json.loads(r.stdout.splitlines()[-1])
            ok = result.get("ledger_valid", result.get("registry_valid", result.get("manifest_valid", result.get("package_valid", False))))
            failed = result.get("failed_check_count", -1)
        except Exception:
            ok = False
            failed = "parse error"
        all_ok &= check(
            v,
            ok and failed == 0,
            f"failed_checks={failed}" if not (ok and failed == 0) else "0 failed checks",
        )

    section("Key Output Folders")
    key_folders = [
        "outputs/corrected_pressure_runs",
        "outputs/corrected_pennes_thermal_dx0p5",
        "outputs/ct_sweep_scan_079_dx0p75",
        "outputs/evidence_registry",
    ]
    for folder in key_folders:
        path = ROOT / folder
        exists = path.exists()
        detail = f"{sum(1 for _ in path.rglob('*'))} items" if exists else "missing"
        all_ok &= check(folder, exists, detail)

    section("Disk Space")
    total, used, free = shutil.disk_usage(ROOT)
    gb_free = free / (1024**3)
    all_ok &= check(
        "Free disk space >= 10 GB",
        gb_free >= 10,
        f"{gb_free:.1f} GB free",
    )

    section("Git Status")
    git = Path("D:/AIprogram/tools/Git/cmd/git.exe")
    if git.exists():
        r = run([str(git), "status", "--short"], cwd=ROOT)
        dirty = bool(r.stdout.strip())
        detail = r.stdout.strip().replace("\n", "; ")[:120] if dirty else "clean"
        check("Working tree clean", not dirty, detail)
    else:
        check("Git status", False, "git not found")

    section("Summary")
    if all_ok:
        print("All checks passed. Project is healthy.")
        return 0
    else:
        print("Some checks failed. Investigate above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
