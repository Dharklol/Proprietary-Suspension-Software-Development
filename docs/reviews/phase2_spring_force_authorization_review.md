# Phase 2 conservative spring-force authorization review

## Review status

**Review-ready authorization packet for PR #47.**

No spring-force implementation is added by this PR. `AUTH-SUSP-0004` becomes effective only after reviewer approval and merge.

## Proposed scope

PR #47 proposes:

- `MOD-SUSP-0004`: one conservative coil-spring force/energy/generalized-force provider;
- `EQ-SUSP-0013`: explicit spring compression and preload/reference coordinate;
- `EQ-SUSP-0014`: conservative force, stored energy, and tangent stiffness, including an explicitly reviewed affine tangent-rate progressive law;
- `EQ-SUSP-0015`: signed generalized spring force through potential energy/virtual work;
- `ASM-SUSP-0002`: WUFR-27 zero-preload/full-extension reference and rear progressive-rate modeling assumption;
- `BENCH-SUSP-0009`: analytical synthetic spring benchmark;
- `BENCH-SUSP-0010`: WUFR-27 spring package/reference/progressive-law benchmark;
- `WUFR27_SPRING_PACKAGE_V0`: frozen source and assumption boundary for the reviewed current spring/damper package.

## Architecture decision

The spring is a conservative force provider, not a wheel-rate calculator.

The governing path is:

```text
suspension/actuation state
        -> explicit spring compression x_s
        -> F_s(x_s), U_s(x_s), k_t
        -> Q_s = -partial U_s/partial q
```

For an explicitly frozen direct-coilover reference mapping,

```text
x_s = x_pre + L_ref - L_d
Q_s = F_s partial L_d/partial q
```

and for the reviewed physical wheel coordinate:

```text
Q_delta_z = F_s rho_dw.
```

This preserves the sign of `MOD-SUSP-0003`'s `rho_dw`. It does not adopt historical OptimumK `Motion Ratio Heave`, an absolute motion ratio, or `k*MR^2` as governing force physics.

## WUFR source and reviewer update

The reviewer-declared WUFR-27 setup is:

```text
KW V5 Racing Formula Student piggyback damper
front: 36 N/mm linear spring
rear: 30 -> 36 N/mm linear-progressive spring
free length: 100 mm
intentional preload: zero
no tender/helper spring
```

On 2026-07-26 the reviewer further clarified:

- KW does not publish the rear rate progression and the team has not yet tested it;
- for the current engineering model, assume the transition between the 30 and 36 N/mm endpoint rates is linear;
- the inboard suspension-geometry line from chassis to rocker is the line used to place the piggyback damper in CAD;
- ARB blade geometry adjacent to that line is a separate coupled element;
- a ride-height shock-pot reading was reported as `44m`, but no calibration semantics were supplied.

Those statements are handled explicitly rather than silently inferred.

## Vendor and geometry evidence

The attached KW technical document gives:

```text
piggyback full-extension eye-to-eye = 185.7 mm
damper travel = 57 mm
```

It does not provide measured rear spring force-deflection data.

The reviewer-run suspension-geometry export gives the design-intent damper placement line:

```text
front nominal eye-to-eye = 164.599347 mm
rear nominal eye-to-eye  = 164.610539 mm
```

Those independently agree with the reviewed `MOD-SUSP-0003` actuation fixture values of `164.600 mm` front and `164.611 mm` rear.

## Zero-preload/reference decision

`ASM-SUSP-0002` freezes the first prototype interpretation of zero intentional preload:

```text
x_s = 0 at KW piggyback full extension, L_d = 185.7 mm
x_s = 185.7 mm - L_d
```

for the current fixed-seat-offset direct-coilover design-intent configuration.

The nominal model spring compressions are therefore:

```text
front x_s0 = 21.100653 mm
rear  x_s0 = 21.089461 mm
```

This is an explicit team modeling assumption, not installed perch/seat metrology. It must be replaced or validated when perch measurements or calibrated shock-pot data are available.

The raw shock-pot value is not used until its unit, zero, span, sign, and mapping to damper eye-to-eye length are frozen.

## Front spring decision

The front law is exact within this model:

```text
k_f = 36000 N/m
F_f = k_f x_s
U_f = 0.5 k_f x_s^2
```

At the nominal design-intent compression:

```text
F_f0 ~= 759.624 N
```

This is a spring-provider benchmark value, not a solved corner load.

## Rear progressive spring decision

The rear spring remains untested, so PR #47 does not present a fabricated vendor curve. Instead, `ASM-SUSP-0002` makes the team's current assumption explicit:

```text
k_0 = 30000 N/m at x_s = 0
k_1 = 36000 N/m at x_s = 0.057 m
k_t(x_s) = k_0 + ((k_1-k_0)/0.057) x_s
```

Because `k_t=dF_s/dx_s`, the correct conservative force and energy are

```text
F_s = k_0 x_s + 0.5*((k_1-k_0)/0.057)*x_s^2
U_s = 0.5*k_0*x_s^2 + ((k_1-k_0)/(6*0.057))*x_s^3
```

for `0 <= x_s <= 0.057 m`.

The implementation must not use `F_s=k_t*x_s`; tangent rate is not secant stiffness.

At nominal rear compression:

```text
k_t0 ~= 32.2199 N/mm
F_r0  ~= 656.093 N
```

The 57 mm span is an explicit team modeling assumption tied to the direct-coilover usable damper compression range. It is **not** a KW-published spring-rate test range and is **not** installed wheel-travel authority.

## Seated-spring mode

The first model supports a seated compression coil spring only. A state that produces `x_s<0` is reported as `spring_unseated`; compression/force is not silently clipped to zero.

For the assumed rear law, `x_s>57 mm` returns `constitutive_domain_exceeded`; the model does not extrapolate the 30-to-36 N/mm progression.

Because the reviewed WUFR setup has no tender/helper spring, no secondary spring contact law is introduced.

## Benchmark review

`BENCH-SUSP-0009` freezes analytical checks for:

- linear force/energy/tangent stiffness;
- explicit preload/reference arithmetic;
- signed generalized force and finite-difference potential-energy consistency;
- unseated failure;
- a synthetic bounded progressive table with exact hand values and no extrapolation.

`BENCH-SUSP-0010` now freezes:

- the front 36 N/mm law;
- the 185.7 mm zero-preload/full-extension reference;
- the nominal CAD/actuation damper lengths and resulting spring compression;
- the rear affine tangent-rate assumption from 30 to 36 N/mm over 57 mm;
- integrated force/energy rather than `k_t*x_s`;
- explicit `ASM-SUSP-0002` provenance;
- non-use of the raw shock-pot value until calibration.

## Prohibited scope

PR #47 does not authorize:

- spring-force implementation before merge;
- presenting `ASM-SUSP-0002` as KW measured spring data;
- damper dyno/velocity force or damping ratios;
- gas force, friction, hysteresis, stops, or thermal behavior;
- ARB kinematics/stiffness/preload;
- governing wheel-rate/MR shortcuts;
- vehicle equilibrium/load transfer/wheel-load generation;
- linkage forces or stress/FEA;
- installed/as-built travel, stroke, clearance, or production claims.

## Review decision requested

Approve `AUTH-SUSP-0004` as the bounded conservative spring-force authorization with `ASM-SUSP-0002` explicitly carrying the current team assumptions for:

1. zero-preload/full-extension spring reference;
2. rear 30-to-36 N/mm linear tangent-rate progression over 57 mm compression.

Both assumptions have explicit replacement gates: rear spring testing for the constitutive law, and perch/seat metrology or calibrated shock-pot data for the installation reference.
