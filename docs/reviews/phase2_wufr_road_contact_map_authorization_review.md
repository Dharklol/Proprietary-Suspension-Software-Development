# Phase 2 WUFR road-contact map authorization review

## Review target

Authorize `MOD-VEH-0006` as the WUFR-specific compatibility layer between the already implemented physical suspension/steering mechanisms and the generic `MOD-VEH-0004` quasi-static kernel.

## Source decision

The recovered OptimumK result contains explicit `Contact Patch X/Y/Z` channels in addition to wheel-center and upright/tie-rod points. This review does not promote those channels into a general tire model.

Under `ASM-VEH-0004`, the first rigid-road R&D model treats the nominal source Contact Patch positions as upright-attached road-reference points. Historical heave rows are used to verify the rigid-transport interpretation.

## Mechanism composition

Rear:

`MOD-SUSP-0002 physical z_wc -> rear toe-link-closed upright pose -> source contact reference`.

Front:

`MOD-SUSP-0002 physical z_wc -> minimum-twist unresolved-steering upright pose -> transformed existing WUFR steering geometry -> MOD-STEER-0001 centered-rack tie-rod closure -> source contact reference`.

This preserves the established ownership boundary: suspension supplies the zero-extra-steering pose and the steering analyzer supplies the tie-rod-induced upright rotation. The vehicle layer may adapt frames but may not duplicate the steering closure equation.

## Road compatibility

For each wheel, a scalar physical wheel-center vertical coordinate is solved from the actual road gap

`g_i = n dot (r_cp_i^road-r_road_ref)=0`.

The resulting four coordinates form `z_w(q_b)`. `J_wb`, the road-normal contact coefficients, and unsprung gravity wheel generalized forces are then derived by two-step numerical virtual-work differentiation through those same point providers.

This directly supplies the coordinate data required by the already authorized generic QSS kernel.

## Rejected shortcuts

The review explicitly rejects:

- body roll multiplied by track/half-track;
- direct left/right wheel-travel-difference closure;
- scalar spring/ARB motion ratios as the body-to-wheel Jacobian;
- crossweight repair rules;
- OptimumK scalar `Steer Angle` as the front rotation input;
- translation-only front contact motion that suppresses bump steer;
- generic tire-radius/lowest-point construction;
- hard-coded `c_i=1` or `Q_u=-49.05 N` away from an independently verified limiting state.

## Verification before implementation merge

`BENCH-VEH-0008` must show that the source Contact Patch evidence is compatible with the rigid reference-point interpretation, including historical 3D source twist rather than scalar steer angle.

`BENCH-VEH-0009` must verify unique road roots, road-gap residuals, canonical coordinate order, two-step `J_wb`, contact coefficients, wheel-center gravity virtual work, and structured failure behavior at nominal and nonzero body states.

## Still not authorized

This review does not yet publish WUFR wheel loads. The first WUFR static road-reaction result remains a separate composition gate combining:

- `MOD-SUSP-0004` springs;
- `MOD-SUSP-0005` Z-bar ARB;
- `MOD-VEH-0005` gravity;
- `MOD-VEH-0006` road compatibility;
- `MOD-VEH-0004` equilibrium/contact recovery.

Tire compliance/loaded radius, alternate contact modes, installed validation, and production optimization also remain separate.
