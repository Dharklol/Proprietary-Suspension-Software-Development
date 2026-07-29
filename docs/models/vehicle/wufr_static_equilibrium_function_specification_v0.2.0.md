# WUFR static-equilibrium composition function specification v0.2.0

## Supersession

This specification supersedes the reduced-equilibrium and result-record sections of `wufr_static_equilibrium_function_specification.md` after the merged `AUTH-VEH-0010` correction. The original document remains the historical `AUTH-VEH-0009` specification; superseded `EQ-VEH-0016` is not an implementation fallback.

## Authorized state

`MOD-VEH-0007` is limited to:

- `WUFR27_SUSPENSION_BASELINE_V0`;
- `WUFR26_DRIVER_NO_FUEL_DESIGN_INTENT_REFERENCE`;
- centered rack, flat rigid road, all four contacts active;
- gravity, conservative springs, and conservative front/rear Z-bars only;
- explicit integer front/rear ARB settings in `1..5` with no default or interpolation;
- result label `uncorrelated_design_intent_static_gravity`.

## Provider ownership

The composition may consume only:

- `MOD-VEH-0003` body/road frames, point transport, analytical point-force mapping, and physical wrench assembly;
- `MOD-VEH-0004` reduced quasi-static solve and contact recovery;
- `MOD-VEH-0005` sprung and four source-owned unsprung gravity point loads;
- `MOD-VEH-0006` road-compatible wheel coordinates, `J_wb`, contact/wheel-center points, contact coefficients, and wheel-coordinate unsprung-gravity projections;
- `MOD-SUSP-0004` four conservative spring states;
- `MOD-SUSP-0005` front and rear conservative Z-bar states.

No component law, mass allocation, road geometry, setup value, or equilibrium solver is redefined.

## Corrected compatible gravity reduction

For body coordinates `q_b=[z_s,phi,theta]` and compatible physical wheel coordinates `z_w(q_b)`, each unsprung point load contributes both a direct body-coordinate term and a mapped wheel-coordinate term:

```text
Q_u,b,direct = sum_i J_r,wc_i(q_b,z_i)^T F_u,i
Q_u,red      = Q_u,b,direct + J_wb(q_b)^T Q_u,z
```

`Q_u,b,direct` is evaluated at the exact current wheel-center body points while holding each wheel coordinate fixed. `Q_u,z` remains the existing `MOD-VEH-0006` projection. The direct, mapped, and total reduced terms must remain separately visible.

The corrected reduced equilibrium is:

```text
Q_susp = Q_spring + Q_ARB
R_b = Q_sprung_gravity + Q_u,red + J_wb^T Q_susp = 0
```

Equivalently:

```text
R_b = Q_sprung_gravity
    + Q_u,b,direct
    + J_wb^T (Q_u,z + Q_susp)
```

The implementation must use the unchanged `MOD-VEH-0004` bounded deterministic damped-Newton solver. It may not omit either gravity term, count either term twice, add a scalar weight correction, or use `EQ-VEH-0016`.

## Contact recovery

After convergence, recover only:

```text
lambda_i = -(Q_susp,i + Q_u,z,i) / c_i
```

Negative reactions remain negative and fail the all-four-active contact mode. No clipping, redistribution, crossweight rule, or diagonal-load rule is allowed.

## Independent checks

The complete compatible potential is:

```text
Pi(q_b) = U_susp(z_w(q_b))
        + V_sprung_gravity(q_b)
        + sum_i m_u,i g z_wc,i^road(q_b,z_w(q_b))
```

The implementation must verify `R_b=-dPi/dq_b` at two perturbation scales and independently verify the `EQ-VEH-0018` unsprung portion at nominal and bounded nonzero body states.

Physical road-frame closure uses:

- four recovered road-normal reactions at exact current contact points;
- sprung gravity at the transported sprung-CG point;
- four unsprung gravity loads at exact current wheel-center points.

Required closure is `1e-6 N` and `1e-6 N*m`. No balancing wrench is allowed.

The retained old-equation probe must demonstrate that omitting `Q_u,red` fails physical closure, while corrected `EQ-VEH-0019` agrees with the independently assembled physical wrench.

## Result contract

The governed records are:

```text
benchmarks/vehicle/wufr_static_equilibrium_result_v0.2.0.toml
benchmarks/vehicle/wufr_static_equilibrium_result_v0.2.0.json
```

They retain provider identities, settings and role labels, body/wheel coordinates, component forces and energies, direct/mapped/reduced gravity terms, reactions, exact physical points, solver diagnostics, continuation comparison, potential-gradient checks, physical closure, old-equation negative evidence, and explicit authority boundaries.

## Failure behavior and boundary

The implementation fails closed for invalid settings, source/order/unit/configuration mismatch, provider failure, missing or nonfinite chain-rule inputs, negative contact reaction, numerical failure, energy disagreement, or physical-closure disagreement.

`AUTH-VEH-0010` does not authorize historical scale fitting, installed/as-built prediction, physical correlation, setup selection, tire/damper/aero/brake/drive/inertia forces, alternate contact modes, maneuver QSS, carrier wrenches, structural propagation, stress, FEA, fatigue, or production release.
