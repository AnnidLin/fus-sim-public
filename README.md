# fus-sim

**经颅聚焦超声研究工具与证据快照 · Public research snapshot (baseline 2026-10-16) · issues and PRs reviewed, best effort**

Python/k-Wave research workflows for transcranial focused ultrasound: CT-derived acoustic models, source-array/time-reversal focusing, numerical benchmarks, sensitivity analysis and reproducibility records.

本仓库公开保留可分享的代码、测试、研究笔记、稿件草案与精简结果，供学习和后续研究参考。日常以 best-effort 方式维护：issue 与 pull request 会被查看并在可行时回应；代码基线以 2026-10-16 的公开快照为准，只有明确接受后才会改动，不承诺路线图或时间表。

**Research software only.** H115 external comparison remains **nonpassing**. Complete CT convergence, validated absolute pressure, independent-solver agreement and clinical safety have not been established. Public release does not mean the manuscript is submission-ready.

## Start here

| Document | Purpose |
|---|---|
| [Project status](PROJECT_STATUS.md) | Achievements, paused status and unresolved scientific limitations |
| [Release notes](RELEASE_NOTES_20261016.md) | Scope of the October public snapshot |
| [Data availability](DATA_AVAILABILITY.md) | Included files, excluded data and reproduction limits |
| [September review](PLATFORM_STATUS_AND_NEXT_PLAN_20260920.md) | Evidence-based platform assessment; its proposed work is now deferred |
| [Code map](CODE_MAP.md) | Simulation and analysis entry points |
| [Compact evidence](evidence/README.md) | Shareable numeric comparisons and failed-run summaries |
| [Manuscript draft](paper/PUB2_MANUSCRIPT_DRAFT_V0_1_20260812.md) | Unsubmitted research draft, not a publication or validation certificate |
| [Third-party notices](THIRD_PARTY_NOTICES.md) | Licence boundary for dependencies and the vendored patch |

## Public quickstart — no medical data or solver required

Python 3.12 was used for verification. Create an environment using your usual platform-specific activation command, then:

```sh
python -m venv .venv
# Activate .venv before the following commands.
python -m pip install -r requirements-public-smoke.txt
python examples/public_smoke.py
python -m unittest tests.test_bbb_roi tests.test_windows_process_tree_guard_20260807 tests.test_generate_submission_archive_manifest
```

The example exercises a synthetic geometry mask and reads a numerical preset. It does **not** run k-Wave or establish acoustic accuracy. The named tests use synthetic inputs and temporary files. See [PUBLIC_VALIDATION.json](PUBLIC_VALIDATION.json) for the release check results.

Full research dependencies are recorded in `requirements-kwave312.txt`. Full historical runs require separately obtained inputs, original execution artifacts, parameter/resource gates and suitable compute. Archived paths may refer to the original Windows workspace. Do not expect blanket test discovery or manuscript reconstruction to pass without the excluded artifacts.

## Retained result and its limits

In one matched Case079 250 kHz intermediate-domain comparison, TR moved the global peak from **57.379 mm** to **2.487 mm** from the target. The target-point/global ratio increased from **0.477400** to **0.984864**. This is a within-model engineering observation.

The historical analysis freeze says *target-window/global* while quoting the *target-point/global* numbers. The actual window ratios are **0.723139 → 1.000000**. Both are retained explicitly; the discrepancy was not silently repaired or presented as prospectively registered. The September review documents the issue.

## Repository layout

- Root Python scripts: simulation, analysis, benchmark adapters and governance tools.
- `tests/`, `examples/`: tests and the public synthetic smoke entry point.
- `acoustic_mapping_profiles/`, `simulation_presets.json`, `planning_contracts/`, `governance_schemas/`: parameter and contract definitions.
- `paper/`: historical drafts, tables and audits; missing data/outputs references are intentional.
- `literature_tFUS_review/`: bibliographic notes and research references, without paper PDFs.
- `evidence/`: selected small numerical summaries, not the private execution archive.
- `legacy_archive/`: historical source retained for traceability, not the preferred current workflow.
- `patches/`: optional historical backend patch with its own LGPL notices.

Original private Git history, raw CT, anatomy volumes, large fields, private handoff logs and third-party PDFs have not been imported. Existing earlier public files are retained; their dated plans do not override [PROJECT_STATUS.md](PROJECT_STATUS.md).

## Licence and attribution

Project-owned code is [MIT licensed](LICENSE), confirmed by the maintainer on 2026-10-16. Third-party code and datasets retain their respective licences. Packaging/review assistance does not replace original implementation or research attribution. This snapshot has no new DOI and is not a journal submission.
