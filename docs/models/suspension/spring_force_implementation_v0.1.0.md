# Conservative suspension spring-force implementation v0.1.0

## Scope

`MOD-SUSP-0004` implements the bounded spring provider authorized by `AUTH-SUSP-0004` / PR #47. The implementation lives in `src/pssd_suspension/spring_force.py` and covers `EQ-SUSP-0013` through `EQ-SUSP-0015` only.

It does not solve vehicle equilibrium and it does not add damper, anti-roll-bar, tire, structural, compliance, or installed-limit physics.

## 1. Spring compression reference

The provider exposes both authorized compression forms:

```text
x_s = L_free - L_seat
```

and, for a reviewed direct-coilover reference,

```text
x_s = x_pre + L_ref - L_d.
```

Positive `x_s` means compression from the zero-load/free-length reference. Negative `x_s` returns `spring_unseated`; it is never clipped.

For `WUFR27_SUSPENSION_BASELINE_V0`, `ASM-SUSP-0002` supplies the design-intent reference

```text
x_pre = 0
L_ref = 0.1857 m
x_s = 0.1857 - L_d.
```

That mapping is an explicit team assumption tied to the reviewed KW V5 piggyback/CAD setup. It is not installed perch or spring-seat metrology.

## 2. Constitutive laws

### Linear

```text
F_s = k x_s
U_s = 0.5 k x_s^2
k_t = k
```

### Affine tangent-rate progressive law

For

```text
k_t(x_s) = k_0 + a x_s
```

the implementation integrates tangent stiffness:

```text
F_s = k_0 x_s + 0.5 a x_s^2
U_s = 0.5 k_0 x_s^2 + (a/6) x_s^3.
```

It intentionally does **not** use `F_s = k_t(x_s) x_s`.

The WUFR rear design-intent assumption is

```text
k_0 = 30000 N/m
a = 6000 / 0.057 N/m^2
0 <= x_s <= 0.057 m.
```

Requests above 57 mm return `constitutive_domain_exceeded`; the law is not extrapolated.

### Piecewise-linear force table

A generic bounded force-versus-compression table is included for source-defined future nonlinear springs and for `BENCH-SUSP-0009`. Force is linearly interpolated only between frozen points, stored energy is the exact segmentwise trapezoidal integral, and the active-segment slope is reported as tangent stiffness. No extrapolation is permitted.

## 3. Generalized force

The governing elastic action remains potential-energy based:

```text
Q_s = -partial U_s/partial q.
```

For the direct-coilover reference,

```text
partial x_s/partial q = -partial L_d/partial q
Q_s = F_s partial L_d/partial q.
```

The implementation accepts a scalar or vector `dL_d/dq`, preserves coordinate order and units, and does not take an absolute value.

When a successful `MOD-SUSP-0003` state contains the canonical local

```text
rho_dw = d(delta_L_d)/d(delta_z_wc_body),
```

`evaluate_spring_from_actuation` may use it directly so

```text
Q_delta_z = F_s rho_dw.
```

No historical OptimumK motion-ratio scalar is used as an input.

## 4. Energy-gradient verification

`check_spring_energy_gradient` performs an independent local centered finite-difference check at two declared step sizes by evaluating

```text
x(q+h) = x_s - (dL_d/dq) h
x(q-h) = x_s + (dL_d/dq) h
Q_fd = -(U(q+h)-U(q-h))/(2h).
```

This check validates constitutive integration and generalized-force sign locally. It does not claim that the actuation Jacobian is constant over finite suspension travel.

## 5. WUFR-27 adapter

`load_wufr27_spring_package` reads `data_catalog/wufr27_spring_package_v0.toml` rather than duplicating setup parameters in code.

The adapter produces:

- front: `36 N/mm` linear spring;
- rear: `30 -> 36 N/mm` affine tangent-rate assumption over `57 mm`;
- free length: `100 mm`;
- zero intentional preload;
- no tender/helper spring;
- `ASM-SUSP-0002` provenance on front/rear/reference objects;
- `installed_as_built_authority = false`.

The raw shock-pot datum `44m` is carried only as source/correlation metadata and is not consumed by force calculations.

## 6. Frozen benchmark results

`BENCH-SUSP-0009` passes the synthetic hand cases:

- linear `k=10000 N/m`, `x_s=0.020 m`: `F=200 N`, `U=2 J`, `k_t=10000 N/m`;
- signed generalized force: `-50 N` for `dL_d/dq=-0.25`;
- maximum two-step energy-gradient residual: `1.1652900866465643e-10`;
- table state at `x_s=0.015 m`: `F=170 N`, `U=1.175 J`, `k_t=14000 N/m`;
- negative compression returns `spring_unseated`;
- out-of-table-domain requests return `constitutive_domain_exceeded`.

`BENCH-SUSP-0010` passes the WUFR design-intent cases:

- front nominal `L_d = 0.16459934705216786 m`;
- rear nominal `L_d = 0.1646105387908077 m`;
- front nominal compression `0.021100652947832144 m`;
- rear nominal compression `0.021089461209192306 m`;
- front nominal spring-axis force `759.6235061219571 N`;
- rear nominal spring-axis force `656.0925401754548 N`;
- rear nominal tangent stiffness `32219.94328517814 N/m`;
- rear energy-gradient residual `1.8487412489776034e-08`;
- `k_t*x` would give `679.5012440751404 N`, explicitly differing from the integrated force by `23.408703899685634 N`.

These are provider verification/design-intent values. They are not corner weights, tire normal loads, installed spring-force measurements, or vehicle-equilibrium solutions.

## 7. Failure behavior

The implementation returns structured failures for nonfinite inputs, missing parameter/reference authority, spring unseating, constitutive-domain exceedance, malformed conservative laws, upstream actuation failure, and unavailable/mismatched generalized-force Jacobians.

No failure path silently clips compression, extrapolates a nonlinear law, averages progressive endpoint rates, replaces the signed Jacobian with an absolute motion ratio, or introduces an alternate physics model.

## 8. Remaining boundary

The next elastic element is the separately authorized coupled left/right anti-roll bar. `MOD-SUSP-0004` remains a one-corner spring provider and must later be consumed by the body-equilibrium/QSS residual system rather than growing its own equilibrium loop.

Physical spring testing should replace the rear progression assumption when available. Installed spring-seat/perch or calibrated shock-pot evidence should similarly validate or replace the current full-extension reference without changing the provider architecture.
