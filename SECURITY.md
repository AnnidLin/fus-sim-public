# Security and Data Safety

Please report issues that could expose private data, encourage unsafe simulation defaults, or weaken safety gates.

Examples include:

- Accidentally tracked medical images, DICOM/NIfTI files, ZIP datasets, generated model arrays, or paper PDFs.
- Scripts that silently bypass dry-run quality checks.
- Defaults that imply clinical validity without evidence.
- Incorrect acoustic attenuation semantics, units, or thermal safety claims.
- Output examples that could be mistaken for patient-specific treatment guidance.

For public issues, avoid sharing private data. Describe the affected file, command, or parameter boundary, and use minimal reproducible examples with synthetic data whenever possible.

