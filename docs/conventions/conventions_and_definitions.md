# Conventions and Definitions Specification

**Status:** Proposed; not frozen  
**Normative intent:** Internal calculations use one explicit convention. Import/export adapters perform conversions at their boundaries.

## 1. Units

- Internal calculations use coherent SI units.
- Internal angular calculations use radians.
- Display units are presentation only and never alter stored values.
- Mass, weight, normal force, and load are separate quantities.
- Torsional and roll stiffness are stored per radian.

## 2. Vehicle body frame

The proposed body-fixed frame follows the right-handed ISO-style convention:

- `+x`: forward;
- `+y`: vehicle left;
- `+z`: upward.

Positive rotations follow the right-hand rule:

- positive roll about `+x` raises the left side;
- positive pitch about `+y` raises the front;
- positive yaw about `+z` turns the vehicle left.

This convention must be approved before model equations are accepted.

## 3. Required frame metadata

Every vector or moment quantity identifies:

- coordinate frame;
- reference point;
- force direction convention, such as road-on-tire or tire-on-road;
- whether the frame is inertial, body-fixed, wheel-fixed, tire-fixed, sensor-fixed, or external-tool-specific.

## 4. Steering quantities

The canonical dictionary must not use a generic `steering_angle`. Distinct quantities include:

- steering-wheel angle;
- primary-shaft angle;
- rack displacement;
- left road-wheel steer angle;
- right road-wheel steer angle;
- mean road-wheel steer angle;
- equivalent single-track steer angle.

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

## 8. Open convention decisions

Before freezing this specification, review:

- tire coordinate and slip definitions against the selected Pacejka and Guiggiani formulations;
- imported OptimumK, ADAMS, ANSYS, and logger frame conventions;
- positive damper and ride-height travel;
- steering sensor electrical polarity;
- aerodynamic coefficient signs and reference area;
- left/right and inside/outside naming in mirrored maneuvers.
