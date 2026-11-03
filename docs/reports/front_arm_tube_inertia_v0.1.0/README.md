# Bilateral front wishbone tube inertia

Reproduce: `PYTHONPATH=src python scripts/run_front_arm_tube_inertia.py`.
All eight source tube instances pass the predeclared gates. This is an offline
nominal local contribution, not full-arm or full-vehicle transient authority.

The snapshot binds COM SU!B90:P97 to front upper/lower fore/aft tube instances,
left and right. Every row's positive-products conversion independently passes
physical tensor checks, slender-axis projection and source CG geometry checks.
CG line distances are 0.0112–0.0162 mm. The prior owner-confirmed axes and explicit
product-sign policy are retained; no blanket policy is applied to other parts.

The upper-arm angular derivative comes from implicit kingpin-length closure.
Independent native ±qL solves check it and each transported tube CG at two steps.
The common coordinates are [body heave, front-up pitch, left qL, right qL], with
units [m,rad,rad,rad]. Direct summed 3D member kinetic energy matches the assembled
quadratic form, and the reflected left/right matrix agrees exactly in this fixture.
Full source records, Jacobians, checks, matrix and hashes are in results.json.

The tube subset mass is 0.815559 kg, compared with 2.298806 kg for the 5.068 lb
front-corner CAD assembly: 35.48% mass coverage. The uncovered 64.52% includes
other corner parts; neither percentage is a dynamic effective-mass fraction.
The body-heave diagonal is the represented tube mass, while angular diagonal
and off-diagonal entries retain the appropriate mixed coordinate units.

This increment does not alter the half-car solver or replace its diagonal masses.
No tube contribution is added on top of an existing body/corner lump, which would
double-count mass. It must eventually replace the corresponding bookkeeping rows.
The no-driver body CG is only a coordinate reference; the full body kinetic energy
is not included in this matrix.

## Next boundary

Complete the rigid-member ownership map before adding bearings, housings,
endcaps, rod ends, fasteners or pullrods. A part attached to an arm can share its
transform; hardware on opposite sides of a joint cannot be grouped by assembly
name alone. Then cover rear members and the remaining moving bodies.
Nonzero-state studies must rotate centroidal tensors and use q-dependent
Jacobians; transient use also needs convective inertia terms and energy checks.
The native matrix is not yet a valid replacement for the diagonal HalfCar model.
Mass inventory and force-source uncertainties remain separate limitations.
Drive remains unchanged. No new owner input is required for this checkpoint.
