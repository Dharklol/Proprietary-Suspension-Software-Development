# WUFR synchronized static Level-1 interface-load function specification

## Purpose

`MOD-SUSP-0009` is a thin source-preserving composition layer. It exists to connect the now-implemented `MOD-VEH-0008` four-corner static carrier-wrench result to the already-implemented `MOD-SUSP-0007` Level-1 three-body statics solver without duplicating or changing either model.

It produces the first actual WUFR four-corner suspension-interface load packet for the exact driver/no-fuel, centered-rack, flat-rigid-road, all-four-contact, spring-plus-Z-bar-plus-gravity fixture.

## Required input

The function consumes one successful `MOD-VEH-0008` collection in fixed order:

1. front left;
2. front right;
3. rear left;
4. rear right.

Each corner must retain its exact Level-1 carrier wrench, carrier reference, frame, body/wheel state, source configuration, and load-case identity. The function then obtains the exact matching current suspension and actuation states. Front tie-rod endpoints must come from an explicit current centered-rack `MOD-STEER-0001` closure; the existing adapter prohibition against substituting nominal suspension toe points remains active.

## Composition

For each corner `i`:

```text
geometry_i = current Level-1 geometry at the exact carrier-wrench state
result_i   = solve_level1_interface_statics(geometry_i, carrier_wrench_i)
```

The existing `MOD-SUSP-0007` topology, unknown order, application-point ownership, direct linear solve, conditioning gates, action-reaction records, and physical residual checks are used unchanged.

`MOD-SUSP-0009` adds no tire, road, gravity, spring, ARB, damper, brake, drive, aero, inertia, gyroscopic, or balancing load. It does not recompute the carrier wrench.

## Atomic output

A successful result is one ordered four-corner packet. One failed corner fails the collection. No partial set is promoted as an integrated WUFR result.

Per corner, retain:

- signed tie-rod/toe-link axial force;
- signed pullrod/pushrod axial force;
- upper/lower spherical action-reaction forces;
- upper/lower equivalent inboard hinge force and perpendicular moment;
- exact points, frames, state/source/load-case identities;
- 18x18 scaling, condition, pivot, and solve diagnostics;
- independent carrier, UCA, and LCA force/moment residuals.

## Rocker handoff

The only downstream handoff named here is the exact successful actuation `force_on_remote_N` at `remote_point_m`. It may later be consumed unchanged by the existing `MOD-SUSP-0008` rocker included-load adapter.

This does not make the rocker result complete. `AUTH-SUSP-0015` still identifies the unavailable KW V5 non-spring static force and prohibits assuming it is zero.

## Failure behavior

Fail before solve on corner/order, state, source, configuration, frame, reference, or current-geometry disagreement. Fail the whole collection on any corner solve, conditioning, pivot, hinge-axis, nonfinite, or physical residual failure.

No fallback may use mirroring, historical force tables, corner scales, scalar load-transfer distribution, motion ratios, nominal front tie-rod points, clipping, absolute values, balancing forces/couples, pseudoinverse, least squares, regularization, stiffness weighting, or partial publication.

## Fidelity boundary

The result is complete only as a Level-1 interface equilibrium solution for the exact authorized uncorrelated static-gravity carrier loads. It does not resolve individual A-arm chassis joints, welded tubes, rocker bearings, damper static force, internal upright/hub/brake/drive components, structural stress, maneuver cases, as-built correlation, setup selection, or FEA release.
