# Whole-vehicle force-coordinate source audit

## Purpose

This audit bounds the evidence used by `AUTH-VEH-0003` and `MOD-VEH-0003`. The authorized slice creates a common coordinate/wrench/generalized-force/contact foundation. It does **not** create spring, ARB, tire, load-transfer, equilibrium, or linkage-force physics.

## 1. Project state entering this authorization

The repository already contains three reviewed suspension providers:

- `MOD-SUSP-0001`: rigid ideal-joint double-wishbone position kinematics;
- `MOD-SUSP-0002`: source-bounded wheel-center/wheel-plane reference and body-frame vertical-state inversion;
- `MOD-SUSP-0003`: rigid push/pull-rod, rocker, coilover-displacement, and signed local actuation derivative.

Those providers preserve front/rear source-local suspension origins and explicitly refuse to infer a whole-vehicle rear translation from wheelbase alone. `WUFR27_SUSPENSION_BASELINE_V0` is an active design-intent R&D configuration, not installed/as-built authority.

The project also contains:

- `MOD-VEH-0001`, an explicit operating-state exchange provider that does not generate wheel loads or vehicle response;
- `MOD-VEH-0002`, a planar wheel-velocity/slip-kinematics provider that consumes externally supplied `u`, `v`, and `r` and does not solve equilibrium.

Therefore the next valid dependency is a common whole-vehicle geometry and force-coordinate layer, not a hidden load-transfer calculation inside any existing provider.

## 2. User-reviewed design decisions

The following decisions were explicitly confirmed for this program on 2026-07-25:

1. WUFR-27 will not use suspension geometry different from WUFR-26.
2. The first contact model is a flat rigid road with vertically rigid tires and all four contacts active.
3. A negative road-normal reaction is wheel lift/contact-mode invalidity and must not be clipped.
4. The first later linkage-force model will use ideal pin-jointed two-force members as a global load-path approximation, followed by separate structural/FEA work rather than treating ideal member forces as final stresses.

These decisions are frozen as `ASM-VEH-0001`, `ASM-VEH-0002`, and `ASM-SUSP-0001`.

## 3. Literature basis

### Guiggiani

`The Science of Vehicle Dynamics` supplies the primary road-vehicle coordinate and equilibrium framework:

- Chapter 1 defines the vehicle axes as `+x` forward, `+y` left, and `+z` upward and distinguishes wheelbase, tracks, CG location, suspension geometry, and static/reference conditions.
- Chapter 9 develops vehicle position and orientation using yaw-pitch-roll elemental rotations and writes equilibrium equations with roll and pitch motion.
- Section 9.7 separates equilibrium, load transfer, tire constitutive equations, and kinematic congruence.
- Section 10.1 explicitly organizes a vehicle model into kinematic, equilibrium, and constitutive equations and distinguishes suspension forces from road-contact reactions.

The authorization uses those concepts to keep coordinate transport, wrench assembly, force laws, and equilibrium as separate software responsibilities.

### Pacejka

`Tyre and Vehicle Dynamics`, Section 11.3, defines generalized forces from virtual work. Equations 11.62 and 11.82-11.84 express virtual work as the sum of generalized forces multiplied by their associated virtual coordinates and obtain generalized forces by substituting the application-point virtual displacements.

The present authorization adopts only this general mechanics structure:

```text
delta_W = F dot delta_r + M dot delta_omega = Q^T delta_q
Q = J_r^T F + J_omega^T M
```

The motorcycle-specific coordinates, parameters, and equations in that section are not imported.

### Gillespie

`Fundamentals of Vehicle Dynamics` is retained as an independent consistency source for vehicle free-body equilibrium and quasi-static load-transfer moment balances. It does not authorize importing a legacy spreadsheet load-transfer block, fixed coefficient, or hidden elastic-load-distribution rule.

## 4. WUFR geometry authority

The reviewed project statement is:

> WUFR-27 uses the same suspension geometry as WUFR-26.

This supports continued use of the existing suspension geometry snapshot and `WUFR27_SUSPENSION_BASELINE_V0` for suspension-local kinematics. It does **not** provide all data needed for a common whole-vehicle force model.

Still missing or not yet frozen for implementation:

- one body/CG origin shared by front and rear suspension geometry;
- front and rear axle stations relative to that origin;
- CG position and mass-property authority;
- static corner weights and sprung/unsprung allocation;
- installed ride-height/contact-reference authority;
- road-plane datum relative to the body configuration;
- force-application points for aero, brakes, powertrain, and component masses.

Wheelbase `1.5624 m` is reviewed vehicle context but remains insufficient to derive the missing front/rear source-origin transform.

## 5. Contact-model boundary

The first contact model intentionally uses:

- one flat rigid road plane;
- one declared unit road normal;
- one contact-reference point per corner;
- vertically rigid tires;
- all four contacts active;
- zero gap at each active contact;
- nonnegative road-normal reaction at each active contact.

A negative normal reaction is not a small numerical defect. It means the assumed all-four-active contact mode is not admissible. The model must return an explicit `wheel_lift` or `contact_mode_invalid` status. It may not clip the load, redistribute it, or change contact mode internally.

Tire radial compliance, uneven roads, curbs, aerodynamic platform control, and contact-mode switching require later authorizations.

## 6. Linkage-force boundary

The user-approved first linkage fidelity is preserved for later work:

- tie rods, push/pull rods, ARB links, and individual wishbone legs may be idealized as two-force members along declared centerlines;
- upright, rocker, and ideal node bodies may be treated as rigid;
- external wheel/contact, spring/ARB, brake-reaction, inertia, and aero loads must enter at explicit application points;
- equilibrium rank, conditioning, and residuals must be reported.

That model can produce useful global axial load paths and deterministic FEA boundary-condition inputs. It cannot by itself establish tube bending, weld stress, bracket flexibility, bearing load distribution, fatigue, buckling, compliance, or installed durability.

No linkage-force equation is authorized in PR #45.

## 7. Source conflicts and unresolved items

No source conflict blocks the coordinate/wrench authorization. The main unresolved issue is missing WUFR whole-vehicle placement and mass/contact authority. The implementation must preserve unavailable fields and synthetic-only benchmarks until those data are supplied and reviewed.

## 8. Audit decision

The evidence is sufficient to authorize:

- body-fixed point transport;
- force/couple wrench translation and summation;
- virtual-work generalized-force mapping;
- flat-road rigid-contact gap/reaction classification;
- strict frame, origin, application-point, and provenance diagnostics.

The evidence is not sufficient to authorize force laws, wheel loads, QSS equilibrium, alternate contact modes, linkage forces, stress, or production decisions.