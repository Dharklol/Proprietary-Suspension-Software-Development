# WUFR steady-cornering development producer proposal

Date: 2026-10-10. Status: accepted development specification; coupled producer
implementation and complete physics verification remain in progress. Owner requested this specification/authorization
change after selecting the driver/no-fuel reference and native pose production.
The owner accepted the assumptions and development scope on 2026-10-10;
AUTH-VEH-0012 permits development implementation. Result verification stays gated.

## Purpose and authority

Proposed `MOD-VEH-0009` produces an internally consistent, uncorrelated steady
cornering state from the native suspension, steering, conservative spring/ARB,
road-contact, mass-reference, and signed pure-lateral tire providers. It is a
development experiment, not an installed setup recommendation or production
steering ranking. Proposed authorization is `AUTH-VEH-0012`.

The selected total mass is **306.17484975 kg**, driver/no fuel, loaded from the
reviewed reference, not entered as an independent runtime constant. No 320 kg
spreadsheet load is scaled or copied. Mass/CG source ownership remains explicit.
The static AUTH-VEH-0010 result remains gravity-only and unchanged.

PR 106's native pose adapter is an implementation dependency, not an independent
validation source. Historical calculators, LLTD proxies, and simulations remain
comparison evidence. A synchronized external simulation export is not required.

## First model and proposed assumptions

Flat rigid road, four active contacts, constant speed and signed path curvature,
constant body pose in a yaw-following frame, zero tire longitudinal slip, no aero,
braking, drivetrain, dampers at nonzero velocity, or tire vertical compliance.

`ASM-VEH-0006` proposes a **uniform-acceleration inertial-load approximation**:
the reviewed sprung lump and four prototype wheel-center lumps each receive
`-m_j a_G` at their current points. Total current CG is computed from those same
points and masses. Angular-momentum-rate terms, wheel gyroscopic couples, and
local `r^2` acceleration variation between lumps are omitted. This is an explicit
new maneuver approximation; static ASM-VEH-0003 alone does not authorize it.
No inertia tensor or physical per-corner mass measurement is inferred.

`ASM-VEH-0007` proposes an optional **ideal speed-holding force** at total current
CG, tangent to its trajectory. Its scalar magnitude is solved and published.
It is an external virtual actuator, not tire Fx, engine capability, drive torque,
brake force, or a combined-slip model. Caller policy must explicitly allow it;
otherwise constant-speed cases requiring it return `speed_hold_not_authorized`.
This avoids dropping the longitudinal component of steered lateral tire forces.

`ASM-VEH-0008` proposes extending the fixed-radius, zero-width rigid circular
contact geometry into this development maneuver. It does not promote static
ASM-VEH-0005 into measured loaded-radius or maneuver tire-compliance authority.

These approximations cannot establish a quantified accuracy envelope without
additional evidence. Low speed alone does not prove omitted inertia negligible.
They must appear in every success record and be accepted separately in review.

## Inputs and frames

Every run requires explicit configuration/source revisions, all three proposed
assumption IDs, front/rear discrete ARB settings, spring/perch reference, source
and intended tire identities, **four gauge pressures**, selected signed tire
provider, and numerical bounds/scales/continuation controls. No default pressure,
ARB setting, CG, target weight, or tire-state substitution is permitted.

Maneuver controls are speed `V>0` and signed CG-path curvature `kappa` in 1/m.
Positive curvature is left turn; zero curvature is the straight limiting case.
The run supplies bounds on sideslip beta, rack displacement s, and body pose.
The selected case and pressure remain study inputs, not configuration discoveries.

Distinguish the yaw-following **horizontal heading frame H** (+x vehicle heading,
+y left, +z road normal) from the rolled/pitched body frame B and axle-local
suspension/steering frames. H shares the road-plane basis at the evaluation yaw.
The exact current total CG defines the motion origin. Wheel-center x/y coordinates
for planar velocity are expressed in H relative to that CG. Rigid transforms,
origin translations, and force directions are recorded, never assumed identical.

## Governing proposal

