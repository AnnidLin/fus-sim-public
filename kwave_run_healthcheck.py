from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_PYTHON = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")
REQUIRED_MODULES = ("kwave", "numpy", "h5py", "PIL")


def check_module(module_name: str) -> dict[str, Any]:
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, "__version__", None)
        return {"module": module_name, "ok": True, "version": version, "error": None}
    except Exception as exc:  # pragma: no cover - diagnostic path
        return {"module": module_name, "ok": False, "version": None, "error": repr(exc)}


def check_writable_dir(path: Path) -> dict[str, Any]:
    path.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(dir=path, delete=True) as handle:
            handle.write(b"ok")
        return {"path": str(path), "exists": path.exists(), "writable": True, "error": None}
    except Exception as exc:  # pragma: no cover - diagnostic path
        return {"path": str(path), "exists": path.exists(), "writable": False, "error": repr(exc)}


def list_kwave_python_processes() -> list[dict[str, Any]]:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "Get-Process python -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Path -like 'D:\\AIprogram\\python-envs\\kwave312\\*' } | "
            "Select-Object Id,CPU,ProcessName,Path | ConvertTo-Json -Compress"
        ),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    except Exception as exc:  # pragma: no cover - diagnostic path
        return [{"error": repr(exc)}]
    output = result.stdout.strip()
    if not output:
        return []
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return [{"raw": output, "stderr": result.stderr.strip()}]
    if isinstance(parsed, dict):
        parsed = [parsed]
    return parsed


def run_healthcheck(output_dir: Path, python_exe: Path) -> dict[str, Any]:
    tmp_dir = PROJECT_ROOT / ".tmp"
    mpl_dir = PROJECT_ROOT / ".tmp" / "mplconfig-kwave-runner"
    env_paths = {
        "TEMP": os.environ.get("TEMP"),
        "TMP": os.environ.get("TMP"),
        "MPLCONFIGDIR": os.environ.get("MPLCONFIGDIR"),
    }
    module_checks = [check_module(name) for name in REQUIRED_MODULES]
    process_list = list_kwave_python_processes()
    warnings: list[str] = []
    if not python_exe.exists():
        warnings.append("kwave312_python_not_found")
    if any(not item["ok"] for item in module_checks):
        warnings.append("required_module_import_failed")
    if process_list:
        warnings.append("existing_kwave312_python_processes_detected")
    summary = {
        "description": "k-Wave runner health-check. This does not start k-Wave simulation.",
        "python_executable": str(python_exe),
        "python_executable_exists": python_exe.exists(),
        "current_python": sys.executable,
        "project_root": str(PROJECT_ROOT),
        "environment_paths": env_paths,
        "recommended_runtime_paths": {
            "TEMP": str(tmp_dir),
            "TMP": str(tmp_dir),
            "MPLCONFIGDIR": str(mpl_dir),
        },
        "writable_dirs": {
            "tmp": check_writable_dir(tmp_dir),
            "mplconfig": check_writable_dir(mpl_dir),
        },
        "module_checks": module_checks,
        "kwave312_python_processes": process_list,
        "warnings": warnings,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "healthcheck_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "healthcheck_summary.md").open("w", encoding="utf-8-sig") as handle:
        handle.write("# k-Wave Runner 健康检查\n\n")
        handle.write("本检查不会启动 k-Wave 仿真。\n\n")
        handle.write(f"- Python: `{python_exe}`\n")
        handle.write(f"- Python exists: `{python_exe.exists()}`\n")
        handle.write(f"- Current Python: `{sys.executable}`\n")
        handle.write(f"- Warnings: `{warnings}`\n\n")
        handle.write("## 依赖导入\n\n")
        for item in module_checks:
            handle.write(f"- {item['module']}: ok={item['ok']} version={item['version']} error={item['error']}\n")
        handle.write("\n## 目录可写性\n\n")
        for name, item in summary["writable_dirs"].items():
            handle.write(f"- {name}: `{item['path']}` writable={item['writable']} error={item['error']}\n")
        handle.write("\n## 现有 kwave312 Python 进程\n\n")
        handle.write(json.dumps(process_list, ensure_ascii=False, indent=2))
        handle.write("\n")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check k-Wave runner environment without starting k-Wave.")
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "outputs" / "kwave_runner_health"))
    parser.add_argument("--python-exe", default=str(DEFAULT_PYTHON))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_healthcheck(Path(args.output_dir), Path(args.python_exe))
