# fus-sim Runbook

> **For AI agents**: copy-pasteable commands for the most common operations. Always use the project-local Python environment and tool paths.

> **Status boundary (2026-08-29):** this is an operational recipe collection,
> not authorization to launch a solver. Example input paths may belong to older
> workflows. For the current paper-facing, non-solver verification path use
> `paper/REVIEWER_REPRODUCTION_GUIDE_20260829.md`. Any new pressure run still
> requires a new Evidence Brief, exact dry-run and device gate; none is currently
> authorized.

---

## Environment Shortcuts

```bash
# Python for k-Wave / Pennes / governance
PY="D:/AIprogram/python-envs/kwave312/Scripts/python.exe"

# Git (project-local)
GIT="D:/AIprogram/tools/Git/cmd/git.exe"
```

---

## 1. Check Project Health

One command:

```bash
$PY check_fus_sim_health.py
```

Or run validators individually:

```bash
$PY validate_run_ledger.py
$PY validate_evidence_registry.py
$PY validate_reproducibility_manifest.py
$PY validate_final_reproducibility_package.py
```

Expected: all report `*_valid: true, failed_check_count: 0`.

---

## 2. Build CT Acoustic Model

```bash
$PY build_ct_acoustic_model.py \
  --ct data/case_079/ct.nii.gz \
  --profile acoustic_mapping_profiles/simple_hu300.json \
  --output-dir outputs/ct_acoustic_model_3d_profile_hu300_dx0p75 \
  --resolution 0.75
```

Common profiles: `simple_hu300`, `simple_hu250`, `simple_hu400`, `continuous_skull`, `prestus_marsac_mueller`, `prestus_fit_alpha_power_2`.

---

## 3. Dry-Run Quality Check

```bash
$PY simulate_kwave_3d_focus.py \
  --model outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/079_candidate_006_model.npz \
  --entry-plan outputs/ct_entry_plan_079/079_candidate_006_entry_plan.json \
  --preset standard \
  --dry-run-quality
```

Check `PPW >= 6`, `CFL <= 0.2`, `PML >= 12`, memory estimate before executing.

---

## 4. Run 3D Pressure Simulation

Use the wrapper (recommended):

```bash
$PY run_kwave_command.py \
  --script simulate_kwave_3d_focus.py \
  --model outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/079_candidate_006_model.npz \
  --entry-plan outputs/ct_entry_plan_079/079_candidate_006_entry_plan.json \
  --preset standard \
  --checkpoint 120 \
  --hard-stop 480 \
  --execute
```

Expected runtime: 10–60 min for dx0.75; 1–10 hours for dx0.5 depending on grid size.

---

## 5. Run Pennes Bioheat

```bash
$PY simulate_pennes_bioheat.py \
  --pressure outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard/pressure_max_mpa.npz \
  --summary outputs/corrected_pressure_runs/079_candidate_006_dx0p75_pml12_cfl0p2_standard/summary.json \
  --output-dir outputs/corrected_pennes_thermal_dx0p5 \
  --gao-cooling-protocol
```

> **Gotcha**: `--gao-cooling-protocol` must be enabled (it is now the default). Without it, temperature rises are massively overestimated.

---

## 6. Refresh Governance After a Run

```bash
$PY generate_run_ledger.py
$PY generate_evidence_registry.py
$PY generate_reproducibility_manifest.py
$PY generate_final_reproducibility_package.py

$PY validate_run_ledger.py
$PY validate_evidence_registry.py
$PY validate_reproducibility_manifest.py
$PY validate_final_reproducibility_package.py
```

Always run validators after refreshing.

---

## 7. Plan a Transducer Sweep

```bash
$PY plan_transducer_sweep.py --case 079 --target target_020 --output outputs/ct_sweep_scan_079_dx0p75
```

---

## 8. Geometric Proxy Screening (fast, no k-Wave)

```bash
$PY plan_geometric_proxy_screening_079.py \
  --candidates outputs/ct_sweep_scan_079_dx0p75/candidates.json \
  --output outputs/geometric_proxy_screening_079
```

---

## 9. Compare Continuous vs Binary Skull Mapping

```bash
$PY compare_continuous_vs_binary.py \
  --binary outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/079_candidate_006_model.npz \
  --continuous outputs/ct_acoustic_model_3d_profile_continuous/079_candidate_006_model.npz \
  --output outputs/continuous_vs_binary_comparison
```

---

## 10. Common Gotchas

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `pressure_allowed_by_alpha_semantics=false` | `simple_hu300.json` lacks `alpha_semantics` block | Apply Option B fix in `build_ct_acoustic_model.py` + `simulate_kwave_3d_focus.py` |
| Pennes max dT >> 2°C | Missing `--gao-cooling-protocol` | Re-run with cooling protocol |
| Global peak far from target | Phase aberration, no correction | Implement phase correction / source-point array |
| Validator fails after moving files | Relative paths in ledger/registry broken | Do not move referenced folders; update ledger if you must |
| dx0.5 run crashes / very slow | Grid too large or standoff too short | Check dry-run quality; ensure standoff >= 12 mm |

---

## 11. Background Task Pattern

For long k-Wave runs:

```bash
$PY run_kwave_command.py ... --execute > outputs/my_run.log 2>&1 &
```

Then poll with:

```bash
tail -f outputs/my_run.log
```

Always state expected runtime, memory, and hard-stop limit before starting.

---

## 12. What Not to Run

- Do **not** run `simulate_kwave_3d_focus.py` directly for production runs unless you have a specific reason; use `run_kwave_command.py` for checkpointing and ledger integration.
- Do **not** run large 3D simulations without a prior dry-run quality check.
- Do **not** modify `data/source_code_refs/` external reference code.

---

*Update this runbook when new scripts or common failure modes appear.*
