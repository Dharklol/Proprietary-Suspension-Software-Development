# WUFR static carrier external wrench function specification

## 1. Purpose

`MOD-VEH-0008` is the source-preserving boundary adapter between the accepted whole-vehicle static equilibrium (`MOD-VEH-0007`) and the existing Level-1 suspension interface statics (`MOD-SUSP-0007`).

For each corner it answers one narrowly bounded question:

> What complete external force/couple wrench is applied to the outboard-carrier suspension-interface boundary by the external loads represented in the accepted spring-plus-Z-bar-plus-gravity static model?

The answer contains only:

1. the recovered road-normal force at the exact current rigid-circle contact point; and
2. the source-owned prototype unsprung gravity point force at the exact current physical wheel center.

It does not calculate or add suspension interface reactions. Those are solved downstream by `MOD-SUSP-0007`.

Every successful result is labelled:

```text
uncorrelated_design_intent_static_carrier_wrench
```

The wrench is complete only for the exact authorized static-gravity model. It is not complete for the physical vehicle, a maneuver, or an installed/as-built state.

## 2. Required upstream state

The adapter requires one successful `MOD-VEH-0007` result under `AUTH-VEH-0010` with:

- configuration `WUFR27_SUSPENSION_BASELINE_V0`;
- static state `WUFR26_DRIVER_NO_FUEL_DESIGN_INTENT_REFERENCE`;
- centered rack;
- flat rigid road;
- all four contacts active;
- corner order `[front_left, front_right, rear_left, rear_right]`;
- nonnegative road reactions;
- exact current road-frame contact and wheel-center points;
- exact road normal and frame/origin identities;
- accepted physical force/moment closure;
- result label `uncorrelated_design_intent_static_gravity`.

The first benchmark consumes the frozen setting-1/1 result only as a verification fixture. It does not establish the current ARB setup.

## 3. Outboard-carrier boundary

`MOD-SUSP-0007` defines `outboard_carrier` as a net suspension-interface load-transmission boundary. Wheel, hub, tire, bearing, brake, and drive internals may remain unresolved upstream.

The current carrier reference point is:

```text
r_C = 0.5 * (r_upper_spherical + r_lower_spherical)
```

using the exact current upper and lower outboard spherical-joint centers from the matching Level-1 geometry state.

A wrench may be expressed about another named point only through exact rigid-wrench transport. Changing the reference point does not change force; it changes moment by the corresponding force moment arm.

## 4. Per-corner physical composition

For corner `i`, let:

- `lambda_i` be the recovered nonnegative road-normal reaction;
- `n_R` be the exact unit road normal;
- `r_cp,i` be the exact current rigid-circle contact point;
- `m_u,i` be the source-owned prototype corner unsprung mass;
- `g_R` be the road-frame gravity vector;
- `r_wc,i` be the exact current physical wheel-center point;
- `r_C,i` be the exact current carrier reference point.

The two physical point forces are:

```text
F_road,i = lambda_i * n_R
F_u,i    = m_u,i * g_R
```

The carrier resultant is `EQ-VEH-0020`:

```text
F_C,i = F_road,i + F_u,i

M_C,i = (r_cp,i-r_C,i) x F_road,i
      + (r_wc,i-r_C,i) x F_u,i
```

No free couple is added.

The source `ASM-VEH-0003` places the full prototype 5 kg corner unsprung lump at the physical wheel center. Carrying that exact point load onto the outboard boundary is source preserving, but it is not a claim that the physical wheel, upright, brake, arms, half-shaft, damper, or other components have that distribution.

## 5. Loads deliberately excluded

The prescribed carrier external wrench does **not** contain:

- upper/lower spherical reactions;
- tie-rod or toe-link force;
- pushrod or pullrod force;
- spring or anti-roll-bar force;
- rocker or chassis reaction;
- tire `Fx`, `Fy`, or `Mz`;
- brake or drive torque;
- aero;
- translational, rotational, or gyroscopic inertia;
- tire vertical compliance;
- alternate-contact reactions;
- damper velocity force or bump-stop force.

The first group is internal to the downstream suspension graph. The second group is absent from the authorized upstream static model.

## 6. Frame placement

### 6.1 Frames

The relevant reviewed frames are:

