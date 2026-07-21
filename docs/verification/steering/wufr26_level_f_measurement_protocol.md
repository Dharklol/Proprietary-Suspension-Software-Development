# WUFR-26 Steering Level F Measurement Protocol

**Status:** Proposed for review; adapted to available equipment and existing evidence  
**Model:** `MOD-STEER-0001`  
**Related benchmark:** `BENCH-STEER-0001`  
**Purpose:** Separate rigid kinematic error from installed backlash, compliance, hysteresis, setup, and fabrication effects.

## Validation boundary

The frozen Level E result establishes nominal design-source consistency. Level F must use physical evidence and must not reuse the historical polynomial residual envelope as its acceptance tolerance.

The physical system includes effects excluded from the rigid model:

- rack housing, rack bushings, and rack mounting compliance;
- rack-and-pinion and bevel-gear mesh backlash;
- steering-column shaft torsion, coupling clearance, bearing clearance, and joint compliance;
- rod-end radial/axial play and tie-rod axial compliance;
- quick-release interface backlash;
- upright, steering arm, chassis, wheel bearing, wheel, tire, and measurement-fixture compliance;
- friction, preload, temperature, tire scrub, and direction-history effects.

## Existing evidence and available equipment

The physical work does not begin from zero. The existing evidence packet is `docs/models/steering/wufr26_force_compliance_evidence.md`.

Available evidence includes:

- approximately `4.0 deg` current whole-system steering-wheel free play with the front tires scrub-constrained (`PAR-STEER-0004`);
- historical `2.35 deg` free play and directional compliance points of `0.26 deg/N*m` and `0.47 deg/N*m` (`PAR-STEER-0005` and `PAR-STEER-0006`);
- calculated parked and cornering rack, column, bevel-gear, and shaft-bearing load cases from `Suspension Calculations 2026`;
- a KHK `MMSG2-20R/L` supplier gear-backlash observation retained separately from whole-system free play.

Available or planned equipment:

- installed rack linear potentiometer (`SNS-STEER-0001`);
- planned primary-shaft rotary potentiometer (`SNS-STEER-0002`);
- torque rig and digital force gauge;
- digital angle gauge;
- calipers.

The prior free-play and compliance observations do not need to be repeated merely to prove that they exist. They do need a repeatable, frozen setup before they can be promoted into a Level F acceptance dataset.

## Required setup record

Before testing, record:

- vehicle revision, date, operator, and test location;
- installed rack, pinion, tie rods, rod ends, steering-column joints, quick release, bevel gears, uprights, wheels, and relevant revisions;
- static toe and camber on both sides;
- ride height, tire pressure, surface, wheel/tire or rigid-fixture state, and whether the car is supported or loaded;
- rack-center definition and physical left/right stop definitions;
- all sensor IDs, calibration records, resolution, sample rate, logger channel, repeatability, and mounting photographs;
- ambient temperature, steering position, applied-torque threshold, and any known preload or adjustment state.

The nominal CAD setup uses `-1.00 deg` side-local toe-out convention input and `-2.25 deg` camber per side from the WUFR-26 setup sheet. The physical test must measure the actual installed values rather than assume them.

## Measurement channels

### Minimum implementable channel set

The currently achievable minimum set is:

1. signed rack displacement from `SNS-STEER-0001`;
2. signed primary-shaft angle from `SNS-STEER-0002` after installation;
3. applied steering-wheel torque from the torque rig and force gauge;
4. left and right projected wheel heading at selected settled rack positions using the digital angle gauge and a rigid wheel reference.

Before the rotary potentiometer is installed, useful manual work remains possible with rack-pot displacement plus digital-angle-gauge wheel headings. The rotary potentiometer is required to automate shaft-to-rack deadband and gain measurements.

Recommended additional channels:

- steering-wheel angle measured separately from primary-shaft angle when quick-release or upper-column attribution is required;
- chassis/rack-mount displacement relative to a stable reference;
- tie-rod axial force or a controlled wheel/steering-arm load;
- left/right toe or wheel-heading fixture deflection.

Projected wheel heading should be measured from a rigid wheel-plane reference or fixture and reduced to the road-plane intersection angle. Tire sidewall features are not an acceptable precision datum.

