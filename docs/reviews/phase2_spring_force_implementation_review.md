# Phase 2 conservative spring-force implementation review

## Review status

**Review-ready implementation packet for PR #48.**

`AUTH-SUSP-0004` was approved and merged in PR #47 before implementation began. PR #48 implements only that bounded authorization.

## Implemented scope

PR #48 adds:

- `src/pssd_suspension/spring_force.py`;
- `tests/test_suspension_spring_force.py`;
- `scripts/run_suspension_spring_force_benchmarks.py`;
- `benchmarks/suspension/suspension_spring_force_result_v0.1.0.toml`;
- spring-force exports in `pssd_suspension`;
- CI execution of implementation tests and BENCH-SUSP-0009/0010;
- implementation documentation and registry/governance promotion of `MOD-SUSP-0004` to an M1/B prototype.

## Equation implementation

### EQ-SUSP-0013

Both reviewed spring-compression forms are implemented:

```text
x_s = L_free - L_seat
x_s = x_pre + L_ref - L_d.
```

Negative compression returns `spring_unseated` and is retained in the failure result. No `max(x_s,0)` repair exists.

### EQ-SUSP-0014

The provider implements:

1. exact linear springs;
2. an affine tangent-rate law integrated analytically to force and stored energy;
3. bounded piecewise-linear force tables with exact segmentwise trapezoidal energy.

The WUFR rear assumption is implemented as tangent stiffness, not an effective secant spring rate:

```text
k_t = 30000 + (6000/0.057) x_s
F_s = 30000 x_s + 0.5 (6000/0.057) x_s^2
U_s = 0.5(30000)x_s^2 + (1/6)(6000/0.057)x_s^3.
```

### EQ-SUSP-0015

Generalized force is implemented as

```text
Q_s = F_s dL_d/dq
```

for the authorized direct-coilover reference. Scalar and vector Jacobians are supported with explicit coordinate ordering and units. The `MOD-SUSP-0003` local `rho_dw` may be consumed directly; its sign is preserved.

A two-step centered finite-difference energy check independently verifies `Q_s=-dU/dq` locally.

## WUFR adapter review

The implementation reads `WUFR27_SPRING_PACKAGE_V0` and preserves `ASM-SUSP-0002` on the WUFR spring definitions/reference.

The prototype setup remains:

```text
front spring = 36 N/mm linear
rear spring = 30 -> 36 N/mm linear-progressive assumption
free length = 100 mm
intentional preload = zero
tender/helper = none
reference = 185.7 mm full-extension eye-to-eye
rear assumed progression domain = 0..57 mm spring compression
```

The current WUFR mapping is

```text
x_s = 0.1857 - L_d.
```

It remains design-intent assumption authority, not installed spring-seat/perch metrology.

## Benchmark decision

`BENCH-SUSP-0009` passes. Key results:

- linear hand-case force/energy/tangent errors: zero at report precision;
- signed generalized force: `-50 N`;
- two-step energy-gradient maximum residual: `1.1652900866465643e-10`;
- synthetic table result: `170 N`, `1.175 J`, `14000 N/m`;
- `spring_unseated` and `constitutive_domain_exceeded` failures are exercised.

`BENCH-SUSP-0010` passes. Key WUFR design-intent results:

- front nominal spring compression: `21.100652947832144 mm`;
- rear nominal spring compression: `21.089461209192306 mm`;
- front nominal spring-axis force: `759.6235061219571 N`;
- rear nominal spring-axis force: `656.0925401754548 N`;
- rear nominal tangent stiffness: `32.21994328517814 N/mm`;
- rear energy-gradient maximum residual: `1.8487412489776034e-08`;
- the incorrect `k_t*x` shortcut differs from integrated rear force by `23.408703899685634 N` at nominal state.

The result record is `benchmarks/suspension/suspension_spring_force_result_v0.1.0.toml`.

## Failure / provenance review

The implementation explicitly preserves:

- `ASM-SUSP-0002` on WUFR results;
- `installed_as_built_authority = false`;
- source/configuration identity;
- uncalibrated shock-pot `44m` as metadata only;
- no nonlinear extrapolation;
- no endpoint averaging;
- no negative-compression clipping;
- no absolute motion ratio;
- no hidden use of OptimumK `Motion Ratio Heave`.

## Prohibited scope retained

PR #48 does not add:

- damper velocity force, gas force, seal friction, hysteresis, or stops;
- ARB stiffness/energy/coupling;
- tire force or tire radial stiffness;
- heave/roll/pitch equilibrium or load transfer;
- four-corner wheel-load generation;
- linkage/member/bearing loads;
- compliance;
- stress, fatigue, buckling, or FEA boundary-condition release;
- installed travel/stroke/clearance authority;
- production optimization or setup release.

## Review decision requested

Approve `MOD-SUSP-0004` as the M1/B conservative spring-force prototype implemented under `AUTH-SUSP-0004`, with the WUFR rear progression and zero-preload/full-extension reference remaining explicitly labeled `ASM-SUSP-0002` assumptions.

After merge, the next force-model authorization should be the coupled left/right anti-roll-bar element. The later QSS residual system should consume the spring and ARB providers rather than embedding their equations in the equilibrium solver.
