# Local rigid-link kinetic-energy reduction v0.1.0

Owner continued analytical moving-link work on 2026-11-01 after the coupled mass
allocation study. AUTH-SUSP-0021 / MOD-SUSP-0013 authorize a provider-neutral,
manufactured verification kernel. No native inertia is inferred or installed
prediction promoted. Existing half-car equations remain unchanged.

## EQ-SUSP-0039: local mass matrix

For each distinct rigid member with mass m>0, centroidal physical inertia tensor
I_G, local CG velocity v_G=Jv*qdot and angular velocity omega=Jw*qdot:
T=0.5*m*(v_G dot v_G)+0.5*omega^T*I_G*omega.
Thus M_link=m*Jv^T*Jv+Jw^T*I_G*Jw and T=0.5*qdot^T*M_link*qdot.
Sum each physical member once. Jv and Jw have 3 rows and one column per declared
coordinate; each member must use identical coordinate order, units, configuration,
frame and state identities. I_G, v_G and omega must use that same orthonormal frame.
I_G is the physical symmetric tensor, not unsigned CAD products of inertia.
No origin tensor or parallel-axis shift is substituted for centroidal inertia.

This is the local quadratic kinetic-energy form, not a scalar sprung fraction.
For mixed translational/angular coordinates, M entries carry the corresponding
mixed units; ordinary unscaled matrix eigenvalues are not vehicle modes.
Rank-deficient matrices are allowed (unexcited coordinates); negative energy is
not. State-dependent M requires the appropriate inertial terms in a future
transient solver. The local matrix alone must not be pasted into the current
constant diagonal-mass HalfCar engine.

## Contracts

Require finite m>0, finite 3x3 physical tensor and finite matching 3xn Jacobians,
nonempty unique coordinate IDs with explicit units, member/source/configuration,
frame/state IDs and an exact member-count manifest. Reject duplicate members and
identity mismatches. Validate tensor symmetry to 1e-12 relative scale, PSD via all
principal minors, and physical realizability via PSD of (trace(I)/2)*Identity-I.
Use normalized values for these checks; zero tensor is valid for a point mass.
No symmetrizing, clipping or invented rotational inertia. Reject nonfinite matrix
or energy results. Matrix assembly uses supplied Jacobians; their geometry/state
correctness is a provider responsibility, not established by PSD.

## BENCH-SUSP-0039 references

* Point mass translating in two independent directions: diagonal m and direct
  kinetic-energy equality.
* A uniform horizontal slender rod, two independent endpoint vertical velocities:
  centroid velocity=(vA+vB)/2, angular speed=(vB-vA)/L,
  Itransverse=m*L²/12. The exact integral gives
  T=m*(vA²+vA*vB+vB²)/6. Hence M=m/6*[[2,1],[1,2]].
  With one end fixed, endpoint effective mass is m/3. With both ends moving
  together the effective mass is m. Half the rod mass misses the coupling.
  End velocities are an admissible instantaneous tangent at the horizontal pose;
  the example is not a finite-motion rod with independently imposed endpoints.
* Fixed hinge at known radius: local mass=m*r²+I_axis, independently obtained
  from the parallel-axis theorem. Compare analytic CG Jacobian with centered
  point-rotation differences at h=1e-3/5e-4 rad; require errors ratio 3.9..4.1
  and fine relative Jacobian error <1e-6.
* Rotated common orthonormal frame leaves energy and mass matrix invariant.
* Multiple members add energy; member duplication, tensor sign/shape/physicality,
  nonfinite inputs and mismatched identities fail explicitly.

Analytical matrix/energy comparisons use absolute 1e-12 tolerances in the small
manufactured fixtures. This verifies the formula independently of endpoint or
hinge provider code. It does not establish WUFR effective masses.

## Native binding gate

The current COM pitch snapshot retains Lyy only. Three-dimensional arm motion
requires each member's full centroidal tensor and a source-to-current rotation,
rigid member ownership (including its fasteners), CG transport, angular Jacobian
and all coordinate couplings. Known hinge/actuation geometry supports some CG
transport, but the snapshot does not yet establish that whole binding. Preserve
this boundary; do not replace missing Ixx/Izz/products by zero or identify an
entire corner assembly as one rigid link. Next: a source-linked member manifest
and full-tensor snapshot, then a native mass-matrix study. KW data is irrelevant
to this conservative kinetic-energy verification and stays as already supplied.

## Selected native member diagnostic (bounded extension before binding)

Read SU!B96:P96 for SU-70107-AA front-left lower fore tube: full centroidal
entries are available in the live COM source. Archive that row and use the native
lower-arm fore/aft hinge to transport its CG. Evaluate only at nominal qL=0,
with coordinates body heave, positive-front-up body pitch and native lower-arm
angle. Body origin is the middle no-driver CAD sprung CG from the prior budget.
Jv=[ez, (-ey) cross (r-CGbody), u_hinge cross (r-hinge)],
Jw=[0,-ey,u_hinge]. Check the hinge column against native point transport at the
same two h values and thresholds as the manufactured hinge test. Retain the full
3x3 matrix and cross terms. This is one tube, not an arm/corner mass provider.

Owner confirmed axes, but CAD product-of-inertia versus physical off-diagonal
sign convention was not independently frozen. Run two explicit diagnostic tensor
variants (as-entered physical entries; negated off-diagonal entries); require
both tensors physical, preserve differences, do not pick the convenient result.
Native CG/Jacobian binding remains exploratory until rigid membership, sign
convention and source pose are finalized. No zero-filled missing tensor, nonlinear
mass model, native trajectory or coupling into HalfCar is authorized here.

## Source finding / gate disposition

The declared native gate does NOT pass: as-entered entries fail physical tensor
realizability; negated off-diagonal CAD-product interpretation passes. No tolerance
or native gate was relaxed, and no interpretation is promoted automatically.
The diagnostic report distinguishes `verification_passed` (manufactured kernel,
CG derivative and accepted-variant energy identities) from
`native_binding_gate_passed` (both source interpretations physical), which remains
false. The script's process success means verification/report reproduction,
not native readiness. The physical-tensor rejection is retained verbatim.
This reopens the source convention review before a native member provider.
Axis alignment confirmation does not resolve product-of-inertia sign semantics.
The previous pitch-only audit uses diagonal Lyy, so this sign question does not
alter its diagonal parallel-axis calculation.

## Resolution superseding the initial ambiguity gate — 2026-11-01

The selected native row now has an explicitly declared positive-products policy,
reviewed in docs/reviews/com_tensor_sign_resolution_2026_11_01.md before adapter
implementation. Diagonals are preserved and off-diagonal entries negated once.
No policy is inferred by the generic adapter. The earlier two-interpretation
failure remains historical evidence, but is no longer an unresolved live variant.
Selected-member gate requires accepted declared conversion, unchanged tensor
physicality, retained raw negative-control rejection, CG reference-line distance
<5e-5 m with projection inside the leg, axial moment/trace <0.01, and all prior
CG-derivative/energy checks. It passes. Whole-suspension readiness remains open.
The conversion has an independent off-axis point-mass energy test; physical-entry
identity and unknown-policy rejection prevent accidental guessing/double-negation.
