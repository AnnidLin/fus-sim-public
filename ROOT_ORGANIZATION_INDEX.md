# fus-sim Root Organization Index

> Updated: 2026-08-04
> Scope: project-root files only. Simulation data and historical outputs remain under `outputs/` and are not moved by this index.

---

## Current Entry Points

Read these first when resuming project work:

1. `AI_PROJECT_SNAPSHOT.md` - current state, blockers, and next action.
2. `PAPER_EXECUTION_MASTER_PLAN.md` - only active scientific execution plan.
3. `AI_TODO.md` - prioritized task board.
4. `AGENT_OPERATING_MODEL.md` - Codex + DS responsibilities and handoff rules.
5. `WORK_TRACE_PROTOCOL.md` - mandatory authorship, trace and closeout fields.
6. `paper/MANUSCRIPT_EVIDENCE_MAP.md` - manuscript claims mapped to evidence.
7. `literature_tFUS_review/00_导航/Home.md` - DS-maintained knowledge-base entry.
8. `CODE_MAP.md` / `RUNBOOK.md` - implementation map and command recipes.

Use `ACTIVE_WORK.md` and `HANDOFF_LOG.md` for append-only historical trace, not as first-read context.

---

## Active Root Files

| Group | Files |
|---|---|
| AI/context entry | `AI_PROJECT_SNAPSHOT.md`, `PAPER_EXECUTION_MASTER_PLAN.md`, `AI_TODO.md`, `AGENT_OPERATING_MODEL.md`, `WORK_TRACE_PROTOCOL.md`, `ROOT_ORGANIZATION_INDEX.md` |
| Handoff/governance logs | `ACTIVE_WORK.md`, `HANDOFF_LOG.md`, `HANDOFF_TEMPLATE.md`, `AGENTS.md` |
| Maps/runbooks | `CODE_MAP.md`, `RUNBOOK.md`, `PIPELINE_TEMPLATES.md`, `NEXT_PHASE_EXECUTION_PLAN.md` |
| Current plan | `PAPER_EXECUTION_MASTER_PLAN.md` only; older acoustic/night plans are historical references, not authorization |
| Core simulation scripts | `build_ct_acoustic_model.py`, `simulate_kwave_3d_focus.py`, `simulate_pennes_bioheat.py`, `simulate_source_array_focus*.py`, `simulate_time_reversal_focus.py`, `run_kwave_command.py`, `run_kwave_point_waveform_command.py` |
| Active paper route | `regenerate_paper_route_after_dx05.py` + the 10 generator scripts listed in `CODE_MAP.md` |
| Governance generators | `generate_run_ledger.py`, `generate_evidence_registry.py`, `generate_reproducibility_manifest.py`, `generate_final_reproducibility_package.py`, `generate_module_evidence_brief.py` |
| Validators/health | `validate_*.py` (7 scripts), `check_fus_sim_health.py` |
| Tests | `tests/` (63 unittest modules; `python -m unittest discover -s tests -t . -p "test_*.py"`), `pytest.ini` |
| Project/human docs | `README.md`, `安装记录.md`, `项目总结.md` |

Local-only working files: `scratch/` and `regeneration_log.txt` are gitignored. `scratch/` is preserved as historical execution evidence; `.tmp/` and `__pycache__/` are disposable caches.

---

## Root Archives

The following root-level files were preserved, not deleted:

| Archive folder | Contents |
|---|---|
| `legacy_archive/root_superseded_20260705/` | `closing_summary.md`, `deep_review_and_plan.md`, `final_stage_review_and_plan.md`, `task.md`, `walkthrough.md`, `safety_constrained_comparison.png` |
| `legacy_archive/root_superseded_20260719/` | `ACOUSTIC_AUTONOMOUS_8H_PLAN_20260715.md`, `ACOUSTIC_AUTONOMOUS_8H_PLAN_20260716.md`, `HANDOFF_20260710.md` |
| `legacy_archive/kimi_era_overnight_20260715_20260720/` | Kimi-era A.3/TR plan, subsequent overnight closeout plan and handoff; historical only |
| `legacy_archive/stage_scripts_20260719/` | 13 closed-stage one-off scripts and their tests (Gate A selection/finalize, D60 stage closeout/audits, Gate B freefield plans) |
| `legacy_archive/ai_program_root_outputs_20260705/` | Preserved top-level `D:\AIprogram\outputs\paper_plan_*.md` workspace planning files |
| `legacy_archive/ai_program_root_scratch_20260705/` | Preserved top-level `D:\AIprogram\scratch\*.py` historical experiment scripts |

These files are superseded by `NEXT_PHASE_EXECUTION_PLAN.md`, `AI_PROJECT_SNAPSHOT.md`, `outputs/_reports_current/`, and the governance artifacts under `outputs/`. Archived scripts are preserved records; some imports of root modules may no longer resolve when run in place.

---

## Output Folder Index

Use `outputs/_organization_index.md` for the authoritative map of simulation outputs, current reports, archived exploratory results, and governance artifacts.
