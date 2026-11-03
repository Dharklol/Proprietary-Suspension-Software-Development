# Generalized deformation force ports

MOD-SUSP-0014 / EQ-SUSP-0040 / BENCH-SUSP-0044 / AUTH-SUSP-0021.

The numerical primitive in `src/pssd_suspension/generalized_forces.py` maps scalar
deformation ports to a provider-owned ordered coordinate vector. Providers must
bind coordinate order/units, geometry, configuration, state, source identity and
rates consistently before calling this leaf function; vector length alone is
not an identity check. No installed source calibration is implied by the API.

For deformation e(q,t) in m, gradient g=de/dq, stiffness k>=0 N/m, damping
c>=0 Ns/m and explicit support rate e_t in m/s:

edot=g dot qdot+e_t; effort=k e+c edot;
Q=-g effort; V=0.5 k e^2; D=c edot^2; P_support=effort e_t.

Thus Q dot qdot+Vdot=P_support-D. Summing independent ports preserves this
identity, including nonlinear geometry and moving support. The gradient has units
m per coordinate unit; the corresponding generalized forces have work-conjugate
units. Sign and preload belong to the deformation provider. Never add static
preload twice or confuse deformation rate with generalized velocity.

The primitive validates nonempty finite rates, unique/nonempty port IDs, matching
gradient dimensions, finite inputs/outputs and nonnegative stiffness/damping.
Empty port lists return zero force/energy for a valid coordinate vector.
Compression-only ports require e>0 and effort>0. Contact branch failure raises
ValueError without clipping, continuing through separation or simulating impact.
Integration checks occur at RK stages and accepted samples; no exact event-time
or between-sample contact guarantee is provided.

## Integrated verification provider

`scripts/run_generalized_force_verification.py` retains the eight front tubes,
finite-pitch kinematics and complete inertial bias of BENCH-SUSP-0043. The explicit
mass ledger maps the same source instances once; its sum and the heave mass diagonal
are 0.81555908126 kg. No other front assembly, body, wheel, rear or HalfCar mass
is included or replaced. The reconstructed body CG is a reference only.

Two artificial arm ports use e=0.2 sin(qL), k=0.3 N/m and c=0.02 Ns/m. Two
artificial support ports attach to left/right lower-fore tube CG heights:
e=0.005+r(t)-(z(q)-z_nominal), g=-dz/dq, e_t=rdot, k=0.2 N/m, c=0.03 Ns/m.
These are massless verification loads, not native coilovers, tires or wheel-ground
geometry. The 5 mm compression is artificial preload; there is no gravity or
claim of native static equilibrium. Moving support uses
r=0.0001[sin(5t+phase)-sin(phase)], phase=0/0.4 rad; the stationary case uses r=0.

Initial q=[0,0,0.002,-0.002], qdot=[0,0,0.004,-0.004], duration 0.15 s. Explicit
RK4 integrates M qddot+c_inertial=Q and work/dissipation states at 8,16,32 steps.
E=T+V must satisfy E-E0-W_support+E_diss=0 within 1e-9 J at all accepted samples.
Dissipated energy must be positive; stationary-support total energy must fall.
The moving-support work and dissipation must each exceed 100 times the maximum
balance residual, so omitting either is detectably wrong. Existing native numerical
travel bounds remain enforced; lifted-support and qL=0.081 failure controls must
raise. These controls demonstrate refusal, not physical wheel contact prediction.

Five unit tests independently check nonlinear potential gradients, moving-support
power, contact rejection (including positive compression but tensile damping),
invalid contracts and additive ports. Registry validation is required.

## Native ride integration boundary

Next bind the existing native spring/actuation displacement to a deformation and
its gradient in these same coordinates, verifying virtual work and static preload.
Require explicit damper force law/provenance rather than fitting vendor ranges.
Wheel/road ports require wheel-reference pose/velocity, tire law, normal preload,
contact model and a compatible body/upright/wheel/member inventory. Remove replaced
mass rows before adding native moving members; do not augment a full corner lump.
The current driver/no-fuel static provider cannot silently supply equilibrium for
the no-driver/no-fuel inertia configuration. Until these contracts agree, the
combined analytical fixture is verified but installed ride prediction remains open.
