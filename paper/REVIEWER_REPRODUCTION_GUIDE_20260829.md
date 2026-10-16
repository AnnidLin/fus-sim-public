# Reviewer reproduction guide (non-solver path)

Trace: `TRACE-20260829-001`  
Scope: compact artifact verification and manuscript reconstruction only.  
Current release status: `submission_ready=false`; local archive candidate only.

This route lets a reviewer inspect the reported tables, figures, scalar values,
negative results and claim boundaries without rerunning a long k-Wave solve. It
does not reproduce the excluded full pressure fields and does not establish
physical validation.

## 1. Obtain code and external inputs

Use the immutable repository revision and archive DOI supplied by the authors
after release. Those fields are currently unresolved. Install the exact Python
packages from `requirements-kwave312.txt`.

- UCL H115 comparator: DOI `10.5522/04/28025240.v2`, CC BY 4.0. Obtain it from
  the publisher; the archive references rather than republishes the dataset.
- Case079 CT-ICH v1.3.1: DOI `10.13026/4nae-zg36`, registered restricted-data
  process. The raw CT and reconstructable CT-derived volumes are not included.
- Do not place credentials, signed data-use agreements, private ethics records
  or personal identifiers in the repository.

## 2. Verify the compact candidate

The canonical file list, byte counts and SHA-256 hashes are in
`paper/submission_archive_20260829/manifest.json` and `files.csv`. The current
candidate remains blocked until the project licence, immutable revision and DOI
are supplied. A matching hash verifies file identity, not scientific validity.

From the repository root, write regenerated reports to a scratch directory:

```powershell
python validate_h115_paper_bundle_manifest.py --manifest paper/h115_paper_bundle_20260826/manifest.json
python validate_h115_manuscript_consistency.py --output scratch/manuscript_consistency.json
python validate_h115_submission_preflight.py --output-dir scratch/preflight
python validate_submission_status_consistency.py --output-dir scratch/status
```

Expected boundaries are a valid 31-file paper bundle, zero technical preflight
failures, `submission_ready=false` and a nonpassing H115 external comparison.

## 3. Recheck reporting-sensitive claims

```powershell
python audit_submission_negative_results.py --output-dir scratch/negative_results
python audit_manuscript_numeric_transcription.py --output-dir scratch/numeric_transcription
python audit_figure_table_captions.py --output-dir scratch/caption_semantics
```

These checks verify that failed endpoints remain reported, manuscript scalars
match machine-readable evidence, and figure/table captions preserve projection,
coordinate, normalization and claim-boundary semantics.

## 4. What this route does not do

- It does not execute `simulate_kwave_3d_focus.py`,
  `simulate_time_reversal_focus.py` or another pressure solver.
- It does not regenerate excluded raw CT, voxel-property volumes or full
  pressure fields.
- It does not turn package integrity into numerical convergence, absolute
  pressure accuracy, experimental validation, efficacy or safety.
- A full solver reproduction requires authorized input access, the frozen
  release contract, documented hardware and the project's dry-run/device gates.

## 5. Expected reviewer conclusion

The compact route should reconstruct the paper-facing evidence trail and expose
all retained failures. H115 remains a nonpassing external comparison, and the
Case079 mapping, threshold segmentation and engineering target remain without
independent physical/anatomical validation.
