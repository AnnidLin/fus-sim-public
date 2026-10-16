# Dependency licence and exclusion inventory

- status: `conditional_project_licence_missing`
- pinned dependencies: `29`
- project licence: unresolved author decision

| Package | Version | Licence metadata |
|---|---:|---|
| beartype | 0.22.9 | MIT License |
| colorama | 0.4.6 | BSD License |
| contourpy | 1.3.3 | BSD License |
| cycler | 0.12.1 | BSD License |
| deepdiff | 8.6.2 | MIT License |
| Deprecated | 1.3.1 | MIT License |
| fonttools | 4.62.1 | MIT |
| h5py | 3.15.1 | BSD-3-Clause |
| jaxtyping | 0.3.2 | MIT License |
| k-Wave-python | 0.6.1 | GNU General Public License v3 (GPLv3) |
| kiwisolver | 1.5.0 | BSD License |
| matplotlib | 3.10.7 | Python Software Foundation License |
| nibabel | 5.4.2 | MIT |
| numpy | 2.2.6 | BSD License |
| opencv-python | 4.13.0.92 | Apache Software License |
| orderly-set | 5.5.0 | MIT License |
| packaging | 26.2 | Apache-2.0 OR BSD-2-Clause |
| pillow | 12.2.0 | MIT-CMU |
| pydicom | 3.0.1 | MIT License |
| pyparsing | 3.3.2 | MIT |
| python-dateutil | 2.9.0.post0 | BSD License; Apache Software License |
| scipy | 1.15.3 | BSD License |
| setuptools | 82.0.1 | MIT |
| six | 1.17.0 | MIT License |
| tqdm | 4.67.3 | MPL-2.0 AND MIT |
| typing_extensions | 4.15.0 | PSF-2.0 |
| wadler_lindig | 0.1.7 | Apache Software License |
| wheel | 0.47.0 | MIT |
| wrapt | 2.1.2 | BSD-2-Clause |

## Archive exclusions

- `data/raw_ct/079.nii` — restricted health data; record DOI, size and SHA-256 but do not redistribute
- `CT-derived voxel property volumes and masks` — potentially reconstructable anatomy; exclude pending formal derived-data/privacy decision
- `pressure_max_mpa.npz and full solver fields` — large generated artifacts; retain hashes and compact summaries in the execution record
- `data/source_code_refs/PRESTUS_source and BabelBrain_source` — third-party source snapshots; cite upstream repositories and licences rather than repackaging
- `credentials, signed agreements and private ethics records` — private author/institutional records; never include in a public archive

Installed-package metadata is an inventory aid, not legal advice; the copyright holder must choose the project licence and approve the final notices before release.
