# Evidence Governance Roadmap

This document is the cross-agent governance entry point for fus-sim. Future Codex, Antigravity, or Claude sessions should read it before changing project direction.

## Current Status

All eight governance items are now complete at v1 for the current project state. The follow-up read-only CFL/environment gate is also implemented and indexed. This does not upgrade the physics evidence to paper-grade; it makes the current M2 engineering baseline more auditable and transferable across agents.

| # | Governance item | Status | Current artifact |
|---:|---|---|---|
| 1 | Evidence Registry | v1 complete | `outputs/evidence_registry/evidence_registry.json`, `governance_schemas/evidence_registry.schema.json`, `outputs/evidence_registry/evidence_registry_validation.json` |
| 2 | Profile / preset / run separation | v1 complete | `outputs/profile_preset_run_contract/profile_preset_run_contract.json`, `outputs/profile_preset_run_contract/profile_preset_run_conformance.json` |
| 3 | Gate state machine | v1 complete | `outputs/gate_state_machine/gate_state_machine.json`, `outputs/gate_state_machine/gate_state_machine_validation.json` |
| 4 | Run ledger | v1 complete | `outputs/run_ledger.jsonl`, `outputs/run_ledger_validation.json` |
| 5 | Maturity model | v1 complete | `outputs/maturity_model/maturity_model.json`, `outputs/maturity_model/maturity_model_validation.json` |
| 6 | Claim policy | v1 complete | `outputs/claim_policy/claim_policy.json`, `outputs/claim_policy/claim_policy_validation.json` |
| 7 | Script/module boundary cleanup | v1 complete as manifest | `outputs/module_boundary_manifest/module_boundary_manifest.json`, `outputs/module_boundary_manifest/module_boundary_manifest_validation.json` |
| 8 | M2 baseline hardening program | v1 complete | `outputs/m2_baseline_hardening_program/m2_baseline_hardening_program.json`, `outputs/m2_baseline_hardening_program/m2_baseline_hardening_program_validation.json` |
| M2G2 | Read-only CFL/environment gate | complete, gate remains block | `outputs/cfl_environment_gate/cfl_environment_gate.json`, `outputs/cfl_environment_gate/cfl_environment_gate_validation.json` |

## Mandatory Handoff Entry Points

Future agents must read these before acting:

1. `AGENTS.md`
2. `ACTIVE_WORK.md`
3. `HANDOFF_LOG.md`
4. `EVIDENCE_GOVERNANCE.md`
5. `outputs/evidence_registry/evidence_registry.json`
6. The evidence brief for the module they intend to change or create

## Current Maturity

Current level:

```text
M2_standard_engineering_baseline_hardening
```

Meaning:

- One user-authorized `simple_hu300` standard engineering pressure run exists.
- The run is not paper-grade.
- The profile is not a validated pressure baseline.
- Medical/safety conclusions are not allowed.
- Paper-grade, alpha semantics, and numerical quality gates remain blocked.
- The CFL/environment gate is implemented, but its gate status is `block` because the historical run environment record is partial.

Next target:

```text
M2_environment_record_and_numerical_sensitivity_planning
```

## Governance Principles

- Treat `outputs/evidence_registry/evidence_registry.json` as the current high-level state index.
- Every new governance module still requires Evidence Brief first.
- Every completed stage must write gap feedback.
- New pressure runs require explicit user authorization, runner gating, and dry-run quality.
- Do not run additional pressure while `numerical_quality_gate` is blocked unless a specific gate authorizes exactly one run.
- Do not promote mapping profiles while `alpha_semantics_gate` is blocked.
- Do not write paper-grade, validated baseline, or medical/safety claims while `paper_grade_gate` is blocked.
- Treat `outputs/cfl_environment_gate/cfl_environment_gate.json` as the current read-only CFL/environment status. It records CFL/PML/runtime metadata and separates current environment observation from historical run capture.
- Future runner-gated outputs should include `environment_record` via `simulation_environment.py`; historical summaries must not be silently rewritten to appear more complete than they were.
- Treat `outputs/numerical_sensitivity_planning/079_candidate_006/numerical_sensitivity_plan.json` as the current read-only index for grid/PML/CFL planning. It does not authorize pressure execution.
- Treat `outputs/one_run_authorization_package/079_candidate_006/one_run_authorization_package.json` as the current single-run decision package. Its recommended candidate is `cfl0p3_pressure_comparison`, but execution still requires explicit user authorization.
- The authorized CFL0.3 standard pressure comparison now lives at `outputs/ct_cfl_sensitivity_runs/079_candidate_006_dx0p75_pml12_cfl0p3_standard`. It supports only an engineering-level CFL sensitivity observation versus the existing CFL0.2 baseline; it does not change paper-grade, medical/safety, thermal, source-backed alpha, or profile-promotion gates.

## Claim Policy

Currently allowed:

- `simple_hu300` is the current reproducible engineering baseline.
- One runner-gated `standard` pressure run completed for 079 `candidate_006`, dx0.75, PML12.
- Current pressure output is standard engineering evidence only.
- Post-pressure readiness keeps paper-grade blocked.

Currently blocked:

- validated pressure baseline
- paper-grade reproduction
- medical or safety conclusion
- source-backed alpha pressure eligibility
- default profile promotion

## Target Architecture

