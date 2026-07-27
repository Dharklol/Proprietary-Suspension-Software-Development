# WUFR road-contact reference source audit

## Purpose

`MOD-VEH-0004` now has a generic reduced-coordinate quasi-static kernel, and `MOD-VEH-0005` supplies bounded WUFR gravity inputs. The remaining compatibility input is an explicit physical wheel map

`z_w(q_b), J_wb = partial(z_w)/partial(q_b)`

for the flat-road active-contact mode.

This audit recovers the WUFR source evidence needed to construct that map without replacing the existing suspension/steering mechanisms with track-width or scalar motion-ratio approximations.

## Source contact-reference evidence

The current recovered OptimumK result `WUFR-26 8.21 Heaves 1inch.xlsx` (Box `2014806871001`, result version `2.3.0`) contains explicit per-corner channels for:

- wheel-center X/Y/Z;
- Contact Patch X/Y/Z;
- lower/upper upright points;
- front tie-rod upright point;
- camber/toe/steer outputs.

The existing wheel-reference benchmark already freezes the source frame rule for this pure-heave result:

`p_body_optk_mm = p_export_optk_mm - [0,0,heave_mm]`

then

`p_body_can_m = 0.001*[x,-y,z]`.

At nominal state the Contact Patch channels are exactly on `z=0` and at the source half tracks:

- front left/right `[0, +/-0.61598556, 0] m`;
- rear left/right `[-1.5624, +/-0.60328556, 0] m`.

These values are frozen in `WUFR26_ROAD_CONTACT_REFERENCE_V0`.

## Why this is not a generic tire model

`AUTH-SUSP-0002` intentionally left generic contact-patch/tire-envelope construction open. This audit does not close that broader problem.

Instead, `ASM-VEH-0004` makes a narrower source-specific interpretation: the OptimumK `Contact Patch` channel supplies a **nominal upright-attached road reference point** for this rigid design-intent model. The point is transported with the solved upright/steering pose. It is not promoted as:

- a loaded tire radius;
- a carcass-deflection model;
- an instantaneous geometric lowest point of an arbitrary tire envelope;
- a finite contact footprint;
- physical installed tire metrology.

Selected pure-heave rows show that the source Contact Patch moves in x/y as the upright changes while remaining on the external road in the OptimumK result frame. After removal of the prescribed body heave, the point moves relative to the chassis as expected for a road-constrained upright-attached reference.

## Front steering separation

Front suspension position under `MOD-SUSP-0002` deliberately stops at the minimum-twist zero-extra-steering upright reference. The tie rod then owns the remaining steering rotation.

The historical OptimumK result contains a scalar `Steer Angle`, but `BENCH-SUSP-0005` already proves that this scalar is not the correct three-dimensional rotation used to remove source steering. The existing benchmark reconstructs the actual twist from the lower/upper/tie points.

Therefore:

- **source-correlation check:** minimum-twist transform + already-reconstructed historical source twist may be used to verify the Contact Patch interpretation;
- **WUFR runtime map:** minimum-twist transform + `MOD-STEER-0001` centered-rack tie-rod closure must be used.

The historical twist is not a runtime substitute for current WUFR steering geometry.

## Rear closure

Rear upright twist is already resolved by the reviewed chassis toe-link closure in the suspension model. The rear contact reference is therefore transported with the same final rear upright transform as the physical wheel reference. No second steering/toe solve is introduced.

## Whole-vehicle placement

Suspension/steering source coordinates use the same canonical design frame lineage in which the front axle is near `x=0`, the rear axle is at `x=-1.5624 m`, and `z=0` is the nominal road plane.

`MOD-VEH-0003` already owns the reviewed WUFR whole-vehicle adapter, body origin, road plane, and body-point transport. The road-map implementation must convert source points into that body frame through the existing reviewed source-origin/CG relation and then use the existing body pose transport. It may not infer a new CG/front/rear origin from wheelbase alone.

## Compatibility equation

For each corner, the implementation will solve the exact source-contact road gap

`g_i(q_b,z_i) = n_road dot (r_cp,i^road(q_b,z_i) - r_road_ref) = 0`

where `z_i` is the existing physical wheel-center vertical coordinate from `MOD-SUSP-0002`.

This yields four road-compatible coordinates without introducing a crossweight equation or a track-width wheel-travel rule.

## Work-conjugate derivatives

The same exact providers then define:

- `J_wb = partial(z_w)/partial(q_b)`;
- `c_i = n_road dot partial(r_cp,i^road)/partial(z_i)`;
- `Q_u_i = F_u,i dot partial(r_wc,i^road)/partial(z_i)`.

These quantities are evaluated numerically with two step sizes and branch checks. `c_i=1` and `Q_u=-49.05 N` may appear near the nominal level state, but neither is a governing hard-coded relation.

## Open boundaries

This audit still does not authorize:

- tire vertical compliance or loaded radius;
- alternate contact modes after wheel lift;
- final WUFR spring+ARB static equilibrium or road reactions;
- installed/as-built correlation;
- maneuver tire forces or tire-force saturation.

The first real WUFR static road-reaction result remains one authorization downstream of this compatibility provider.
