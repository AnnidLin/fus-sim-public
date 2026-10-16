# Reproducibility environment and command-interface audit

Trace: `TRACE-20260829-001`  
Status: `passed_with_test_runner_gap`

The retained runtime matches the manuscript: CPython 3.12.10 on Windows 11,
k-Wave-python 0.6.1, NumPy 2.2.6, SciPy 1.15.3, Matplotlib 3.10.7 and h5py
3.15.1. Accepted H115 summaries record the C++/CPU backend and the `standard`
engineering preset with `is_paper_grade=false`.

All 11 non-solver command interfaces named by the reproduction workflow loaded
and exposed their expected required arguments under `--help`. No analysis was
recomputed and no pressure solver was started.

## Retained test-runner gap

`requirements-kwave312.txt` exactly pins the scientific runtime but does not pin
pytest, and pytest is not installed in the retained k-Wave environment. The new
focused submission checks were therefore invoked directly as Python functions.
This is sufficient evidence for those focused assertions, but it is not a fresh
full pytest-suite run. Do not report a full clean test-suite result until a
separate development/test lock is frozen and the suite is rerun.

