# Synchronized-state composition v0.1.0

This increment composes supplied results; it does not predict maneuver equilibrium
or establish physical WUFR authority. All numerical physics remains in existing
providers. Source stamps are explicit upstream assertions, not independent evidence
that records were measured together.

## Interfaces

- `pssd_vehicle.synced_state.StateSourceStamp` identifies configuration, state,
  sample, synchronization revision, canonical frame, and component source path,
  revision, authority, and fidelity. Component revisions need not be identical.
- `compose_synced_state_sample` preserves the supplied vehicle, zero-steer pose,
  and planar motion objects, validating shared keys, pose identity, body speed,
  and turn direction. Units are SI except existing wheel inclination/pressure
  fields, which retain the established degree/kPa contract.
- `SyncedStateSweep` requires at least three samples on the exact declared rack
  grid with unique rack positions and sample IDs. It preserves input order and
  rejects mixed configuration/state/revision, role, weight, or vehicle authority.
  Pose and tire points may vary in the exchange layer.
- `signed_runtime_readiness` calls the existing complete-cell signed tire inverse
  with explicitly selected source tire, convention, and optional branch. It retains
  multiple roots and structured provider failures. Multiple roots are not silently
  selected. Unit conversion does not clip or snap to a source knot; strict provider
  domain checks remain authoritative even at a floating-point boundary.
- `magnitude_branch_readiness` separately calls the exact-point magnitude provider.
  It distinguishes missing input, unavailable exact branch, and infeasible force
  demand. This deliberately labelled magnitude query does not validate signed force.
- `pssd_steering.optimization.synced_state_targets.build_synced_sweep_target_set`
  calls the existing motion-aware target builder. It requires an explicit
  design-input role and positive weight, matching rack grid, one unchanged pose,
  constant inside/outside tire operating points at turning samples, and
  turn-consistent signed front demands. The normalization scale is explicit.

## Center and consumer boundaries

The existing consumer preserves the declared centered-rack alignment with straight
motion and zero front demands; this is not a claimed successful zero-force tire
inverse. Ordinary readiness calls retain the actual tire-provider outcome at center.
The first consumer cannot represent sample-varying poses or tire points. Such
sweeps remain valid exchange records but target construction rejects them, rather
than freezing their values. Evidence/report-only states cannot gain objective weights.

No target is published when any sample fails. The exchange and tire-readiness layers
do not authorize a design target merely because all inputs are present or invertible.
Source tire/intended tire, branches, and provider provenance remain on the retained
provider result and downstream target records.

## Verification

Synthetic fixtures verify exact agreement with the existing motion-target builder,
source-object preservation, deterministic composition, grid order and duplicate
rejection, mixed-source rejection, missing-input reasons, bounded tire-domain
failure, retained multiple signed roots, exact branch feasibility, evidence-role
rejection, force-sign rejection, and refusal to freeze varying poses/tire points.

These fixtures have software-verification authority only. Existing WUFR maneuver
states remain blocked by the evidence review; no load allocation, camber, pressure,
body motion, target weight, or tire extrapolation is invented here. Static physical
correlation and separate authorization still gate a predictive maneuver-QSS producer.
