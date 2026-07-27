# Quasi-static equilibrium implementation v0.1.0

## Scope

PR #60 implements the provider-neutral `MOD-VEH-0004` kernel authorized by `AUTH-VEH-0004` after the PR #58 source audit and PR #59 authorization packet.

The implementation is intentionally generic. It does not contain a WUFR mass/gravity adapter and cannot generate WUFR road reactions from the existing corner-scale/CG records alone.

Implementation:

```text
src/pssd_vehicle/quasi_static.py
```

## Implemented mechanics

### Explicit compatibility provider

The solver consumes an externally supplied physical wheel-coordinate map:

```text
z_w = z_w(q_b)
J_wb = partial(z_w)/partial(q_b)
```

with exact body/wheel coordinate order, units, and provenance. The implementation verifies matrix dimensions and refuses mismatched suspension-force coordinates.

No track-width/body-roll approximation, historical motion ratio, crossweight rule, or load-transfer equation is embedded.

### Reduced body equilibrium

The assembled body residual is:

```text
R_b = Q_body_ext + J_wb^T Q_susp_w
```

where the suspension generalized wheel force must come from an explicit provider using the same wheel-coordinate contract.

Wheel-only external forces such as future unsprung gravity are not inserted into the reduced body residual. They are retained for constrained wheel/contact equilibrium so they cannot be double counted after the active road compatibility has eliminated the wheel coordinates from the body solve.

### Active-contact reaction recovery

After body convergence:

```text
lambda_i = -(Q_susp_i + Q_wheel_ext_i) / c_i
```

where every `c_i` is explicit and signed. `wheel_external_generalized_force=None` returns `missing_wheel_external_force_authority`; zero is never assumed internally.

Any negative `lambda_i` is retained and returns `negative_normal_reaction`. It is not clipped or redistributed.

## Provider result contracts

The public API exposes structured provider/result objects:

- `CompatibilityState`;
- `SuspensionGeneralizedForceState`;
- `BodyExternalGeneralizedForceState`;
- `QuasiStaticEvaluation`;
- `QuasiStaticSolveResult`;
- `ContactRecoveryResult`;
- `EnergyGradientCheckResult`.

Provider exceptions, explicit provider failure, coordinate mismatch, nonfinite values, missing wheel force authority, missing/zero contact coefficient, singular tangent, bounds/line-search failure, nonconvergence, negative reaction, and energy-gradient failures are surfaced explicitly.

## Numerical method

The first kernel uses a small dependency-free damped Newton method suitable for the initial reduced 1-3 coordinate program.

### Scaling

Callers must supply:

- positive coordinate scales;
- positive residual scales.

The finite-difference tangent is formed using scaled residuals with respect to normalized coordinate perturbations. This avoids silently mixing raw newtons and newton-meters in the convergence norm.

### Tangent

Centered finite differences are preferred. A one-sided derivative is used only where a declared bound removes one perturbation direction. If neither direction is available, the solve fails.

The actual perturbation and derivative method are retained in the result.

### Linear solve and conditioning

The normalized Newton system is solved by deterministic partial-pivot Gaussian elimination. The first implementation reports a reciprocal pivot-ratio diagnostic and rejects a tangent that violates the configured minimum ratio or pivot magnitude.

No external numerical dependency was added to the package.

### Line search and bounds

The Newton step is converted back into dimensional coordinates. A geometric line search accepts only an in-bounds state with a strictly smaller scaled residual norm.

If no such state is found, the solver returns `line_search_failure`. It never clips a coordinate to its bound and declares convergence.

## Conservative verification

When both suspension and body external providers expose potential energy, `check_total_potential_gradient` independently verifies:

```text
R_b = -partial(Pi)/partial(q_b)
```

using at least two declared centered-difference step multipliers.

This is separate from the numerical residual tangent and therefore checks the generalized-force sign/energy convention rather than simply reproducing the Newton derivative.

## BENCH-VEH-0005 result

The dedicated CI report uses only synthetic inputs:

```text
sprung mass                         100 kg
g                                  9.81 m/s^2
four support stiffnesses            10000 N/m
synthetic wheel-side mass/corner    5 kg
```

The four synthetic wheel coordinates use a full-rank heave/roll/pitch compatibility fixture. The analytical symmetric state is:

```text
z_s = -0.024525 m
phi = 0
theta = 0
z_w = +0.024525 m at each corner
Q_susp = -245.25 N at each corner
Q_wheel_ext = -49.05 N at each corner
lambda = +294.30 N at each corner
sum(lambda) = 1177.20 N
```

First passing PR #60 dedicated CI produced:

```text
max body-coordinate error          2.4529e-14
max wheel-coordinate error         2.4529e-14 m
scaled residual norm               9.8112e-13
reciprocal pivot ratio             0.4444444444
energy-gradient max disagreement   3.4153e-09
reaction-sum error                 9.8112e-10 N
Newton iterations                  1
```

The benchmark's 5 kg/corner value is a synthetic fixture constant and explicitly has **no WUFR authority**.

## BENCH-VEH-0006 result

The first passing CI result froze:

```text
repeatability max q difference         3.5891e-14
singular fixture failure               singular_or_ill_conditioned_tangent
bounded unreachable fixture failure   line_search_failure
missing wheel-force failure            missing_wheel_external_force_authority
negative reaction failure              negative_normal_reaction
preserved negative reaction            -10 N
hidden WUFR mass default used          false
```

## WUFR boundary

The project now has the numerical equilibrium kernel needed to compose the reviewed spring and WUFR Z-bar generalized-force providers, but the physical WUFR gravity input remains intentionally absent.

Current reviewed mass evidence remains:

- driver/no-fuel scale state `178/175/163/159 lb`;
- source-separated driver-equivalent `z_CG=0.290 m` design reference;
- measured unsprung totals `10 kg front axle + 10 kg rear axle`.

There is still no reviewed left/right unsprung split/application convention or independent sprung-body mass/CG gravity model. Consequently this implementation does not expose a WUFR four-corner road-reaction function.

The next WUFR step requires a focused mass/gravity authority decision before any physical corner-load result is generated.
