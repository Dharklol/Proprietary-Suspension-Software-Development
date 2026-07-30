# Phase 3 WUFR static rocker included-load authorization review

## Outcome

`AUTH-SUSP-0018` authorizes the next static load-path composition after merged `MOD-SUSP-0009`.

The future `MOD-SUSP-0010` implementation may connect each accepted static Level-1 actuation reaction to the exact matching current spring, Z-bar, and rocker states and invoke the already-implemented `MOD-SUSP-0008` included-load adapter. The collection is atomic across front-left, front-right, rear-left, and rear-right.

## Reviewed handoff

The push/pull force must be copied from the successful Level-1 `AxialReaction.force_on_remote_N` at `remote_point_m`. This is the force applied at the rocker-side rod pickup. The A-arm-side `force_on_body_N` is not interchangeable and may not be substituted.

The other two included loads remain source-owned:

- conservative coil-spring force from `AUTH-SUSP-0014` at the exact current spring rocker eye;
- physical Z-bar linkage force from `AUTH-SUSP-0013` at the exact current mechanism rocker pickup.

All three loads retain signed vectors and distinct application points.

## Authorized result

For each corner, the existing ideal-revolute kernel may publish:

- included resultant force and moment about the current rocker pivot;
- ideal-revolute support-force contribution;
- support-moment contribution perpendicular to the signed rocker axis;
- signed free-axis moment residual;
- exact residual diagnostics and provenance;
- explicit included and missing load identities.

The four-corner collection remains `uncorrelated_design_intent_static_rocker_included_loads` and is complete only for the named push/pull, spring, and ARB load set.

## Damper influence decision

A per-unit hypothetical non-spring damper-force influence coefficient is authorized because it is a purely geometric linear sensitivity. Positive force is defined along the current chassis-eye-to-rocker-eye direction, applied at the rocker eye.

The coefficient does not select, infer, or imply a KW V5 force magnitude. It may not be treated as a zero-force assumption or as a complete reaction. A future measured or manufacturer-supplied signed scalar can be applied only after satisfying `AUTH-SUSP-0015` and separately authorizing the complete composition.

## Atomic and fail-closed policy

One stale, reordered, missing, mismatched, nonfinite, or residual-failing corner rejects the entire collection. The implementation may not mirror a side, reuse another corner, move an application point, alter a force sign, clip compression, add a balancing torque, or publish a successful subset.

## Deliberate stopping boundary

This authorization does not permit:

- an actual KW V5 gas/static-friction force model;
- complete rocker equilibrium or total pivot/bearing reaction;
- bearing load sharing or chassis pickup loads;
- structural packets, stress, buckling, fatigue, factor of safety, or FEA release;
- maneuver, curb, impact, aero, brake, drive, or inertial loads;
- setup selection, physical correlation, installed/as-built claims, or production use.

After this authorization is reviewed and merged, the next implementation gate is to freeze and independently regenerate the first four-corner incomplete rocker included-load result and unit damper-force influence map.
