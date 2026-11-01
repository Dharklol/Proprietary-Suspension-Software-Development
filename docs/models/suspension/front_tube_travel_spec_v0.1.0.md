# Fixed-chassis front tube travel metric

MOD-SUSP-0013 / EQ-SUSP-0039 / BENCH-SUSP-0042 / AUTH-SUSP-0021.
This offline verification extends the eight previously verified front tubes to
nonzero arm states. It does not modify the HalfCar solver.

Each corner has one independent coordinate q=qL (rad); chassis is fixed. Native
kingpin-length closure determines upper-arm angle u(q). Axes remain CAD +x
forward, +y left, +z up. The nominal SI physical tensors retain the explicitly
declared positive-products conversion from BENCH-SUSP-0040.

Let d=U-L, with point derivatives taken about each fixed arm hinge. Then

u'=(d dot L')/(d dot U'),

u''=-[(L' dot L' - d dot L'') - 2(U' dot L')u'
      +(U' dot U' + d dot U'')(u')^2]/(d dot U').

Reject closure failure or |d dot U'|<1e-10 m^2. Transport each CG by native hinge
rotation and its physical tensor by I(q)=R I0 R^T. Its scalar mass contribution
is m |dr/dq|^2 + omega_q^T I(q) omega_q, retaining both arms' contributions.
For each rigid arm rotating about its fixed axis, the coefficient C with respect
to its own angle is invariant. Consequently M(q)=C_lower+C_upper(u')^2 and
M'(q)=2 C_upper u' u''. No housing, joint hardware, upright, chassis or wheel
mass is included, and no existing lump is augmented with these masses.

The kinetic equation for this restricted coordinate is
tau=M(q) qddot + 0.5 M'(q) qdot^2. The second term is required for power to equal
d(0.5 M qdot^2)/dt. This is not the complete multi-coordinate vehicle equation.

## Verification envelope and thresholds

- Sample each side at qL=-0.06,-0.03,0,0.03,0.06 rad. This is a sampled numerical
  envelope, not established clearance, contact, material or as-built travel limits.
- Independent centered differences at h=0.001 and 0.0005 rad check M' and u''.
  Fine-step absolute errors must be <1e-7 kg m^2/rad and <1e-5 rad^-1 respectively.
- Independent CG position differences at h=0.0005 rad must agree within
  1e-7 m/rad. Matrix energy must match direct member energy within 1e-12 J.
- Tensor trace is invariant within 1e-12 kg m^2. A full asymmetric manufactured
  tensor rotated 90 degrees about z checks orientation/signs within 1e-12.
  The scalar hinge metric alone cannot detect every tensor rotation error.
- Reflection requires M_left(q)=M_right(-q) and opposite derivative within
  1e-12 in corresponding SI coordinate units.
- Prescribed verification motion q=0.04 sin(7t), 0<=t<=0.8 s, is integrated by
  trapezoidal power quadrature at 200,400,800 steps. Work-energy residual must
  be <1e-8 J and fall by >3 per refinement. Omitting the convective term must
  produce >10 times the finest retained residual. This is an inverse-dynamics
  verification, not a force-driven transient integrator test.

## Housing diagnostic boundary

COM SU!B100:P103 provides full centroidal entries for four housings. Both
positive-products and raw-physical interpretations pass physicality at existing
tolerances. That result cannot select the source signs. No housing is included
in the native tube metric, and candidate housing tensors are not promoted.
Housing-specific orientation/CAD export evidence or an explicitly bounded sign
sensitivity is required before those contributions can be relied upon.

## Downstream work

Generalize verified nonzero-state transport to the coupled body/arm coordinates,
derive all convective terms and verify power/energy there before introducing a
force-driven integrator. Preserve existing nominal matrix as a regression anchor.
Remaining front/rear mass inventory work proceeds independently of this kernel.
