# Native rod/endcap pose and conditional gravity map

MOD-VEH-0014 / BENCH-VEH-0027 / AUTH-SUSP-0021.
Run `PYTHONPATH=src python scripts/run_rod_gravity_map.py`.

## Scope and source ownership

Map the two front pullrod tubes, two rear pushrod tubes and eight owner-confirmed
fixed turnbuckle endcaps. Exactly twelve unique COM instances are included, each
with unchanged mass/CG. Rod-end bearings, jam nuts, bolts and spacers remain
excluded. Front tube identities are SU-70109; rear are SU-70209. Preserve source
part labels even where a drawing title or thread label differs; no substitution
with later redesign parts is made. The existing 52-part arm map is unchanged.

Each rod connects the native arm attachment A(qL) and rocker rod point B(qL).
The existing actuation provider owns those poses and branch selection. Front A
belongs to the upper arm; rear A belongs to the lower arm. Implicit constant rod
length gives theta'=[(B-A) dot A']/[(B-A) dot B_theta]. Endpoint derivatives follow
native hinges and compatible upper-arm closure. Reject denominators below 1e-10
m^2, closure failure and source CGs outside the segment or farther than 1e-4 m
from its nominal line. Rear axle-local geometry is translated explicitly to the
whole-source frame before comparison to COM CGs.

## Explicit axial-spin convention

Two endpoints do not define material rotation about the rod axis. Do not claim
they determine full rod angular velocity or rotational inertia. Decompose each
nominal source CG as A0+f*(B0-A0)+o, with o perpendicular to the nominal unit axis
u0. Preserve the source offset instead of projecting it away. At current unit
direction u, choose the shortest rotation R(u0,u), giving
r=A+f*(B-A)+R o. This is a declared no-axial-spin gauge, not source-measured spin.

`pssd_suspension.rod_pose.transport_rod_offset` implements R and its analytic
derivative: with v=u0 cross u and c=u0 dot u, R o=o+v cross o+
v cross (v cross o)/(1+c). Differentiate that expression using u'. Validate finite
three-vectors, unit u0/u and tangent u' within 1e-10; reject 1+c<1e-8 rather than
selecting an arbitrary antiparallel axis. No automatic normalization or clipping.

Any alternative axial spin can change this CG by at most 2|o|. Hence the pose-wise
total gravitational-potential difference is bounded by sum(2 m g |o|). This run's
bound is 7.632997e-5 J; maximum radial source offset is 1.681454e-5 m. This is NOT
a bound on generalized torque, rate, inertia or trajectory error: those require
spin/rate information or an additional approximation. Gravity results remain
conditional on the stated gauge. Full native static-equilibrium authority is not
granted by the small energy bound.

## Generalized gravity and bookkeeping

Use coordinates [h,p,qFL,qFR,qRL,qRR] in [m,rad,rad,rad,rad,rad], +x forward,
+y left, +z up and front-up pitch about -y. Apply common body heave/pitch about
the reconstructed CAD dry CG, then compute Vg=sum(m g z) and Qg=-dVg/dq from
analytic CG derivatives. Fixture bounds are |p|<=0.1, |qL|<=0.06 rad and finite
inputs. These are numerical verification bounds, not physical travel limits.

Rod/endcap mass is 0.61325688424 kg. Combined with 52 arm parts, 64 unique source
instances total 3.23048485914 kg. Subtract their exact mass and first moments from
the 203.73055939313 kg dry CAD inventory. The remaining aggregate is unallocated,
not a rigid sprung-body lump. No mass is added atop the previous whole-car model.
The independent 27.851 lb CAD/scale discrepancy remains open.

## Verification and downstream boundary

Eight study checks cover the exact twelve-member manifest, nominal CG preservation
within 1e-12 m, native rod length and rigid distances to both endpoints within
1e-9 m, analytic gravity versus independent energy differences within 1e-5 N/Nm
at steps 0.001/0.0005, disjoint 64-part inventory and mass/first moments within
1e-12 kg/kg m. Nominal and finite mixed body/arm states are retained in results.
Four independent primitive tests check a known rotation/derivative, general
direction finite differences and norm invariance, nominal identity and rejection.

Update the front audit: the two pullrod tubes now have source-supported owners,
leaving four adjacent nuts as candidates. No joint clamping ownership is inferred.
Next resolve rod-end endpoints, clamping stacks and an explicit centered-ball
static-gravity model if used. Full rod rotational inertia and housing tensor signs
remain separate dynamic-source tasks. Compose a matching no-driver gravity/spring/
ARB/contact equilibrium only after those allocations are explicit.
