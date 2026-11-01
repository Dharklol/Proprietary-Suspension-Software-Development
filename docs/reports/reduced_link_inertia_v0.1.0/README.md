# Local moving-link inertia verification

Reproduce: `PYTHONPATH=src python scripts/run_reduced_link_inertia.py`.

Seven manufactured tests pass: exact rod energy/cross coupling, point mass,
hinge parallel-axis inertia and derivative refinement, orthonormal frame change,
multiple-member energy addition, rank deficiency, and invalid input/tensor/
identity/member-manifest rejection. The matrix retains translation/rotation and
coordinate cross terms; it is not a scalar sprung/unsprung fraction.

For a uniform 3 kg rod with one endpoint fixed, endpoint effective mass is 1 kg,
not 1.5 kg. Its two-endpoint local mass matrix is [[1,.5],[.5,1]] kg. Equal endpoint
motion recovers the full 3 kg. These exact integral references verify the local
kinetic-energy formula independently of implementation.

A single source-linked front-left lower fore tube diagnostic uses COM SU!B96:P96
and the native lower-arm hinge. CG derivative error ratio is 4.000002 and fine
relative error is 4.17e-8. Body heave/pitch and arm-angle cross terms are retained.
This represents one tube at nominal qL=0, not a complete arm/corner model.

**Native binding gate remains false.** As-entered off-diagonal entries fail
physical inertia realizability; negating entries as CAD products passes. Both
outcomes are archived and no interpretation is selected automatically. The
owner-confirmed axis convention does not determine CAD product signs. Previous
diagonal-Lyy pitch bookkeeping is unaffected by this off-diagonal question.

`verification_passed` and script exit success cover manufactured verification,
CG derivative reproduction and accepted-variant energy identities. They do not
mean `native_binding_gate_passed`; that flag remains false under the predeclared
rule. No gate was relaxed. Full matrices, source identities, errors and hashes
are in results.json. No native HalfCar masses or trajectories are replaced.

Next: establish CAD product-of-inertia sign semantics and a complete rigid-member
ownership/pose manifest, then assemble state-dependent native inertia. The
constant diagonal-mass half-car engine needs a separate generalized-coordinate
formulation before these cross terms can enter its transient calculations.