### EQ-VEH-0023: steady motion

For constant V, beta and kappa:

```
r = V kappa
u = V cos(beta); v = V sin(beta)
a_G^H = (-r v, r u, 0)
t_G^H = (u/V, v/V, 0)
```

Thus `a_G dot t_G = 0`, while heading-frame ax need not be zero. Use the existing
MOD-VEH-0002 wheel velocity field `(u-r*y_i, v+r*x_i)` and signed slip contract
after explicit frame/origin placement. Do not substitute speed alone for u/v/r,
derive beta from steering geometry, or confuse `u/r` with CG path radius `V/r`.

### EQ-VEH-0024: tires and speed holding

At each exact current road-contact geometry, project the steered wheel-forward
direction into the road plane and normalize it to e_xi. Set e_yi = n cross e_xi.
Derive tire inclination in that provider's signed convention from the fully
steered road-frame wheel plane, not from nominal camber or minimum twist alone.

Evaluate the existing signed tire response **forward** at each wheel's actual
alpha, recovered Fz, inclination, and explicit pressure:

```
F_tire_i = lambda_i n + Fy_i e_yi
F_hold = h t_G at current total CG
```

Use all four tires and preserve source tire versus engineering-proxy identities.
Unavailable signed inclination, complete cell, slip domain, load, or pressure
fails the case; no absolute-value sign repair, negative-camber substitution,
reflection, interpolation beyond provider authority, or extrapolation is allowed.
Rear tires require the same source-domain checks as fronts.

No force demand is allocated by front balance, load ratio, or m ay/2. Per-wheel
signed demand is the converged provider force, after global balance succeeds.
The exact magnitude-branch steering consumer is a separate downstream interface;
complete signed-runtime success does not authorize it at a new operating point.

### EQ-VEH-0025: compatible generalized forces and contact

For each trial `(q_b,beta,s,h)`, re-solve suspension/steering and road compatibility
using the fully steered wheel plane. Front tie-rod closure is applied once; rear
toe-link closure remains native. Neither a centered-rack contact map nor its
Jacobian is frozen while rack varies. Extend the contact provider explicitly
under this authorization; do not expand AUTH-VEH-0008 silently.

Map gravity, proposed inertial point loads, tire lateral contact forces, and the
CG holding force through their actual point-position Jacobians. For any point
depending on both body coordinates and wheel coordinates, retain both terms:

```
Q_red,j = J_point,b,j^T F_j + J_wb^T J_point,w,j^T F_j
R_b = Q_body_ext_direct + J_wb^T (Q_wheel_ext + Q_susp) = 0
lambda_i = -(Q_wheel_ext_i + Q_susp_i) / c_i
```

Normal reactions are constraint forces, recovered once; they are not also added
to the reduced external-force term. Tire lateral forces depend on lambda, so
reaction recovery and tire evaluation form a coupled system. Use four lambda
unknowns/residuals rather than a hidden fixed-point load substitution.

For virtual work, hold instantaneous applied-force values fixed when checking
point Jacobians. Differentiate their state dependence in the nonlinear residual
tangent. The maneuver residual need not be a conservative potential gradient;
do not reuse the static total-energy gate as its only verification.

### EQ-VEH-0026: coupled closure

Proposed primary unknowns are `(z_s,phi,theta,beta,s,h,lambda_FL,lambda_FR,
lambda_RL,lambda_RR)`. Four contact compatibility equations eliminate physical
wheel coordinates through a bounded native root solve. Solve ten residuals:
three body-coordinate balances, four constrained wheel balances, and heading-
frame horizontal force-x, force-y, and global yaw-moment balances.

Assemble all gravity, tire, holding, and proposed inertial loads independently at
their current physical points. Under ASM-VEH-0006 require the entire resultant
force and moment to close, not merely the ten solve residuals. Force residual
must be <=1e-6 N and moment <=1e-6 N*m. If reduced-coordinate closure and physical
wrench closure disagree, report failure and revise the derivation; no balancing
wrench, relaxed tolerance, or fitted load correction is allowed.

