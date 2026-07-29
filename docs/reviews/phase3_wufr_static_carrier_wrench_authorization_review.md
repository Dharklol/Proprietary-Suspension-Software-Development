# Phase 3 review — WUFR static carrier external wrench authorization

## Decision

Authorize `MOD-VEH-0008` as the narrow source-preserving adapter from the accepted `MOD-VEH-0007` static-gravity result to four complete prescribed outboard-carrier external wrenches for that exact restricted load case.

The authorization is intentionally separated from both upstream vehicle equilibrium and downstream linkage statics:

```text
MOD-VEH-0007 accepted static state
    -> MOD-VEH-0008 carrier external wrenches
    -> later synchronized MOD-SUSP-0007 integration
```

This prevents the vehicle model from solving suspension reactions and prevents the suspension statics model from inventing its own road/tire/gravity load case.

## Why this slice is ready

PR #87 merged the corrected static equilibrium and froze:

- one bounded body and wheel state;
- four nonnegative road reactions;
- exact current rigid-circle contact points;
- exact current physical wheel-center points;
- the road normal and frame/origin identities;
- source-owned sprung and prototype unsprung gravity;
- independent physical force/moment closure.

`MOD-SUSP-0007` is already implemented and accepts one complete finite prescribed wrench on an explicitly named outboard-carrier boundary. Its current missing input is therefore no longer a force magnitude or application-point problem for the restricted static case; it is an authorization and frame-preserving composition problem.

## Physical composition reviewed

For each corner, the only external loads represented on the outboard boundary by the accepted static model are:

1. road-normal reaction at the exact current contact point; and
2. prototype unsprung gravity at the exact current wheel-center point.

Their resultant about the exact current carrier reference is:

```text
F_C = lambda*n_road + m_u*g
M_C = (r_contact-r_C) x (lambda*n_road)
    + (r_wc-r_C) x (m_u*g)
```

Spring, ARB, ball-joint, tie/toe-link, and push/pull forces are not added because they are internal forces of the downstream suspension graph.

## Unsprung-gravity limitation

`ASM-VEH-0003` is a high-severity prototype allocation: 5 kg at each physical wheel center. The carrier-wrench adapter carries that exact point load forward because changing its location or splitting it among components would violate source ownership.

This makes the adapter consistent with the accepted whole-vehicle model, but it does not make the result a measured component-level gravity distribution. The result must remain explicitly uncorrelated and design-intent only.

## Frame review

The road result and the existing Level-1 suspension geometry are not stored in the same frame representation.

The authorization therefore freezes the exact existing placement chain rather than assuming identity:

```text
Level-1 axle-local
  + reviewed axle source x-position
-> WUFR26 suspension source
  + reviewed source-to-body translation
-> WUFR27 body reference
  + converged BodyPose Rz Ry Rx transform
-> WUFR27 road frame
```

The current carrier reference is the midpoint of the current upper and lower outboard spherical-joint centers. The road-frame resultant may be pulled back to the Level-1 frame only by exact rigid transformation. Nonzero body roll and pitch are preserved.

## Independent verification

The four carrier resultants provide a useful boundary-decomposition check:

- transport all four to the current body-origin road reference;
- add sprung gravity once;
- recover the accepted whole-vehicle physical resultant.

The required gates remain `1e-6 N` and `1e-6 N*m`. No balancing wrench or reaction adjustment is permitted.

This reconstruction is not physical correlation; it verifies that no external load was lost, duplicated, or moved while crossing the vehicle-to-suspension boundary.

## Authorized output

Each successful result may state:

```text
complete_for_authorized_static_gravity_case = true
```

It must also state:

```text
complete_physical_hardware_wrench = false
maneuver_complete = false
installed_as_built_authority = false
```

The distinction allows `MOD-SUSP-0007` to receive a mathematically complete prescribed wrench for the modeled static case without overstating the physical scope.

## Explicitly rejected alternatives

The review rejects:

- using historical corner-scale readings as carrier loads;
- adding spring or ARB force directly to the carrier wrench;
- relocating the wheel-center unsprung lump;
- assuming road/body/Level-1 vector components are identical;
- using wheelbase, track, crossweight, or scalar load-transfer shortcuts;
- adding a balancing force or couple;
- adding missing maneuver loads by inference;
- publishing linkage loads under the carrier-wrench authorization itself.

## Records introduced

- `AUTH-VEH-0011`
- `MOD-VEH-0008`
- `EQ-VEH-0020..0022`
- `BENCH-VEH-0015..0017`
- `WUFR27_STATIC_CARRIER_WRENCH_V0`

## Next gate

After this authorization is reviewed and merged:

1. implement `MOD-VEH-0008`;
2. freeze the four road-frame and Level-1 carrier wrenches;
3. verify exact four-corner reconstruction;
4. review that result;
5. separately authorize synchronized four-corner `MOD-SUSP-0007` linkage/interface-load publication.

The later linkage result can supply actual push/pull forces to the existing rocker included-load model. Complete rocker hardware reaction remains blocked only by the unavailable KW V5 non-spring static force, which can be added after the planned Instron characterization.
