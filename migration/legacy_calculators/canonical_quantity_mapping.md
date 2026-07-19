# Legacy-to-Canonical Quantity Mapping

**Status:** Candidate dictionary mapping  
**Authority:** Proposed names and IDs; definitions must be reviewed before convention freeze  
**Purpose:** Prevent legacy labels, cell names, and locally defined symbols from becoming software interfaces.

## Mapping rules

1. One physical quantity has one canonical meaning, unit, frame, reference point, and sign.
2. Multiple observations of the same quantity remain separate parameter/evidence records linked to the same quantity ID.
3. Quantities that look similar but differ physically receive separate IDs.
4. A derived output cannot also be entered as an independent active input for the same model configuration without an explicit reconciliation rule.
5. Left/right quantities are canonical. Inside/outside are maneuver-dependent aliases generated at analysis time.
6. Candidate IDs below are reserved for review and must not be reused for another meaning.

## Mass properties and vehicle geometry

| Candidate ID | Canonical quantity | Canonical unit | Legacy aliases or locations | Definition issue to resolve |
|---|---|---:|---|---|
| `QTY-MASS-0001` | Total vehicle mass | kg | Existing registry record; `W`, total weight/mass | Configuration content: driver, fuel, accumulator, ballast |
| `QTY-MASS-0002` | Sprung mass | kg | LLTD sprung mass/weight | Exact unsprung-mass boundary |
| `QTY-MASS-0003` | Unsprung mass at one corner | kg | Often omitted or lumped | Corner allocation and rotating-mass treatment |
| `QTY-GEO-0001` | Wheelbase | m | `L`, 1.5624 m, 1.538 m | Axle-center definition and active vehicle revision |
| `QTY-GEO-0002` | Front wheel-center track | m | Front track | Loaded/setup state and wheel-center versus steering-axis track |
| `QTY-GEO-0003` | Rear wheel-center track | m | Rear track | Loaded/setup state |
| `QTY-GEO-0004` | Front steering-axis ground-intersection track | m | Ackermann track, wheel track minus scrub terms | Exact ground-plane and steering-axis definition |
| `QTY-GEO-0005` | CG longitudinal coordinate in body frame | m | CG-to-front/rear distance | Frame origin and sign |
| `QTY-GEO-0006` | CG vertical coordinate above reference road plane | m | CG height | Ride-height/configuration dependence |
| `QTY-GEO-0007` | Effective sprung-mass roll moment arm | m | LLTD effective roll arm | Must not silently absorb roll-axis, unsprung, aero, or measurement error |
| `QTY-GEO-0008` | Front roll-reference height | m | Front roll center | Kinematic definition and model fidelity |
| `QTY-GEO-0009` | Rear roll-reference height | m | Rear roll center | Kinematic definition and model fidelity |

## Loads, transfer, and aero

| Candidate ID | Canonical quantity | Canonical unit | Legacy aliases or locations | Definition issue to resolve |
|---|---|---:|---|---|
| `QTY-LOAD-0001` | Tire normal force | N | `Fz`, corner load, normal load | Road-on-tire positive direction and instantaneous/static state |
| `QTY-LOAD-0002` | Static tire normal force | N | `Fz0,l`, `Fz0,r`, corner weight | Current sheet values appear mass-equivalent in places |
| `QTY-LOAD-0003` | Total longitudinal axle load transfer | N | Longitudinal load transfer | Sign and front-positive convention |
| `QTY-LOAD-0004` | Total lateral load transfer at an axle | N | Front/rear lateral transfer | Difference convention: outside increase or half-difference |
| `QTY-LOAD-0005` | Geometric lateral load-transfer contribution | N | Roll-center/jacking contribution | Force-path definition and inclusion of unsprung components |
| `QTY-LOAD-0006` | Elastic lateral load-transfer contribution | N | Spring/ARB contribution | Body/chassis compatibility model |
| `QTY-LOAD-0007` | Unsprung lateral load-transfer contribution | N | Usually omitted | Unsprung CG and lateral-force path |
| `QTY-LOAD-0008` | Front elastic lateral load-transfer distribution | 1 | LLTD, front load-transfer fraction | Explicitly elastic, not total LLTD |
| `QTY-LOAD-0009` | Front total lateral load-transfer distribution | 1 | Magic number, LLTD | Includes geometric, elastic, unsprung, aero as applicable |
| `QTY-AERO-0001` | Aerodynamic downforce magnitude | N | Aero load | Sign and reference condition |
| `QTY-AERO-0002` | Aerodynamic drag force magnitude | N | Drag | Sign, reference area, and speed convention |
| `QTY-AERO-0003` | Front aerodynamic load fraction | 1 | Aero balance | Application points and ride-height state |

## Suspension rates, roll, and pitch

