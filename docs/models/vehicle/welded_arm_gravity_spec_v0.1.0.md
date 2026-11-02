# Source-supported welded-arm ownership and gravity

MOD-VEH-0013 / BENCH-VEH-0026 / AUTH-SUSP-0021.
Reproduce with `PYTHONPATH=src python scripts/run_welded_arm_gravity.py`.

## Ownership evidence

Six welding-jig assembly drawings establish rigid ownership for exact SU-70xxx
baseline part identities. Their Box IDs and part lists are retained in
`data_catalog/wufr26_welded_arm_ownership_evidence_v0.json`. No later SU-30xxx
redesign is substituted. Fixture assembly weights include tooling and are never
used as vehicle masses; the original COM instance masses/CGs govern.

| Arm on each side | Parts sharing its motion | Evidence Box file |
|---|---|---|
| Front upper | SU-70103/05/06 housing/tubes | 2212894192309 |
| Front lower | SU-70104/07/08 housing/tubes | 2212884754818 |
| Rear upper | SU-70203/05/06 housing/tubes | 2212897983602 |
| Rear lower | SU-70204/07/08 housing/tubes | 2212895802675 |
| Front upper attachments | SU-70110 tabs, SU-70111 connector | 2212895915302 |
| Rear lower attachments | SU-70210 tabs, SU-70211 connector | 2212894105772 |

The six drawings resolve 36 instances: sixteen tubes, eight housings, eight tabs
and four connectors. The owner subsequently confirmed fixed endcap-to-tube
attachment. Sixteen SU-70112 endcaps now extend the arm gravity manifest to 52
instances; eight turnbuckle endcaps have confirmed rod ownership with rod pose
binding still separate. The explicit row/leg manifest is in
`data_catalog/wufr26_endcap_attachment_confirmation_v0.json`. Rear upper jig BOM agrees with the separate rear-corner assembly,
but its contact note incorrectly names front SU-70105/6 tubes. Preserve that
conflict and use the corroborated BOM identities; do not silently rewrite source.

Extracted text was read directly. Both advertised raw PDF download tools returned
tool-not-found errors, so no visual weld-symbol/callout inspection is claimed.
Ownership is source-supported design architecture, not an as-built inspection.

## Gravity mapping

Coordinates [h,p,qFL,qFR,qRL,qRR] have units [m,rad,rad,rad,rad,rad]. World vertical
is +z and positive pitch rotates about -y. CG reference is the reconstructed dry
whole-car CAD CG. Native axle-local rear geometry is translated by the explicitly
declared rear axle x station from the whole-vehicle placement record; do not apply
that translation twice to the already whole-source COM CGs.

Rotate each source CG about its owned arm hinge. Upper angle/derivative follows
native kingpin closure; lower angle is the corner qL. Apply common body pitch and
heave: r_world=CGdry+h ez+R(p)(r_arm-CGdry). Sum Vg=m g z with g=9.81 m/s^2.
Generalized gravity is -dVg/dq, using analytic hinge/chassis Jacobians. In particular
Qh=-sum(m)g. Full centroidal tensors and bearing product signs are not needed for
this gravity calculation; no new dynamic inertia authority is implied.

The 52-instance arm source mass is 2.6172279749 kg. Rod endcap membership is
recorded separately and is not added to this arm gravity subset. Subtract their exact masses and
first moments from the 203.73055939313 kg CAD dry total. The remaining aggregate
is an unallocated inventory, not a rigid body to be added to the dynamics. Its
CG only demonstrates bookkeeping closure; it grants no sprung/unsprung ownership.

## Acceptance

Ten study checks require exact source-evidence part matching, 52 unique arm rows and eight confirmed rod endcaps,
unchanged COM mass/CG, eight complete arm owner groups (eight parts for each front
upper/rear lower arm, five for the other arms), reference tube CG line distances
<1e-4 m, gravity-energy derivative agreement <1e-5 in matching SI force units,
vertical weight within 1e-12 N and mass/first-moment subtraction closure within
1e-12 kg/kg m. Independent energy differences use h=0.001/0.0005 in each coordinate
at nominal and finite mixed states. Numerical bounds |p|<=0.1, |qL|<=0.06 rad are
fixture limits, not physical clearance or installed travel limits.

Update BENCH-SUSP-0041's front audit so the six front tabs/connectors are no longer
uncertain candidates. That report now has twenty-two source-supported owners, six
candidates, sixteen joint components and seventy-two unresolved hardware instances,
in addition to eight previously verified nominal tubes. No new tensor binding is
claimed for these source-supported parts.

## Remaining source questions

The owner confirmed both SU-70112 arm endcaps and the pullrod/pushrod turnbuckle
endcaps are fixed to their respective tubes. Arm row/leg assignments additionally
pass the same reference-line geometry gate as the tubes. No new attachment question
is pending for those caps. Rod pose/gravity binding remains to be implemented.
Clamping-stack ownership of bolts/washers/spacers and rod-end endpoint assignment
remain unresolved. Whole-part assembly membership alone is insufficient.

For gravity, inner-ball intrinsic rotation is irrelevant if its CG lies at the
joint center; an explicit centered-ball approximation could therefore unblock
static mapping without a full inertia split. It must be declared and justified,
not silently promoted from the whole-part CAD export. Dynamic inertia still needs
appropriate body/ball rotational treatment. The housing tensor signs and separate
27.851 lb scale gap remain independent issues; neither is solved by these jigs.

Full vehicle static equilibrium remains unpassed. Continue source resolution or
explicit bounded static approximations before composing native generalized gravity
with spring/ARB/road forces. Do not return to isolated force tests as a substitute.
