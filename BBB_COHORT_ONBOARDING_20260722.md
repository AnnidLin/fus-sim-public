# BBB Multi-Case Onboarding and Readiness Audit

## Goal

Extend the Case 079 pure-simulation prototype into a deterministic multi-case intake boundary without inventing registered anatomy, device geometry, exposure inputs, or pressure evidence.

## Platform interface

- `bbb_cohort_readiness.py` validates a cohort manifest and reuses the frozen BBB plan schema.
- `planning_contracts/examples/bbb_cohort_manifest.json` shows how a case links its plan contract, ROI summary, path ranking, element plan, exposure proxy, automatic report, and report validation.
- Outputs are `cohort_readiness.json`, `case_readiness.csv`, and `cohort_readiness.md`.
- Project-relative paths are constrained to the repository root; duplicate case IDs, missing artifacts, plan/case mismatches, and invalid contracts fail explicitly.

## Readiness semantics

The audit separates four states:

1. pure-simulation prototype artifact consistency;
2. registered anatomy plus authoritative world mapping;
3. physical device geometry readiness;
4. exposure evidence readiness.

The multi-case registered-analysis gate requires at least two cases and requires every case to pass both the prototype and registered-anatomy gates. No audit state represents clinical readiness or safety.

## Case 079 result

The frozen Case 079 fixture passes all current prototype artifact checks and verifies the patient-model and entry-plan file hashes. It remains a single case with a synthetic ROI and unavailable world affine. Physical device geometry, waveform-derived in-situ PNP, a BBB pulse train, a microbubble protocol, and PCD/AE evidence are also unavailable.

Canonical output: `outputs/bbb_cohort_readiness_20260722/`.

## Verification

```powershell
D:\AIprogram\python-envs\kwave312\Scripts\python.exe -m py_compile bbb_cohort_readiness.py
D:\AIprogram\python-envs\kwave312\Scripts\python.exe -m unittest discover -s . -p 'test_bbb*.py' -v
D:\AIprogram\python-envs\kwave312\Scripts\python.exe bbb_cohort_readiness.py --verify-files --output-dir outputs\bbb_cohort_readiness_20260722
```

The 2026-07-22 verification completed 37/37 BBB tests and reproduced the same JSON hash on a second report generation. No k-Wave or Pennes run was started.

## Next input gate

The next useful platform input is a contract-valid case with a registered anatomical ROI mask and authoritative voxel-to-world affine. Add at least one additional independently registered case before making a multi-case analysis claim.
