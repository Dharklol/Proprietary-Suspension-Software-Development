# Steering Canonical Definitions — Proposed Review Subset

**Status:** Proposed for Phase 0 review  
**Scope:** Rigid nominal-height steering geometry and transmission  
**Authority:** Not frozen; no production model may treat these definitions as approved until the review checklist is closed

## Purpose

This document defines the smallest canonical quantity and terminology subset needed to evaluate and later optimize the rack–tie-rod–steering-arm mechanism without depending on spreadsheet cell names, CAD motion-study labels, or ambiguous steering terminology.

The first steering release is a rigid kinematic model. Tire-informed targets, steering effort, compliance, suspension travel, loads, tolerances, and transient behavior must extend these definitions rather than replace them.

## 1. Reference frames and geometric objects

### 1.1 Vehicle body frame

The project-wide body frame remains governed by `conventions_and_definitions.md`. Until that convention is frozen, every steering artifact must declare:

- frame origin;
- positive longitudinal, lateral, and vertical axes;
- handedness;
- angle rotation rule;
- whether coordinates are design, measured, unloaded, or installed values.

No steering point may be stored as three unlabeled numbers.

### 1.2 Ground or road reference plane

The road reference plane used for Ackermann and turning geometry must be identified. A nominal flat plane is acceptable for the first model, but it must not be silently substituted for a measured setup plane or a road plane estimated from sensors.

### 1.3 Point

A point record contains a coordinate vector, frame ID, configuration ID, source/evidence ID, uncertainty, and revision. Steering-arm and tie-rod endpoints are joint-center points, not visual CAD edges.

### 1.4 Axis line

The steering axis and rack axis are directed three-dimensional lines. Each requires a point, direction vector, frame, source, uncertainty, and revision. Caster and KPI are derived displays; the axis line remains canonical.

### 1.5 Reference configuration

Tie-rod length, static toe, rack center, steering-arm position, and zero angles are all defined in one named reference configuration. At minimum, that configuration states ride height, wheel travel, roll, pitch, heave, static toe, camber, rack position, driver/load state, and whether compliance loads are absent.

## 2. Canonical geometric quantities

### `QTY-GEO-0001` — wheelbase

Distance in the defined road plane between front and rear axle reference centers. The axle-center construction must be stated. Wheelbase is not inferred from a turning-radius equation.

### `QTY-GEO-0004` — front steering-axis ground-intersection track

Distance between the left and right steering-axis intersections with the selected road plane in the reference configuration. This is distinct from wheel-center track and may be the appropriate track for ideal low-speed Ackermann construction.

### Rack origin, direction, width, and inner-joint points

The rack is defined by its directed axis and by left/right inner-joint locations at rack center. Rack width is the distance between those joint centers projected or measured according to the declared spatial model. Rack longitudinal distance from the front axle is a derived coordinate statement, not a sufficient rack definition.

### Steering-arm outer-joint points

The left and right outer tie-rod joints are points fixed in their respective upright frames. Steering-arm length may be displayed, but the pickup point and steering-axis line are authoritative.

## 3. Canonical transmission quantities

### `QTY-STEER-0001` — steering-wheel angle

Angular displacement of the steering wheel from its declared zero, in radians internally. The record must define polarity, continuous unwrap behavior, and whether free play is excluded, measured, or modeled.

### `QTY-STEER-0002` — primary steering-shaft angle

Angular displacement of the primary shaft at its declared measurement/model section. This quantity is distinct from steering-wheel and pinion angles so column irregularity, backlash, and torsional compliance can later be identified.

### `QTY-STEER-0003` — pinion angle

Angular displacement of the pinion from rack-center zero. Pinion angle remains distinct even when a rigid fixed-ratio column makes it numerically proportional to steering-wheel angle.

### `QTY-STEER-0004` — rack displacement

Signed translation of the rack along its directed axis from rack center. The measurement point and sign must be explicit. Total travel, one-sided travel, and displacement from center are separate fields.

### `QTY-STEER-0005` — rack displacement per pinion angle

Local or constant transmission relation expressed canonically in metres per radian. The legacy term `C-factor` is an alias only after its exact definition is recovered. Values expressed in millimetres per revolution are display conversions of the same reviewed quantity when the rack relation is constant.

A variable-ratio rack requires a function and derivative, not one scalar C-factor.

## 4. Road-wheel angles and toe

### `QTY-STEER-0006` and `QTY-STEER-0007` — left and right road-wheel steer angles

Yaw orientation of the left or right wheel plane relative to its declared zero/reference orientation, expressed in the declared vehicle or road frame. These are stored as left/right quantities. `Inside` and `outside` are analysis-time aliases determined by turn direction.

### `QTY-ALIGN-0001` and `QTY-ALIGN-0002` — left and right static toe angles

Road-wheel steer angles at the reference configuration and rack-center condition. The project toe sign convention must be frozen before these quantities become active parameters.

### Mean road-wheel angle

