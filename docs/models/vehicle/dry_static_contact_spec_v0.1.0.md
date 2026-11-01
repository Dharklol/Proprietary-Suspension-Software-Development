# CAD no-driver/no-fuel static and contact composition boundary

MOD-VEH-0012 / BENCH-VEH-0025 / AUTH-SUSP-0021.
Run `PYTHONPATH=src python scripts/run_dry_static_contact_audit.py`.

This source audit reconciles the represented CAD inventory and global vertical
balance, then rebases the existing steering-closed ideal-circle geometry to the
CAD dry CG. It does not claim a complete suspension equilibrium or a native ride
model. The report's `passed` applies to audit checks;
`full_native_static_equilibrium_passed` remains false.

## Exact mass ledger

Reconstruct the unchanged 2469-row COM snapshot, remove the explicitly identified
12 lb liquid-fuel row, and retain all 2468 other instances exactly once. Add the
15.842 lb electrical approximation at the reconstructed dry CG, with zero intrinsic
inertia as previously accepted. The electrical row is an additional approximate
point, not another CAD instance. CAD mass/CG and centroidal entries are unchanged.

Separate verified front tube rows SU90:97 from the remaining mixed assemblies
before summarizing. Categories are inventory labels, not rigid ownership or
sprung/unsprung fractions. No f=0.5 allocation is selected. Require unique row keys,
mass closure and first-moment closure within 1e-9 in kg and kg m; tube mass agrees
within 1e-12 kg. The dry result is 449.149 lb / 203.73055939313 kg.

The distinct no-driver/no-fuel scale result is 477 lb, leaving 27.851 lb unexplained.
Do not scale CAD masses, add fictitious ballast or use the driver-equivalent tilt
height as the dry CG. CAD CG [-0.843894575576,0.006753688991,0.293533760117] m is a
reconstruction, not same-session measured dry-CG authority.

## Global reaction family

`pssd_vehicle.static_balance.reaction_family` solves vertical weight, pitch and
roll balance on symmetric left/right two-axle supports. Inputs are positive mass,
gravity, half tracks, ordered axle x stations and finite 3D CG. The front axle
load is W*(xCG-xRear)/(xFront-xRear). Rear load is the complement.

Choose front-left reaction lambda; front-right is Ffront-lambda. Rear left/right
sum to Frear and differ by [W*yCG-yFront*(2*lambda-Ffront)]/yRear. Intersect the
nonnegative-reaction inequalities to return the admissible lambda interval and
its endpoint reactions. Reject unsupported CGs instead of clipping. Unique corner
loads occur only if that interval collapses (1e-12 N numerical threshold); otherwise
do not pick a crossweight or equal split. This family is necessary global balance,
not proof any endpoint satisfies spring/ARB/geometry equilibrium.

Use nominal ideal-circle contact support positions from this audit, not approximate
axle stations, for the reported family and independent force/first-moment closure.
Require bilateral nominal support symmetry/flatness within 1e-12 m and closure
within 1e-9 N/Nm. Four unit tests cover a hand solution, offset CG, invalid/outside
support geometry and a uniquely supported vertex.

## Existing wheel/contact provider reuse

Load the unchanged MOD-VEH-0006 provider. Call `evaluate_corner_point_state` for
source-frame physical wheel centers and plane normals. Front plane orientation
uses MOD-STEER-0001 centered-rack closure; rear uses the toe-link-closed upright.
Do not substitute front minimum-twist orientation alone, infer rear source origin
from wheelbase, or transport the historical contact point as material geometry.

The provider also returns a driver-referenced body point. Discard it. This audit
never uses the provider's driver CG, driver BodyPose, gravity allocation, equilibrium
solve or road reaction. Construct a separately labelled CAD-dry frame explicitly:
center_world=CGdry+h ez+R(-ey,p)*(center_source-CGdry). Rotate plane normals by the
same R, then call the existing ideal zero-width-circle contact geometry against
the upward world road normal. World/source origins agree at zero body motion.
No shared source file or original driver provider is modified.

Each of four corners is checked at [wheel-body-z,h,p]=[0,0,0],
[0.002,0.003,0.02],[-0.002,-0.002,-0.02], units m/m/rad. Wheel-coordinate centered
differences at 0.0002/0.0001 m give dgap/dwheel and dqL/dwheel; their ratio maps
to the arm coordinate used by the inertia studies. Reject |dqL/dwheel|<1e-6 rad/m.
The two dgap/dqL estimates must agree within 1e-4 m/rad. Heave and pitch differences
at 0.0001 check unit heave sensitivity within 1e-10 and rigid-contact pitch virtual
work within 1e-7 m/rad. Front steering residuals must be <1e-8 m.

These are sampled geometry/virtual-work checks, not a tire force law, contact
compliance, transient event handling or continuous travel validation.

## Remaining full-composition gates

Whole-car balance does not require knowing how each part moves. Generalized
gravity and transient inertia do. Resolve remaining mixed-member ownership or
introduce an explicit bounded approximation before assembling their mass/gravity
contributions. A body/wheel/member decomposition must preserve total mass and
first moments and remove represented members from replaced lumps.

Then solve the no-driver spring/ARB/gravity/road-compatible static state and check
independent physical wrench closure. Do not reuse the driver/no-fuel static source
by relabelling it. A tire law/compliance and compatible dynamic mass inventory are
additional gates before native ride integration. Existing KW uncertainty is not
resolved by this audit. No new operational/UI or physical-correlation milestone
is introduced.
