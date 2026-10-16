# Pipeline Templates

> **For AI agents**: copy-pasteable multi-step command sequences for the most common workflows. Each template assumes you are in `<PRIVATE_WORKSPACE>\` and using the project-local Python environment.

---

## Environment Variable

Set once per session:

```bash
PY="D:/AIprogram/python-envs/kwave312/Scripts/python.exe"
```

---

## Template 1: Standard Pressure + Thermal Baseline

Goal: build model, dry-run, run pressure, run Pennes thermal, refresh governance.

```bash
PY="D:/AIprogram/python-envs/kwave312/Scripts/python.exe"
CASE=079
CANDIDATE=candidate_006
PROFILE=simple_hu300
DX=0.75
MODEL_DIR="outputs/ct_acoustic_model_3d_profile_${PROFILE}_dx${DX/./p}"
PRESSURE_DIR="outputs/corrected_pressure_runs/${CASE}_${CANDIDATE}_dx${DX/./p}_standard"
THERMAL_DIR="outputs/corrected_pennes_thermal_${CASE}_${CANDIDATE}_dx${DX/./p}"

# 1. Build acoustic model
$PY build_ct_acoustic_model.py \
  --ct "data/case_${CASE}/ct.nii.gz" \
  --profile "acoustic_mapping_profiles/${PROFILE}.json" \
  --output-dir "$MODEL_DIR" \
  --resolution "$DX"

# 2. Dry-run quality check
$PY simulate_kwave_3d_focus.py \
  --model "${MODEL_DIR}/${CASE}_${CANDIDATE}_model.npz" \
  --entry-plan "outputs/ct_entry_plan_${CASE}/${CASE}_${CANDIDATE}_entry_plan.json" \
  --preset standard \
  --dry-run-quality

# 3. Run pressure (background recommended for long jobs)
$PY run_kwave_command.py \
  --script simulate_kwave_3d_focus.py \
  --model "${MODEL_DIR}/${CASE}_${CANDIDATE}_model.npz" \
  --entry-plan "outputs/ct_entry_plan_${CASE}/${CASE}_${CANDIDATE}_entry_plan.json" \
  --preset standard \
  --checkpoint 120 \
  --hard-stop 480 \
  --execute

# 4. Run Pennes thermal
$PY simulate_pennes_bioheat.py \
  --pressure "${PRESSURE_DIR}/pressure_max_mpa.npz" \
  --summary "${PRESSURE_DIR}/summary.json" \
  --output-dir "$THERMAL_DIR" \
  --gao-cooling-protocol

# 5. Refresh governance
$PY generate_run_ledger.py
$PY generate_evidence_registry.py
$PY generate_reproducibility_manifest.py
$PY generate_final_reproducibility_package.py

# 6. Validate
$PY validate_run_ledger.py
$PY validate_evidence_registry.py
$PY validate_reproducibility_manifest.py
$PY validate_final_reproducibility_package.py
```

---

## Template 2: Grid Convergence Study

Goal: run the same case at two resolutions and compare.

```bash
PY="D:/AIprogram/python-envs/kwave312/Scripts/python.exe"
CASE=079
CANDIDATE=candidate_006
PROFILE=simple_hu300

for DX in 0.75 0.5; do
  MODEL_DIR="outputs/ct_acoustic_model_3d_profile_${PROFILE}_dx${DX/./p}"
  PRESSURE_DIR="outputs/ct_grid_convergence_runs/${CASE}_${CANDIDATE}_dx${DX/./p}_standard"

  $PY build_ct_acoustic_model.py \
    --ct "data/case_${CASE}/ct.nii.gz" \
    --profile "acoustic_mapping_profiles/${PROFILE}.json" \
    --output-dir "$MODEL_DIR" \
    --resolution "$DX"

  $PY run_kwave_command.py \
    --script simulate_kwave_3d_focus.py \
    --model "${MODEL_DIR}/${CASE}_${CANDIDATE}_model.npz" \
    --entry-plan "outputs/ct_entry_plan_${CASE}/${CASE}_${CANDIDATE}_entry_plan.json" \
    --preset standard \
    --checkpoint 120 \
    --hard-stop "$([ "$DX" = "0.5" ] && echo 600 || echo 180)" \
    --execute
