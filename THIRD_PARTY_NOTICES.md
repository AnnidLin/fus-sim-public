# Third-party notices

The repository MIT licence covers project-owned contributions, not external datasets,
publications or third-party code.

## k-Wave-python C++ backend patch

`patches/kwave_cpp_backend_20260719/cpp_simulation.py` is a modified source copy from
k-Wave-python 0.6.1. It is distributed under the upstream GNU LGPL version 3 terms,
not relicensed under MIT. The modification date and changes are documented in that
directory's README: source flag semantics, record flags, source scaling and output order.
The source is provided in editable form; no compiled solver is bundled.

- Upstream: https://github.com/waltsims/k-wave-python
- LGPL text: `patches/kwave_cpp_backend_20260719/COPYING.LESSER`
- Incorporated GPL v3 text: `patches/kwave_cpp_backend_20260719/COPYING`

The patch is not automatically installed by the public quickstart. Full historical
backend reproduction requires deliberate environment setup and the original evidence gates.

PRESTUS, BabelBrain, NumPy, SciPy and other cited/dependent projects retain their own
copyright and licences. Source snapshots, binaries and third-party paper PDFs are not
included in this publication.
