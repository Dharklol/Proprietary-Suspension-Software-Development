# Phase 2 whole-vehicle force-coordinate authorization review

**Authorization:** `AUTH-VEH-0003`  
**Model:** `MOD-VEH-0003`  
**Equations:** `EQ-VEH-0004` through `EQ-VEH-0007`  
**Benchmarks:** `BENCH-VEH-0003`, `BENCH-VEH-0004`

## Decision

**Accepted for review as the next bounded vehicle-dynamics authorization packet.**

The packet authorizes only common whole-vehicle coordinate transport, wrench assembly, virtual-work generalized-force mapping, and first rigid-contact classification. It does not authorize a force law or equilibrium solver.

## 1. Program decision

The recommended QSS architecture uses one top-level residual assembly supplied by independent physics providers. Before spring, ARB, tire, or equilibrium equations can be added, the project needs a shared and auditable mechanics boundary for:

- point placement;
- force application points;
- moment reference points;
- generalized coordinates and conjugate force signs;
- contact-gap and normal-reaction status;
- source/frame/origin authority.

`MOD-VEH-0003` provides that boundary without collapsing later subsystem models into one procedural load-transfer loop.

## 2. Reviewed user decisions

The authorization incorporates the following reviewer/user decisions:

1. WUFR-27 retains the WUFR-26 suspension geometry.
2. The initial contact model is a flat rigid road with vertically rigid tires and all four wheels in contact.
3. Negative normal reaction is wheel lift/contact-mode invalidity, not a value to clip.
4. The first later linkage-force fidelity will use ideal two-force members as a global load-path approximation, with stress/FEA retained as a separate layer.

The decisions are recorded in `ASM-VEH-0001`, `ASM-VEH-0002`, and `ASM-SUSP-0001`.

## 3. Equation review

### `EQ-VEH-0004`

Uses an explicit yaw-pitch-roll body transform:

```text
r_I = r_O + R_z(psi) R_y(theta) R_x(phi) r_B
```

The first later quasi-static coordinate order is `q=[z_s,phi,theta]`, but this authorization does not solve those coordinates.

### `EQ-VEH-0005`

Preserves the application point of each force:

```text
M_O = M_P + (r_P-r_O) cross F
```

This prevents wheel-center, contact-patch, CG, brake, aero, and suspension forces from being moved silently without their corresponding moment arm.

### `EQ-VEH-0006`

Maps applied actions through virtual work:

```text
delta_W = F dot delta_r + M dot delta_omega = Q^T delta_q
Q = J_r^T F + J_omega^T M
```

This is the intended foundation for later spring and ARB force providers. A scalar motion ratio may remain a diagnostic output, but it cannot replace the complete signed Jacobian when the model has multiple coordinates or coupled left/right elements.

### `EQ-VEH-0007`

Defines the initial rigid-contact contract:

```text
g_i = n_road dot (r_contact_i-r_road)
lambda_i = n_road dot F_contact_i
```

The first supported mode requires all four `g_i=0` and all four `lambda_i>=0`.

## 4. Source review

The source packet is adequate for the general mechanics layer:

- Guiggiani supplies the project-compatible vehicle axes, yaw-pitch-roll pose structure, roll/pitch equilibrium context, and separation of kinematic/equilibrium/constitutive equations.
- Pacejka supplies the virtual-work definition of generalized forces. Only the general mechanics relationship is adopted; motorcycle-specific coordinates and parameters are excluded.
- Gillespie supplies an independent vehicle free-body and quasi-static consistency reference.

No legacy spreadsheet equation is promoted by this authorization.

## 5. WUFR boundary review

The statement that WUFR-27 retains WUFR-26 suspension geometry is sufficient to continue consuming the reviewed suspension-local models. It is not sufficient to assemble a common whole-vehicle body/CG frame.

Implementation remains blocked from WUFR-specific whole-vehicle placement until the following are explicit:

- body/CG origin;
- front and rear axle stations relative to that origin;
- contact-reference/road datum;
- mass and static-load authority where required downstream.

Wheelbase alone remains insufficient to infer the source-origin relationship.

## 6. Contact review

The rigid four-contact model is intentionally limited but appropriate for the first quasi-static foundation. Its most important behavior is the rejection of negative normal reaction without clipping or hidden mode switching.

Tire radial compliance and alternate contact modes are not prerequisites for the coordinate/wrench layer and remain future authorizations.

## 7. Linkage-force review

The approved ideal two-force-member fidelity is recorded for downstream planning only. It is not implemented here.

The later linkage solver must assemble simultaneous rigid-body equilibrium because the WUFR front pushrod acts on the upper arm and the rear pushrod acts on the lower arm. Treating those forces as direct upright forces would bypass the reviewed load path.

Ideal member forces will be useful for:

- global tension/compression load paths;
- joint and chassis reaction estimates;
- deterministic FEA load export.

They will not be final stress, weld, fatigue, bearing-distribution, or durability authority.

## 8. Benchmark gates

`BENCH-VEH-0003` will verify:

- exact rigid point transport;
- wrench translation and summation;
- reference-point consistency;
- analytical/virtual-work/numerical generalized-force agreement;
- structured frame/origin/Jacobian failures.

`BENCH-VEH-0004` will verify:

- contact-gap sign;
- valid four-contact classification;
- explicit negative-reaction wheel lift;
- unsupported contact fidelity;
- WUFR-27 geometry inheritance;
- refusal to infer missing whole-vehicle placement;
- absence of linkage-force output.

## 9. Remaining restrictions

Separate authorization remains mandatory for:

- spring force, preload, and stored energy;
- damper or gas force;
- ARB kinematics, torsion, adjustment, and preload;
- tire force or tire radial compliance;
- wheel-load/load-transfer generation;
- heave/roll/pitch equilibrium;
- linkage, bearing, rocker, or chassis reactions;
- stress, FEA, fatigue, buckling, and durability;
- physical travel, stops, packaging, and articulation;
- installed/as-built correlation;
- optimization and production release.

## 10. Next gate

After this authorization merges, PR #46 may implement only the mechanics primitives and synthetic benchmarks. WUFR-specific whole-vehicle assembly should remain explicitly unavailable until the required placement data are supplied and reviewed.