| Candidate ID | Canonical quantity | Canonical unit | Legacy aliases or locations | Definition issue to resolve |
|---|---|---:|---|---|
| `QTY-SUSP-0001` | Spring force per spring displacement | N/m | Spring rate | Linear tangent, secant, or tabular nonlinear rate |
| `QTY-SUSP-0002` | Spring displacement per wheel vertical displacement | 1 | Motion ratio | Explicit numerator/denominator and sign |
| `QTY-SUSP-0003` | Wheel vertical displacement per spring displacement | 1 | Inverse motion ratio | Must not share ID with `QTY-SUSP-0002` |
| `QTY-SUSP-0004` | Installed wheel rate | N/m | Wheel rate | State-dependent or local tangent value |
| `QTY-SUSP-0005` | Tire vertical stiffness | N/m | Tire rate | Load, pressure, and frequency dependence |
| `QTY-SUSP-0006` | Anti-roll-bar torsional stiffness | N*m/rad | ARB stiffness | Bar twist only; not wheel or axle contribution |
| `QTY-SUSP-0007` | Anti-roll-bar wheel-rate contribution | N/m | ARB wheel rate | Installation geometry and side coupling |
| `QTY-SUSP-0008` | Front axle elastic roll stiffness | N*m/rad | Front roll stiffness | Whether tire compliance is included |
| `QTY-SUSP-0009` | Rear axle elastic roll stiffness | N*m/rad | Rear roll stiffness | Whether tire compliance is included |
| `QTY-SUSP-0010` | Chassis torsional stiffness between front and rear reference planes | N*m/rad | Chassis stiffness | Plane locations, installed system versus bare frame |
| `QTY-SUSP-0011` | Body roll angle | rad | Roll angle | Body plane and reference road plane |
| `QTY-SUSP-0012` | Front suspension roll angle | rad | Front suspension roll | Relative body-to-wheel-plane definition |
| `QTY-SUSP-0013` | Rear suspension roll angle | rad | Rear suspension roll | Relative body-to-wheel-plane definition |
| `QTY-SUSP-0014` | Front-to-rear body-plane twist angle | rad | Chassis twist proxy | Measurement model required before physical interpretation |
| `QTY-SUSP-0015` | Body pitch angle | rad | Pitch/dive | Positive sign and reference state |
| `QTY-SUSP-0016` | Roll gradient with respect to lateral acceleration | rad/(m/s^2) | rad/g, deg/g | Store SI derivative; convert only for display |

## Tire quantities

| Candidate ID | Canonical quantity | Canonical unit | Legacy aliases or locations | Definition issue to resolve |
|---|---|---:|---|---|
| `QTY-TIRE-0001` | Tire slip angle | rad | SA, alpha | Guiggiani/Pacejka/source sign convention |
| `QTY-TIRE-0002` | Tire longitudinal slip ratio | 1 | Kappa, slip ratio | Driving/braking denominator convention |
| `QTY-TIRE-0003` | Tire inclination/camber angle | rad | Camber, gamma | Wheel/tire coordinate sign |
| `QTY-TIRE-0004` | Tire lateral force | N | Fy | Road-on-tire versus tire-on-road |
| `QTY-TIRE-0005` | Tire longitudinal force | N | Fx | Road-on-tire versus tire-on-road |
| `QTY-TIRE-0006` | Tire aligning moment | N*m | Mz, SAT | Reference point and sign |
| `QTY-TIRE-0007` | Small-slip cornering stiffness | N/rad | Cornering stiffness polynomial | Derivative sign and operating state |
| `QTY-TIRE-0008` | Tire force-utilization ratio | 1 | Friction/traction-circle use | Selected combined-slip capacity definition |

## Steering geometry and transmission

| Candidate ID | Canonical quantity | Canonical unit | Legacy aliases or locations | Definition issue to resolve |
|---|---|---:|---|---|
| `QTY-STEER-0001` | Steering-wheel angle | rad | Steering input, handwheel angle | Zero, polarity, and unwrap convention |
| `QTY-STEER-0002` | Primary steering-shaft angle | rad | Shaft input | Sensor and mechanism reference |
| `QTY-STEER-0003` | Pinion angle | rad | Rack input angle | Gear relation and zero |
| `QTY-STEER-0004` | Rack displacement | m | Rack travel, steering output | Positive direction and measured point |
| `QTY-STEER-0005` | Rack displacement per pinion angle | m/rad | C-factor, mm/rev | Recover exact legacy definition |
| `QTY-STEER-0006` | Left road-wheel steer angle | rad | Left wheel angle | Wheel plane and body-frame definition |
| `QTY-STEER-0007` | Right road-wheel steer angle | rad | Right wheel angle | Wheel plane and body-frame definition |
| `QTY-STEER-0008` | Mean road-wheel steer angle | rad | Mean tire angle | Arithmetic versus kinematic equivalent definition |
| `QTY-STEER-0009` | Equivalent single-track steer angle | rad | Bicycle steer angle | Curvature-matching definition |
| `QTY-STEER-0010` | Local steering-wheel-to-road-wheel ratio | 1 | Steering ratio | Derivative-based and selected wheel/mean output |
| `QTY-STEER-0011` | Secant steering-wheel-to-road-wheel ratio | 1 | Steering ratio | Input/output interval and zero handling |
| `QTY-STEER-0012` | Nominal tie-rod joint-center distance | m | Tie-rod length | Inner/outer joint centers and adjustment state |
| `QTY-STEER-0013` | Ackermann reference outside-wheel angle | rad | Ideal outside angle | Track based on steering-axis intersections |
| `QTY-STEER-0014` | Ackermann steering error | rad | Ackermann error, percentage | Exact measured-minus-reference definition |
| `QTY-STEER-0015` | Vehicle turning radius under kinematic assumptions | m | Minimum turn radius | Radius to CG, rear axle center, outside body, or tire path |
| `QTY-STEER-0016` | Rack force | N | Tie-rod/rack load | Net rack-axis force and load case |
| `QTY-STEER-0017` | Steering-wheel torque | N*m | Steering effort | Driver-applied torque, assistance state, friction, and frequency |