## Test sequence

### A. Rack-to-wheel rigid-response sweep

Use at least the following rack positions on each side of center:

```text
0, 10%, 25%, 50%, 75%, 90%, and 100% of the measured installed travel
```

At every point:

- approach once from decreasing rack displacement;
- approach once from increasing rack displacement;
- record the settled rack-pot value;
- measure left and right projected wheel heading with the digital angle gauge;
- hold long enough to record a stable mean;
- repeat the full cycle at least three times.

Record both the nominal command and the measured settled rack position. Do not treat steering-wheel or shaft angle as rack displacement unless the installed transmission has been measured.

### B. Primary-shaft-to-rack sweep

After `SNS-STEER-0002` is installed and calibrated, acquire synchronized primary-shaft angle and rack displacement during slow bidirectional sweeps.

Report:

- shaft-to-rack secant and local gain;
- center offset;
- approach-direction hysteresis;
- reversal deadband in both shaft degrees and rack millimetres;
- repeatability over at least three complete cycles.

This stage isolates the primary-shaft, bevel-box, rack-pinion, and rack-support group from rack-to-wheel effects. It does not isolate quick-release or steering-wheel-to-primary-shaft motion unless steering-wheel angle is measured separately.

### C. Reversal and deadband test

At center and at representative mid-travel positions:

1. preload the steering system in one direction;
2. reverse slowly through zero torque;
3. record the primary-shaft motion required before rack motion begins;
4. continue until each wheel-heading measurement responds;
5. repeat in the opposite direction.

Report separate deadbands where the available channels permit:

- steering wheel to primary shaft;
- primary shaft to rack;
- rack to each road wheel;
- total steering-wheel free play under the named tire-scrub condition.

The approximately `4 deg` system value is a prior whole-system observation and must not be assigned to the KHK gears or another component without these staged measurements.

### D. Compliance test

At center and at one representative left and right steer state, apply controlled positive and negative steering torque without intentionally changing the commanded kinematic state.

Make sure the free-play limit is engaged before fitting an elastic slope. Report:

- steering-wheel or primary-shaft angle per applied torque;
- rack displacement per applied torque;
- left/right wheel-heading change per applied torque;
- tie-rod or rack-mount deflection where measured;
- linearized compliance slope only over the range where the response is approximately linear;
- separate positive- and negative-direction slopes.

Do not combine deadband and elastic slope into one stiffness number. Do not average the historical `0.26` and `0.47 deg/N*m` observations without preserving their directional difference.

### E. Stop and center verification

Measure:

- physical left stop rack position;
- physical right stop rack position;
- midpoint of those stops;
- setup-defined center if different;
- steering-wheel and primary-shaft angles at each stop and center;
- whether stop contact occurs in the rack, upright, steering arm, tire, column, or another component.

The nominal design study uses `+/-1.00 in` rack motion. This is not accepted as installed stop authority until measured.

## Required reductions

For each side and each approach direction, calculate:

- total toe-inclusive projected heading;
- incremental projected heading relative to the measured centered state;
- local road-wheel gain with respect to measured rack displacement;
- primary-shaft-to-rack gain after the rotary potentiometer is installed;
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
| Steering wheel moves before primary shaft | Quick release, wheel hub, upper-column coupling |
| Primary shaft moves before rack | Bevel gears, shaft couplings, lower column, rack-pinion mesh, rack bushings |
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
- the engineering use case is stated, such as hardpoint selection, steering-ratio prediction, driver-control design, or reliability improvement;
- the tolerance is justified independently of the observed Level E or Level F residuals.

Until then, physical results remain descriptive and the rigid model remains a nominal kinematic evaluator.

## Data package

The immutable validation package should contain:

- raw rack-pot and rotary-pot time-series files;
- manually measured left/right wheel-heading point table;
- torque-rig force and lever-arm records;
- processed point table;
- calibration files;
- photographs and fixture drawings;
- setup sheet and measured setup values;
- code commit and configuration ID;
- analysis report with uncertainty budget;
- source hashes and a clear separation between calibration, identification, and validation data.
