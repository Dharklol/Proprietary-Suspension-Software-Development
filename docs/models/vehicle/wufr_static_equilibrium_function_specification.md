# WUFR static-equilibrium composition function specification

## 1. Purpose

`MOD-VEH-0007` is the first source-preserving WUFR composition that connects the already implemented conservative suspension, gravity, road-compatibility, and provider-neutral equilibrium modules into one bounded static-gravity result.

The authorized state is:

- configuration `WUFR27_SUSPENSION_BASELINE_V0`;
- gravity state `WUFR26_DRIVER_NO_FUEL_DESIGN_INTENT_REFERENCE`;
- driver present and no fuel;
- centered rack;
- flat rigid road;
- ideal rigid circular centerline tires under `ASM-VEH-0005`;
- all four contacts active;
- no tire constitutive forces, aero, brake, drive, damping, inertia, or chassis compliance;
- explicit front and rear ARB settings selected from the existing discrete set `1..5`.

The result label is always:

```text
uncorrelated_design_intent_static_gravity
```

The model is not an installed/as-built corner-weight predictor and is not independent validation against the historical scale state because that design reference participates in the gravity source chain.

## 2. Existing owners

`MOD-VEH-0007` introduces no new force law and no replacement numerical solver.

| Quantity or operation | Owning model |
|---|---|
| Body/road frames, point transport, generalized-force mapping, wrench assembly | `MOD-VEH-0003` |
| Reduced body solve and active-contact recovery | `MOD-VEH-0004` |
| Sprung and prototype unsprung gravity allocation | `MOD-VEH-0005` |
| Road-compatible wheel coordinates, `J_wb`, contact points, `c_i`, unsprung-gravity projection | `MOD-VEH-0006` |
| Four conservative spring states | `MOD-SUSP-0004` |
| Front and rear conservative physical-wheel Z-bar states | `MOD-SUSP-0005` |

The adapter may validate and assemble those outputs. It may not rederive, fit, replace, or silently repair them.

## 3. Coordinates and ordering

### 3.1 Body coordinates

```text
q_b = [z_s_m, phi_rad, theta_rad]
```

with units:

```text
[m, rad, rad]
```

The body/road frame and origin identities are inherited exactly from `MOD-VEH-0003` and `MOD-VEH-0006`.

### 3.2 Wheel coordinates

```text
z_w = [z_FL, z_FR, z_RL, z_RR]
```

in the exact order:

```text
[front_left, front_right, rear_left, rear_right]
```

Each coordinate is `MOD-SUSP-0002 delta_z_wc_body_m`, positive upward and measured in metres.

No adapter-owned permutation, left/right sign reflection, absolute value, body-roll-times-track mapping, or scalar motion-ratio conversion is permitted.

## 4. Runtime configuration

The public constructor or solve function requires both:

```text
front_arb_setting: int
rear_arb_setting: int
```

Each must be an integer in `1..5`. Boolean values are rejected despite Python integer compatibility. There is no default, interpolation, averaging, or target-based setting selection.

The benchmark pair `front=1`, `rear=1` is a deterministic verification fixture only. It is not current setup authority and must be labelled as such in the frozen result.

The initial body state is an explicit numerical input. The first benchmark uses:

```text
q_b0 = [0, 0, 0]
```

only as a deterministic seed, not as a measured ride-height or attitude condition.

## 5. Provider adapters

### 5.1 Road compatibility adapter

For each body state `q_b`, construct the exact `BodyPose` accepted by `MOD-VEH-0006` and call:

```text
evaluate_wufr_road_contact(provider, pose, gravity)
```

A successful result must provide:

- four road-compatible wheel coordinates;
- a converged `4 x 3` `J_wb`;
- four exact current contact points;
- four exact current wheel-center points;
- four signed contact coefficients;
- four unsprung-gravity generalized wheel forces;
- source/configuration/assumption identities.

The adapter returns the existing `MOD-VEH-0004 CompatibilityState` contract without changing order, units, signs, or values.

Any road root, steering, contact geometry, derivative, coefficient, gravity projection, source, or domain failure propagates as a structured failure.

### 5.2 Suspension force adapter

For the requested `z_w`, solve one front and one rear `MOD-SUSP-0005` physical-wheel Z-bar state at the explicit settings.

The resulting axle states already contain the exact successful left/right actuation states used by the physical-wheel-to-rocker coordinate chain. Those same actuation states are passed to `MOD-SUSP-0004` for spring evaluation. This avoids creating a second independent actuation interpretation in the vehicle adapter.

For each corner, require a successful `SpringStateResult` with:

- one generalized force in the matching physical wheel coordinate;
- finite stored energy;
- matching configuration identity;
- matching requested/returned wheel coordinate;
- retained `ASM-SUSP-0002` provenance.

For each axle, require a successful `ZBarWheelStateResult` with:

- two generalized wheel forces in left/right order;
- finite stored energy from its `ZBarForceResult`;
- matching axle/configuration identity;
- retained explicit setting and `ASM-SUSP-0003` provenance.

Compose `EQ-VEH-0015`:

```text
Q_spring = [Q_s,FL, Q_s,FR, Q_s,RL, Q_s,RR]
Q_ARB    = [Q_a,FL, Q_a,FR, Q_a,RL, Q_a,RR]
Q_susp   = Q_spring + Q_ARB

U_spring = sum(U_s,i)
U_ARB    = U_ARB,front + U_ARB,rear
U_susp   = U_spring + U_ARB
```

Return a `MOD-VEH-0004 SuspensionGeneralizedForceState` with exact wheel-coordinate order/units and source identity.

### 5.3 Sprung-gravity adapter

At the same body pose, call the existing:

```text
gravity.sprung_body_generalized_gravity(pose)
```

