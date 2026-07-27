# WUFR flat-road contact-map function specification

> **Replacement authority:** `AUTH-VEH-0008` authorizes the explicitly low-fidelity `ASM-VEH-0005` ideal rigid circular tire after merge. It does not revive the failed `ASM-VEH-0004` OptimumK material-point interpretation preserved by `AUTH-VEH-0007` / `BENCH-VEH-0008`.

## Public responsibility

`MOD-VEH-0006` supplies the WUFR-specific compatibility inputs required by `MOD-VEH-0004`. It does not solve the final spring/ARB equilibrium or publish WUFR road reactions.

Canonical body coordinate order is `q_b=[z_s_m, phi_rad, theta_rad]`.
Canonical wheel coordinate order is `z_w=[FL_delta_z_wc_body_m, FR_delta_z_wc_body_m, RL_delta_z_wc_body_m, RR_delta_z_wc_body_m]`.

## 1. Per-corner physical wheel state

For requested physical wheel-center vertical coordinate `z_i`:

1. call `MOD-SUSP-0002` physical-state inversion;
2. retain the solved physical wheel center and wheel-plane normal;
3. rear uses the reviewed final toe-link-closed wheel plane;
4. front uses the `MOD-SUSP-0002` minimum-twist state followed by the existing `MOD-STEER-0001` centered-rack closure; rotate the wheel plane by that steering solution;
5. do not reproduce the tie-rod closure equation in the vehicle layer.

The historical OptimumK Contact Patch output is not transported as a material point.

## 2. Ideal rigid circular tire contact — `EQ-VEH-0014`

`ASM-VEH-0005` freezes the source-setup tire radius

`R = 0.23241 m`

from `WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0`. This is the same source radius already used by `MOD-SUSP-0002` wheel-reference construction. It is not loaded-radius or installed-tire authority.

Inputs are current wheel center `r_wc`, unit wheel-plane normal `n_w`, and unit road normal `n_R`.

Compute

`v = n_R - (n_R dot n_w) n_w`

`s = ||v||`

`e = v / s`

`r_cp = r_wc - R e`

where `e` is the upward road-normal direction projected into the wheel plane. `r_cp` is therefore the minimum-road-height point on the zero-width circle.

Required identities:

- `||r_cp-r_wc|| = R`;
- `(r_cp-r_wc) dot n_w = 0`;
- changing `n_w` to `-n_w` does not change `r_cp`;
- when `n_w` is perpendicular to `n_R`, `r_cp=r_wc-R n_R`.

Reject `s` at or below the declared degeneracy threshold. Do not substitute body vertical.

## 3. Nominal WUFR geometry check

Using the frozen nominal wheel references and horizontal road, the ideal-circle points are approximately:

- FL `[+0.000159242280, +0.615984170, 0] m`;
- FR `[+0.000159242280, -0.615984170, 0] m`;
- RL `[-0.000035395821, +0.603285406, 0] m`;
- RR `[-0.000035395821, -0.603285406, 0] m`.

The small nonzero longitudinal coordinates arise from the fully three-dimensional toe/camber wheel plane and are retained. They are not forced to the historical OptimumK Contact Patch `x=0` output. The historical output is comparison context only.

## 4. Whole-body/road placement

Convert suspension-source wheel/contact points into the reviewed WUFR body frame using the existing whole-vehicle source-origin/CG transform, then use `MOD-VEH-0003` body pose transport to obtain road-frame points.

No new front/rear origin convention may be inferred from wheelbase.

## 5. Per-corner road root — `EQ-VEH-0012`

For fixed `q_b`, define

`g_i(z_i)=n_R dot (r_cp,i^R(q_b,z_i)-r_R0)`.

Solve `g_i=0` over the declared physical wheel-coordinate interval tied to the reviewed `MOD-SUSP-0002` branch.

The root algorithm must sample/bracket without clipping, reject upstream/contact failures, reject ambiguous multiple accepted roots, refine deterministically, and report bracket, iterations, residual, branch, steering, and contact diagnostics.

All four roots must succeed before `z_w(q_b)` is available.

## 6. Body-to-wheel Jacobian and contact coefficient — `EQ-VEH-0013`

Compute `J_wb=partial(z_w)/partial(q_b)` at two declared finite-difference step scales.

At a converged state and fixed body pose,

`c_i=n_R dot partial(r_cp,i^R)/partial(z_i)`.

Both derivatives must pass two-step convergence on the same nominal-continuation branch. Centered differences are required whenever both perturbations are valid. One-sided differentiation is permitted only at an explicit declared bound.

`c_i` must remain finite and bounded away from zero. No absolute-value or unit-coefficient repair is allowed.

## 7. Unsprung gravity generalized wheel force

For the `MOD-VEH-0005` physical wheel-center gravity force `F_u,i`, evaluate

`Q_u,i = F_u,i dot partial(r_wc,i^R)/partial(z_i)`.

This uses physical wheel-center motion, not contact-point motion. Verify independently as the negative gradient of `U=m g z_wc^road`.

## 8. Negative source evidence retained

`BENCH-VEH-0008` remains failed negative evidence against `ASM-VEH-0004`: the selected historical rigid-point reconstruction disagreed with the OptimumK Contact Patch output by up to `0.845816 mm` versus `0.005 mm` allowed.

That benchmark is not retuned and does not become an acceptance target for the rigid-circle model.

## 9. Failure semantics

Structured failures include source/configuration mismatch, suspension-state/domain failure, suspension branch failure, front steering closure failure, invalid radius or normals, circle-projection degeneracy, unbracketed/ambiguous/nonconvergent road roots, finite-difference failure, derivative nonconvergence, zero/near-zero contact coefficient, and nonfinite point/force/Jacobian state.

No hidden fallback is permitted.

## 10. Explicit exclusions

`AUTH-VEH-0008` does not authorize tire width/edge contact, contact-patch footprint, loaded radius, vertical tire stiffness, pressure/load/temperature/speed dependence, carcass deformation, wheel lift/alternate contact modes, installed/as-built tire geometry, or production fidelity.

The output remains a **compatibility/provider state**, not a wheel-load result. A separate authorization is required before composing springs, Z-bar, gravity, compatibility, and the generic QSS kernel into WUFR road reactions.
