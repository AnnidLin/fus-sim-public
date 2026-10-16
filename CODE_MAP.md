# fus-sim Code Map

> **For AI agents**: use this file to find which script does what, instead of grepping through the whole repo. Root currently holds 130 `.py` files, grouped below. Unit tests live in `tests/`; superseded one-off stage scripts are preserved under `legacy_archive/stage_scripts_20260719/` (earlier batches under `legacy_archive/`).

---

## Core Simulation Pipeline

| Script | Purpose | Typical Input | Typical Output |
|--------|---------|---------------|----------------|
| `build_ct_acoustic_model.py` | Build CT acoustic property volumes (sound speed, density, alpha) from NIfTI CT + mapping profile | `data/case_079/ct.nii.gz`, `acoustic_mapping_profiles/<profile>.json` | `outputs/ct_acoustic_model_3d_*/<case>/*.npz` |
| `simulate_kwave_3d_focus.py` | Run 3D k-Wave pressure simulation for a given entry plan | CT acoustic model NPZ, entry plan JSON | `pressure_max_mpa.npz`, `summary.json` |
| `simulate_pennes_bioheat.py` | Pennes bioheat solver on k-Wave pressure fields | `pressure_max_mpa.npz` | `pennes_summary.json`, thermal images |
| `simulate_source_array_focus.py` | Source-point-array pressure sim with per-element phase delays / apodization / free-field mode | CT model + array config | pressure NPZ + summary |
| `simulate_source_array_focus_point_waveform.py` | Point-waveform variant of the source-array sim | same | target waveform series |
| `simulate_source_array_focus_split_sensor.py` | Split-sensor variant (memory partitioning) | same | pressure NPZ |
| `simulate_time_reversal_focus.py` | Full-wave time-reversal focus (calibrate → refocus) | CT model + TR config | refocus field + metrics |
| `run_kwave_command.py` | Wrapper for `simulate_kwave_3d_focus.py` with checkpoints, hard-stop, ledger integration | same as above | same as above + `runner_status.json` |
| `monitor_kwave_process.py` / `monitor_kwave_process/` | Stage-aware long-run supervisor with dynamic ceiling and attention files | child k-Wave command | monitor status/history/attention JSON + captured logs |
| `run_kwave_command/` | Module wrapper for timeout-aware k-Wave command execution | pressure command | partial-safe runner status |
| `run_kwave_point_waveform_command.py` | Point-waveform runner wrapper (1500-point target waveform) | CT model + point plan | waveform NPZ/JSON |
| `simulation_quality.py` | Dry-run quality checks (grid, CFL, PML, memory, PPW) | CT model + preset | `quality_dry_run_summary.json` |
| `simulation_environment.py` | Record Python/k-Wave/platform versions | — | environment record JSON |

---

## Active Paper Route (regenerate after new authoritative data)

`regenerate_paper_route_after_dx05.py` runs these in order, then three validators. Do not rename/move these without updating that script:

| Script | Role |
|--------|------|
| `generate_d60_grid_convergence_report_corrected.py` | Corrected grid-convergence report (imports `build_report`/`write_report` from `generate_d60_grid_convergence_report.py` — the older module is a live dependency, keep it) |
| `generate_reference_paper_gap_matrix.py` | Reference-paper parameter gap matrix |
| `generate_paper_skeleton_20260715.py` | Manuscript skeleton |
| `generate_fine_grid_decision_gate_20260715.py` | Fine-grid resumption decision gate |
| `generate_d60_supplementary_figures_20260715.py` | Supplementary figures |
| `generate_d60_supplementary_analysis_20260715.py` | Supplementary analysis |
| `generate_manuscript_draft_20260715.py` | Manuscript draft |
| `generate_manuscript_final_20260715.py` | Manuscript final |
| `generate_latex_final_20260715.py` | LaTeX final |
| `generate_acoustic_paper_submission_package_20260715.py` | Submission package |

Related recent one-offs still referenced by current sessions: `generate_a4_quick_screen_report_20260718.py` (A.4 screen report), `generate_d60_pml_cfl_sensitivity_20260717.py` (PML16/CFL0.1 sensitivity), `generate_time_reversal_comparison_20260717.py` (TR comparison figures), `generate_d60_grid_convergence_three_level_20260719.py` (three-level grid convergence; pending-state until dx0.375 lands, auto-switches on rerun). Archived Gate-A/D60 stage scripts are in `legacy_archive/stage_scripts_20260719/`.

---

## Planning & Sweeping

| Script | Purpose | Notes |
|--------|---------|-------|
| `plan_ct_target_entry.py` | Plan CT target entry points | case-target planning |
| `plan_entry_offset_sensitivity_079.py` | Entry-offset sensitivity plans for case 079 | offset sweep input |
| `select_paper_gate_a_trajectories.py` | Gate A trajectory selection | imported by `select_paper_gate_a_fixed_radius.py` — keep |
| `select_paper_gate_a_fixed_radius.py` | Fixed-radius Gate A candidate selection | imported by `validate_gate_a_d60_source_safety.py` — keep |

---

## Governance & Evidence

| Script | Purpose | Run After |
|--------|---------|-----------|
| `generate_run_ledger.py` | Update `outputs/run_ledger.jsonl` | any new k-Wave run |
| `governance_recent_evidence.py` | Declarative 2026-07-24 through 2026-07-30 run/artifact registration specs | workspace closeout evidence refresh |
| `analyze_h3_large_matched_baseline_tr_20260730.py` | Audit strict H3-large baseline/TR equivalence, hash artifacts and generate matched metrics | H3-large baseline plus TR completion |
| `generate_evidence_registry.py` | Update `outputs/evidence_registry/evidence_registry.json` | ledger refresh or new evidence |
| `generate_reproducibility_manifest.py` | Update reproducibility manifest | governance refresh |
| `generate_final_reproducibility_package.py` | Package final reproducibility artifacts | end of milestone |
| `generate_module_evidence_brief.py` | Generate evidence briefs for modules | pre/post execution |
| `evaluate_profile_promotion_gate.py` | Evaluate whether an alpha profile can be promoted | profile model-build validation |

