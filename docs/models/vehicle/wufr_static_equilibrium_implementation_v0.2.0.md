# WUFR static-equilibrium implementation v0.2.0

## Implemented scope

`src/pssd_vehicle/wufr_static_equilibrium.py` implements `MOD-VEH-0007` under `AUTH-VEH-0010` for the driver/no-fuel, centered-rack, flat-road, all-four-active, gravity-only WUFR design-intent state.

The adapter composes only the reviewed providers:

- `MOD-VEH-0003` body/road frames, point transport, generalized-force mapping, and physical wrench assembly;
- `MOD-VEH-0004` bounded reduced quasi-static solve and active-contact recovery;
- `MOD-VEH-0005` sprung and four-corner unsprung gravity point loads;
- `MOD-VEH-0006` rigid-circle road compatibility, exact contact/wheel-center points, `J_wb`, contact coefficients, and wheel-coordinate unsprung-gravity projections;
- `MOD-SUSP-0004` conservative spring force and energy;
- `MOD-SUSP-0005` conservative physical-wheel-coordinate front/rear Z-bar force and energy.

No new component force law or alternate equilibrium solver is introduced.

## Corrected reduced mechanics

The suspension composition remains:

```text
Q_susp = Q_spring + Q_ARB
U_susp = sum(U_spring,i) + U_ARB,front + U_ARB,rear
```

For each unsprung gravity point force, the implementation retains the direct body-coordinate term while holding the physical wheel coordinate fixed and the mapped compatible wheel-coordinate term:

```text
Q_u,b,direct = sum_i J_r,wc_i^T F_u,i
Q_u,red = Q_u,b,direct + J_wb^T Q_u,z
```

The corrected body residual is:

```text
R_b = Q_sprung_gravity + Q_u,red + J_wb^T Q_susp = 0
```

Contact recovery remains:

```text
lambda_i = -(Q_susp,i + Q_u,z,i) / c_i
```

Negative reactions are retained and fail the all-four-active mode. The implementation contains no balancing wrench, clipping, load redistribution, historical corner-load fit, or fallback to superseded `EQ-VEH-0016`.

## Source-preserving numerical interfaces

The runtime uses one shared implicit road-root derivative bundle for:

- the compatible wheel-coordinate Jacobian `J_wb`;
- contact coefficients;
- wheel-center unsprung-gravity projections.

The WUFR static composition uses a source-owned internal-`qL` rocker derivative mode so the spring derivative follows the same successful mechanism branch as the wheel-coordinate solve. This mode is local to the composition and does not change the public suspension coordinate authority.

The body solve remains the existing deterministic bounded damped-Newton implementation in `MOD-VEH-0004`. The declared physical closure gates remain `1e-6 N` and `1e-6 N*m`.

## Verification

The focused implementation verifies:

- exact provider identities, coordinate order, units, settings, and source ownership;
- explicit front/rear ARB settings in integer range `1..5`, with no default or interpolation;
- convergence from two bounded initial body states to the same continuation solution;
- four nonnegative unmodified road reactions and wheel equilibrium residuals;
- two-step total-potential gradient agreement;
- independent road-frame force and moment closure at the exact physical application points;
- nominal and bounded-nonzero compatible unsprung-gravity potential-gradient oracles;
- retained negative evidence showing that the superseded equation can numerically approach equilibrium while failing physical closure;
- structured source, domain, setting, contact, and numerical failures.

## Frozen result

The governed summary is:

```text
benchmarks/vehicle/wufr_static_equilibrium_result_v0.2.0.toml
```

The complete generated report is:

```text
benchmarks/vehicle/wufr_static_equilibrium_result_v0.2.0.json
```

The fixture uses front/rear ARB settings `1/1` only for deterministic verification. It is not current setup authority or a recommendation.

## Boundary

Every successful result is labeled `uncorrelated_design_intent_static_gravity`.

This implementation does not authorize installed/as-built corner weights, physical correlation, setup selection, tire/damper/aero/brake/drive/inertia forces, alternate contact modes, maneuver QSS, carrier wrenches, structural propagation, stress, FEA, fatigue, or production release.
