# Synchronized vehicle-state producer: initial scope

Status: proposed contract; no maneuver physics or WUFR design-input authority is granted by this document.

## Purpose

Produce one source-traceable package whose wheel loads, tire operating points,
suspension pose, and planar motion describe the same configuration and operating
state. Reuse `VehicleOperatingState`, the tire bridge, suspension-pose providers,
and planar kinematics. Keep the education frontend a consumer of production code.

## First implementation boundary

Begin with a provider-neutral composition/readiness layer over explicitly supplied
upstream results. This layer does not solve maneuver equilibrium. Require shared
configuration, state, source revision, frame, units, and sample identity across the
four-wheel state, suspension pose, and motion schedule. Reject mismatched identities
atomically rather than joining records by proximity or silently copying a nominal
state. Preserve underlying authority, assumptions, fidelity, and missing reasons.

For a steering target, check the required front inside/outside normal loads,
inclination, gauge pressure, lateral-force demand, suspension-pose identity, and
planar u/v/r at every steering sample. An explicit positive target weight is
required for design-input states; report/evidence states retain zero weight.
Use existing tire-runtime domain checks for complete-cell queries and the exact
branch adapter rules for named-branch inversions. These are different readiness
gates and must not be conflated. Missing or out-of-domain inputs produce a report
with reasons and no design target.

## Verification plan

- Accept a complete synthetic synchronized package, clearly labelled synthetic.
- Reject cross-configuration, cross-state, frame, and sample mismatches.
- Preserve missing inclination, pressure, demand, pose, or motion without defaults.
- Reject tire-domain violations without clipping or extrapolation.
- Retain source tire versus intended tire identities and upstream provenance.
- Preserve evidence-only zero weights and require explicit design-input weights.
- Verify deterministic output and unchanged downstream provider results.

## Current evidence blocker

`phase4_r25b_steering_target_input_readiness_review.md` establishes that the two
existing 1.2 g Suspension Calculations states supply no synchronized inclination,
pressure, lateral demand, pose, or u/v/r schedule. Some wheel loads also exceed
the authorized R25B domain. They cannot serve as valid integrated target fixtures.
The Lesson 2 exact R25B operating point is a teaching tire query, not an integrated
vehicle maneuver state.

A reviewed simulation/measurement export or separately authorized engineering
schedule can unblock the composition layer's WUFR target demonstration. An actual
maneuver equilibrium producer needs a separate source audit, function specification,
and authorization. `post_rigid_contact_program_v0.1.0.md` additionally gates
integrated maneuver QSS on static physical correlation. Do not invent force
allocation, LLTD, camber, tire pressure, sideslip, yaw rate, or target weights to
bypass either gate.

## Next action

Review the contract against the existing pose and planar-motion APIs, then implement
the source-preserving composition/readiness layer with synthetic fixtures. Keep
WUFR target publication blocked until the required synchronized evidence exists.