The forward signed tire surface may admit multiple equilibria. Initialize from the
gravity-only static seed, then solve the actual zero-curvature tire/holder state
before bounded positive and negative curvature continuation. Static toe or camber
thrust may require nonzero holding force and a different zero-curvature pose;
zero curvature alone does not guarantee recovery of the gravity-only solution.
retain branches and conditioning. Do not label a converged root unique or stable
without the corresponding separate evidence. No silent pre/post-peak switching.

## Outputs and synchronization

Return convergence status, V/kappa/beta/u/v/r/acceleration, q_b, rack, four native
corner/road states, poses, contact-frame inclination, pressures, signed Fy and
normal reactions, source-domain results, virtual hold force, contribution wrenches,
physical closure, conditioning, branch and continuation history, and all revisions.
Publish label `uncorrelated_design_intent_steady_cornering_with_virtual_speed_hold`
only when all gates pass and caller accepted all assumptions.

One converged maneuver is one synchronized sample. An arbitrary prescribed rack
grid is not automatically a set of equilibria at fixed V/kappa. Construct sweeps
from explicitly varied maneuver controls and retain solved rack values. PR 105's
current target consumer requires a constant pose and role operating points; varying
results must remain evidence until a separately reviewed consumer extension.
Weights remain zero/evidence-only. No structural carrier or setup authority follows.

## Verification gates before implementation promotion

BENCH-VEH-0018: independent motion/force-frame hand cases, both turn signs,
nonzero beta, zero curvature, force projection, CG placement, and virtual holding
power `P_hold=h V`. No transient prediction is claimed.

BENCH-VEH-0019: manufactured synthetic four-wheel equilibrium, off-CG point loads
checking both virtual-work terms, lateral contact action and reaction recovery,
two-scale point-Jacobian checks, independent full-wrench closure, zero-curvature
recovery of the existing static state with an explicitly zero-force synthetic tire
fixture, and positive/negative continuation. Real toe/camber-force zero-curvature
cases are solved separately rather than forced onto that fixture. Symmetry
is tested only for symmetric synthetic inputs, not forced onto asymmetric WUFR data.

BENCH-VEH-0020: missing pressures/inertial/hold/radius policies, source-domain and
frame errors, front double steering, rear source failure, negative reaction,
singularity, multiple branches, failed convergence and physical closure. No clipping
or pressure/load/IA repair. Reject unsupported design-ranking/installed authority.

Synthetic implementation verification can proceed after reviewed authorization.
A WUFR maneuver result is not promised: actual front/rear tire domains may prevent
any complete case. No pressure or maneuver values are invented to make one pass.

## Source basis and decisions remaining

Guiggiani (2022), printed pp. 76-78, Sec. 3.2.5-3.2.6, Eqs. 3.24 and 3.29-3.37:
heading-frame acceleration, speed, sideslip and curvature. Printed pp. 81-82,
Sec. 3.3, Eqs. 3.53-3.58: wheel velocity and slip. Printed pp. 93-94, Sec. 3.6,
Eqs. 3.72-3.77, and pp. 102-104, Sec. 3.8, Eqs. 3.93-3.96: force/moment balance
and the angular-momentum/gyroscopic terms omitted by the proposed approximation.
The text explicitly warns that race-car wheel gyroscopic effects may matter.

Project source: the attached Guiggiani PDF, existing AUTH-VEH-0002/0003/0010,
AUTH-TIRE-0002, native pose PR 106, and the mass/contact/spring/ARB source records.
The virtual holder and uniform-acceleration reduction are project model choices,
not textbook assertions of exact vehicle dynamics.

Review must decide whether ASM-VEH-0006/0007/0008 are acceptable for this experiment
and accept the proposed pre-correlation development exception. Before a concrete
WUFR case, select four tire pressures, V/kappa range, and setup revisions. A later
physical/predictive maneuver producer needs richer inertia, longitudinal tire/drive
and speed control, tire vertical behavior, and correlation evidence as applicable.
