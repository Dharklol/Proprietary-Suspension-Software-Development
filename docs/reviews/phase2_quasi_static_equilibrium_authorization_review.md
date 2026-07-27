# Phase 2 quasi-static equilibrium authorization review

## Decision requested

Review `AUTH-VEH-0004` as the next bounded vehicle-mechanics slice after the conservative spring and coupled WUFR Z-bar providers have reached physical wheel-coordinate generalized forces.

The requested authorization is deliberately split into two levels:

1. **authorize a generic provider-neutral reduced-coordinate quasi-static kernel** with explicit mass/external-force inputs and synthetic verification;
2. **do not authorize a WUFR road-reaction adapter yet**, because the reviewed current unsprung evidence is only `10 kg front axle + 10 kg rear axle` and does not define a per-corner gravity allocation/application convention.

## Why a generic implementation is now supportable

The earlier equilibrium blockers were not only numerical. The repository did not yet have source-grounded conservative suspension forces in compatible coordinates. That has changed.

- `MOD-VEH-0003` supplies explicit body/contact coordinates, wrench assembly, virtual-work generalized-force mapping, and the flat-rigid-road contact contract.
- `MOD-SUSP-0004` supplies conservative spring force/energy/generalized-force outputs.
- `MOD-SUSP-0005` now supplies the WUFR two-arm Z-bar force through physical left/right `delta_z_wc_body_m` coordinates after the full geometry/rocker/wheel Jacobian chain.

This allows the equilibrium solver itself to remain a small mechanics/numerics kernel rather than reimplementing suspension physics or importing legacy load-transfer equations.

## Proposed reduced-coordinate architecture

The active road/contact compatibility is supplied explicitly as:

```text
z_w = z_w(q_b)
J_wb = partial(z_w)/partial(q_b)
```

with body coordinates expected initially to use the existing project convention:

```text
q_b = [z_s, phi, theta]
```

Conservative suspension force is supplied in the physical wheel coordinates:

```text
Q_susp_w = -partial(U_susp)/partial(z_w)
```

The reduced body residual is then:

```text
R_b = Q_body_ext + J_wb^T Q_susp_w
```

and the quasi-static state satisfies `R_b=0`.

Road reactions are recovered afterward from the per-wheel constrained-coordinate equilibrium:

```text
Q_susp_i + Q_wheel_ext_i + c_i lambda_i = 0
```

This separation matters. Unsprung gravity or another wheel-side load should affect the road reaction without being double-counted as though it also acted on the sprung-body reduced coordinate after the road constraint has fixed the wheel-side absolute position.

## Numerical proposal

The first implementation may use a small deterministic damped-Newton solve with:

- caller-declared coordinate scales and bounds;
- scaled finite-difference residual tangent;
- pivoted small-matrix linear solve;
- explicit singular/conditioning diagnostics;
- residual-reducing line search;
- no hidden clipping;
- independent two-step conservative energy-gradient verification.

This is sufficient for the first 1-3 coordinate synthetic/reference cases and avoids introducing a heavy numerical dependency before the problem size requires it.

## Analytical benchmark

`BENCH-VEH-0005` freezes a fully synthetic case:

```text
sprung mass = 100 kg
four spring rates = 10000 N/m
g = 9.81 m/s^2
four explicit synthetic wheel-side masses = 5 kg each
```

At the symmetric branch, `z_i=-z_s`. The exact solution is:

```text
z_s = -0.024525 m
z_i = +0.024525 m
Q_susp_i = -245.25 N
Q_wheel_ext_i = -49.05 N
lambda_i = +294.30 N
sum(lambda_i) = 1177.20 N
```

The synthetic wheel masses are benchmark-local numbers. They are intentionally chosen to demonstrate correct road-reaction recovery and may not be copied into a WUFR adapter.

`BENCH-VEH-0006` freezes singular tangent, bound/nonconvergence, provider-contract, negative reaction, and missing-WUFR-mass-authority failures.

## WUFR mass evidence reviewed

The accompanying source audit records:

- driver/no-fuel scale state `178/175/163/159 lb`, total `675 lb`;
- planar CG derived from that state;
- a separate `0.290 m` driver-equivalent-ballast tilt-test height used only as a source-separated design-intent reference;
- current measured unsprung mass `10 kg front axle + 10 kg rear axle`.

The audit also found current/historical calculations containing:

- `10 kg per corner unsprung`, explicitly labelled a WUFR-26 ride-frequency target assumption;
- `207 kg` sprung mass in the LLTD calculator, whose inputs are replaceable/template values and whose suspension representation is legacy scalar stiffness;
- `220 kg car + 100 kg driver = 320 kg` in Suspension Calculations 2026.

None of those calculation inputs is promoted to governing WUFR gravity-force authority.

## Why the WUFR road-reaction result remains blocked

Rigid whole-vehicle vertical force/roll/pitch equilibrium supplies only three independent equations for four road-normal reactions. The fourth relation must come from suspension/contact compatibility, which the new architecture can now provide.

However, once actual spring/ARB wheel generalized forces are known, per-wheel reaction recovery still requires the explicit wheel-side external forces. For static gravity that means an unsprung gravity allocation. The current `10 kg front + 10 kg rear` measurement does not specify left/right split or force application convention.

The generic solver should not turn that missing information into a hidden `5 kg/corner` assumption.

A later WUFR authorization can close the gap by reviewing either:

- measured per-corner unsprung mass/application locations;
- an explicitly named prototype allocation assumption for the measured axle totals; or
- an independently reviewed sprung-mass/sprung-CG force model that avoids inferring the same quantities indirectly.

## Requested disposition

Approve `AUTH-VEH-0004` for a separate implementation PR limited to the provider-neutral generic kernel and `BENCH-VEH-0005/0006`.

Do not interpret approval as authority to publish WUFR static corner loads, load transfer, LLTD, body roll/pitch/heave, or maneuver tire loads. Those remain behind the explicit WUFR mass/gravity gate and later external-force/contact authorizations.
