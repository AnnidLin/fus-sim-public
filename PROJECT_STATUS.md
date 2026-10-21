# 项目状态 / Project status

**2026-10-16：按维护者决定，本项目以公开研究快照保留。2026-10-21：恢复 best-effort 维护。**

This repository is a public research snapshot. Issues and pull requests are reviewed on a
best-effort basis; the code baseline stays at the 2026-10-16 snapshot unless a change is
explicitly accepted. Historical plans, TODOs and manuscript drafts describe work at their
original dates; they do not authorize new simulations or imply that the remaining work was completed.

## What was achieved

- Python/k-Wave acoustic modelling, source-array and time-reversal workflows.
- CT acoustic-property mapping infrastructure and synthetic BBB planning utilities.
- Public ITRUSST benchmark adapters, numerical-sensitivity tools and evidence audits.
- A single-case matched intermediate-domain localization observation: target-point/global
  pressure ratio 0.477400 to 0.984864 and global-peak distance 57.379 to 2.487 mm.
- Manuscript drafts, literature notes, tests and compact result summaries.

## Known limitations retained at closure

- H115 external comparison remains **nonpassing**. No successful experimental validation is claimed.
- Complete CT grid/domain convergence, independent solver verification and population generalization are absent.
- A historical endpoint-definition discrepancy remains documented: the July analysis freeze
  describes target-window/global but quotes target-point/global. Their respective ratios
  are 0.723139 to 1.000000 and 0.477400 to 0.984864. Neither was silently substituted.
- BBB and thermal modules are research prototypes, not validated dosing or safety tools.
- `submission_ready=false` remains the manuscript status. Public code release is a separate
  maintainer decision, authorized on 2026-10-16; it does not clear the scientific gates.
- Earlier statements that a root project licence is missing are historical: this public
  snapshot has an MIT licence approved by the maintainer. There is no new archive DOI.

## What this snapshot reproduces

The public smoke example and documented synthetic unit tests run without medical images,
measurements, k-Wave executables or full pressure propagation. Full historical experiment
reproduction requires separately obtained data, private execution artifacts, the recorded
environment and explicit resource/parameter gates. This is not a self-contained copy of
the entire private experiment archive.

See [data availability](DATA_AVAILABILITY.md), [release notes](RELEASE_NOTES_20261016.md)
and the [September review](PLATFORM_STATUS_AND_NEXT_PLAN_20260920.md).
