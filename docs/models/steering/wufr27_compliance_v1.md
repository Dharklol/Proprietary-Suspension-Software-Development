# WUFR-27 steering compliance: bounded initial implementation

**Status:** preliminary engineering screen. Not a final structural release, a
validated vehicle simulation, or a replacement for the rigid steering model.

## Source and inputs

- WUFR-27 Steering PDR and user-supplied 2026-10-20 CAD dimensions.
- Steering force calculation evidence in
  `docs/models/steering/wufr26_force_compliance_evidence.md`.
- Common provisional steel shear modulus: 80 GPa.
- Circular steel column tubes: OD 0.750 in, ID 0.625 in, free lengths
  upper 4.878 in and lower 6.600 in.
- Shaft circular sections: OD 0.590 in, free lengths upper 0.787 in and
  lower 2.753 in.
- D joint: nominal 0.590 in major diameter, 0.472 in across flats, 0.375 in
  engagement. Profile torsion, bearing contact and interfacial stiffness not
  evaluated in this initial implementation.
- Existing factored parked steering column torque: 35.54700928 N m;
  corresponding unfactored column torque: 23.69800619 N m.
- Existing KHK miter gear pair is nominally 1:1, but torque propagation through
  the actual system must be explicitly reviewed for gear efficiency and bearing
  reaction loads.

## Core interface

```python
from pssd_steering.compliance import (
    evaluate_circular_spans, wufr27_provisional_circular_spans,
    DoubleDProfile, ToleranceEnvelope, ClevisPinScreen,
)

spans = wufr27_provisional_circular_spans()
result = evaluate_circular_spans(spans, 35.54700928)
print(result.twist_deg, result.stiffness_nm_per_deg)
profile = DoubleDProfile()
print(profile.flat_depth_in, profile.flat_chord_in)
print(ToleranceEnvelope(.472, .005, .005).clearance_range_in)
print(ClevisPinScreen().allowable_shear_force_n())
```

All values use explicitly named units. The torque multipliers are one in the
provisional fixture and may be overridden only with reviewed torque propagation.
The model is intentionally standalone and does not affect existing rigid
steering geometry, tire requests or readiness assertions.

## Manufacturing tolerance decision

The available in-house process holds approximately +/-0.005 in on an
across-flats feature. Independent identical nominal dimensions on male and female
parts could produce a relative mismatch ranging from -0.010 in (interference)
to +0.010 in (clearance). This is a dimensional envelope, **not** an exact
rotational backlash prediction. The female bore is consequently recommended
for wire EDM with a drawing-level fit tolerance and inspection of actual
mating components. Any angular backlash estimate requires a complete planar
contact-envelope calculation and actual measured fit.

## Axial pin screen

McMaster 90378A114: 18-8 stainless clevis, diameter 0.121--0.123 in,
two shear planes. Min-diameter double-shear calculation assumes a 205 MPa
yield and factor of safety three. Actual certified pin yield, transverse pin
bending span, individual loaded wall bearing, edge/net section, actual axial
load and cotter hardware require verification. Gear thrust must not be treated
as equivalent to clevis-pin force without demonstrating the physical axial
load path.

## Required downstream adapter (next PR)

1. Add an opt-in *load-case adapter* from reviewed steering torque and the
   calculated input-referenced elastic twist into a rigid steering evaluator.
2. Define precise reference angles: input wheel angle, bevel input, bevel
   output, and pinion angle. Avoid applying a stiffness correction twice.
3. Keep free play and hysteresis as separate bounded/nonlinear contributions.
4. Add paired rigid-vs-compliant sweeps and tests that at zero torque both
   return identical angles; maintain tire-state readiness and provenance.
5. Only solve steering/tire coupled equilibrium with actual aligning-moment
   data; tire lateral peak-slip summaries alone are not a tire aligning-moment
   prediction.

Run tests: `python -m unittest tests.test_steering_compliance`.

## Release blockers

Confirm steel grades/heat treatment; validate double-D torsional rigidity,
welds and pin bore geometry; acquire an EDM fit specification and measured
backlash; validate experimental load/deflection data. No final joint strength
or steering-wheel feeling claim is made.
