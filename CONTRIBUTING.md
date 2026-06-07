# Contributing

Contributions are welcome when they improve reproducibility, evidence traceability, safety boundaries, or public usability.

## Ground Rules

- Do not add private medical data, raw CT/DICOM/NIfTI files, generated model arrays, large binary outputs, or redistributed paper PDFs.
- Keep examples runnable with public, synthetic, or user-provided data.
- Do not promote exploratory parameters to defaults without source-backed evidence.
- Do not remove simulation quality metadata, dry-run checks, or conservative warning fields.
- Keep claims precise: distinguish quick screening, standard review, paper-grade readiness, and validated clinical use.

## Evidence-Driven Changes

For changes to physical parameters, CT-to-acoustic mapping, boundary settings, thermal assumptions, k-Wave presets, or numerical quality gates:

1. Add or update an evidence brief.
2. Record unsupported assumptions and remaining gaps.
3. Run the lightest relevant verification before claiming success.
4. Keep generated heavy outputs out of git.

## Public Data Hygiene

Before opening a pull request, check:

```powershell
git status --short
git ls-files *.pdf *.nii *.dcm *.npz *.zip
```

The second command should return no tracked private/heavy scientific artifacts unless there is a documented, redistribution-safe reason.

