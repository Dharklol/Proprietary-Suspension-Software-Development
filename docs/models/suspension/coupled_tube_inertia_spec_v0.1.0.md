# Coupled finite-pitch tube inertia fixture

MOD-SUSP-0013 / EQ-SUSP-0039 / BENCH-SUSP-0043 / AUTH-SUSP-0021.
Run `PYTHONPATH=src python scripts/run_coupled_tube_inertia.py`.

This offline fixture includes exactly the eight source-verified front arm tubes.
Coordinates are [world vertical heave h, front-up pitch p, left qL, right qL],
units [m,rad,rad,rad], with +x forward, +y left, +z up. Pitch axis b=-ey.
The reconstructed middle-case no-driver body CG is a coordinate reference only;
no body mass, housing, joint hardware, wheel, spring, gravity or damper is added.
The legacy HalfCar solver remains unchanged. No native corner mass is counted twice.

## Pose and kinematics

Let r(a) be each tube CG after native hinge rotation in the chassis frame, O the
reference CG, R(p) the finite rotation about b, and a its corner's qL. The world
position is x=O+h ez+R(p)(r-O). Upper arm angle follows native closure u(a).
Centroidal physical tensors rotate first with the arm and then with the chassis.
The existing explicit per-tube positive-products declaration is retained.

Velocity columns are ez, R[b cross (r-O)], and R r_a in the active corner column;
the other corner column is zero. Angular columns are 0, b and R(s axis), where
s=u' for upper tubes and 1 for lower tubes. Closure u'' is analytic as in
BENCH-SUSP-0042. The CG second derivative includes both u'' and (u')^2 terms.

The acceleration terms at zero generalized acceleration are

abias = R[b cross (b cross (r-O)) pdot^2
          + 2 b cross r_a pdot adot + r_aa adot^2],

alphabias = R[b cross (s axis) pdot adot + s' axis adot^2].

For each member, assemble M=m Jv^T Jv+Jw^T I Jw and generalized inertial bias
c=Jv^T m abias + Jw^T[I alphabias + omega cross (I omega)]. Thus M qddot+c=tau.
All matrix cross terms and gyroscopic terms are retained. This is a moving-tube
subsystem equation, not a complete vehicle equation.

## Independent verification and limits

Three mixed-state/rate fixtures include nominal and finite-pitch/asymmetric arm
states. Native closure failure, nonfinite input and |p|>0.1 or |qL|>0.08 rad are
rejected. These are numerical fixture bounds, not physical travel/clearance limits.

- The complete nominal matrix must match BENCH-SUSP-0040 within 1e-12 in matching
  SI coordinate units.
- Independent centered mass-matrix derivatives at 0.001/0.0005 in each coordinate
  form Christoffel bias. Fine-step absolute generalized-force error is <1e-7
  (N for heave; N m for angular coordinates).
- Power identity qdot^T c=0.5 qdot^T Mdot qdot must agree within 1e-8 W; omitting
  bias must produce >1e-5 W defect in at least one nonzero-state fixture.
- Direct member energy agrees with the quadratic form within 1e-12 J.
- Independent pose-path five-point differences (time step 0.01 s) check bias
  acceleration within 2e-6 m/s^2 and angular acceleration within 1e-7 rad/s^2.
  The wider high-order stencil avoids amplifying native closure tolerances with
  a tiny second-difference step; acceptance tolerances are unchanged.

## Bounded force-driven verification

Integrate the tube-only equation with explicit RK4, partial-pivot elimination
(reject pivots below 1e-12 in this fixed SI fixture), and an integrated work state
Wdot=tau dot qdot. Initial q=[0,0.02,0.01,-0.015], qdot=[0.02,0.03,0.04,-0.025].
Duration is 0.08 s; 2,4,8 steps resolve truncation error above the closure floor.
Two cases use zero forcing and manufactured forcing
[0.01 cos(9t),0.001 sin(7t),0.0002 cos(5t),-0.0001 sin(6t)] in [N,Nm,Nm,Nm].
These small artificial loads are not road inputs or vehicle load predictions.

All work-energy residuals must be <1e-9 J. Forced endpoint differences must shrink
by >8 between refinements. The unforced differences are already at the solver
floor, so require <1e-11 endpoint stability rather than claim convergence order.
This fixture is not a reusable production integrator or an ill-conditioned-matrix
qualification. No springs/contact/damping/stability limit is inferred from it.

## Next boundary

Before native ride integration: define a compatible whole mass inventory and
remove replaced lumps, add verified generalized elastic/dissipative/road forces,
and test combined energy, dissipation and contact/travel boundaries. Continue
remaining front/rear ownership and housing sign evidence independently. UI,
operational release, telemetry decoding and physical correlation remain deferred.
