# Planar wheel-velocity and tire-slip kinematics v0.1.0

## Purpose

PR #33 introduces a provider-neutral planar kinematics layer between an upstream vehicle-motion source and downstream tire/steering target logic. It addresses a limitation of the PR #30 Ackermann-anchored force-demand target: exact low-speed Ackermann is a special wheel-velocity-heading construction, not a universal high-lateral-acceleration velocity field.

The new layer does **not** predict vehicle motion. An upstream source must explicitly supply body-frame longitudinal velocity `u`, lateral velocity `v`, and yaw rate `r`.

## Literature basis

The implementation follows Guiggiani, *The Science of Vehicle Dynamics* (2022):

- Section 3.2.3, Eqs. 3.13-3.14: velocity-center coordinates `R=u/r`, `S=-v/r`;
- Section 3.3, Eqs. 3.53-3.54: front wheel-center velocity components;
- Section 3.3, Eqs. 3.55-3.58: wheel-center velocity headings and `alpha = delta - beta_hat`.

The generalized rigid-body field used for any wheel center at body coordinates `(x_j,y_j)` is:

`Vx_j = u - r*y_j`

`Vy_j = v + r*x_j`

with canonical project axes `+x` forward, `+y` vehicle left, `+z` upward. Positive yaw is left/CCW by the right-hand rule.

## Core contracts

`pssd_vehicle.planar_kinematics` provides:

- `PlanarMotionSample` for explicit `u,v,r`;
- `PlanarMotionSchedule` for ordered source-preserving motion states;
- `FourWheelPlanarGeometry` and explicit wheel-center locations;
- exact wheel-center velocity and velocity-heading evaluation;
- diagnostic `R` and `S` velocity-center coordinates;
- signed tire slip `alpha = delta - beta_hat`;
- inverse required wheel heading `delta = beta_hat + alpha_required`.

A zero yaw rate leaves `R` and `S` unavailable rather than assigning a large numerical sentinel. A zero wheel-center speed is rejected when a tire-slip direction is requested.

## Limiting cases

BENCH-VEH-0002 exercises several useful limiting cases.

### Velocity center on the rear axle

When `S=-a2` and the required tire slip is zero, the front wheel-center velocity headings reproduce the classical no-slip Ackermann construction. This demonstrates that the existing Ackermann reference is contained as a special kinematic case rather than contradicted by the new provider.

### Parallel steer and velocity-center location

For parallel front wheel headings, the exact velocity field reproduces Guiggiani's relative-slip result:

- `-a2 < S < a1`: the outer front tire has the larger slip;
- `S = a1`: the front tire slips are equal;
- `S > a1`: the inner front tire has the larger slip.

Therefore a tire's load-sensitive required slip difference alone cannot determine one global pro/parallel/anti-Ackermann steering geometry. The vehicle motion state also determines the difference between the left/right wheel-center velocity headings.

## Motion-aware steering adapter

`pssd_steering.optimization.motion_force_targets` combines this kinematic provider with the merged PR #30 bounded tire-force branch inversion.

For every noncenter sample:

1. the explicit yaw-rate sign determines left/right turn direction and inside/outside front wheel identity;
2. PR #30 branches independently invert inside and outside `|Fy|` demand to required slip magnitudes;
3. the required slip sign is set from the explicit turn direction;
4. MOD-VEH-0002 calculates left/right wheel-center velocity headings from `u,v,r` and wheel-center geometry;
5. each total wheel heading is formed independently as `delta_j = beta_hat_j + alpha_required,j`;
6. the total heading is converted to the same incremental-from-pose wheel-plane quantity evaluated by MOD-STEER-0001;
7. pro/parallel/anti-Ackermann is reported only when the resulting incremental pair is a meaningful same-direction steering pair.

The centered rack sample is preserved exactly and requires zero yaw rate and zero force demands. Static toe is part of the centered pose reference and is not silently steered out to manufacture a zero-slip straight-line state.

## Why this supersedes the Ackermann anchor when motion is known

PR #30's formula is retained as a bounded development/limiting path when no reviewed vehicle motion state exists. When explicit `u,v,r` is available, however, using exact Ackermann as the wheel-velocity baseline would discard supplied vehicle-motion information. The motion-aware path therefore records `ackermann_anchor_used=false` and uses `wheel_velocity_heading_plus_required_tire_slip` as its target mapping.

## Current authority boundary

The benchmark motion schedules and force branches are synthetic. No current WUFR spreadsheet reviewed so far supplies an authoritative synchronized `u,v,r` schedule. In particular, the PR #29 `VehicleOperatingStateSet` carries speed/acceleration and wheel-state exchange fields but intentionally does not solve body sideslip or yaw-rate response.

A production-relevant motion source should come from a separately reviewed QSS/vehicle model, telemetry reconstruction, or higher-fidelity external simulation. It must use the same body frame/origin and operating-state synchronization as the wheel loads, suspension pose, and tire demands consumed downstream.
