from __future__ import annotations

import ctypes
import os
import time
from ctypes import wintypes
from dataclasses import dataclass
from typing import Any


TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
PROCESS_TERMINATE = 0x0001
PROCESS_VM_READ = 0x0010
PROCESS_SET_INFORMATION = 0x0200
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000


class FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD),
    ]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


@dataclass(frozen=True)
class GuardThresholds:
    maximum_equivalent_cores: float = 6.5
    maximum_working_set_gib: float = 12.0
    minimum_free_memory_gib: float = 4.0


def _require_windows() -> None:
    if os.name != "nt":
        raise RuntimeError("windows_process_tree_guard requires Windows.")


def process_parent_map() -> dict[int, int]:
    _require_windows()
    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        raise ctypes.WinError()
    mapping: dict[int, int] = {}
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        success = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while success:
            mapping[int(entry.th32ProcessID)] = int(
                entry.th32ParentProcessID
            )
            success = kernel32.Process32NextW(
                snapshot, ctypes.byref(entry)
            )
    finally:
        kernel32.CloseHandle(snapshot)
    return mapping


def descendants_including_root(root_pid: int) -> list[int]:
    parents = process_parent_map()
    selected = {int(root_pid)}
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if parent in selected and pid not in selected:
                selected.add(pid)
                changed = True
    return list(selected)


def _filetime_seconds(value: FILETIME) -> float:
    ticks = (int(value.dwHighDateTime) << 32) | int(
        value.dwLowDateTime
    )
    return ticks / 10_000_000.0


def process_metrics(pid: int) -> dict[str, float] | None:
    _require_windows()
    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    access = (
        PROCESS_QUERY_LIMITED_INFORMATION
        | PROCESS_QUERY_INFORMATION
        | PROCESS_VM_READ
    )
    handle = kernel32.OpenProcess(access, False, int(pid))
    if not handle:
        return None
    try:
        creation = FILETIME()
        exit_time = FILETIME()
        kernel = FILETIME()
        user = FILETIME()
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            return None
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        working_set = 0
        if psapi.GetProcessMemoryInfo(
            handle,
            ctypes.byref(counters),
            ctypes.sizeof(counters),
        ):
            working_set = int(counters.WorkingSetSize)
        return {
            "cpu_s": _filetime_seconds(kernel)
            + _filetime_seconds(user),
            "working_set_bytes": float(working_set),
        }
    finally:
        kernel32.CloseHandle(handle)


def system_memory() -> dict[str, float]:
    _require_windows()
    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(
        ctypes.byref(status)
    ):
        raise ctypes.WinError()
    return {
        "total_physical_bytes": float(status.ullTotalPhys),
        "free_physical_bytes": float(status.ullAvailPhys),
        "memory_load_percent": float(status.dwMemoryLoad),
    }


def set_below_normal_priority(pid: int) -> None:
    _require_windows()
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION
        | PROCESS_SET_INFORMATION
        | PROCESS_TERMINATE,
        False,
        int(pid),
    )
    if not handle:
        raise ctypes.WinError()
    try:
        if not kernel32.SetPriorityClass(
            handle, BELOW_NORMAL_PRIORITY_CLASS
        ):
            raise ctypes.WinError()
    finally:
        kernel32.CloseHandle(handle)


class ProcessTreeSampler:
    def __init__(self, root_pid: int):
        self.root_pid = int(root_pid)
        self.previous_at = time.monotonic()
        self.previous_cpu_by_pid: dict[int, float] = {}

    def sample(self) -> dict[str, Any]:
        now = time.monotonic()
        elapsed = max(now - self.previous_at, 1e-9)
        pids = descendants_including_root(self.root_pid)
        current: dict[int, float] = {}
        working_set = 0.0
        cpu_delta = 0.0
        for pid in pids:
            metrics = process_metrics(pid)
            if metrics is None:
                continue
            cpu_s = float(metrics["cpu_s"])
            current[pid] = cpu_s
            working_set += float(metrics["working_set_bytes"])
            if pid in self.previous_cpu_by_pid:
                cpu_delta += max(
                    0.0, cpu_s - self.previous_cpu_by_pid[pid]
                )
        memory = system_memory()
        equivalent_cores = (
            cpu_delta / elapsed
            if self.previous_cpu_by_pid
            else None
        )
        self.previous_at = now
        self.previous_cpu_by_pid = current
        gib = 1024.0**3
        return {
            "root_pid": self.root_pid,
            "process_count": len(current),
            "pids": sorted(current),
            "sample_interval_s": elapsed,
            "equivalent_cores": equivalent_cores,
            "logical_cpu_fraction": (
                equivalent_cores / (os.cpu_count() or 1)
                if equivalent_cores is not None
                else None
            ),
            "working_set_gib": working_set / gib,
            "system_free_memory_gib": (
                memory["free_physical_bytes"] / gib
            ),
            "system_total_memory_gib": (
                memory["total_physical_bytes"] / gib
            ),
            "system_memory_load_percent": memory[
                "memory_load_percent"
            ],
        }


def breach_reasons(
    sample: dict[str, Any],
    thresholds: GuardThresholds,
) -> list[str]:
    reasons: list[str] = []
    cores = sample.get("equivalent_cores")
    if (
        cores is not None
        and float(cores) > thresholds.maximum_equivalent_cores
    ):
        reasons.append("equivalent_cpu_cores")
    if (
        float(sample["working_set_gib"])
        > thresholds.maximum_working_set_gib
    ):
        reasons.append("process_tree_working_set")
    if (
        float(sample["system_free_memory_gib"])
        < thresholds.minimum_free_memory_gib
    ):
        reasons.append("system_free_memory")
    return reasons


def terminate_process_tree(root_pid: int, exit_code: int = 3) -> None:
    _require_windows()
    kernel32 = ctypes.windll.kernel32
    pids = descendants_including_root(root_pid)
    for pid in reversed(pids):
        handle = kernel32.OpenProcess(
            PROCESS_TERMINATE, False, int(pid)
        )
        if not handle:
            continue
        try:
            kernel32.TerminateProcess(handle, int(exit_code))
        finally:
            kernel32.CloseHandle(handle)
