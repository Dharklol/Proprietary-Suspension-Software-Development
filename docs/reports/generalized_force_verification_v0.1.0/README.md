# Generalized force and dissipative integration checkpoint

Run `PYTHONPATH=src python scripts/run_generalized_force_verification.py`.
Specification: `docs/models/suspension/generalized_force_ports_spec_v0.1.0.md`.

All twelve integrated checks and five force-port unit tests pass. The source mass
ledger contains exactly eight tubes (0.81555908126 kg); the reduced heave mass
matches that ledger. No body/corner/wheel lump is added. Existing coupled inertia
and its convective/gyroscopic terms are retained unchanged.

| Moving support | Steps | Maximum energy-balance residual (J) |
|---|---:|---:|
| No | 8 | 3.49e-17 |
| No | 16 | 3.31e-18 |
| No | 32 | 4.42e-18 |
| Yes | 8 | 4.93e-15 |
| Yes | 16 | 3.10e-16 |
| Yes | 32 | 2.14e-17 |

At 32 steps the moving support supplies about 1.33910e-7 J and dampers dissipate
1.00126e-8 J. Omitting either term is detectable against the residual. Stationary
support gives zero external work and decreasing total energy. Contact loss and
the declared numerical arm-travel boundary both stop explicitly; no force clipping
or continuation through separation is used. No convergence order is claimed at
the stationary case's numerical floor.

## Meaning and next step

This joins changing native tube inertia to a verified generalized spring/damper/
moving-support primitive. All rates, deformation geometry and support points are
analytical fixtures. A tube-CG support is not wheel/ground geometry; none of these
numbers is an installed ride prediction or KW calibration.

The next high-value step is native spring deformation/gradient and preload binding,
with independent virtual-work checks, then compatible wheel/tire/body mass and
contact contracts. Existing no-driver inertia and driver/no-fuel static states
must remain separate until explicitly reconciled. Housing signs and other member
ownership remain open source tasks. G3/G5a analytical integration remains the focus;
UI/operational release and physical correlation remain downstream. No new owner
input is required to develop the spring mapping and analytical verification cases.