and return the exact `MOD-VEH-0004 BodyExternalGeneralizedForceState` contract:

- generalized force in `[z_s,phi,theta]` order;
- gravitational potential energy where available;
- exact gravity/source/configuration identity.

The adapter does not alter the reviewed total mass, derived sprung mass/CG, or `ASM-VEH-0003` prototype unsprung allocation.

## 6. Reduced equilibrium

`EQ-VEH-0016` is evaluated only through `MOD-VEH-0004`:

```text
R_b(q_b) = Q_sprung_gravity(q_b)
         + J_wb(q_b)^T Q_susp(z_w(q_b))
```

Solve:

```text
R_b = 0
```

using the existing deterministic damped-Newton method, scaling, bounds, finite-difference tangent, pivot-ratio gate, line search, convergence criteria, and structured failures.

`MOD-VEH-0007` may provide a reviewed configuration of those existing controls. It may not add an alternate solver, least-squares fallback, fitted restart, or hidden state clipping.

At least two bounded declared initial states are evaluated in `BENCH-VEH-0012`. They must converge to the same continuation solution within the benchmark tolerance. A distinct solution is reported as an alternate root for review rather than silently ranked or discarded.

## 7. Contact recovery

After a successful body solve, reevaluate all providers at the converged state and use only the existing `MOD-VEH-0004` contact recovery:

```text
lambda_i = -(Q_susp,i + Q_unsprung_gravity,i) / c_i
```

with wheel residual:

```text
r_i = Q_susp,i + Q_unsprung_gravity,i + c_i lambda_i
```

The road reaction is positive along the `MOD-VEH-0006` road normal.

Any negative `lambda_i` is retained and returned as an all-four-active contact-mode failure. It is never clipped, redistributed, or replaced by a diagonal/crossweight rule.

## 8. Independent verification

### 8.1 Energy-gradient check

Where all component energies are available, independently evaluate:

```text
Pi(q_b) = U_susp(z_w(q_b)) + V_sprung_gravity(q_b)
```

and verify at two declared perturbation sizes:

```text
R_b = -dPi/dq_b
```

using the existing `MOD-VEH-0004` energy-gradient check or a source-equivalent wrapper that does not change its semantics.

### 8.2 Road-frame physical wrench closure

This check is independent of generalized-coordinate equilibrium assembly.

At the converged state, construct physical road-frame point loads:

- four road-normal reactions at the exact current `MOD-VEH-0006` contact points;
- sprung gravity at the transported `MOD-VEH-0005` sprung-CG point;
- four unsprung gravity loads at the exact current physical wheel-center points.

Sum all forces and moments about the named body-origin reference through `MOD-VEH-0003` wrench assembly:

```text
F_res = sum(F_road,i) + F_sprung,g + sum(F_unsprung,g,i)

M_res,O = sum((r_contact,i-r_O) cross F_road,i)
        + (r_sprung-r_O) cross F_sprung,g
        + sum((r_wc,i-r_O) cross F_unsprung,g,i)
```

Required acceptance tolerances are:

```text
||F_res||_inf <= 1e-6 N
||M_res,O||_inf <= 1e-6 N*m
```

A failure is reported. No balancing wrench may be introduced.

## 9. Result contract

A successful result must retain at least:

- status and structured failure code/message;
- result label and explicit uncorrelated/installed/production booleans;
- configuration and static-state identities;
- explicit front/rear ARB settings and their role labels;
- converged body and wheel coordinates;
- all four spring states;
- front/rear Z-bar states;
- `Q_spring`, `Q_ARB`, `Q_susp`;
- spring, ARB, and total suspension energies;
- sprung generalized gravity;
- four unsprung generalized gravity values;
- `J_wb`, contact coefficients, exact contact points, exact wheel-center points;
- four signed road-normal reactions;
- body and wheel equilibrium residuals;
- solver, tangent, conditioning, line-search, and derivative diagnostics;
- energy-gradient diagnostics;
- road-frame force/moment closure residuals;
- all authorization, assumption, source, fixture, and configuration IDs;
- explicit excluded-force and prohibited-use lists.

The first machine-readable result is planned as:

```text
benchmarks/vehicle/wufr_static_equilibrium_result_v0.1.0.toml
```

## 10. Failure behavior

The implementation fails closed for:

- absent, boolean, noninteger, or out-of-range ARB settings;
- any attempt to request a default or interpolation;
- source/configuration/assumption/order/unit mismatch;
- road-contact or derivative failure;
- spring seating/domain/actuation failure;
- Z-bar mechanism/Jacobian/constitutive failure;
- nonfinite provider data;
- body bound, singular/ill-conditioned tangent, line-search, or nonconvergence failure;
- missing contact coefficient or wheel external force;
- negative road reaction;
- energy-gradient disagreement;
- physical wrench closure disagreement.

No fallback may use historical corner loads, crossweight, diagonal rules, scalar motion ratios, scalar wheel rates, alternate contact modes, fitted parameters, or hidden clipping.

## 11. Explicit exclusions and next gate

`AUTH-VEH-0009` does not authorize:

- historical scale reconstruction or correlation;
- setup selection or recommended ARB settings;
- installed/as-built static prediction;
- damper gas, seal friction, velocity force, or stops;
- tire compliance or tire force;
- aero, brake, drive, or inertia;
- maneuver QSS, load transfer, LLTD, or roll gradient;
- carrier/upright wrench generation;
- suspension linkage or complete rocker hardware reactions;
- structural load-case packets, stress, fatigue, factor of safety, or FEA release.

After implementation and review of the first uncorrelated static result, the next authorization may convert the exact road reactions and contact points, together with the source-owned unsprung gravity loads, into a complete per-corner carrier external wrench for `MOD-SUSP-0007`.