### 1. Evidence Registry

Central machine-readable index:

```text
outputs/evidence_registry/evidence_registry.json
```

It contains artifact entries, gate states, global claim policy, maturity level, run ledger seed, and recommended next action.

Current v1 support files:

```text
governance_schemas/evidence_registry.schema.json
validate_evidence_registry.py
outputs/evidence_registry/evidence_registry_validation.json
outputs/evidence_registry/evidence_registry_validation.md
```

Any future registry update must pass:

```powershell
python validate_evidence_registry.py
```

### 2. Profile / Preset / Run Separation

Every future summary should distinguish:

```json
{
  "profile_status": "baseline_compatible_not_validated",
  "preset_level": "standard",
  "run_claim_level": "standard_engineering_pressure_output"
}
```

Do not let a successful run upgrade a profile.

Current v1 support files:

```text
governance_schemas/profile_preset_run_contract.schema.json
generate_profile_preset_run_contract.py
validate_profile_preset_run_contract.py
outputs/profile_preset_run_contract/profile_preset_run_contract.json
outputs/profile_preset_run_contract/profile_preset_run_conformance.json
```

Any future run-summary governance update must preserve:

- profile status is independent from preset level
- preset level is independent from claim level
- run success does not upgrade profile or paper-grade status

### 3. Gate State Machine

Use fixed gate names:

- `mapping_profile_gate`
- `alpha_semantics_gate`
- `pressure_execution_gate`
- `numerical_quality_gate`
- `interpretation_gate`
- `paper_grade_gate`

Gate status values are `pass`, `warn`, and `block`. Each gate should expose one `next_action`.

Current v1 support files:

```text
governance_schemas/gate_state_machine.schema.json
generate_gate_state_machine.py
validate_gate_state_machine.py
outputs/gate_state_machine/gate_state_machine.json
outputs/gate_state_machine/gate_state_machine_validation.json
```

Any gate refresh must pass:

```powershell
python validate_gate_state_machine.py
python validate_evidence_registry.py
```

### 4. Run Ledger

Current v1 ledger:

```text
outputs/run_ledger.jsonl
```

Each real run should record timestamp, command, input hashes, output directory, preset, runtime, runner status, pressure generated or not, claim level, and user authorization source.

Current support files:

```text
governance_schemas/run_ledger.schema.json
generate_run_ledger.py
validate_run_ledger.py
outputs/run_ledger_summary.json
outputs/run_ledger_validation.json
```

After every real run, update and validate:

```powershell
python generate_run_ledger.py
python validate_run_ledger.py
python generate_evidence_registry.py
python validate_evidence_registry.py
```

### 5. Maturity Model

Use these levels:

- `M0_plumbing_smoke`
- `M1_reproducible_engineering_baseline`
- `M2_standard_engineering_baseline_hardening`
- `M3_numerical_sensitivity_package`
- `M4_source_backed_profile_cross_checked`
- `M5_paper_grade_candidate`

Current project state is M2, not M3/M4/M5.

Current v1 support files:

```text
governance_schemas/maturity_model.schema.json
generate_maturity_model.py
validate_maturity_model.py
outputs/maturity_model/maturity_model.json
outputs/maturity_model/maturity_model_validation.json
```

### 6. Claim Policy

Every report or summary should include:

```json
{
  "allowed_claims": [],
  "blocked_claims": [],
  "medical_or_safety_conclusion_allowed": false,
  "paper_grade_ready": false,
  "profile_promotion_allowed": false
}
```

Current v1 support files:

```text
governance_schemas/claim_policy.schema.json
generate_claim_policy.py
validate_claim_policy.py
outputs/claim_policy/claim_policy.json
outputs/claim_policy/claim_policy_validation.json
```

Any report wording or claim-boundary change must keep:

```powershell
python validate_claim_policy.py
python validate_evidence_registry.py
```

### 7. Script And Module Boundary Cleanup

Future cleanup target:

```text
scripts/evidence/
scripts/gates/
scripts/model_build/
scripts/runners/
scripts/reports/
```

Current v1 support files:

```text
governance_schemas/module_boundary_manifest.schema.json
generate_module_boundary_manifest.py
validate_module_boundary_manifest.py
outputs/module_boundary_manifest/module_boundary_manifest.json
outputs/module_boundary_manifest/module_boundary_manifest_validation.json
```

The current v1 completed artifact is a manifest and validator, not a physical move. Do not reorganize files during active physics work. Do physical reorganization only as a separate evidence-briefed cleanup after import and command-reference audit.

### 8. M2 Baseline Hardening Program

Current v1 support files:

```text
governance_schemas/m2_baseline_hardening_program.schema.json
generate_m2_baseline_hardening_program.py
validate_m2_baseline_hardening_program.py
outputs/m2_baseline_hardening_program/m2_baseline_hardening_program.json
outputs/m2_baseline_hardening_program/m2_baseline_hardening_program_validation.json
```

Near-term program:

1. Governance spine complete: items 1-8 v1.
2. Create read-only CFL/environment gate.
3. Refresh evidence registry.
4. Then decide whether one additional comparison run is justified.

## Current Recommended Next Action

Create a read-only CFL/environment gate and then refresh:

```text
outputs/evidence_registry/evidence_registry.json
```

Do not run more pressure before that gate.
