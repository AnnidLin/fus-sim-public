# Public contents and data availability

The release includes project source, tests, parameter/schema definitions, literature notes,
manuscript drafts and selected compact numerical summaries. Historical public files and
commits have been retained; the private repository history has not been merged or pushed.

The following remain outside the public release:

- Raw CT/MRI/DICOM/NIfTI data, voxel-wise anatomical masks and acoustic-property volumes.
- Full simulated pressure arrays and large solver/HDF5/binary outputs.
- Third-party paper PDFs, downloaded datasets and upstream source checkouts.
- Private handoff logs, credentials, signed agreements and workstation/session state.

Case079 data must be obtained from its original PhysioNet source under its access terms.
The H115 measurement source is DOI [10.5522/04/28025240.v2](https://doi.org/10.5522/04/28025240.v2).
Availability of a citation does not grant permission to redistribute restricted inputs.

## Evidence files and historical paths

`evidence/` contains six selected compact comparison/status JSON files. The
`paper/` directory contains manuscript and audit documents, including the September review.
References to excluded `outputs/`, `data/` or private logs are intentionally retained as
historical provenance; they are not promises that those files are in this repository.
Workstation paths have been replaced in publication copies. Historical checksums refer
to the original private artifacts and are not a manifest for this public export.
Use `PUBLIC_MANIFEST.json` for the public snapshot's file hashes.

Archive/experiment-dependent validators and tests need the omitted artifacts and are not
part of the public smoke suite. The README lists the verified data-independent commands.

The sole `.nii` path allowed in tests is a 42-byte plain-text exclusion fixture containing
`restricted test fixture; not medical data`. It is not a NIfTI image or patient record.

## Licences

Project-owned code is MIT licensed. External datasets and cited publications retain their
own terms. The vendored modified k-Wave-python module under `patches/` retains its LGPL
terms; see [third-party notices](THIRD_PARTY_NOTICES.md).
