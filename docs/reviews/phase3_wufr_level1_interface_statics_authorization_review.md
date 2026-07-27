# Phase 3 WUFR Level-1 interface statics authorization review

## Decision

Authorize implementation of `MOD-SUSP-0007` under `AUTH-SUSP-0012` after this review is merged.

The reviewer decision on 2026-07-27 resolves the principal hold from `AUTH-SUSP-0011`: WUFR27 keeps the WUFR26 suspension load paths, geometry, and hardware, source-backed connection inference is acceptable, and the first target is Level-1 interface reactions.

## Source recovery result

The physical WUFR26 drawings support a coherent first-order ideal-joint map:

- front/rear corner assemblies use two HAB spherical bearings per corner at the upper/lower outboard bearing housings;
- front tie rods are carbon-tube links with one RH and one LH QA1 rod end per link;
- rear toe links and rear pushrods are adjustable rod-end links;
- front pullrods are adjustable rod-end links;
- after accounting for the push/pull and toe-link adjuster pairs, the remaining corner BOM rod-end count is consistent with four fore/aft A-arm chassis pivots per corner;
- rocker bearing packages support a separate one-axis revolute rocker body later.

The endpoint mapping is deliberately recorded as a **reviewed inference**. The previous rule against claiming that aggregate BOM counts self-identify every endpoint remains valid.

## Chosen Level-1 architecture

The first current-car solver contains only:

`outboard carrier/upright + rigid UCA + rigid LCA`.

Interfaces:

- UCA/LCA outboard: spherical, 3 force unknowns each;
- UCA/LCA inboard: equivalent revolute supports on the exact fore/aft hinge lines, 5 reaction unknowns each;
- front tie rod / rear toe link: one signed axial unknown;
- front pullrod / rear pushrod: one signed axial unknown at the actual arm-mounted pickup.

This gives exactly

`5 + 5 + 3 + 3 + 1 + 1 = 18`

unknowns for `3 x 6 = 18` rigid-body equilibrium equations.

That is preferable to introducing a stiffness-based forward/aft load split merely to recover individual chassis-joint forces. At Level 1 the net hinge wrench is the authoritative output.

## External-load boundary

The first graph consumes one **complete external wrench on the outboard-carrier boundary**. This avoids prematurely inventing brake-caliper, rotor, hub, bearing, or halfshaft reactions while still allowing correct net suspension-interface equilibrium.

An incomplete contact-patch/braking/drive description must fail closed. Internal upright/brake/drive decomposition is a later model.

## Numerical policy

The new solver inherits the conservative policy established for `MOD-SUSP-0006`:

- explicit physical geometry;
- exact square system;
- per-body moment scaling;
- direct pivoted solve;
- finite/full-rank/conditioning gates;
- independent physical residual reconstruction;
- signed compression/tension retained;
- no pseudoinverse, least-squares, minimum norm, regularization, stiffness weighting, clipping, or geometry repair.

`BENCH-SUSP-0021` freezes a full-rank synthetic 18x18 fixture with an exact nontrivial signed reaction vector. `BENCH-SUSP-0022` freezes WUFR application-point ownership. `BENCH-SUSP-0023` freezes invariance and failure behavior.

## Deliberate stopping boundary

This authorization does **not** yet solve the rocker. The v0.1 graph stops at push/pull-rod axial force.

That is intentional: spring and ARB providers already own their constitutive mechanics, but the structural rocker solve needs physical force vectors at their actual rocker interfaces. In particular, the existing Z-bar path currently provides deformation/generalized rocker or wheel forces; a separate reviewed mapping is needed before those quantities are treated as the physical ARB-link force vector for rocker pivot equilibrium.

The clean next stage after `MOD-SUSP-0007` implementation is therefore rocker-interface propagation, not higher-fidelity A-arm stress.

## Review outcome

`AUTH-SUSP-0012` is technically review-ready with the following boundaries:

- WUFR27 topology carryover: resolved;
- Level-1 joint idealization: resolved for this model;
- Level-1 output fidelity: resolved;
- complete external-wrench requirement: explicit;
- individual chassis-joint/member load sharing: deferred;
- rocker/spring/ARB structural propagation: deferred;
- maneuver load generation and structural release: prohibited.
