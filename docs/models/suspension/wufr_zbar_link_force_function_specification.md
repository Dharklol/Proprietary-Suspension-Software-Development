# WUFR physical Z-bar linkage-force function specification

## Purpose

Recover the signed physical axial force vector carried by each rod-ended WUFR rocker-to-blade ARB linkage from the already-authorized Z-bar mechanism state.

The function is an internal force-interface adapter for `MOD-SUSP-0005`; it does not solve rocker equilibrium or generate wheel/tire/load-transfer forces.

## Required inputs

For one front or rear axle:

- successful `ZBarMechanismResult` from the exact current `AUTH-SUSP-0008` mechanism state;
- successful `ZBarForceResult` from the same state and exact discrete blade setting;
- matching `ZBarAxleFixture`;
- source/configuration identity;
- numerical projection/verification tolerances.

The implementation must require current:

- housing angle;
- `d_left`, `d_right`;
- current blade tips;
- current rocker pickups;
- rocker pivots and rocker axis;
- fixture nominal blade-link joints and housing axis.

## Geometry and sign convention

For side `i`, define:

`a_i = B_nom_i - C`

`a_hat_i = normalize(a_i)`

`n_nom_i = normalize(u_h cross a_hat_i)`

`n_i = R(u_h, theta_h) n_nom_i`

where `n_i` is exactly the signed transverse direction already used by the blade deformation coordinate.

Let current blade tip and rocker pickup be `B_i` and `P_i` and define

`u_i = normalize(P_i-B_i)`.

`u_i` therefore points from blade tip to rocker.

Signed linkage axial force uses

`T_i > 0` = tension.

A tensile linkage applies

- `F_blade_i = +T_i u_i` at the blade tip;
- `F_rocker_i = -T_i u_i` at the rocker pickup.

## Force recovery

The existing blade elastic coordinate action is

`f_i = k_b d_i`.

Virtual work in the transverse blade coordinate gives

`T_i (u_i dot n_i) = f_i`.

Therefore

`T_i = f_i / (u_i dot n_i)`.

This projection is current geometry. It is not a scalar motion ratio and is not replaced by a nominal link angle.

Default absolute projection threshold:

`|u_i dot n_i| > 1e-6`.

Below that threshold the physical force is unavailable and the function returns `degenerate_link_projection`.

## Verification

Reconstruct the transverse action:

`f_reconstructed_i = T_i (u_i dot n_i)`

and require agreement with `k_b d_i` within `1e-8 N`.

Then compute the physical generalized rocker torque

`tau_i = u_R dot ((P_i-R_i) cross F_rocker_i)`

and require

`tau_i = Q_rocker_i`

within `1e-8 N*m` whenever the upstream `ZBarForceResult` contains its reviewed generalized rocker torque.

The torque check is mandatory for nonzero benchmark states and for production use when the upstream generalized torque is available.

## Result

Return per side:

- canonical blade-tip-to-rocker unit link axis;
- blade transverse unit direction;
- projection `u dot n`;
- signed elastic transverse action `k_b d`;
- signed axial force `T`;
- physical force on rocker;
- physical force on blade tip;
- physical rocker-axis torque;
- projection and torque residuals;
- exact axle/side/setting/source/configuration provenance.

## Failure behavior

Fail closed for:

- upstream mechanism or force failure;
- source/configuration mismatch;
- missing/nonfinite current geometry;
- degenerate link length;
- degenerate transverse direction;
- near-zero link/transverse projection;
- closure residual outside existing tolerance;
- transverse force reconstruction failure;
- physical rocker torque disagreement with existing generalized torque.

No absolute-value sign repair, clipping, nominal-angle substitution, motion ratio, generalized-force reinterpretation, or regularization is allowed.

## Scope boundary

The result is a physical axial linkage force at a physical rocker pickup. It is not:

- a rocker pivot reaction;
- a spring force;
- a wheel/tire force;
- load transfer;
- a body-equilibrium result;
- linkage stress/buckling/fatigue authority;
- installed/as-built load authority.
