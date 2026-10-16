# Case079 provenance and compliance audit

Trace: `TRACE-20260829-001`  
Audit date: 2026-08-29  
Scope: local evidence plus official dataset records; no legal conclusion

## Decision

The local `data/raw_ct/079.nii` can now be traced to the PhysioNet **Computed
Tomography Images for Intracranial Hemorrhage Detection and Segmentation v1.3.1**
resource, DOI `10.13026/4nae-zg36`. This resolves the dataset identity and supports
dataset-level ethics and de-identification statements. It does **not** prove who
accepted the restricted-data agreement for this local copy, does not document an
individual-consent waiver, and does not permit bundling the raw CT in a public
archive. Submission remains conditional on author confirmation of lawful local
access and the journal-specific ethics wording.

## Evidence chain

| Claim | Evidence | Assessment |
|---|---|---|
| Local file came from PhysioNet CT-ICH v1.3.1 | NTFS `Zone.Identifier` on `data/raw_ct/079.nii`: referrer `https://physionet.org/content/ct-ich/1.3.1/ct_scans/`; host `https://physionet.org/files/ct-ich/1.3.1/ct_scans/079.nii?download` | Strong local provenance evidence |
| Dataset identity and version | Official PhysioNet record, DOI `10.13026/4nae-zg36`, version 1.3.1 | Supported |
| Dataset ethics approval | Official record states retrospective collection was approved by the Iraqi Ministry of Health, Babil Office research and ethics board, approval 1369 | Supported at dataset level |
| Patient data and faces were de-identified | Official methods and release notes state sensitive information was anonymized and faces were de-identified; v1.3.1 describes blurring plus random noise | Supported at dataset level |
| Individual informed consent or waiver | No explicit consent/waiver statement was found in the official dataset page inspected in this audit | Unresolved; author/journal blocker |
| Local access was obtained under the required agreement | Official record requires registered users to sign the specified data-use agreement; the local file metadata does not identify the account or acceptance record | Unresolved; author blocker |
| Raw CT can be redistributed in the paper archive | The official restricted-data licence prohibits sharing access to restricted data | Not permitted by current evidence; raw CT must be excluded |
| Derived code can be public | The licence requires code associated with publications using the data to be contributed to an open repository | Supported, subject to third-party code licences |

## Local artifact identity

- Path: `data/raw_ct/079.nii`
- Size: 20,972,464 bytes
- SHA-256: `3963abaaa94e565b836b0bfff9c70fd027b38864d09652348c4ead7b64f36ef0`
- NIfTI shape: `512 × 512 × 40`
- Voxel size: `0.390625 × 0.390625 × 5.0 mm`
- Stored datatype: `int16`
- Header: Siemens / Head_SAFIRE; no patient name or identifier was observed in
  the inspected NIfTI header fields. This header check is not a formal PHI audit.

## Official sources

1. M. Hssayeni, *Computed Tomography Images for Intracranial Hemorrhage Detection
   and Segmentation*, v1.3.1, PhysioNet (2020), DOI
   [10.13026/4nae-zg36](https://doi.org/10.13026/4nae-zg36).
2. [PhysioNet CT-ICH v1.3.1 official record](https://physionet.org/content/ct-ich/1.3.1/).
3. [PhysioNet Restricted Health Data License 1.5.0](https://physionet.org/content/ct-ich/view-license/1.3.1/).

## Manuscript-safe wording

> The computational case used subject 079 from the PhysioNet CT-ICH v1.3.1
> dataset (DOI: 10.13026/4nae-zg36). The source dataset reports ethics approval
> by the Iraqi Ministry of Health, Babil Office (approval 1369), anonymization of
> sensitive patient information, and facial de-identification of the released
> NIfTI images. Access is governed by the PhysioNet Restricted Health Data
> License and Data Use Agreement. The raw CT is therefore not redistributed;
> qualified users should obtain it directly from PhysioNet.

Do not add a statement that informed consent was obtained or waived unless the
authors supply documentary support or the journal accepts the dataset-level
ethics statement without it.

## Archive disposition

| Item | Public archive action | Reason |
|---|---|---|
| `data/raw_ct/079.nii` | Exclude; record DOI, relative path, size and SHA-256 only | Restricted health data; no redistribution evidence |
| CT-derived full voxel property fields | Exclude by default pending a derived-data and re-identification risk decision | May encode reconstructable anatomy and inherit restricted-data risk |
| Code, schemas and parameter profiles | Candidate for inclusion after licence inventory | Reproducibility without redistributing CT |
| Small aggregate metrics, tables and non-identifying figures | Candidate for inclusion after disclosure review | Derived results; still require claim and privacy review |

## Remaining author actions

1. Identify the registered PhysioNet user or institutional process under which
   the local copy was downloaded and retain the agreement/approval record
   privately; do not place credentials in the repository.
2. Confirm whether the target journal requires an informed-consent waiver
   statement beyond the dataset's documented ethics approval and anonymization.
3. Confirm that the planned public archive excludes the raw CT and any
   reconstructable derived anatomy.

