# Front native spring deformation and force binding

MOD-SUSP-0015 / BENCH-SUSP-0045 / AUTH-SUSP-0021.
Composes MOD-SUSP-0003 actuation, MOD-SUSP-0004 spring and MOD-SUSP-0014 force ports.

`bind_front_spring_port` consumes a front corner, matching nominal wheel reference,
the reviewed linear front spring package, qL, geometry identity and source authority.
It returns a source-labelled deformation port plus the native actuation/spring
states and derivative diagnostics. Nonfinite q, absent source identity, rear or
nonlinear law, wrong attachment owner, closure failure, singular closure derivative
or unavailable spring state raises ValueError. It does not silently choose a
different actuation architecture. The historical rocker geometry is the existing
reviewed native baseline; this pass does not claim a later direct-damper redesign.

## Geometry derivative

Let U and L be current upper/lower upright joints and d=U-L. Derivatives of each
joint with respect to its own arm angle are axis cross (point-hinge). Then
u'(qL)=(d dot L')/(d dot U'). The front source attachment belongs to the upper arm,
so its derivative A_q=u' axis_U cross (A-hinge_U).

For rocker rod point P(theta), rocker axis v and pivot H, define
P_theta=v cross (P-H). Constant pullrod length gives
theta_q=[(P-A) dot A_q]/[(P-A) dot P_theta]. Reject either closure denominator
below 1e-10 m^2. For coil eye C, C_q=theta_q v cross (C-H). With chassis eye D,
L_q=(C-D) dot C_q / |C-D|. Spring compression gradient is -L_q in the active qL
column and zero in the other three columns of [heave,pitch,left qL,right qL].
Units are [m,rad,rad,rad]. Common rigid chassis translation/rotation changes neither
eye separation nor spring compression. This zero rigid-body action is required,
not a small-angle approximation. Any individual eye force still has a body action;
it cancels only with the opposite eye and the ideal linkage constraint actions.

Native actuation solves use root-angle and length residual tolerances 1e-13,
squared-residual zero tolerance 1e-20, to keep numerical closure noise below the
derivative checks. No physical source tolerance or tensor acceptance is relaxed.

## Spring reference, authority and restrictions

The unchanged reviewed front package is 36000 N/m, with x=0.1857-L. Zero
intentional preload applies at full extension. Nominal CAD L=0.164599347052 m
therefore gives x=0.021100652948 m and F=759.623506 N; do not add that nominal
compression again as preload. The spring provider's own reference and constitutive
checks supply x, energy and generalized force. No spring free-length substitution
or re-estimation is made by this adapter.

The returned port uses the same x, stiffness, gradient, zero explicit support rate
and zero damping. Source/configuration and ASM-SUSP-0002 provenance are retained,
including false installed-as-built authority. Rear nonlinear laws, KW damping,
ARB, gravity, tire contact, whole-car equilibrium and installed travel limits are
excluded. Different driver/no-driver mass configurations are not mixed.

This is a force-map diagnostic with ideal kinematic transmission. It does not
authorize a native transient system that omits the real rocker/pullrod/body/wheel
masses or their gravity loads. In particular, the roughly 760 N nominal spring
force is not balanced by the eight-tube inventory. No such free-response prediction
is introduced. A compatible complete mass/equilibrium composition remains required.

## Independent acceptance

Run `PYTHONPATH=src python scripts/run_native_spring_port.py`.
Ten states cover both front sides at qL=-0.04,-0.02,0,0.02,0.04 rad. This is a
sampled numerical envelope, not a continuous travel/clearance guarantee.

- Independent five-point compression and energy derivatives at steps 0.001 and
  0.0005 rad check the analytic gradient and force; fine errors <1e-7 m/rad and
  <1e-4 Nm respectively.
- Port force agrees with the existing spring generalized-force provider within
  1e-10 in corresponding SI force units; energy within 1e-12 J.
- Equal/opposite physical spring-eye forces, transformed with finite chassis pitch
  and arbitrary chassis/arm rates, give generalized power within 1e-10 W.
- Zero heave/pitch deformation, nominal compression within 1e-10 m and preserved
  source assumptions/false installed authority are checked explicitly.
- A prescribed qL=0.02 sin(6t) cycle over 0.4 s checks spring work=-Delta V with
  trapezoidal power quadrature at 100/200/400 steps. Finest error <1e-5 J; error
  must shrink by >3 per halving. This is not a force-driven equilibrium simulation.

Four adapter unit tests check reference/authority, energy gradient, reflection and
rejection boundaries. Existing spring/physical-vector and reduced-dynamics tests
remain required. CI archives the source-hashed report.

## Next dependency

Reconcile no-driver/no-fuel body/wheel/member masses and corresponding static
gravity/preload before composing native ride dynamics. Bind wheel-reference
vertical pose/Jacobians and tire/contact forces in the same coordinates; retain
damper uncertainty as explicit scenarios until a force law is available. Remaining
member ownership and housing product signs are source limitations, not reasons to
invent mass or mix the older driver/no-fuel static equilibrium into this model.
