# WUFR flat-road contact-map function specification

## Public responsibility

`MOD-VEH-0006` supplies the WUFR-specific compatibility inputs required by `MOD-VEH-0004`. It does not solve the final spring/ARB equilibrium.

Canonical body coordinate order:

`q_b = [z_s_m, phi_rad, theta_rad]`.

Canonical wheel coordinate order:

`z_w = [FL_delta_z_wc_body_m, FR_delta_z_wc_body_m, RL_delta_z_wc_body_m, RR_delta_z_wc_body_m]`.

All public results must preserve this order and explicit units.

## 1. Per-corner rigid point provider

Inputs:

- requested physical wheel-center vertical coordinate `z_i`;
- WUFR suspension geometry/profile/domain;
- source nominal contact-reference point;
- for front corners, centered WUFR steering geometry/rack state.

Steps:

1. call `MOD-SUSP-0002` physical-state inversion for `z_i`;
2. retain the solved current physical wheel center;
3. rear: apply the final rear upright transform to the nominal contact reference;
4. front: apply the minimum-twist front transform to the nominal contact reference, steering-axis points, and outer tie-rod point; keep rack inner joint chassis-fixed; call the existing `MOD-STEER-0001` position closure at rack displacement `0`; rotate the pre-steering contact reference by the returned upright rotation about the transformed steering axis;
5. return current contact-reference and wheel-center points plus all upstream branch/provenance diagnostics.

The vehicle layer may adapt frames and call the existing steering solver, but it may not reproduce the tie-rod closure equation.

## 2. Whole-body/road placement

Convert suspension-source points into the reviewed WUFR body frame using the existing whole-vehicle source-origin/CG transform. Then use `MOD-VEH-0003` body pose transport to obtain road-frame points.

No new front/rear origin convention may be inferred from wheelbase.

## 3. Per-corner road root

For fixed `q_b`, define

`g_i(z_i) = n_road dot (r_cp,i^road(q_b,z_i)-r_road_ref)`.

Solve `g_i=0` over a declared physical wheel-coordinate interval tied to the reviewed `MOD-SUSP-0002` branch.

The root algorithm must:

- sample/bracket without clipping;
- reject nonfinite/upstream failures;
- reject zero roots only when residual criteria fail;
- reject multiple accepted sign-changing intervals/ambiguous mappings;
- refine the unique bracket deterministically;
- report bracket, iterations, final residual, wheel coordinate, suspension branch, and front steering closure diagnostics.

All four roots must succeed before `z_w(q_b)` is considered available.

## 4. Body-to-wheel Jacobian

Compute

`J_wb = partial(z_w)/partial(q_b)`

at two declared finite-difference step scales. Centered differences are required where both body perturbations remain inside the declared map domain. One-sided differentiation is permitted only at an explicit declared bound, never because an otherwise valid perturbation produced an upstream failure.

Report both matrices and a convergence metric before returning the accepted Jacobian.

## 5. Contact coefficient

At a converged state and fixed body pose,

`c_i = n_road dot partial(r_cp,i^road)/partial(z_i)`.

Evaluate through the exact point provider at two step sizes. `c_i` must be finite and bounded away from zero. Sign is retained; no absolute-value repair is allowed.

## 6. Unsprung gravity generalized wheel force

For the `MOD-VEH-0005` physical point gravity force `F_u,i`, evaluate

`Q_u,i = F_u,i dot partial(r_wc,i^road)/partial(z_i)`.

This uses physical wheel-center motion, not contact-reference motion. Verify the result independently as the negative gradient of the wheel point gravitational potential `U=m g z_wc^road`.

## 7. Source-correlation helper

A verification-only helper may reconstruct the historical front OptimumK contact-reference rows from:

- frozen nominal contact reference;
- the existing exact historical lower/upper/tie/wheel-center source fixture;
- `minimum_twist_upright_transform`;
- `reconstruct_source_steering_twist` / frozen expected twist.

It must not use the OptimumK scalar `Steer Angle` as a rotation input and must not feed historical twist into the runtime WUFR map.

## 8. Failure semantics

Structured failures include at least:

- source/configuration mismatch;
- suspension state outside reachable domain;
- suspension closure/branch failure;
- front steering closure infeasible/singular;
- road root unbracketed;
- multiple/ambiguous road roots;
- road-root nonconvergence;
- finite-difference perturbation failure;
- derivative convergence failure;
- zero/near-zero contact coefficient;
- nonfinite point/force/Jacobian state.

No hidden fallback is permitted.

## 9. Output authority

The result is a **compatibility/provider state**, not a wheel-load result. It may be consumed by a later authorized composition with `MOD-SUSP-0004`, `MOD-SUSP-0005`, `MOD-VEH-0005`, and `MOD-VEH-0004`. It may not itself report road reactions as WUFR predictions.
