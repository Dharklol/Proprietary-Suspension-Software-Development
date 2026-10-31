# Varying-state native steering evidence consumer

## Scope

This is an evidence-only composition of MOD-STEER-0001/0002, MOD-VEH-0002/0009,
the AUTH-TIRE-0002/0003 signed table kernel and owner-accepted ASM-VEH-0009.
It uses AUTH-VEH-0012's uncorrelated native exports from PR 109. It introduces
no component force law, vehicle equilibrium, optimization objective, root-choice
policy, candidate ranking or installed/setup/predictive authority.

The separate review gate for a varying-state *optimizer target* consumer remains.
This reader reconstructs the source baseline and reports signed all-root evidence
with role `evidence_only`, weight zero and target publication disabled.

## Per-state replay

Each packet is re-exported against current providers and must match in full.
Every sample then supplies its own unresolved front pose, actual rack position,
body-to-heading bridge, current CG, motion and tire operating points. The source
baseline is wrapped for the existing `apply_pose_state` evaluator; MOD-STEER-0001
closes each posed tie rod once at the actual rack displacement. No candidate
search or alternate steering closure implementation is added.

The nominal source wheel center and plane are transported through the unresolved
pose and solved steering rotation, then through the explicit axle/body/heading
mapping. The replay must recover the original native center, road heading and
inclination. Current center coordinates relative to current CG feed the existing
planar wheel-velocity/slip provider. Signed inclination is measured from the full
road-frame plane, using contact-frame-left normal orientation.

Forward tire replay must recover the original signed force within 1e-6 N and
retain the same source branch signature. Geometric replay limits are 1e-10 m
for centers and 1e-10 for direction/inclination comparisons. No nominal camber,
common center, common pose or series-wide tire point is substituted. Zero
curvature does not force alignment-related tire force to zero.

## Signed inverse evidence

The existing signed piecewise-linear inverse returns every root over the common
supported slip domain. No named branch selector is supplied. For negative IA,
the accepted reflection maps requested physical force to opposite source force,
uses positive source IA, and maps every source slip root back with opposite sign.
Load and pressure are unchanged. Nonnegative IA uses the measured table directly.
Source candidate order, classifications, contributing segments and provenance
remain intact; reflected physical roots therefore need not be ascending.

Every physical root is mapped to a required heading through the existing
`required_wheel_heading_rad` provider. The observed source-equilibrium root is
identified only as a reconstruction check, with 1e-9 rad tolerance. All other
roots remain reported. This does not choose a design root or imply stability.
Alternative root headings are conditional on the current operating point and
wheel-center velocity; they are not asserted to be mechanically achievable,
road-compatible or alternative vehicle equilibria.

No extrapolation, abs(Fy) conversion, hidden bias removal or new symmetry rule
at zero IA is permitted. Source inverse failures propagate without repair.
The direct/reflected zero-IA boundary is retained from the packet; there is no
new continuation across the known artificial source-bias seam.

## Failure and authority behavior

One failed sample stays in its original series position with its input packet,
source failure code/message, and any completed posed/closure/wheel diagnostics.
Other samples remain visible. Completion requires all samples to pass. Duplicate
IDs, mixed source revisions and role/weight promotion remain rejected by the
packet/series contracts. The old fixed-pose/fixed-tire target consumer is unchanged.

## Verification

Six tests cover native straight/left/right replay with changing centers, poses,
loads and IA; exact current-CG velocity placement; nonzero signed straight-state
forces; retention of two real reflected tire roots; source failure retention;
frozen-pose substitution; out-of-domain/no-root failure and authority gates.

The report runner verifies all eight explicit native benchmark fixtures and
sixteen front-wheel replays. Verification controls remain V=8 m/s, four 68.9 kPa
gauge pressures, discrete front/rear ARB setting 1 and the source spring reference.
They are not user setup defaults. Saved native coordinates are seeds only; exact
input source hashes are checked and each case is re-solved/re-exported first.
Round-trip force/heading/center errors measure software self-consistency, not
physical tire or vehicle accuracy.

The compact report is
`benchmarks/steering/varying_state_native_evidence_summary_v0.1.0.json`.
CI regenerates and uploads full packets, posed evaluator diagnostics, forward
queries and signed inverse evidence. A separate exact source-state test uses
Fz=222 N, IA=-2 degrees and P=82.7 kPa to demonstrate two reflected roots;
no alternate root is silently removed.

Next is an explicitly reviewed policy for using this conditional evidence in
steering target construction. Any changed steering candidate that alters tire
geometry/contact or forces also needs compatible vehicle re-equilibration; this
baseline replay does not authorize freezing an old equilibrium for ranking.
