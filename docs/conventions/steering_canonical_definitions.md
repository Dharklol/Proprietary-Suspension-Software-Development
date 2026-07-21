# Steering Canonical Definitions — Frozen Rigid-Evaluator Subset

**Status:** Reviewed and frozen for the rigid nominal-height steering evaluator  
**Task:** `P0-STR-001`  
**Machine-readable contract:** `schemas/steering_definition_contract.toml`  
**Review record:** `docs/reviews/phase0_steering_definition_role_closeout.md`

## Purpose and authority

This document freezes the smallest project-wide steering vocabulary required to evaluate a rack–tie-rod–steering-arm mechanism without depending on spreadsheet labels, CAD monitor names, or a generic `steering angle` field.

Freezing a quantity definition does not freeze a vehicle parameter value. Numerical geometry, setup, sensor, calibration, and test values remain configuration- and evidence-specific. The current WUFR-26 numerical authority is `WUFR26_DESIGN_NOMINAL_V0`; installed and as-built authority remains open.

The first model layer is rigid nominal-height kinematics. Tire-informed targets, steering effort, compliance, backlash, tolerance, suspension travel, loads, and transient response extend these definitions in separate model layers rather than changing them.

## 1. Units, frame, and rotation

Internal length is metres and internal angle is radians.

The rigid steering evaluator uses the right-handed `CANONICAL_ISO8855_BODY` frame:

- `+x`: vehicle forward;
- `+y`: vehicle left;
- `+z`: upward;
- positive rotation: right-hand rule about a declared directed axis;
- positive global road-wheel heading: counterclockwise yaw viewed from `+z`, so the wheel points toward vehicle left.

A nominal flat road plane may be `z = 0` only inside a named reference configuration. CAD, OptimumK, logger, fixture, and sensor frames require explicit adapters. No source tuple is accepted as three unlabeled numbers.

## 2. Frozen geometry objects

### Point

A mechanism point is a joint-center coordinate with:

- coordinates and unit;
- frame ID and configuration ID;
- source/evidence ID and source role;
- uncertainty or an explicit unknown-uncertainty state.

Visual CAD edges do not replace joint centers.

### Directed axis line

The steering axis and rack axis are directed three-dimensional lines. Each stores a point, normalized direction, frame, configuration, source, source role, and uncertainty. Caster, KPI, and scalar rack placement are derived views; they do not replace the axis line.

Axis direction sign is retained because angular polarity follows the right-hand rule about that directed axis.

### Wheel-plane reference

A centered wheel-plane reference stores:

- side identity;
- plane normal at center;
- forward direction at center;
- frame and configuration;
- source and source role.

The forward vector resolves the 180-degree ambiguity of the wheel-plane/road-plane intersection.

### Reference configuration

A steering reference configuration names, at minimum:

- vehicle revision and configuration ID;
- road plane;
- rack-center definition;
- left/right static toe and camber;
- load state and compliance state;
- source authority.

Ride height, heave, roll, pitch, wheel travel, driver/load state, tire state, tie-rod adjustment, and camber shim stack are recorded when available. A missing field remains an explicit applicability limit and is never silently set to zero.

## 3. Transmission quantities and zeros

The transmission stages remain distinct:

- `QTY-STEER-0001`: steering-wheel angle;
- `QTY-STEER-0002`: primary steering-shaft angle at a declared section;
- `QTY-STEER-0003`: pinion angle;
- `QTY-STEER-0004`: rack displacement;
- `QTY-STEER-0005`: rack displacement per pinion angle.

Steering-wheel, primary-shaft, and pinion angles are signed about their declared directed axes. A configuration or measurement session assigns their physical zeros and polarity adapters. They are not assumed equal merely because a nominal CAD study uses a rigid 1:1 input relation.

Rack displacement is signed translation along the declared directed rack axis from a named rack center. Total travel, one-sided travel, installed stop positions, and displacement from center are separate fields.

For WUFR-26 design-source evaluation, positive historical `Steer Input` maps to canonical `+y` rack motion. That adapter is not installed steering-wheel transmission authority.

The recovered WUFR-26 `C-factor` alias is permitted only where the source explicitly means rack travel per pinion/input revolution. A different or undocumented source must use the canonical quantity name until its definition is recovered.

## 4. Road-wheel heading, static toe, and camber

### Total road-wheel heading

`QTY-STEER-0006` and `QTY-STEER-0007` are the left and right total road-wheel headings.

Heading is the forward-oriented intersection of the wheel center plane and the declared road plane, resolved by:

```text
heading = atan2(direction_y, direction_x)
```

Both sides use the same global heading sign: positive points toward vehicle left.

### Incremental road-wheel steer

Incremental steer is derived independently on each side:

```text
incremental_heading_side = wrap(total_heading_side - centered_total_heading_side)
```

Static toe is therefore retained in the total heading and removed only by this explicit centered subtraction. Hardpoints are not altered to remove static toe.

`inside` and `outside` are analysis-time aliases selected from turn direction. They are never fixed synonyms for left and right.

### Static toe

`QTY-ALIGN-0001` and `QTY-ALIGN-0002` store side-local static toe-out angles at the named rack-center reference state:

- positive toe means the front of that wheel points away from vehicle centerline;
- negative toe means toe-in;
- left global centered heading equals the left side-local toe value;
- right global centered heading equals the negative of the right side-local toe value.

