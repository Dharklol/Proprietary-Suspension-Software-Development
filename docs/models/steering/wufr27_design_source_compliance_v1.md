# WUFR-27 nominal steering transmission and elastic projection comparison

**Status:** WUFR-27 **design-source** steering prediction, not an installed
vehicle model or production-release requirement. Adds no new rigid geometry,
frozen tire input or physical-calibration authority.

## Why this is now source-backed rather than synthetic

Previous PR #111 exercised the rigid/compliant steering bridge against the
synthetic steering benchmark's arbitrary `0.010 m/rad` transmission and
synthetic wheel geometry. That is useful for solver testing but not sufficient
for steering FDR angle comparisons.

The selected nominal WUFR-27 design inherits the reviewed
`WUFR26_DESIGN_NOMINAL_V0` assembly hardpoints. The inherited
`[input_transmission]` specification records the recovered
`STEERING ACKERMAN CALC` SolidWorks design equation
`rack ratio = 3.5 / 360` inch/degree, the design-study 1:1 steering/pinion
input interpretation, and positive input to canonical `+y` rack motion.

Source identity:
- `PAR-STEER-0001` = WUFR-26 design-study mapping
- `WUFR26_DESIGN_NOMINAL_V0` = canonical nominal mechanism and centered alignment
- `WUFR27_STEERING_BASELINE_V0` = exact numerical inheritance for current design work
- `docs/models/steering/wufr26_level_e_preparation.md` = Level E projected-heading evidence
- `docs/conventions/steering_canonical_definitions.md` = frame and signed-angle conventions
- `docs/models/steering/wufr26_force_compliance_evidence.md` = workbook torque classification

The design-source relation is

```text
pinion input = +1 * design-study input (nominal rigid study only)
rack travel  = (3.5 in/rev)(0.0254 m/in)/(2 pi rad/rev) * input rad
             = 0.014148874440869498 m/rad * input rad
positive input -> +y canonical rack translation
```

The source adapter loads the exact source files, validates their identity,
mapping consistency and sign, and refuses unexpected input configurations.
It **does not** declare actual steering-wheel/bevel shaft signs or installed
3.5-in/rev rack pinion calibration verified.

## Correct canonical wheel-heading projection

For each rack solution, `wufr27_design_compliance` reuses
`reference_from_static_alignment` and `projected_wheel_heading` to rotate
the **wheel-plane normal** with the existing rigid steering-axis/upright solver,
then intersect with the road plane. This preserves the nominal static
`-1 deg` side-local toe-out setting, left canonical heading `-1 deg`,
right canonical heading `+1 deg`, and `-2.25 deg` nominal camber.

This is the exact projection method used in WUFR-26 Level E. It is *not*
the provisional plain wheel-forward-vector heading method and not the
legacy SolidWorks `Dimension2` included-angle monitor.

## Opt-in usage

```python
from pathlib import Path
from math import radians, degrees
from pssd_steering.compliance import wufr27_provisional_circular_spans
from pssd_steering.compliance_bridge import PrescribedTorqueInput
from pssd_steering.wufr27_design_compliance import (
    load_wufr27_design_source, evaluate_wufr27_design_source_sweep,
)

source = load_wufr27_design_source(Path.cwd())
rows = evaluate_wufr27_design_source_sweep(
    source,
    (PrescribedTorqueInput(radians(45), 23.69800619,
       "calculated unfactored parked structural case; not measured torque"),),
    spans=wufr27_provisional_circular_spans(),
)
for row in rows:
    print(row.comparison.elastic_twist.twist_deg)
    print(degrees(row.left.rigid_incremental_rad))
    print(degrees(row.left.loaded_incremental_rad))
```

Reproducible JSON:
`python scripts/run_wufr27_design_compliance_benchmarks.py`.
The script reports commanded input, factored/unfactored/cornering **calculated**
torque-case magnitudes, rigid and elastic rack travel, and both sides' total
and incremental projected wheel heading, with validation disposition.

## Engineering limits and next gate

- No published values here are measured input/driver torque. The workbook's
  `Steering Column Forces!C9/C10/C15` are calculated structural moments,
  and assigning resisting torque sign by steering direction is an illustrative
  choice, not a tire self-aligning model.
- Four free-span circular sections, provisional `G=80 GPa` and equal torque
  in upper/lower sections are an incomplete *component* stiffness model;
  the D sections, welds, quick release, gearbox, rack and other
  compliance are not yet modeled or verified.
- Elastic twist is subtracted from the driver's commanded angle before
  applying the nominal source input/rack conversion. It is not counted as free
  play, deadband, gear lash or loss of tire force.
- The 1:1 design study and the nominal KHK 1:1 miter pair **do not**
  separately verify the installed angular sign conventions and the
  physical transmission from steering wheel to rack.
- The reviewed nominal rack domain is +/-25.4 mm, which is NOT the
  installed usable-travel or stop dimension; the rigid evaluator still
  returns explicit domain failures and does not clip inputs.
- No tire moment, torque generated by tire, or tire/steering equilibrium
  is computed.
- No installed-geometry physical Level F claim is made. The static
  toe/camber values belong to the inherited design-source configuration.
- Physical upgrade requires slow, bidirectional measured primary-shaft
  angle vs rack-displacement sweeps plus installed center/stops and steering
  wheel-to-primary-shaft sign/zero, then loaded/unloaded angular deflection
  and backlash measurement. The already present rack linear pot and planned
  shaft rotary pot are the proposed measurement route.
- Keep current WUFR design-source output distinct from physical calibration
  datasets and as-built vehicle result naming.

Focused tests:
`python -m unittest discover -s tests -p 'test_wufr27_design_compliance*.py'`

Once the physical transmission relationship is measured and a reviewed
parameter selected, a future, separately authorized *installed* transmission
profile may be supplied through the existing provider-neutral
`SteeringTransmission` interface. This PR must not silently activate
`PAR-STEER-0001` as an installed observation.
