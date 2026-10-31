# Steady-cornering development kernel verification

Date: 2026-10-10. Scope: provider-neutral synthetic kernel under AUTH-VEH-0012.
Native WUFR composition, real tire-domain completeness and physical correlation
remain unverified. The 306.17484975 kg selection remains the WUFR source choice;
the manufactured verification fixture explicitly uses synthetic masses instead.

## Implemented behavior

The separate kernel assembles three reduced body balances, four wheel balances,
two horizontal force balances and one yaw balance. It evaluates all four signed
lateral tires forward at the trial load, pressure, slip and inclination; tire
forces, normal loads, body pose, sideslip, rack and virtual holding force remain
coupled. Normal reactions enter constrained wheel balance and the independently
assembled physical wrench once, and do not enter reduced force assembly twice.

Every geometry trial carries the current body/rack coordinates, state and source
revisions, four steered contact roots/Jacobians and explicit spring forces.
Current mass points determine both lumped inertia and the exact current CG.
The virtual holder publishes its force/power and acts at that same CG.
Malformed frames, query substitution, missing source/policy/pressure, unsupported
result authority, steering ownership, source-domain failure and invalid contact
coefficients fail explicitly. No inferred study values or domain clipping occur.

The solver uses explicitly scaled bounded damped Newton iterations, preserving
provider failures from derivative and line-search probes. Reciprocal pivot ratio
is a conditioning diagnostic, not a condition-number or stability claim. Rank is
checked even at a residual-zero initial guess. Ordered curvature continuation
starts by solving an explicit zero-curvature tire state, retains failed points
and prohibits silent source-branch changes. Separate caller-selected seeds retain
multiple roots; there is no exhaustive root enumeration or uniqueness claim.

## Contact-force correction found by independent closure

A rotating circle's geometric lowest point changes material identity with pose.
Using its position derivative as the applied-force virtual displacement converged
the ten residuals but left about 1.5e-5 N*m pitch moment at synthetic curvature
0.02/m. The physical closure gate rejected that result.

The corrected contract freezes the instantaneous application material point in
the upright frame when taking virtual-work derivatives. Gap/root derivatives
still follow the geometric contact locus. Their normal derivatives agree at the
current contact, as required by implicit compatibility. The regression deliberately
mislabels the old locus derivative and verifies independent physical rejection.
No force correction, balancing wrench or tolerance relaxation was introduced.

Pacejka, *Tyre and Vehicle Dynamics*, 2nd ed., Sec. 11.3, printed pp. 535-536,
Eqs. 11.82-11.84, derives generalized forces from application-point virtual
displacements. This correction is a project mechanics derivation checked by the
synthetic fixture; it is not a source claim of WUFR accuracy.

## Verification evidence

The generated record is
`benchmarks/vehicle/steady_cornering_development_synthetic_v0.1.0.json`.
It preserves case controls, source hashes, current geometry/Jacobians, mass points,
actual tire queries, physical wrench contributions and branch/iteration history.

- 17 new tests pass: motion/inertia/holding, existing static-kernel recovery,
  fully steered contact updates, direct-plus-mapped off-CG virtual work at two
  scales, normal-reaction counting, both curvature signs, three distinct tire
  roots, failed continuation, and failure/source/authority checks.
- Eight samples pass at 8 m/s and curvature 0, +/-0.005, +/-0.01 and +/-0.02 /m.
  All study values in this record are explicitly synthetic.
- Maximum Euclidean physical force residual: 5.473e-9 N.
- Maximum Euclidean physical moment residual: 1.078e-8 N*m.
- Limits remain 1e-6 N and 1e-6 N*m.
- 23 existing static, planar and force-coordinate tests plus the registry test
  pass. Registry structural validation and whitespace checks pass.

The explicitly zero-force tire fixture recovers static equilibrium on evaluation
but has a sideslip/rack null space; the solver reports singularity. It is not
misrepresented as a unique maneuver equilibrium. A source-bounded signed tire
fixture with nonzero slopes supplies the solved zero-curvature recovery check.

CI regenerates the synthetic report and uploads it with motion-aware reports.
BENCH-VEH-0018 through BENCH-VEH-0020 remain full producer promotion gates;
this scoped synthetic evidence does not claim completed native integration.

## Remaining integration

Build the fully steered native WUFR contact/material-point provider, compose the
reviewed 306 kg mass and conservative spring/ARB providers, and connect the
selected signed tire runtime without repairing its inclination/load/pressure
domains. PR 106 remains the native pose adapter dependency. A concrete WUFR
case requires four pressures, explicit speed/curvature controls, discrete front
and rear ARB settings and a spring/perch reference. Varying-state steering target
consumption and any predictive/setup promotion remain separate review gates.