This conversion permits equal left/right side-local alignment settings while preserving mirrored global headings.

### Static camber

The steering wheel-plane constructor uses a side-local camber input. Positive camber means the wheel top leans outward. Camber is part of the wheel-plane basis and is not a substitute for projected heading.

## 5. Tie-rod quantity

`QTY-STEER-0012` is the joint-center distance between the named rack inner joint and upright outer joint in the reference configuration.

The physical tie-rod assembly remains a separate component/setup record containing body length, rod-end shanks, thread handedness, adjustment range, nominal adjustment, thread engagement, tolerance, and left/right equality rules.

Tie-rod joint-center distance is normally derived from geometry. Hardware availability and adjustment may impose hard bounds in a future requirement set, but the same value must not also be entered as an independent unconstrained solver input.

## 6. Steering ratios

`QTY-STEER-0010` is the local derivative ratio:

```text
local ratio = d(steering-wheel angle) / d(selected road-wheel incremental angle)
```

`QTY-STEER-0011` is the finite secant ratio over a declared interval.

Every ratio reports:

- numerator and denominator quantity IDs;
- selected side or reviewed wheel representation;
- reference state and input domain;
- approach direction where hysteresis exists;
- zero handling.

No canonical output is named only `steering ratio`. A road-wheel gain, reciprocal ratio, left-wheel ratio, right-wheel ratio, mean-wheel ratio, and center secant ratio are not interchangeable.

Mean road-wheel angle and equivalent single-track angle remain deferred, so they cannot be used as an undeclared denominator.

## 7. Ackermann reference and error

`QTY-STEER-0013` is the exact planar, low-speed, no-slip outside-wheel incremental-steer magnitude corresponding to a selected positive inside-wheel incremental-steer magnitude, wheelbase, steering-axis ground-intersection track, and road plane.

The reference uses incremental magnitudes with static toe handled separately. The turn direction and side identities remain metadata.

`QTY-STEER-0014` is:

```text
actual outside-wheel incremental-steer magnitude
minus Ackermann reference outside-wheel incremental-steer magnitude
```

The independent variable, turn direction, track definition, road plane, and domain are mandatory. A normalized coefficient or full-lock percentage is a different quantity and is not approved by this freeze.

Ideal Ackermann remains a low-speed benchmark or target candidate, not a universal tire-force optimum.

## 8. Turning-path quantity

`QTY-STEER-0015` is a path-qualified turning radius under declared low-speed kinematic assumptions.

Every value includes a `path_reference_id`, such as:

- rear axle center;
- vehicle CG;
- left or right front wheel center;
- outside front tire envelope;
- outside body envelope;
- competition-defined turning-circle point.

Turn direction, road plane, reference configuration, and assumptions are mandatory. Radii with different path references are different outputs and must not be compared as one generic turning radius.

A minimum-turning requirement is normally a boundary condition, not the steering-performance objective.

## 9. Function-valued results and failure behavior

The canonical steering result is a versioned map or function over an explicit domain. Required metadata includes:

- configuration, model, and version;
- input and output quantity IDs and units;
- ordered sample domain;
- source IDs and adapter revision;
- failure status.

Polynomial or other fitted representations are optional derivatives. They include fit type/order, fit domain, residual metrics, source-map SHA-256, and an extrapolation rule. Extrapolation defaults to prohibited.

Invalid geometry, branch loss, singularity, unavailable prerequisites, and out-of-domain requests return explicit status. They do not produce guessed values, alternate-root substitutions, or silent constraint relaxation.

## 10. Requirement-role separation

One requirement set assigns each item one active solver role. Multiple source observations may support one selected fixed value without becoming duplicate solver inputs.

The frozen WUFR-26 role set is `WUFR26_STEERING_REQUIREMENT_ROLES_V0`. It is evaluation-only: current geometry is fixed, closure and branch are hard requirements, wheel headings and joint-center lengths are derived, and Level E plus physical observations remain evidence/report items.

A future inverse-design study receives a new requirement-set ID with reviewed variables, bounds, targets, weights, packaging evidence, uncertainty treatment, and separate optimizer authorization. It must not mutate the frozen WUFR-26 benchmark role set.

## 11. Model-layer separation

The same core quantities may appear in separate models:

1. rigid nominal-height mechanism;
2. rigid mechanism over bump, rebound, roll, pitch, and heave;
3. manufacturing tolerance and variation;
4. compliance, backlash, friction, and hysteresis;
5. steering force and driver effort;
6. tire-informed target generation;
7. transient steering and vehicle response.

The rigid evaluator cannot claim conclusions belonging to later layers or apply constant free-play/compliance corrections to its geometry solution.

## 12. Deliberately deferred quantities

The freeze does not activate:

- `QTY-STEER-0008`, mean road-wheel angle;
- `QTY-STEER-0009`, equivalent single-track angle;
- a normalized Ackermann coefficient or percentage.

These require separate definitions and benchmarks. They are not aliases for left/right projected headings.

## 13. Reopening rules

Reopen this definition freeze when a change alters:

- frame axes, angular polarity, toe/camber sign, or projection construction;
- quantity meaning, numerator/denominator identity, or zero definition;
- geometry-object required metadata;
- Ackermann error sign or reference construction;
- turning-path identity requirements;
- result-map or failure semantics.

A new vehicle parameter, calibration, source observation, or requirement set normally does not reopen the project-wide definitions unless it exposes an actual semantic conflict.
