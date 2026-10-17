# Synchronized native maneuver evidence export

AUTH-VEH-0012 / MOD-VEH-0009 development export, 2026-10-17. This combines the
native composition from PR 108 with PR 106's existing unresolved-front-pose
adapter. Neither dependency is landed by this integration branch.

`export_native_cornering` re-evaluates a successful result's exact case and
coordinates with current geometry/tire providers, and requires the stored
evaluation to match. It checks solver bounds, residual acceptance, tangent-rank
certificate and the independent 1e-6 N / 1e-6 N*m physical limits. Failed, stale,
altered or authority-promoted evidence cannot be exported.

## Atomic packet and frames

Each `NativeCorneringExport` carries one `SyncedStateSample`, its full equilibrium,
the body pose, front axle placement and native pose frame map. Source stamps share
configuration, case, sample ID and synchronization revision. Their axis marker
does not replace the explicit frame mapping: pose is in the chassis-fixed front
axle reference, while motion, current centers, tire forces and acceleration use
the horizontal heading frame about the current mass-weighted CG.

The paired front pose uses the same two contact-compatible native suspension
states as equilibrium. PR 106's adapter independently verifies minimum twist;
tie-rod steering closure and body attitude remain excluded. Close the tie rod
once at the actual rack position, place axle points using
`front_axle_origin_body_m`, then apply the packet's body rotation and heading-frame
body-origin translation. Revalidation also binds frame IDs, body attitude, motion
and all four wheel operating quantities to the equilibrium.

All wheels retain recovered normal loads, fully steered signed inclination,
explicit gauge pressure and signed lateral response. Local wheel Fx is explicitly
zero under the pure-lateral model; the virtual CG speed holder stays separate,
with force/power retained in the equilibrium. Heading-frame ax/g and ay/g come
from solved motion, including beta.

Role stays `evidence_only`, weight stays zero, original pose source authority is
retained, and tire reflection/query provenance remains in equilibrium evidence.
`NativeCorneringExportSeries` preserves caller order and changing poses, motion,
centers, operating points and demands without sorting/resampling/flattening. It
rejects duplicate sample identities and mixed revisions.

## Consumer boundary

The consumer contract is `native_steady_cornering_varying_state_evidence_v1`.
A consumer must retain the whole packet and frame bridge. The existing
`SyncedStateSweep` and fixed-pose/fixed-tire magnitude target adapter are unchanged;
they cannot freeze these states or promote them into an optimization objective.
Nonzero toe/camber force at zero curvature is preserved rather than forced into
the older centered-rack/zero-demand convention.

## Verification and reproducibility

Five tests verify atomic source/force/motion publication, a real steering API
round trip (exported pose plus one closure reconstructs current front centers),
failure/stale/tamper gates, changing-state order, legacy sweep rejection,
zero-weight authority and JSON frame/force evidence.

The runner checks every source hash of the committed native benchmark. Saved
coordinates are seeds only: cases retain benchmark controls, bind current
loader-derived revisions, and are re-solved before export. Another Python
runtime's numerical snapshot is never treated as a live solved state; no physical
control or source content changes. Each export passes current residual, rank,
domain and physical closure checks.

`scripts/run_wufr_synced_cornering_export.py` writes the full eight-packet JSON
and a summary. The summary is recorded in
`benchmarks/vehicle/wufr_synced_cornering_export_summary_v0.1.0.json`; CI regenerates
and uploads both files. Full JSON retains source/force/geometry evidence and
frame mappings without committing a duplicate large equilibrium record.

Remaining work is the varying-state steering evidence consumer, preserving
signed queries and reflection/branch boundaries. Actual user maneuver schedules,
four pressures and discrete ARB setup stay caller-specified. Installed validation,
predictive/setup authority and design ranking remain separate gates.
