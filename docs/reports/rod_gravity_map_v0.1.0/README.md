# Rod and fixed-endcap gravity checkpoint

Specification: `docs/models/vehicle/rod_gravity_map_spec_v0.1.0.md`.
Run `PYTHONPATH=src python scripts/run_rod_gravity_map.py`.

Four native rod tubes and eight fixed endcaps now have verified rigid endpoint
transport. Their unchanged source masses total 0.613256884 kg. The combined arm/
rod ledger is 64 unique instances / 3.230484859 kg, with exact remaining mass and
first-moment bookkeeping. Eight study checks and four primitive unit tests pass.

Native arm/rocker closure owns the endpoints. The rod CG offsets are preserved at
nominal and transported by an explicit shortest-rotation convention. Endpoint
distances remain rigid and analytic generalized gravity agrees with independent
potential differences at the sampled states. No full rod rotational inertia is
claimed. Remaining front audit candidates are four adjacent nuts; rod tubes are
now source-supported owners, making 24 source-supported parts plus eight previously
verified nominal tubes, sixteen joint components and seventy-two unresolved hardware.

The source CGs lie within 16.815 micrometres of the rod axes. Unknown axial spin
has a pose-wise potential-energy difference bound of 7.633e-5 J for the twelve
parts. This does not bound forces/rates or eliminate the explicit spin convention.
These results are conditional gravity evidence, not full native static equilibrium.

Next is joint endpoint/clamping ownership and an explicit static treatment of
joint-centered bearing/rod-end balls. The remaining unallocated inventory is not
treated as a rigid body. Source work remains the priority over further isolated
force fixtures or UI/release development; scale mass and tensor-sign issues remain
separate. No new owner information is required for the completed rod/endcap map.
