from __future__ import annotations

import ctypes
import sys
import time

# ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
EXECUTION_STATE = 0x80000042


def main() -> None:
    duration_min = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    print(f"Keeping system awake for {duration_min} minutes...")
    ctypes.windll.kernel32.SetThreadExecutionState(EXECUTION_STATE)
    end = time.time() + duration_min * 60.0
    try:
        while time.time() < end:
            ctypes.windll.kernel32.SetThreadExecutionState(EXECUTION_STATE)
            time.sleep(30.0)
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        print("Released wake lock.")


if __name__ == "__main__":
    main()
