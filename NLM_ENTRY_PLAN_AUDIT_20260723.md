# NLM Case 72m Entry Plan Audit & Correction Plan

## Audit Findings (2026-07-23)

### 1. Source Composition Audit

| Aperture | Total Points | Label 0 (Bkg) | Label 1 (Tissue) | Label 2 (Skull) | Source-Safe? |
|----------|-------------|---------------|------------------|----------------|-------------|
| **15 mm** | 349 | 180 (51.6%) | 169 (48.4%) | **0 (0%)** | ✅ No skull |
| 20 mm | 593 | 264 (44.5%) | 326 (55.0%) | **3 (0.5%)** | ❌ Skull present |
| 25 mm | 849 | 341 (40.2%) | 503 (59.2%) | **5 (0.6%)** | ❌ Skull present |
| 30 mm | 1309 | 466 (35.6%) | 838 (64.0%) | **5 (0.4%)** | ❌ Skull present |

**修正后表述**: "15mm aperture avoids skull (0 label 2 voxels), but 48.4% of source points lie in soft tissue (label 1). Source-safe for k-Wave execution, NOT pure-background. Use `--aperture-mm 15`."

### 2. Entry Plan Hash Audit
- **Original (contract)**: `ffcd...` (from planning contract record)
- **Current (on disk)**: `2142029dac7b56a1989c55ba3b4977501535d5b9e20c35b2c992e2477f6db469`
- **Cause**: DS changed standoff from 8mm → 12mm, regenerated plan
- **Action**: Cannot auto-update hash. Hash must be re-anchored after independent audit.

### 3. Missing Dry-Run Evidence
- File `outputs_nlm_kwave_check/quality_dry_run_summary.json` contains **25mm/849pt** result, not 15mm
- Need to generate independent 15mm dry-run with proper output path

### 4. AI_PROJECT_SNAPSHOT.md Errors (line 65)
- "source-safe verified" → should be "no skull crossing for 15mm aperture; source-safe for k-Wave; 48.4% in soft tissue"
- "ROI transfer pending" → ROI transfer is **already complete**

### 5. Missing Evidence Brief
- No gap feedback or Evidence Brief for the entry plan change

## Correction Plan

1. ✅ **Step 1**: Generate independent 15mm dry-run → save with unique path and SHA256
2. ✅ **Step 2**: Create Evidence Brief with gap feedback documenting the aperture reduction rationale
3. ✅ **Step 3**: Fix AI_PROJECT_SNAPSHOT.md line 65 and ROI transfer claim
4. ✅ **Step 4**: Update contract tracking with new hash (after independent verification)
5. ❌ **Deferred**: Finding all-label-0 source positions is geometrically impossible for this target/entry; the head surface has soft tissue extending to the air boundary. 15mm-no-skull is the best achievable source-safe configuration.