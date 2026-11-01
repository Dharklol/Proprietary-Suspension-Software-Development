# Manufactured heave/pitch half-car verification v0.1.0

## Source, scope and authorization

Owner continuation, 2026-10-31, authorizes manufactured half-car development after
the verified quarter-car layer. MOD-VEH-0011 / AUTH-VEH-0014 implement Guiggiani
(2022), chapter 10, printed pp. 440–443, equations 10.2–10.8, with zero inerters.
The source was inspected before implementation. Derive scalar forces below;
do not infer matrix signs from OCR. This is a separately represented longitudinal
system, with explicit total sprung mass/inertia and axle unsprung masses/rates.
There is no automatic doubling/halving of quarter-car or vehicle parameters.
No migration of a legacy calculator or native WUFR parameter authority is claimed.

## Definitions and equations (EQ-VEH-0030/0031)

State order is z [m], theta [rad], uf [m], ur [m], followed by their velocities.
All coordinates are perturbations about an explicitly assumed static balance;
vertical up is positive and positive theta raises the front attachment.
Front/rear attachment heights are z+a*theta and z-b*theta, a,b>0 [m].
Extension ef=z+a*theta-uf, er=z-b*theta-ur. Positive force acts upward on the body:
Ff=-kf*ef-cf*efd, Fr=-kr*er-cr*erd. Road samples provide rf,rr and derivatives.
Incremental normal forces dNf=ktf*(rf-uf), dNr=ktr*(rr-ur).

ms*zdd=Ff+Fr; Jy*thetadd=a*Ff-b*Fr;
muf*ufdd=dNf-Ff; mur*urdd=dNr-Fr.
Static normal loads Nf0=ms*g*b/(a+b)+muf*g and
Nr0=ms*g*a/(a+b)+mur*g assume only weight and suspension support, no aero or
external moment. Guards use N0+dN>0. Gravity is not added again to perturbation
accelerations. Unknown static gas/friction is not modeled as measured zero.

E=(ms*zd²+Jy*thetad²+muf*ufd²+mur*urd²+kf*ef²+kr*er²+
ktf*(uf-rf)²+ktr*(ur-rr)²)/2.
Loss power=cf*efd²+cr*erd²; road power=dNf*rfd+dNr*rrd.
Integrate dissipated energy D and road work W with the same RK4 stages as the
physical state; report E+D-W-E0. No repaired energy or clipped loads.

## Contracts and numerics

Masses, inertia, distances, rates, gravity, and separate compression/extension
bounds must be finite and positive; damping finite and nonnegative. Require
source/configuration and separate road identities. Fixed-step RK4 uses an explicit
finite positive dt and integer steps 1..1000000; no adaptive accuracy claim.
Initial and all stage/output states, road samples, forces and energies must be
finite. Stop on sampled contact loss or travel violation with code, stage time,
and retained accepted history. This is not continuous event location. No tire
nonlinearity, gas/friction, bump stops, roll, steering, aero, or structural loads.
All fixtures are manufactured, not measured, with numerical tolerances below.

## Verification (BENCH-VEH-0024)

1. Zero equilibrium: all states remain zero exactly.
2. Symmetric ms=2, Jy=2, a=b=1 and each axle mu=1,k=2,kt=3.
   Heave has identical end quarter-car equations ms_end=1; pitch has equal and
   opposite quarter-car equations. Initialize the independent hand modes with
   eigenvalues 1 and 6 and verify exact cosine states, max error <1e-9 at
   dt=.0025 s over 10 s. Pure heave must retain theta=0; pure pitch z=0.
3. Asymmetric masses, inertia and lengths: independent force/moment identities
   and finite-difference energy derivative must close to 1e-8 in corresponding SI
   units. This catches front/rear sign and lever-arm errors independently of RK4.
4. Independent front/rear smooth road bumps: two dt values .002/.001 s over 4 s;
   energy residual <1e-8 J; maximum matching physical state difference <1e-7
   in corresponding SI units. Road work and dissipation reported explicitly.
5. Symmetric damped free decay: energy nonincreasing to tolerance 1e-13 J;
   energy residual <1e-10 J at dt=.0025 s, 10 s.
6. Malformed input, initial and later stage contact/travel/nonfinite failures:
   explicit failures retain accepted history; no silent clipping.

## Review/disposition

Scalar balances follow virtual work at front/rear attachments and differentiate
the stated energy. Symmetric limiting cases reduce algebraically to previously
verified quarter-car balances; exact cosine references are independent of both
integrators. Accepted with restrictions for manufactured verification only.
Native inertia, equilibrium linearization and KW digitization remain separate
dependencies. This packet is the bounded implementation/review record for the
owner-authorized continuation, not installed or physical validation.
