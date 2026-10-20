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

## Prescribed-torque rigid versus elastic steering evaluator

`pssd_steering.compliance_bridge.evaluate_prescribed_torque_sweep` composes
`evaluate_circular_spans` with existing `staged_transmission` and
`MOD-STEER-0001`'s `solve_sweep`; it does not modify either rigid solver.

For every explicitly supplied steering-wheel angle and signed *input-shaft*
torque, the adapter computes:

- rigid pinion angle/rack displacement at the requested driver angle;
- input-referenced elastic twist of the selected spans;
- effective input angle `driver_angle - elastic_twist`;
- compliant pinion/rack state and both left/right rigid closure solutions;
- available projected wheel headings and differences; if the wheel-heading
  basis is missing or the intended branch fails, the comparison is unavailable.

Example: the following deliberately uses the synthetic benchmark's 0.010 m/rad
rack map, **not** a claimed WUFR-27 as-built rack specification:

```python
from pathlib import Path
from pssd_steering import load_geometry
from pssd_steering.compliance import wufr27_provisional_circular_spans
from pssd_steering.compliance_bridge import (
    SteeringTransmission, PrescribedTorqueInput, evaluate_prescribed_torque_sweep,
)
root = Path.cwd()
geo = load_geometry(root / "benchmarks/steering/GEO-STEER-BASIC-001.toml")
transmission = SteeringTransmission(
    pinion_angle_per_input_rad=1.0,
    rack_m_per_pinion_rad=0.010,
    authority="BENCH-STEER synthetic transmission; not physical calibration",
)
cases = (
    PrescribedTorqueInput(0.0, 0.0, "synthetic zero torque"),
    PrescribedTorqueInput(0.5, 23.69800619, "WUFR-26 workbook unfactored parked torque"),
    PrescribedTorqueInput(0.5, 35.54700928, "WUFR-26 workbook factored parked torque"),
)
out = evaluate_prescribed_torque_sweep(
    geo, cases, transmission, spans=wufr27_provisional_circular_spans()
)
for row in out:
    print(row.case.input_torque_nm, row.elastic_twist.twist_deg,
          row.rigid_transmission.rack_displacement,
          row.elastic_transmission.rack_displacement,
          row.left.incremental_heading_difference_rad)
```

### Evidence boundaries and review gates

- This is a prescribed-force *post-processing what-if*. The driver-angle
  trajectory and torque trajectory must originate from explicit load cases.
  No tire aligning-moment constitutive relation is available in this adapter,
  so no closed-loop self-aligning moment or vehicle operating-point convergence
  is claimed.
- Nominal 1:1 bevel gearing does not automatically verify the sign convention,
  mechanical efficiency, or load distribution. The default four-span compliance
  assumes equal torque and reports that assumption explicitly.
- The existing WUFR-26 force workbook has 35.54700928 N m **factored**
  and 23.69800619 N m **unfactored** parked values. Neither is measured
  steering-wheel torque.
- Projected tire headings depend on a supplied wheel-forward reference; if
  missing, the adapter reports unavailable and does not construct a surrogate.
- Rigid out-of-domain, root, singularity or branch failures propagate intact.
  No clipping, reverse-fit substitution, or interpolation hides a failure.
- Elastic twist is **not** the same as dead-band/free play. Double-D fitting,
  bevel tooth clearance, rack backlash and hysteresis must be quantified
  independently, and double-D torsional compliance is not included yet.
- Road-wheel-angle response is preliminary pending a reviewed rack
  displacement-per-pinion-radian mapping and physical system-level correlation.

Focused tests:
`python -m unittest discover -s tests -p 'test_steering_compliance*.py'`.
