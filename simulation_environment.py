from __future__ import annotations

import importlib.metadata
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PACKAGE_DISTRIBUTIONS = {
    "k_wave_python": "k-wave-python",
    "numpy": "numpy",
    "scipy": "scipy",
    "matplotlib": "matplotlib",
    "h5py": "h5py",
    "pillow": "pillow",
}


def package_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def build_environment_record(*, backend: str | None = None, device: str | None = None) -> dict[str, Any]:
    packages = {
        key: package_version(distribution)
        for key, distribution in PACKAGE_DISTRIBUTIONS.items()
    }
    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "record_type": "current_execution_environment",
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "backend": backend,
        "device": device,
        "packages": packages,
        "kwave_python_version": packages.get("k_wave_python"),
        "numpy_version": packages.get("numpy"),
        "scipy_version": packages.get("scipy"),
        "matplotlib_version": packages.get("matplotlib"),
        "h5py_version": packages.get("h5py"),
        "temp_dir": os.environ.get("TEMP"),
        "tmp_dir": os.environ.get("TMP"),
        "mplconfigdir": os.environ.get("MPLCONFIGDIR"),
        "cwd": str(Path.cwd()),
        "historical_scope_note": "This record describes the current execution environment only.",
    }
