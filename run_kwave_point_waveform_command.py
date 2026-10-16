from __future__ import annotations

import run_kwave_command as stable_runner


def main() -> None:
    stable_runner.ALLOWED_SCRIPTS.add("simulate_source_array_focus_point_waveform.py")
    stable_runner.main()


if __name__ == "__main__":
    main()

