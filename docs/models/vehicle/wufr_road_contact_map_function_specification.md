# WUFR flat-road contact-map function specification

> **Implementation hold:** `AUTH-VEH-0007` suspends implementation of the original `ASM-VEH-0004` point-provider definition. PR #64 failed mandatory `BENCH-VEH-0008`: the proposed rigid upright-attached OptimumK Contact Patch interpretation disagreed with selected historical rows by up to `0.0008458158026623031 m` versus `0.000005 m` allowed. Sections below preserve the desired provider architecture, but Section 1's contact-point construction is **not authorized** until a replacement contact model/source assumption is reviewed.

## Public responsibility

`MOD-VEH-0006` is intended to supply the WUFR-specific compatibility inputs required by `MOD-VEH-0004`. It does not solve the final spring/ARB equilibrium. Its implementation is currently blocked at the contact-point provider.

Canonical body coordinate order:

`q_b = [z_s_m, phi_rad, theta_rad]`.

Canonical wheel coordinate order:

`z_w = [FL_delta_z_wc_body_m, FR_delta_z_wc_body_m, RL_delta_z_wc_body_m, RR_delta_z_wc_body_m]`.

All future public results must preserve this order and explicit units.

## 1. Per-corner contact-point provider — replacement authority required

The original specification proposed rigidly transporting the nominal OptimumK Contact Patch point with the solved upright/steering pose. `BENCH-VEH-0008` rejected that source interpretation. Do **not** implement it.

The valid upstream pieces remain:

1. call `MOD-SUSP-0002` physical-state inversion for requested physical wheel-center vertical coordinate `z_i`;
2. retain the solved current physical wheel center and wheel/upright orientation state;
3. rear upright pose remains the reviewed final rear toe-link-closed transform;
4. front pose remains `MOD-SUSP-0002` minimum-twist followed by `MOD-STEER-0001` centered-rack closure, with rack inner joint chassis-fixed;
5. a **new reviewed contact model** must map that physical wheel/upright state to `r_cp,i`.

The vehicle layer may adapt frames and call existing solvers, but it may not reproduce the tie-rod closure equation or silently invent a tire/contact relation.

The OptimumK Contact Patch coordinates remain historical road-contact output observations. They are not a governing material-point transport rule.

## 2. Whole-body/road placement

After a replacement contact point is provided, convert suspension-source points into the reviewed WUFR body frame using the existing whole-vehicle source-origin/CG transform. Then use `MOD-VEH-0003` body pose transport to obtain road-frame points.

No new front/rear origin convention may be inferred from wheelbase.

## 3. Per-corner road root

For fixed `q_b`, after replacement contact authority exists, define

`g_i(z_i) = n_road dot (r_cp,i^road(q_b,z_i)-r_road_ref)`.

Solve `g_i=0` over a declared physical wheel-coordinate interval tied to the reviewed `MOD-SUSP-0002` branch.

The root algorithm must:

- sample/bracket without clipping;
- reject nonfinite/upstream failures;
- reject multiple accepted sign-changing intervals/ambiguous mappings;
- refine the unique bracket deterministically;
- report bracket, iterations, final residual, wheel coordinate, suspension branch, front steering closure, and contact-model diagnostics.

All four roots must succeed before `z_w(q_b)` is available.

## 4. Body-to-wheel Jacobian

Compute

`J_wb = partial(z_w)/partial(q_b)`

at two declared finite-difference step scales. Centered differences are required where both body perturbations remain inside the declared map domain. One-sided differentiation is permitted only at an explicit declared bound, never because an otherwise valid perturbation produced an upstream failure.

Report both matrices and a convergence metric before returning the accepted Jacobian.

## 5. Contact coefficient

At a converged state and fixed body pose,

`c_i = n_road dot partial(r_cp,i^road)/partial(z_i)`.

Evaluate through the same reviewed replacement contact-point provider at two step sizes. `c_i` must be finite and bounded away from zero. Sign is retained; no absolute-value repair is allowed.

## 6. Unsprung gravity generalized wheel force

For the `MOD-VEH-0005` physical point gravity force `F_u,i`, evaluate

`Q_u,i = F_u,i dot partial(r_wc,i^road)/partial(z_i)`.

This uses physical wheel-center motion, not contact-reference motion. Verify the result independently as the negative gradient of wheel-point gravitational potential `U=m g z_wc^road`.

This projection is conceptually independent of the failed OptimumK material-point hypothesis, but it must not be promoted into a WUFR road-reaction result until the wheel-coordinate compatibility map is re-authorized.

## 7. Source-correlation evidence

The historical front OptimumK check uses:

- frozen nominal Contact Patch output;
- the existing exact historical lower/upper/tie/wheel-center fixture;
- `minimum_twist_upright_transform`;
- `reconstruct_source_steering_twist` / frozen expected twist.

It does not use scalar OptimumK `Steer Angle` as a rotation input.

The result is now negative evidence: maximum selected-row rigid-point disagreement was `0.845816 mm`. The historical helper must remain a benchmark/audit path and must not feed source twist into a future runtime WUFR map.

## 8. Failure semantics

Structured failures for a future replacement implementation include at least:

- source/configuration mismatch;
- missing/unreviewed contact-model authority;
- suspension state outside reachable domain;
- suspension closure/branch failure;
- front steering closure infeasible/singular;
- contact-model domain/geometry failure;
- road root unbracketed;
- multiple/ambiguous road roots;
- road-root nonconvergence;
- finite-difference perturbation failure;
- derivative convergence failure;
- zero/near-zero contact coefficient;
- nonfinite point/force/Jacobian state.

No hidden fallback is permitted.

## 9. Output authority

After re-authorization, the result will be a **compatibility/provider state**, not a wheel-load result. It may be consumed only by a later authorized composition with `MOD-SUSP-0004`, `MOD-SUSP-0005`, `MOD-VEH-0005`, and `MOD-VEH-0004`. It may not itself report road reactions as WUFR predictions.

## 10. Replacement-contact gate

Before implementation restarts, one explicit contact model/source assumption must be reviewed. Current candidates include:

- a low-fidelity ideal rigid circular centerline tire constructed from reviewed physical wheel center, wheel-plane orientation, and nominal tire radius; or
- physical/empirical loaded-radius/contact authority.

The rigid circular model is only a candidate. This document does not authorize it.
