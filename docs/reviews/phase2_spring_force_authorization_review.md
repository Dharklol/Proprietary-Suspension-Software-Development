# Phase 2 conservative spring-force authorization review

## Review status

**Review-ready authorization packet for PR #47.**

No spring-force implementation is added by this PR. `AUTH-SUSP-0004` becomes effective only after reviewer approval and merge.

## Proposed scope

PR #47 proposes:

- `MOD-SUSP-0004`: one conservative coil-spring force/energy/generalized-force provider;
- `EQ-SUSP-0013`: explicit spring compression and preload/reference coordinate;
- `EQ-SUSP-0014`: source-defined force, stored energy, and tangent stiffness;
- `EQ-SUSP-0015`: signed generalized spring force through potential energy/virtual work;
- `BENCH-SUSP-0009`: analytical synthetic spring benchmark;
- `BENCH-SUSP-0010`: WUFR-27 spring package and incomplete-progressive-law authority benchmark;
- `WUFR27_SPRING_PACKAGE_V0`: frozen source boundary for the reviewed current spring/damper package.

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

## WUFR source review

The reviewer-declared WUFR-27 setup is:

```text
KW V5 Racing Formula Student piggyback damper
front: 36 N/mm linear spring
rear: 30 -> 36 N/mm linear-progressive spring
free length: 100 mm
intentional preload: zero
no tender/helper spring
```

The attached KW technical document corroborates damper hardware, 57 mm travel, the piggyback dimensional package, 36 mm spring-ID compatibility, and spring-perch adjustment. It does not provide the WUFR rear spring progression curve.

Team Box evidence was also audited:

- the WUFR-26 shock BOM lists `KW 35-36-100 / 35-36 N/MM SPRINGS`;
- historical OptimumK stores 36 N/mm front/rear scalar spring fields;
- the historical inboard calculator uses 36 kN/m front and 30 kN/m rear with scalar MR/IR wheel-stiffness logic.

Those artifacts are retained as historical/corroborating evidence and are not allowed to override the later reviewer-declared current setup.

## Front spring decision

The front spring has enough parameter authority to define the ideal constitutive law **as a function of explicitly supplied compression**:

```text
k_f = 36000 N/m
F_f = k_f x_s
U_f = 0.5 k_f x_s^2
```

PR #47 does not claim that nominal loaded spring compression is already known from the coilover eye-to-eye state.

## Rear progressive spring decision

The rear spring cannot yet be turned into an exact force law.

The statement `30 -> 36 N/mm linear-progressive` supplies endpoint tangent-rate information but does not locate those rates on the compression axis. No reviewed source currently supplies the missing rate-versus-compression interval or force-deflection table.

Therefore the authorization requires `progressive_law_incomplete` rather than any of these shortcuts:

- 30 N/mm constant;
- 33 N/mm average;
- 36 N/mm constant;
- 30-to-36 progression spread over the 57 mm damper stroke;
- the historical OptimumK rear 36 N/mm scalar.

This is an intentional source-authority failure, not a numerical problem.

## Preload/reference decision

The reviewer explicitly states zero intentional preload. The authorization preserves that fact without overinterpreting it.

Zero intentional preload does **not** mean:

- zero spring force at nominal loaded ride height;
- nominal `MOD-SUSP-0003` coilover length is the zero-load reference;
- KW's damper dimension by itself fixes spring-seat separation.

A WUFR-specific absolute spring force from solved eye-to-eye geometry therefore still requires an explicit spring-seat separation/reference relation.

## Seated-spring mode

The first model supports a seated compression coil spring only. A state that produces `x_s<0` is reported as `spring_unseated`; compression/force is not silently clipped to zero.

Because the reviewed WUFR setup has no tender/helper spring, no secondary spring contact law is introduced.

## Benchmark review

`BENCH-SUSP-0009` freezes analytical checks for:

- `k=10000 N/m`, `x_s=0.020 m` -> `F=200 N`, `U=2 J`, `k_t=10000 N/m`;
- explicit preload/reference arithmetic;
- signed generalized force and finite-difference potential-energy consistency;
- unseated failure;
- a synthetic bounded progressive table with exact hand values and no extrapolation.

`BENCH-SUSP-0010` freezes the WUFR package boundaries and specifically tests that the rear law cannot be fabricated from endpoint labels or damper stroke.

## Prohibited scope

PR #47 does not authorize:

- spring-force implementation before merge;
- damper dyno/velocity force or damping ratios;
- gas force, friction, hysteresis, stops, or thermal behavior;
- ARB kinematics/stiffness/preload;
- governing wheel-rate/MR shortcuts;
- vehicle equilibrium/load transfer/wheel-load generation;
- linkage forces or stress/FEA;
- installed/as-built travel, stroke, clearance, or production claims.

## Review decision requested

Approve `AUTH-SUSP-0004` as the bounded conservative spring-force authorization while preserving two explicit WUFR parameter gaps for later implementation/use:

1. exact rear 30-to-36 N/mm progression versus spring compression;
2. WUFR spring-seat/reference mapping needed to convert solved coilover eye-to-eye state into absolute spring compression.

Those gaps do not block defining or reviewing the generic conservative spring architecture, but they must not be silently filled in PR #48.
