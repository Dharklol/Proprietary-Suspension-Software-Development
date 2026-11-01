# Local moving-link inertia verification

Reproduce: `PYTHONPATH=src python scripts/run_reduced_link_inertia.py`.

Eight tests pass: exact rod energy/cross coupling, point mass, hinge parallel-axis
inertia and derivative refinement, orthonormal frame change, member accounting,
rank deficiency, invalid inputs and explicit CAD-product conversion. The new
conversion test independently integrates kinetic energy for two off-axis point
masses; the physical-entry policy is an identity to avoid double-negation.

For a uniform 3 kg rod with one endpoint fixed, endpoint effective mass is 1 kg,
not 1.5 kg. Its two-endpoint local matrix is [[1,.5],[.5,1]] kg. Equal endpoint
motion recovers the full 3 kg. Couplings are retained, not folded into fractions.

## Selected nominal tube convention resolved

COM SU!B96:P96 is explicitly declared positive-product data for this selected
member. Off-diagonal entries are negated once; diagonal moments are unchanged.
The source-specific declaration is grounded in official SOLIDWORKS selectable-
notation documentation, the MathWorks SolidWorks-to-physical-tensor example,
and independent geometry/physicality checks. See
[resolution review](../../reviews/com_tensor_sign_resolution_2026_11_01.md).

The native reference leg line is 0.41505 m long; the COM CG is 0.01564 mm from it
and projects within the segment. The converted tensor has an axial moment/trace
ratio 0.002814, consistent with a slender tube, versus 0.2856 for raw-as-physical.
Raw-as-physical also fails the unchanged physical-realizability check and remains
a rejected negative control. The accepted tensor's local CG derivative has error
ratio 4.000002 and fine relative error 4.17e-8. Direct and reduced kinetic energy
agree, and body-heave/pitch/arm-angle cross terms remain in the full matrix.

Both verification_passed and native_binding_gate_passed are now true, where the
latter is explicitly scoped to this one nominal tube diagnostic. The initial
ambiguity gate failed in the preceding revision. It was superseded through the
recorded source-convention review, not by relaxing tensor tolerances. Script exit
success now requires this selected-member gate as well as kernel verification.

The owner-confirmed axes remain unchanged. CAD product signs are separate from
axis direction; the earlier diagonal-Lyy pitch bookkeeping is unaffected. The
selected convention is not a default for every COM row or every SOLIDWORKS export.
The macro itself has not been recovered. Raw source values and both diagnostic
outcomes remain in results.json with hashes and source identities.

Next: full rigid-member ownership/pose manifest and source-checked tensors for
other members, then state-dependent native inertia composition. No complete arm,
corner or vehicle effective mass is claimed. The constant diagonal-mass half-car
engine remains unchanged; it needs a separately verified formulation for these
couplings. Drive is unchanged.
