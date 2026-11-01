# Front native spring mapping checkpoint

Run `PYTHONPATH=src python scripts/run_native_spring_port.py`.
Specification: `docs/models/suspension/native_spring_port_spec_v0.1.0.md`.

All eleven checks pass over ten native front states. An analytic derivative
through upper-arm and rocker closure maps the reviewed spring into the same
[heave,pitch,left qL,right qL] coordinate order used by the inertia work.
Five-point energy-gradient force error is below 1e-7 Nm in this run; the declared
acceptance remains 1e-4 Nm. Direct physical eye-force virtual work agrees, including
finite chassis pitch and heave. Existing spring force and energy are reproduced.

Nominal spring compression is 21.100653 mm and force 759.623506 N under the
reviewed design-intent model. Zero intentional preload remains referenced to full
extension, not to the nominal CAD position. Source/configuration and ASM-SUSP-0002
are retained; installed-as-built authority remains false.

| Cycle quadrature steps | Work + elastic-energy change (J) |
|---:|---:|
| 100 | -9.13370e-5 |
| 200 | -2.28344e-5 |
| 400 | -5.70862e-6 |

This is prescribed-motion conservative work verification. The native spring is
not released onto the unbalanced tube-only inertia fixture. No gravity/body/wheel
mass, damping curve, ARB or wheel-contact model is introduced.

## Stopping point and next steps

The artificial arm-spring mapping now has a verified native alternative. The next
useful dependency is a compatible no-driver/no-fuel mass and static load composition,
followed by wheel-reference/tire-contact force binding. That is needed before this
spring force becomes a meaningful native transient load. Source uncertainty in
remaining component ownership/housing tensors stays explicit. Do not inherit the
older driver/no-fuel equilibrium or scale CAD mass to the unexplained scale total.

This advances G3/G5a analytical integration. UI, operational release and physical
correlation remain downstream. Existing repository sources are sufficient to
develop the next composition and wheel/contact verification cases; no new owner
input is required at this checkpoint.
