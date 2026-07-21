# WUFR-26 Steering Level F Measurement Protocol

**Status:** Proposed for review  
**Model:** `MOD-STEER-0001`  
**Related benchmark:** `BENCH-STEER-0001`  
**Purpose:** Separate rigid kinematic error from installed backlash, compliance, hysteresis, setup, and fabrication effects.

## Validation boundary

The frozen Level E result establishes nominal design-source consistency. Level F must use physical evidence and must not reuse the historical polynomial residual envelope as its acceptance tolerance.

The physical system includes effects excluded from the rigid model:

- rack housing, rack bushings, and rack mounting compliance;
- rack-and-pinion or other gear-mesh backlash;
- steering-column shaft torsion, bearing clearance, and joint compliance;
- rod-end radial/axial play and tie-rod axial compliance;
- quick-release interface backlash;
- upright, steering arm, chassis, wheel bearing, wheel, and measurement-fixture compliance;
- friction, preload, temperature, tire scrub, and direction-history effects.

## Required setup record

Before testing, record:

- vehicle revision, date, operator, and test location;
- installed rack, pinion, tie rods, rod ends, steering-column joints, quick release, uprights, wheels, and relevant revisions;
- static toe and camber on both sides;
- ride height, tire pressure, wheel/tire or rigid-fixture state, and whether the car is supported or loaded;
- rack-center definition and physical left/right stop definitions;
- all sensor IDs, calibration records, resolution, repeatability, and mounting photographs;
- ambient temperature and any known preload or adjustment state.

The nominal CAD setup uses `-1.00 deg` side-local toe-out convention input and `-2.25 deg` camber per side from the WUFR-26 setup sheet. The physical test must measure the actual installed values rather than assume them.

## Measurement channels

Minimum channels:

1. signed steering-wheel angle;
2. signed pinion or lower-column angle, where accessible;
3. signed rack displacement relative to a measured center;
4. left projected road-wheel heading;
5. right projected road-wheel heading.

Recommended additional channels:

- applied steering-wheel torque;
- tie-rod axial force or a controlled wheel/steering-arm load;
- left/right toe or wheel-heading fixture deflection;
- chassis/rack-mount displacement relative to a stable reference.

Projected wheel heading should be measured from a rigid wheel-plane reference or fixture and reduced to the road-plane intersection angle. Tire sidewall features are not an acceptable precision datum.

## Test sequence

### A. Zero-load rigid-response sweep

Use at least the following rack positions on each side of center:

```text
0, 10%, 25%, 50%, 75%, 90%, and 100% of the measured installed travel
```

At every point:

- approach once from decreasing rack displacement;
- approach once from increasing rack displacement;
- hold long enough to record a stable mean;
- repeat the full cycle at least three times.

Record both the nominal command and the measured settled rack position. Do not treat steering-wheel angle as rack displacement unless the installed transmission has been measured.

### B. Reversal and deadband test

At center and at representative mid-travel positions:

1. apply a small positive steering input;
2. reverse slowly through zero torque/input;
3. continue until rack motion begins;
4. continue until each wheel-heading channel responds;
5. repeat in the opposite direction.

Report separate deadbands for:

- steering wheel to pinion/lower column;
- pinion to rack;
- rack to each road wheel.

This separation prevents quick-release or column backlash from being incorrectly attributed to the rack/tie-rod mechanism.

### C. Compliance test

At center and at one representative left and right steer state, apply controlled positive and negative steering torque or wheel/steering-arm load without intentionally changing the commanded kinematic state.

Report:

- steering-wheel angle per applied torque;
- rack displacement per applied torque;
- left/right wheel-heading change per applied torque;
- tie-rod or rack-mount deflection where measured;
- linearized compliance slope only over the range where the response is approximately linear.

Do not combine deadband and elastic slope into a single stiffness number.

### D. Stop and center verification

Measure:

- physical left stop rack position;
- physical right stop rack position;
- midpoint of those stops;
- setup-defined center if different;
- steering-wheel and pinion angles at each stop and center;
- whether stop contact occurs in the rack, upright, steering arm, tire, column, or another component.

The nominal design study uses `+/-1.00 in` rack motion. This is not accepted as installed stop authority until measured.

## Required reductions

For each side and each approach direction, calculate:

- total toe-inclusive projected heading;
- incremental projected heading relative to the measured centered state;
- local road-wheel gain with respect to measured rack displacement;
- candidate-minus-measurement residual on the measured rack grid;
- repeatability standard deviation or range;
- approach-direction hysteresis;
- reversal deadband;
- left/right asymmetry after accounting for setup differences;
- maximum, mean, and RMS residuals over the measured domain;
- measurement uncertainty and confidence statement.

Report the less-steered and more-steered wheels by turn direction rather than assuming a fixed left/right role.

## Component attribution matrix

| Observed discrepancy | Primary checks |
|---|---|
| Steering wheel moves before pinion | Quick release, upper column, splines, joints, bearings |
| Pinion moves before rack | Gear mesh, rack preload, rack bushings |
| Rack moves before wheel heading | Rod ends, tie rods, steering arms, upright/wheel-bearing compliance |
| Direction-dependent offset | Backlash, friction, preload, rod-end clearance, fixture slip |
| Load-dependent smooth slope | Elastic compliance |
| Fixed left/right difference | Setup, fabrication asymmetry, rack centering, unequal tie-rod adjustment |
| Increasing full-travel residual | Geometry, signal scaling, stop definition, or nonlinear compliance |

## Acceptance-rule development

A Level F pass/fail tolerance may be frozen only after:

- sensor and fixture uncertainty is quantified;
- at least three repeated bidirectional sweeps are available;
- deadband and elastic compliance are separated from kinematic residual;
- the engineering use case is stated, such as hardpoint selection, steering-ratio prediction, or driver-control design;
- the tolerance is justified independently of the observed Level E or Level F residuals.

Until then, physical results remain descriptive and the rigid model remains a nominal kinematic evaluator.

## Data package

The immutable validation package should contain:

- raw time-series files;
- processed point table;
- calibration files;
- photographs and fixture drawings;
- setup sheet and measured setup values;
- code commit and configuration ID;
- analysis report with uncertainty budget;
- source hashes and a clear separation between calibration, identification, and validation data.
