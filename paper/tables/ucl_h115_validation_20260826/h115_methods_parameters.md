# Supplementary table — UCL H115 simulation and resource parameters

| Model | Geometry | Radius / aperture (mm) | dx / PPW | PML | CFL / dt / nt | Grid / source points | Solver runtime | Device extrema |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Effective bowl, dx0.50 mm | paper-derived effective bowl | 61.39 / 50.40 | 0.50 mm / 10.98 | 16 points (8.00 mm) | 0.10 / 33.731 ns / 5337 | 201x161x161 / 7997 | 54.32 min | CPU 5.972 cores; WS 1.223 GiB; free 18.167 GiB |
| Effective bowl, dx0.30 mm | paper-derived effective bowl | 61.39 / 50.40 | 0.30 mm / 18.30 | 27 points (8.10 mm) | 0.10 / 20.239 ns / 8894 | 335x268x268 / 22505 | 384.23 min | CPU 5.980 cores; WS 5.095 GiB; free 14.283 GiB |
| Nominal bowl, dx0.50 mm | HDF5 nominal 64/64-mm union | 64.00 / 64.00 | 0.50 mm / 10.98 | 16 points (8.00 mm) | 0.10 / 33.731 ns / 5337 | 201x161x161 / 13117 | 46.59 min | CPU 5.974 cores; WS 1.220 GiB; free 17.282 GiB |

All runs used 270 kHz, 16 cycles, 180 us, homogeneous water, CPU backend and the standard engineering preset. Device extrema are independently read from package-validation records. These rows document execution and do not upgrade the nonpassing external-validation verdict or establish formal convergence.