---

## Validators & Health Checks

| Script | Checks | Should Always Pass |
|--------|--------|-------------------|
| `check_fus_sim_health.py` | Environment, all validators, key folders, disk, git | before starting any new work |
| `validate_run_ledger.py` | Ledger schema, path existence, claim consistency | after ledger refresh |
| `validate_evidence_registry.py` | Registry schema, input path existence | after registry refresh |
| `validate_reproducibility_manifest.py` | Manifest completeness | after manifest refresh |
| `validate_final_reproducibility_package.py` | Final package integrity | before claiming milestone complete |
| `validate_gate_state_machine.py` | Gate state transitions | after gate updates |
| `validate_gate_a_d60_source_safety.py` | Gate A D60 source-safety records | after Gate A selection changes |

---

## Tests

`tests/` holds 63 unittest-style test modules; 50 active-stage tests were consolidated from root on 2026-07-29. kwave312 has no pytest; run with stdlib unittest:

```
D:\AIprogram\python-envs\kwave312\Scripts\python.exe -m unittest discover -s tests -t .
```

Note: `test_time_reversal_smoke.py` and `test_source_array_memory_smoke.py` launch real (small) k-Wave runs — avoid while a long simulation is in flight. A minimal `pytest.ini` exists for future pytest adoption.

---

## Utility

| Script | Purpose |
|--------|---------|
| `keep_awake.py` | Prevent sleep during overnight runs |
| `watch_dx05_and_regenerate.py` | Watch a run and trigger paper-route regeneration |
| `watch_dx0375_and_closeout_20260719.py` | Watch dx0.375 run; on landing run three-level convergence + governance generators + validators (no docs/commit) |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `acoustic_mapping_profiles/simple_hu300.json` | Default binary HU ≥ 300 skull profile |
| `acoustic_mapping_profiles/continuous_skull.json` | Continuous HU-based skull mapping |
| `acoustic_mapping_profiles/prestus_marsac_mueller.json` | PRESTUS-style profile |
| `acoustic_mapping_profiles/prestus_fit_alpha_power_2.json` | Fit-alpha-power-2 experimental profile |
| `simulation_presets.json` | Simulation presets (standard, grid_convergence, etc.) |
| `governance_schemas/*.json` | JSON schemas for ledger, registry, evidence briefs, etc. |

---

## Directory Map

```
fus-sim/
├── *.py                         ← core scripts (this map, 48 files)
├── tests/                       ← unittest suite (run via unittest discover)
├── acoustic_mapping_profiles/   ← JSON acoustic property profiles
├── data/                        ← input data (case CTs), external source refs
├── governance_schemas/          ← JSON schemas
├── literature_tFUS_review/      ← literature notes and MOCs
├── outputs/                     ← all simulation outputs, reports, governance artifacts
│   ├── _reports_current/        ← current authoritative markdown reports
│   ├── _organization_index.md   ← map of outputs/
│   ├── evidence_registry/       ← evidence registry JSON/MD
│   ├── run_ledger.jsonl         ← run ledger
│   └── ...                      ← simulation data folders
├── legacy_archive/              ← preserved superseded scripts/docs; not first-read context
│   ├── stage_scripts_20260719/  ← Gate-A/D60 stage one-off scripts + their tests
│   └── root_superseded_20260719/← superseded dated plans/handoffs
├── scratch/                     ← local one-off working files (gitignored)
├── AGENTS.md                    ← project-specific agent notes
├── AI_PROJECT_SNAPSHOT.md       ← AI-optimized current state
├── ROOT_ORGANIZATION_INDEX.md   ← current root-file layout and archived old root outputs
├── ACTIVE_WORK_SUMMARY.md       ← human daily summary
├── ACTIVE_WORK.md               ← full historical log
├── CODE_MAP.md                  ← this file
└── README.md                    ← project README
```

---

## External Reference Code (do not edit)

- `data/source_code_refs/BabelBrain_source/` — BabelBrain reference implementation
- `data/source_code_refs/PRESTUS_source/` — PRESTUS reference implementation

These are for reading/comparison only. Do not modify.

---

## Quick Decision Tree

**I need to run a new pressure simulation:**
1. Ensure CT acoustic model exists (`build_ct_acoustic_model.py`).
2. Ensure entry plan exists.
3. Run `run_kwave_command.py --execute ...` (not `simulate_kwave_3d_focus.py` directly unless you know why).
4. Run `generate_run_ledger.py` and `validate_run_ledger.py`.

**I need to run thermal analysis:**
1. Ensure pressure output exists.
2. Run `simulate_pennes_bioheat.py --gao-cooling-protocol ...`

**I need to add a new acoustic mapping profile:**
1. Add JSON in `acoustic_mapping_profiles/`.
2. Run `build_ct_acoustic_model.py` with new profile.
3. Run `evaluate_profile_promotion_gate.py` before promoting to default.

**I need to regenerate the paper route after new authoritative data:**
1. `D:\AIprogram\python-envs\kwave312\Scripts\python.exe regenerate_paper_route_after_dx05.py`

**I need to check if everything is still valid:**
1. `validate_run_ledger.py`
2. `validate_evidence_registry.py`

---

*Keep this map updated when new core scripts are added or responsibilities change. Last refresh: 2026-07-19.*
