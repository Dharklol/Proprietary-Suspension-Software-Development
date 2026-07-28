# Phase 2 WUFR static-equilibrium authorization review

## Decision

Authorize `MOD-VEH-0007` under `AUTH-VEH-0009` as the first bounded WUFR spring-plus-Z-bar-plus-gravity static-equilibrium composition.

The authorization is intentionally an integration decision. It creates no new suspension, gravity, contact, or equilibrium physics. It permits a source-preserving adapter to compose the already reviewed providers through the already implemented provider-neutral quasi-static kernel.

The first output is an **uncorrelated design-intent static-gravity result**, not an installed/as-built corner-weight prediction.

## Reviewed upstream state

The required mechanics are already implemented and independently bounded:

- `MOD-VEH-0003`: explicit body/road frames, point transport, generalized-force mapping, and physical wrench assembly;
- `MOD-VEH-0004`: provider-neutral reduced quasi-static equilibrium and active-contact recovery;
- `MOD-VEH-0005`: driver/no-fuel sprung and prototype unsprung gravity allocation;
- `MOD-VEH-0006`: flat-road physical wheel-coordinate compatibility using `ASM-VEH-0005` ideal rigid circular centerline tires;
- `MOD-SUSP-0004`: conservative four-corner spring force and energy;
- `MOD-SUSP-0005`: conservative front/rear Z-bar force and energy in the same physical wheel-coordinate convention.

The corresponding source record is:

```text
data_catalog/wufr27_static_equilibrium_composition_v0.toml
```

It freezes ownership, ordering, signs, required settings, excluded forces, and downstream boundaries.

## Authorized state

The first composition is restricted to:

- `WUFR27_SUSPENSION_BASELINE_V0`;
- `WUFR26_DRIVER_NO_FUEL_DESIGN_INTENT_REFERENCE`;
- driver present, no fuel;
- centered rack;
- flat rigid road;
- all four contacts active;
- gravity-only quasi-static loading;
- explicit front and rear discrete ARB settings.

The body coordinates are:

```text
q_b = [z_s_m, phi_rad, theta_rad]
```

The wheel coordinates are:

```text
z_w = [front_left, front_right, rear_left, rear_right]
```

where every entry is the signed `MOD-SUSP-0002` physical wheel-center vertical displacement, positive upward.

## Composition mechanics

### Conservative suspension force

`EQ-VEH-0015` assembles:

```text
Q_susp = Q_spring + Q_ARB
```

and:

```text
U_susp = sum(U_spring,i) + U_ARB,front + U_ARB,rear
```

The four spring states must use the exact successful actuation states already returned by the front/rear `MOD-SUSP-0005` physical-wheel-coordinate solves. This prevents the vehicle adapter from creating a second actuation geometry interpretation.

No scalar motion ratio, scalar wheel rate, body-roll-times-track relation, or historical effective axle stiffness is allowed.

### Reduced body equilibrium

`EQ-VEH-0016` is:

```text
R_b = Q_sprung_gravity + J_wb^T Q_susp
```

The equation is solved only by `MOD-VEH-0004`, retaining its existing scaling, bounded damped-Newton method, tangent diagnostics, pivot-ratio gate, line search, convergence rules, and structured failures.

### Road-reaction recovery

`EQ-VEH-0017` recovers:

```text
lambda_i = -(Q_susp,i + Q_unsprung_gravity,i) / c_i
```

Any negative reaction remains visible and invalidates the all-four-active contact mode. The adapter may not clip, redistribute, or replace it with a crossweight or diagonal-load rule.

### Independent checks

The implementation must independently check:

1. total conservative potential-energy gradient against the body residual at two step sizes;
2. physical road-frame force and moment equilibrium using the exact current contact, sprung-CG, and wheel-center application points.

The physical wrench residual tolerances are frozen at:

```text
1e-6 N
1e-6 N*m
```

No hidden balancing wrench is allowed.

## Explicit ARB setting decision

The sources define five discrete blade settings but do not establish a current WUFR-27 installed setting for this composition.

Therefore:

- front setting is a required runtime input;
- rear setting is a required runtime input;
- only integer settings `1..5` are accepted;
- booleans are rejected;
- no default exists;
- no interpolation, averaging, fitting, or target-based selection is authorized.

`BENCH-VEH-0012` uses front setting 1 and rear setting 1 only as a deterministic verification fixture. The frozen result must state that the pair is not setup authority or a recommendation.

## Historical scale-state boundary

The reviewed driver/no-fuel corner-scale state contributes to the mass and CG source chain. It therefore cannot serve as independent validation of the first static-equilibrium result.

`AUTH-VEH-0009` prohibits fitting any of the following to reproduce the historical corner loads:

- spring preload or reference;
- body ride height or attitude;
- CG or mass allocation;
- unsprung corner allocation;
- rigid-circle radius;
- front or rear ARB setting;
- contact or solver offsets.

The implementation may retain historical values as source lineage, but may not report agreement or disagreement as independent physical correlation.

## Verification plan

### `BENCH-VEH-0011`

Verifies exact provider ownership and assembly:

- body and wheel coordinate order/units;
- exact `MOD-VEH-0006` `z_w` and `J_wb` transfer;
- spring and ARB force addition;
- conservative energy addition;
- exact actuation-state reuse for spring evaluation;
- explicit ARB setting validation;
- source/configuration consistency.

### `BENCH-VEH-0012`

Requires the first integrated frozen result:

- driver/no-fuel state;
- centered rack;
- flat rigid-circle road compatibility;
- explicit fixture settings 1/1;
- convergence from at least two bounded initial guesses to the same continuation state, or explicit alternate-root reporting;
- nonnegative unmodified road reactions;
- wheel residuals within `1e-8 N`;
- independent energy-gradient agreement;
- road-frame physical force and moment closure;
- complete machine-readable provenance and exclusion labels.

### `BENCH-VEH-0013`

Verifies fail-closed behavior for:

- missing or invalid settings;
- source, configuration, assumption, order, or unit mismatch;
- road/contact/Jacobian failure;
- spring or Z-bar failure;
- nonfinite provider values;
- tangent, bound, line-search, or nonconvergence failure;
- negative contact reaction;
- altered point/frame/reaction physical-closure disagreement;
- forbidden historical or scalar fallback paths.

## Scope restrictions

This authorization does not permit:

- installed/as-built corner-weight prediction;
- static setup recommendation or ARB setting selection;
- physical correlation claims;
- historical scale reconstruction;
- tire compliance or tire forces;
- damper gas, friction, velocity force, or stops;
- aero, brake, drive, or inertial forces;
- alternate contact modes;
- maneuver load transfer, LLTD, roll gradient, or handling prediction;
- carrier/upright external wrenches;
- linkage or complete rocker hardware reactions;
- structural load-case packets, stress, FEA, fatigue, or factors of safety.

## Implementation disposition

After this authorization is reviewed and merged, implementation may add:

```text
src/pssd_vehicle/wufr_static_equilibrium.py
```

plus focused tests, benchmark reporting, and the frozen result:

```text
benchmarks/vehicle/wufr_static_equilibrium_result_v0.1.0.toml
```

The implementation PR must not expand the authorized state or insert missing setup authority.

## Next gate after implementation

After the first static result is reviewed, a separate authorization may construct a complete per-corner carrier external wrench from:

- the recovered road-normal reaction at the exact current contact point;
- the corresponding source-owned unsprung gravity point load;
- explicit frame, origin, and reference-point identities.

That later adapter may feed `MOD-SUSP-0007` Level-1 suspension interface statics. Carrier wrenches and structural propagation are deliberately not authorized here.