done

# Compare
$PY generate_ct_grid_convergence_analysis.py \
  --case "$CASE" \
  --candidate "$CANDIDATE" \
  --profile "$PROFILE"
```

---

## Template 3: Sweep Scan + Geometric Proxy Screening

Goal: generate sweep candidates, screen geometrically, then run top candidates.

```bash
PY="D:/AIprogram/python-envs/kwave312/Scripts/python.exe"
CASE=079
TARGET=target_020
SWEEP_DIR="outputs/ct_sweep_scan_${CASE}_dx0p75"

# 1. Generate sweep candidates
$PY plan_transducer_sweep.py \
  --case "$CASE" \
  --target "$TARGET" \
  --output "$SWEEP_DIR"

# 2. Fast geometric proxy screening
$PY plan_geometric_proxy_screening_${CASE}.py \
  --candidates "${SWEEP_DIR}/candidates.json" \
  --output "outputs/geometric_proxy_screening_${CASE}"

# 3. Run top candidate(s) through full pipeline (use Template 1 with candidate=sweep_005)
```

---

## Template 4: Pressure Scaling Pareto Sweep

Goal: run the same geometry at multiple source pressures for Pareto analysis.

```bash
PY="D:/AIprogram/python-envs/kwave312/Scripts/python.exe"
CASE=079
CANDIDATE=sweep_005
MODEL="outputs/ct_acoustic_model_3d_profile_hu300_dx0p75/079_candidate_006_model.npz"
ENTRY="outputs/ct_sweep_scan_079_dx0p75/sweep_005_entry_plan.json"

for P in 0.5 0.6 0.7 0.8; do
  P_PA=$(echo "$P * 1000000" | bc | cut -d. -f1)
  OUT_DIR="outputs/ct_sweep_scan_079_dx0p75/sweep_005_p${P/./p}"

  $PY run_kwave_command.py \
    --script simulate_kwave_3d_focus.py \
    --model "$MODEL" \
    --entry-plan "$ENTRY" \
    --source-pressure "$P_PA" \
    --preset standard \
    --checkpoint 120 \
    --hard-stop 240 \
    --execute

  $PY simulate_pennes_bioheat.py \
    --pressure "${OUT_DIR}/pressure_max_mpa.npz" \
    --summary "${OUT_DIR}/summary.json" \
    --output-dir "outputs/corrected_pennes_thermal_p${P/./p}" \
    --gao-cooling-protocol
done

# Refresh governance
$PY generate_run_ledger.py
$PY generate_evidence_registry.py
```

---

## Template 5: Free-Field Calibration

Goal: calibrate transducer in water (no skull) to establish source→free-field chain.

```bash
PY="D:/AIprogram/python-envs/kwave312/Scripts/python.exe"

$PY simulate_freefield_transducer.py \
  --aperture 30 \
  --radius 35 \
  --frequency 500000 \
  --resolution 0.75 \
  --preset standard \
  --output-dir outputs/freefield_calibration_current_tuned \
  --execute
```

---

## Template 6: Governance Refresh Only

Goal: after manual runs, refresh all governance artifacts.

```bash
PY="D:/AIprogram/python-envs/kwave312/Scripts/python.exe"

$PY generate_run_ledger.py
$PY generate_evidence_registry.py
$PY generate_reproducibility_manifest.py
$PY generate_final_reproducibility_package.py

$PY validate_run_ledger.py
$PY validate_evidence_registry.py
$PY validate_reproducibility_manifest.py
$PY validate_final_reproducibility_package.py
```

---

## Template 7: Health Check Before Any Work

```bash
D:/AIprogram/python-envs/kwave312/Scripts/python.exe check_fus_sim_health.py
```

---

## Notes

- Always run `check_fus_sim_health.py` first.
- Always run dry-run quality before `--execute`.
- Adjust `--hard-stop` based on grid size and observed runtimes.
- Background long runs and tail the log.
- Refresh governance after any new simulation output.

---

*Last updated: 2026-07-04.*