`QTY-STEER-0008` is not frozen until the averaging rule is selected. Arithmetic mean, curvature-equivalent mean, and bicycle-model equivalent angle are not interchangeable.

### Equivalent single-track steer angle

`QTY-STEER-0009` is a separately derived curvature-matching quantity. It must never be labeled simply `wheel angle` or substituted for either road wheel without declaration.

## 5. Tie-rod definition

### `QTY-STEER-0012` — nominal tie-rod joint-center distance

Center-to-center distance between the specified rack inner joint and upright outer joint in the named reference configuration.

The physical tie-rod assembly record separately states:

- body or tube length;
- rod-end shank lengths;
- thread handedness;
- adjustment range;
- nominal adjustment position;
- minimum thread engagement;
- left/right equality rule;
- tolerance and uncertainty.

Tie-rod length is normally a derived output of geometry. It may also carry hard availability or adjustment bounds.

## 6. Steering ratios

### Local ratio

`QTY-STEER-0010` is a derivative-based ratio at a declared operating point. Its numerator and denominator must be named, for example steering-wheel angle per mean road-wheel angle or steering-wheel angle per left road-wheel angle.

### Secant ratio

`QTY-STEER-0011` is the finite input/output ratio over a declared interval. Zero handling and the selected road-wheel representation must be stated.

No canonical field may be named only `steering ratio`.

## 7. Ackermann reference and error

### `QTY-STEER-0013` — Ackermann reference outside-wheel angle

For a selected inside-wheel angle, wheelbase, and steering-axis ground-intersection track, this is the ideal no-slip low-speed outside-wheel angle under the declared Ackermann construction.

The reference is a benchmark and low-speed target candidate. It is not the universal performance optimum.

### `QTY-STEER-0014` — Ackermann steering error

Default proposed definition:

`actual outside road-wheel angle minus Ackermann reference outside-wheel angle`

The sign, independent variable, track definition, and turn direction must be declared. Normalized coefficients or percentages require separate named definitions and cannot replace the dimensional error.

### Ackermann coefficient

A coefficient such as Guiggiani's dynamic-toe/Ackermann coefficient may be reported only when its fitting model, range, static-toe treatment, and independent variable are declared. A single percentage extracted at full lock is not a canonical curve description.

## 8. Turning quantities

### `QTY-STEER-0015` — vehicle turning radius under kinematic assumptions

This candidate ID is not frozen until the reference path is selected. Required separate variants include radius to:

- rear axle center;
- vehicle CG;
- inside or outside front tire path;
- outside body envelope;
- competition-defined turning-circle point.

A minimum-turning requirement is usually a boundary condition, not the steering-performance objective.

## 9. Function-valued outputs

The canonical steering result is a set of versioned functions or sampled maps with valid domains:

- steering-wheel angle to pinion angle;
- pinion angle to rack displacement;
- rack displacement to left/right road-wheel angle;
- steering-wheel angle to left/right road-wheel angle;
- inside angle to outside angle for each turn direction;
- local derivatives and secant ratios;
- Ackermann reference and error versus input;
- turning-path metrics versus input.

Polynomial fits are optional derived representations. They must include fit domain, residuals, order, source map hash, and an extrapolation prohibition.

## 10. Model-layer separation

The following layers use the same core quantities but must remain separate models:

1. rigid nominal-height mechanism;
2. rigid mechanism over bump, rebound, roll, pitch, and heave;
3. tolerance and manufacturing-variation model;
4. compliant and backlash model;
5. steering-force and driver-effort model;
6. tire-informed target generator;
7. transient steering and vehicle-response model.

The first layer cannot claim conclusions belonging to later layers.

## 11. Literature alignment

The audit should use, without treating any one source as universal authority:

- Guiggiani, Section 3.4, for left/right steering functions, static toe, dynamic toe, Ackermann coefficient, and the distinction between ideal Ackermann and best steering geometry;
- Gillespie, Chapter 8, for rack/tie-rod linkage behavior, trapezoidal approximation, steering ratio variation, steering effort, and suspension-induced geometry errors;
- Pacejka and reviewed tire data for later tire slip, aligning moment, and combined-load objectives;
- reviewed mechanism and multibody references for spatial closure, branch identity, and comparison procedures.

## 12. Freeze checklist

This subset may be frozen only when:

- the project body/road frames and angle signs are accepted;
- the WUFR rack, steering-axis, and upright point definitions are reviewed;
- the exact legacy C-factor definition is recovered or explicitly rejected;
- steering-wheel, primary-shaft, pinion, rack, and road-wheel zero definitions are assigned;
- static toe sign and reference configuration are accepted;
- Ackermann error and any normalized coefficient are named separately;
- turning-radius path variants are separated;
- tie-rod physical and joint-center lengths are separated;
- left/right mirror expectations and allowable asymmetry are stated;
- the result-map and failure-reporting schemas are reviewed;
- analytical and external benchmark cases are frozen.
