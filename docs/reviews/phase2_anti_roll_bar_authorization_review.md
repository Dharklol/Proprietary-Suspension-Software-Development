# Phase 2 Anti-Roll-Bar Authorization Review

**Authorization:** `AUTH-SUSP-0005`  
**Model:** `MOD-SUSP-0005`  
**PR:** #49  
**Status:** reviewer inspection required before merge

## Proposed authorization

Authorize only the first bounded conservative anti-roll-bar prototype contract:

- `EQ-SUSP-0016` — source-defined bilateral elastic deformation coordinate/vector and Jacobian;
- `EQ-SUSP-0017` — conservative stored energy, conjugate elastic action, and tangent stiffness/matrix;
- `EQ-SUSP-0018` — signed generalized ARB force from virtual work;
- `ASM-SUSP-0003` — WUFR-27 Z-bar carryover and zero-preload design-intent boundary;
- `BENCH-SUSP-0011` — analytical common/differential synthetic benchmark;
- `BENCH-SUSP-0012` — WUFR geometry/source/stiffness-authority boundary benchmark.

No ARB implementation is included in PR #49.

## Key architecture decision

The ARB is not represented as an independent spring at each wheel and is not governed by an `ARB wheel rate` scalar.

The sequence is:

`(left state, right state, geometry) -> s_ARB, J_s`

`s_ARB -> U_ARB, a_ARB, K_ARB`

`Q_ARB = -J_s^T a_ARB`

This is compatible with a Z-bar containing one or several elastic blade coordinates and preserves the left/right coupling through the mechanism Jacobian.

## WUFR evidence accepted now

The source packet freezes:

- reviewer direction to carry the 2025 Z-bar/blade design basis into WUFR-27;
- zero intentional ARB preload;
- populated WUFR-26 suspension and front/rear ARB geometry/drawings as carryover design-intent evidence;
- current front/rear blade material and linkage identities;
- raw exporter ARB sketch points with an explicit no-connectivity-inference warning;
- 2025 ARB Stiffness SolidWorks Simulation lineage;
- WUFR-26 active/suppressed ARB assembly-state evidence;
- current WUFR-27 A0303/A0305 identical-file placeholder condition.

## Deliberately unavailable: numeric WUFR ARB stiffness

The audit did not recover a traceable force-deflection/torque-angle result with the necessary FEA/test boundary conditions and deformation definition.

Three tempting substitutes are explicitly rejected:

1. `Weight_transfer_sensitivity.m` values `2560` front and `2270` rear — exploratory/historical, with `%change and figure out` on the front assignment;
2. spec-sheet `Suspension Roll rate` values `556 Nm/deg` front and `458 Nm/deg` rear — whole-suspension values, not ARB-only constitutive evidence;
3. blade material/drawing dimensions — insufficient without an explicitly reviewed beam/FEA/test model and mechanism mapping.

This means PR #50 can implement generic/synthetic ARB mechanics and a WUFR geometry/reference adapter, but WUFR force/energy must return `missing_stiffness_authority` until the stiffness gap is closed.

## Zero preload

Zero preload is a named setup/reference statement, not permission for hidden offset correction. The source-specific bilateral mechanism must reconstruct the nominal state consistently before `s_ARB=0` is accepted as its zero-energy reference.

## Configuration boundary

The current WUFR-26 `FSA` assembly has the front ARB active and the rear top-level ARB suppressed. The authorization records that state but does not generalize it into a WUFR-27 design rule.

A later vehicle configuration must state front/rear ARB enablement explicitly. An explicit no-bar mode returns zero energy/action/generalized force with provenance; it is not modeled as a present bar with zero stiffness.

## Benchmarks before implementation merge

`BENCH-SUSP-0011` requires the synthetic differential mechanism to demonstrate:

- equal common-mode movement -> zero differential ARB energy/action;
- equal-and-opposite movement -> nonzero energy and equal/opposite reactions;
- exact sign preservation;
- generalized-force agreement with finite differences of energy;
- explicit preload/reference behavior;
- explicit no-bar behavior;
- missing/domain failures without extrapolation.

`BENCH-SUSP-0012` requires source-boundary tests to make unsupported WUFR stiffness impossible to use silently.

## Explicitly excluded

Damper force, spring-force duplication, tire force, vehicle equilibrium/load transfer, contact-mode switching, linkage/member/bearing reactions, blade stress/fatigue/FEA release, friction/backlash, installed limits, packaging, installed/as-built validation, and production optimization.

## Reviewer decision requested

Merge approval authorizes **implementation of the bounded coupled mechanics**, not WUFR numeric ARB force. Numeric WUFR force remains separately gated on constitutive evidence.