"""Lightweight PUB.2 queue health watcher.

Runs independently of the orchestrator and the solver. Every interval it records
a health snapshot (queue status, solver liveness, disk and memory headroom) so an
overnight batch leaves an auditable heartbeat timeline. It never mutates results
and never starts or stops the solver.
"""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QUEUE_STATUS = ROOT / "outputs" / "pub2_sensitivity_queue_20260814" / "queue_status.json"
WATCH_LOG = ROOT / "outputs" / "pub2_sensitivity_queue_20260814" / "watch.log"
INTERVAL_S = 600  # 10 分钟


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def solver_live() -> bool:
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Where-Object { $_.CommandLine -match 'simulate_kwave_3d_focus|simulate_time_reversal_focus' } | "
             "Select-Object -First 1"],
            capture_output=True, text=True, timeout=30,
        ).stdout
    except Exception:
        return False
    return bool(out.strip())


def disk_free_gb() -> float:
    import shutil
    return shutil.disk_usage(str(ROOT)).free / (1024 ** 3)


def memory_free_gb() -> float:
    try:
        import ctypes
        class M(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        s = M(); s.dwLength = ctypes.sizeof(s)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s)):
            return s.ullAvailPhys / (1024 ** 3)
    except Exception:
        pass
    return -1.0


def queue_status_text() -> str:
    try:
        d = json.loads(QUEUE_STATUS.read_text(encoding="utf-8"))
        return f"{d.get('status')}/idx={d.get('current_index')}/results={[r.get('status') for r in d.get('results', [])]}"
    except Exception:
        return "no-status-yet"


def main() -> None:
    with WATCH_LOG.open("a", encoding="utf-8") as log:
        log.write(f"[{utc()}] watcher started interval={INTERVAL_S}s\n")
    while True:
        line = (
            f"[{utc()}] queue={queue_status_text()} solver_live={solver_live()} "
            f"disk_free_gb={disk_free_gb():.1f} mem_free_gb={memory_free_gb():.1f}"
        )
        with WATCH_LOG.open("a", encoding="utf-8") as log:
            log.write(line + "\n")
        print(line, flush=True)
        time.sleep(INTERVAL_S)


if __name__ == "__main__":
    main()
