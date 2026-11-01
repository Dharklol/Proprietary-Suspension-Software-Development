# Equilibrium-based local spring stiffness

Reproduce with `PYTHONPATH=src python scripts/run_equilibrium_local_stiffness.py`.
The explicit 1/1 front/rear ARB settings are a study fixture, not a recommendation.

The unchanged source-bounded static solver succeeds. Independent force closure
is 5.16e-8 N and moment closure is 4.57e-8 N*m; the included-load static road
reaction reconstruction is complete within that provider's scope. No missing KW
static force or physical correlation is thereby resolved.

| Corner | Solved wheel coordinate (mm) | Local spring tangent (N/mm) |
|---|---:|---:|
| Front left | 4.7111 | 24.9899 |
| Front right | 4.6134 | 24.9941 |
| Rear left | 0.5298 | 32.5751 |
| Rear right | 0.4334 | 32.5604 |

All four centered derivative step checks and independent spring-energy tangent
checks pass. The tangents include loaded geometric stiffness and use each solved
physical wheel coordinate. They are spring-only fixed-body wheel tangents, not
a complete coupled body stiffness matrix or tire-compliant static equilibrium.
The output does not supply vehicle natural frequencies.

`results.json` retains the solver coordinates, signed residuals, recovered normal
loads, physical closure, derivative checks and source hashes. The model retains
its uncorrelated design-intent and included-load exclusions.

Pitch inertia remains unresolved after a bounded repo/Box audit. Static weights
and CG determine first moments, not pitch inertia. Historical engine inertia,
shaft section inertia and pitch-filter time constants were rejected as substitutes.
The useful next source is a configuration-matched sprung-assembly CG pitch inertia
in kg*m^2 with axes, included components and driver/fuel boundary. No testing-day
CSV/XRK decoding was needed for these calculations. Telemetry identification would
need synchronized calibrated channels and known/reconstructable excitation;
IMU motion alone is insufficient to uniquely separate inertia, damping and input.
