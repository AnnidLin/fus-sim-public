"""Re-apply the fus-sim cpp-backend patch to a kwave-python 0.6.1 install.

Copies the vendored cpp_simulation.py over the site-packages original.
Usage:
    python patches/kwave_cpp_backend_20260719/apply_patch.py [python_exe]

If python_exe is omitted, the project k-Wave interpreter is used.
Prints the target path and a SHA-256 of the installed file for verification.
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENDORED = HERE / "cpp_simulation.py"
DEFAULT_PYTHON = Path(r"D:\AIprogram\python-envs\kwave312\Scripts\python.exe")
REL_TARGET = Path("Lib") / "site-packages" / "kwave" / "solvers" / "cpp_simulation.py"


def main() -> int:
    python_exe = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PYTHON
    env_root = python_exe.parent.parent  # Scripts/python.exe -> env root
    target = env_root / REL_TARGET
    if not target.parent.exists():
        print(f"ERROR: kwave package not found at {target.parent}", file=sys.stderr)
        return 1
    backup = target.with_suffix(".py.orig")
    if target.exists() and not backup.exists():
        shutil.copy2(target, backup)
        print(f"backup: {backup}")
    shutil.copy2(VENDORED, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    print(f"installed: {target}")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