## Alignment and measured channels

| Candidate ID | Canonical quantity | Canonical unit | Legacy aliases or locations | Definition issue to resolve |
|---|---|---:|---|---|
| `QTY-ALIGN-0001` | Left wheel static toe angle | rad | Left toe | Positive toe-in/out convention |
| `QTY-ALIGN-0002` | Right wheel static toe angle | rad | Right toe | Positive toe-in/out convention |
| `QTY-ALIGN-0003` | Axle total toe | rad | Total toe | Sum versus difference convention |
| `QTY-MEAS-0001` | Ride-height sensor distance | m | VCSEL/IR ride height | Sensor ray, target, and local frame |
| `QTY-MEAS-0002` | Damper potentiometer displacement | m | Shock pot travel | Electrical polarity and mount geometry |
| `QTY-MEAS-0003` | Wheel vertical travel inferred from suspension sensor | m | Wheel travel | State-dependent kinematic mapping and uncertainty |
| `QTY-MEAS-0004` | Lateral acceleration at sensor | m/s^2 | Ay | Sensor location/orientation and gravity correction |
| `QTY-MEAS-0005` | Lateral acceleration at vehicle CG | m/s^2 | Corrected Ay | Lever-arm and rotational acceleration correction |
| `QTY-MEAS-0006` | Selection-mask membership | 1 | Use_Row_1_0 | Derived annotation, not a physical sensor quantity |

## Handling and force-distribution outputs

| Candidate ID | Canonical quantity | Canonical unit | Legacy aliases or locations | Definition issue to resolve |
|---|---|---:|---|---|
| `QTY-HAND-0001` | Road-wheel steering gradient | rad/(m/s^2) | Understeer gradient | Selected equivalent road-wheel angle and path definition |
| `QTY-HAND-0002` | Steering-wheel gradient | rad/(m/s^2) | Handwheel understeer gradient | Includes steering ratio/compliance |
| `QTY-HAND-0003` | Yaw-rate gain | 1/s | Yaw response | Input definition and steady/transient state |
| `QTY-HAND-0004` | Vehicle sideslip angle at CG | rad | Beta | Velocity-based definition and sign |
| `QTY-HAND-0005` | Local nonlinear balance sensitivity | varies | Understeer budget contribution | Parameter, state, normalization, and interaction residual |
| `QTY-FORCE-0001` | Requested front longitudinal-force fraction | 1 | Desired front force distribution | Command/design target |
| `QTY-FORCE-0002` | Achieved front longitudinal-force fraction | 1 | Actual bias | Tire and actuator constrained result |
| `QTY-FORCE-0003` | Hydraulic front brake proportion | 1 | Brake bias | Pressure/torque system quantity |
| `QTY-FORCE-0004` | Tire-limited maximum longitudinal force | N | Maximum acceleration/braking force | Combined-slip and wheel-load state |

## Known prohibited aliases

The following labels must not appear as unqualified canonical fields:

- `W`
- `Fz0` without force units and corner identity
- `steering input`
- `steering output`
- `wheel angle`
- `steering ratio`
- `motion ratio`
- `roll angle`
- `chassis twist`
- `LLTD`
- `wheel rate` without installed/state definition
- `ARB stiffness`
- `understeer gradient`
- `turning radius`

## Next review actions

1. Freeze frames, signs, angular units, force-direction convention, and motion-ratio convention.
2. Create formal quantity records for the accepted subset.
3. Link each migration block in `block_disposition_register.md` to its input and output quantity IDs.
4. Convert each legacy value into a parameter observation with source cell, artifact hash, vehicle revision, uncertainty, and applicability.
5. Resolve duplicate values through configuration-specific active-value rules rather than deletion.
