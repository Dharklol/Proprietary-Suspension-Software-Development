# Phase 3 WUFR synchronized static Level-1 interface-load authorization review

## Decision

Authorize implementation of `MOD-SUSP-0009` under `AUTH-SUSP-0017` after this review is merged.

The required upstream and downstream mechanics now both exist:

- `MOD-VEH-0008` supplies four source-preserving complete carrier external wrenches for the exact restricted static-gravity fixture;
- `MOD-SUSP-0007` supplies the source-bounded three-body carrier/UCA/LCA Level-1 equilibrium solver.

The missing step is not another force law. It is an explicit synchronization and publication boundary connecting those two reviewed models.

## Why a separate composition is required

A complete carrier wrench alone does not identify the matching suspension solve unless corner, frame, reference point, body/wheel state, suspension state, actuation state, steering/toe closure, configuration, and load-case provenance are kept synchronized.

Similarly, four individually successful corner solves are not automatically one authoritative vehicle result. The collection must be atomic, fixed-order, and fail closed if any corner is stale, mismatched, incomplete, or numerically invalid.

## Authorized mechanics

For each named corner, the implementation may:

1. accept the exact `MOD-VEH-0008` Level-1 carrier wrench at its exact current carrier reference;
2. recover the exact matching current suspension and actuation geometry;
3. require explicit centered-rack `MOD-STEER-0001` front tie-rod endpoints;
4. invoke the unchanged `MOD-SUSP-0007` 18x18 direct solve;
5. retain every signed interface result, action-reaction partner, application point, source identity, conditioning diagnostic, and physical residual;
6. publish the result only when all four corners pass.

No load is added, removed, redistributed, fitted, clipped, balanced, or inferred.

## Result fidelity

The successful packet is the first actual WUFR Level-1 load-path result for the authorized static fixture:

```text
gravity + spring + Z-bar
-> compatible four-contact equilibrium
-> four carrier external wrenches
-> four carrier/UCA/LCA Level-1 interface solutions
```

It remains `uncorrelated_design_intent_static_level1_interface_loads`. It is not an as-built prediction, setup recommendation, maneuver load case, or structural release.

## Steering and actuation ownership

The prior `AUTH-SUSP-0012` ownership rules remain unchanged:

- front lateral links require explicit current steering-closure endpoints; nominal suspension toe points are not a substitute;
- rear toe links remain owned by the current suspension closure;
- front pullrods act on the UCA;
- rear pushrods act on the LCA;
- arm-mounted points are not moved to the carrier.

## Numerical and failure policy

The composition inherits the `MOD-SUSP-0007` direct-solve policy: no pseudoinverse, least squares, regularization, minimum norm, stiffness weighting, sign clipping, or geometry repair. Each carrier, UCA, and LCA physical residual must pass the existing `1e-9 N` and `1e-9 N*m` gates, and each equivalent hinge must retain zero free-axis reaction moment within `1e-9 N*m`.

One failed corner fails the complete collection. Partial four-corner publication is prohibited.

## Downstream boundary

A successful signed pullrod/pushrod remote-end force may later be passed unchanged to the already-authorized incomplete rocker included-load adapter. This review does not publish rocker results and does not alter the damper hold: the KW V5 non-spring static force remains unavailable under `AUTH-SUSP-0015` and may not be assumed zero.

Individual A-arm chassis-joint loads, welded-member loads, bearing splits, structural exchange packets, stress, fatigue, buckling, factor of safety, FEA boundary conditions, and maneuver cases remain separate future authorizations.

## Review outcome

`AUTH-SUSP-0017` is review-ready because:

- the complete restricted carrier-wrench source is implemented and frozen;
- the Level-1 topology and solver are implemented and frozen;
- the composition adds no new physical assumption;
- exact state/frame/reference/source synchronization is explicit;
- atomic four-corner success and failure behavior are explicit;
- the rocker, structural, maneuver, correlation, and installed-use boundaries remain intact.