- road: `WUFR27_NOMINAL_ROAD`;
- body: `WUFR27_BODY_DRIVER_NO_FUEL_REFERENCE`;
- source: `WUFR26_SUSPENSION_CAD`;
- Level-1: `WUFR26_OPTIMUMK_SUSPENSION_CANONICAL_AXLE_LOCAL`.

All use the canonical orientation `+x` forward, `+y` left, `+z` up before the body pose is applied.

### 6.2 Level-1 point to source point

Use the same placement already used by `MOD-VEH-0006`:

```text
r_source = r_level1 + [x_axle_source, 0, 0]
```

where `x_axle_source` is the reviewed front or rear axle source position. Local `y` and `z` are preserved exactly.

### 6.3 Source to body

Use `MOD-VEH-0003`:

```text
r_body = r_source - r_CG_reference_source
```

The source-to-body rotation is identity, as frozen in the whole-vehicle frame record.

### 6.4 Body to road

Use the exact converged `BodyPose` and the existing rotation convention:

```text
R_RB = Rz(psi) Ry(theta) Rx(phi)
r_road = t_pose + R_RB r_body
```

with `psi=0` for the authorized state. Nonzero roll and pitch remain present; the road and body vector components may not be treated as numerically identical.

## 7. Level-1 wrench representation

The canonical physical assembly occurs in the road frame. The same wrench may then be pulled back to the Level-1 frame for direct `MOD-SUSP-0007` consumption.

For the same physical reference point:

```text
F_L = R_RB^T F_R
M_L = R_RB^T M_R
```

If the reference point changes, translate the moment before or after rotation using the exact named positions. A road-to-Level-1-to-road round trip must preserve force and moment within the authorized tolerances.

## 8. Whole-vehicle reconstruction

`EQ-VEH-0022` verifies the boundary decomposition independently.

Transport all four road-frame carrier resultants to the current body-origin road point and add the matching sprung gravity wrench once:

```text
W_reconstructed = sum_i Transport(W_C,i -> O_body) + W_sprung_gravity
```

This must:

1. satisfy `1e-6 N` force and `1e-6 N*m` moment closure; and
2. match the already accepted `MOD-VEH-0007` physical-closure vector within the tighter comparison tolerance.

This is a mechanics-consistency check, not independent physical validation, because both results use the same design-intent source chain.

## 9. Result contract

A successful per-corner result retains at least:

- corner, axle, and side identity;
- source/configuration/static-state/result IDs;
- exact upstream body and wheel state identity;
- road reaction and road normal;
- road-force `AppliedWrench`;
- prototype-unsprung-gravity `AppliedWrench`;
- exact contact and wheel-center points;
- exact current carrier reference in Level-1, source, body, and road frames;
- road-frame resultant force/moment;
- Level-1-frame resultant force/moment;
- transform and round-trip residuals;
- all assumption and exclusion labels;
- `complete_for_authorized_static_gravity_case=true`;
- `complete_physical_hardware_wrench=false`;
- `maneuver_complete=false`;
- `installed_as_built_authority=false`.

The four-corner result also retains the reconstruction contributions and residuals.

## 10. Failure behavior

The adapter fails closed for:

- unsuccessful or incomplete upstream equilibrium;
- wrong result/configuration/static-state identity;
- negative, nonfinite, missing, duplicated, or reordered reaction;
- missing or mismatched physical point;
- non-unit or mismatched road normal;
- altered unsprung mass/gravity source;
- missing or mismatched current carrier reference;
- frame/origin/transform disagreement;
- nonfinite rigid transform;
- Level-1 round-trip disagreement;
- mixed body states among corners;
- four-corner reconstruction disagreement.

No balancing wrench, clipping, absolute value, historical load, crossweight rule, fitted offset, implicit frame identity, or load redistribution is allowed.

## 11. Authorization boundary and next gate

`AUTH-VEH-0011` authorizes implementation and freezing of the four carrier wrenches only.

It does not yet authorize publication of the synchronized four-corner `MOD-SUSP-0007` linkage/interface loads. That is the next separate authorization after the carrier-wrench result has passed review.

After that integration, the resulting push/pull forces may be propagated into the existing rocker included-load model, but the rocker result remains incomplete until the KW V5 non-spring static force is measured or otherwise authorized.
