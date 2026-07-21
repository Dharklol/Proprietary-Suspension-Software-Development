# Conventions and Definitions Specification

**Status:** Project-wide specification remains proposed; the rigid-steering subset is frozen by `schemas/steering_definition_contract.toml`  
**Normative intent:** Internal calculations use one explicit convention. Import/export adapters perform conversions at their boundaries.

## 1. Units

- Internal calculations use coherent SI units.
- Internal angular calculations use radians.
- Display units are presentation only and never alter stored values.
- Mass, weight, normal force, and load are separate quantities.
- Torsional and roll stiffness are stored per radian.

These unit rules are active for the frozen rigid-steering subset.

## 2. Vehicle body frame

The body-fixed calculation frame follows the right-handed ISO 8855-style convention:

- `+x`: forward;
- `+y`: vehicle left;
- `+z`: upward.

Positive rotations follow the right-hand rule:

- positive roll about `+x` raises the left side;
- positive pitch about `+y` raises the front;
- positive yaw about `+z` turns the vehicle left.

This frame and rotation rule are reviewed and frozen for the rigid steering evaluator. Other model domains still require their own convention review before project-wide Phase 0 closure.

## 3. Required frame metadata

Every point, vector, or moment quantity identifies:

- coordinate frame;
- origin or reference point;
- basis directions and handedness;
- unit system;
- force direction convention, such as road-on-tire or tire-on-road;
- whether the frame is inertial, body-fixed, wheel-fixed, tire-fixed, sensor-fixed, CAD-specific, or external-tool-specific;
- the exact import/export transform and its source evidence.

A standard name or software name does not by itself establish the axes, signs, origin, or units of a specific file.

### 3.1 Simulation and CAD policy

- Physics, optimization, and simulation calculations use `CANONICAL_ISO8855_BODY`.
- CAD may retain an ISO 4130-oriented vehicle reference coordinate system or another documented model coordinate system.
- Native CAD global coordinates are never assumed to equal the project calculation frame.
- Every CAD, multibody, kinematics, FEA, and logger adapter declares its source frame and transformation.
- Source values remain recoverable after conversion; transformed values store source ID, adapter revision, and configuration.

### 3.2 WUFR-26 recovered adapters

For the final OptimumK suspension workbook, `OPTK_WUFR26_EXPORT` uses millimetres and the observed tuple order longitudinal, lateral-positive-right, vertical-positive-up. Convert points to the canonical frame using:

```text
[x_can, y_can, z_can] = 0.001 * [x_optk, -y_optk, z_optk]
```

For the raw WUFR-26 steering-study coordinates in inches, use:

```text
[x_can, y_can, z_can] = 0.0254 * [z_sw, -x_sw, y_sw]
```

These are source-specific mappings documented in `wufr26_coordinate_frame_reconciliation.md`. They are not universal OptimumK or SolidWorks defaults.

## 4. Steering quantities

The canonical dictionary must not use a generic `steering_angle`. The reviewed steering subset distinguishes:

- steering-wheel angle;
- primary-shaft angle;
- pinion angle;
- rack displacement;
- left road-wheel steer angle;
- right road-wheel steer angle;
- side-local static toe;
- local and secant steering ratios with named numerator and denominator;
- Ackermann reference and error;
- path-qualified turning radius.

Mean road-wheel steer angle and equivalent single-track steer angle remain deliberately deferred. The normative steering definitions and sign conversions are in `steering_canonical_definitions.md` and `schemas/steering_definition_contract.toml`.

## 5. Suspension quantities

- Bump and rebound signs must be declared for every imported dataset.
- Motion ratio names must include numerator and denominator, for example `spring_displacement_per_wheel_displacement`.
- Body roll, suspension roll, front body-plane angle, rear body-plane angle, and chassis twist are distinct quantities.
- Kinematic and loaded/compliant geometry are distinct model outputs.

## 6. Tire quantities

The tire convention must explicitly define:

- slip angle;
- longitudinal slip ratio;
- inclination/camber angle;
- wheel spin direction;
- force and moment signs;
- road-on-tire versus tire-on-road output.

Tire adapters must record and convert the source convention rather than assume compatibility.

## 7. Analysis-state terminology

- **Static:** no inertial terms.
- **Steady-state:** state derivatives are zero in the selected reference description.
- **Quasi-static:** a sequence of equilibrium states where neglected dynamics are assumed unimportant.
- **Quasi-transient:** states progress through local equilibria while selected slow states evolve.
- **Transient:** state derivatives and stored energy are represented explicitly.

## 8. Open project-wide convention decisions

Before freezing the complete project-wide specification, review:

- tire coordinate and slip definitions against the selected Pacejka and Guiggiani formulations;
- imported ADAMS, ANSYS, logger, and future OptimumK frame adapters outside the frozen steering sources;
- positive damper and ride-height travel;
- steering sensor electrical polarity for each installed measurement session;
- aerodynamic coefficient signs and reference area;
- left/right and inside/outside naming in non-steering mirrored analyses;
- the project-wide CAD vehicle-reference origin and ISO 4130 implementation.

These open items do not reopen the frozen rigid-steering semantics unless they expose a direct conflict with the steering contract.
