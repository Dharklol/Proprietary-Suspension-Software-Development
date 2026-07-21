# Steering Quantity Subset Review Index

**Status:** Reviewed and frozen for the bounded rigid steering evaluator  
**Task:** `P0-STR-001`  
**Review record:** `docs/reviews/phase0_steering_definition_role_closeout.md`  
**Machine-readable contract:** `schemas/steering_definition_contract.toml`

## Active reviewed records

All records below are active at definition maturity `M1`. This activates their meanings, not any universal numerical vehicle value.

| Quantity ID | Frozen meaning |
|---|---|
| `QTY-GEO-0001` | Wheelbase between reviewed axle reference centers in a declared road plane |
| `QTY-GEO-0004` | Track between steering-axis/road-plane intersections, distinct from wheel or tread track |
| `QTY-STEER-0001` | Steering-wheel angle about a declared directed axis and zero |
| `QTY-STEER-0002` | Primary-shaft angle at a declared section |
| `QTY-STEER-0003` | Pinion angle at a declared pinion zero |
| `QTY-STEER-0004` | Signed rack translation from a named rack center |
| `QTY-STEER-0005` | Rack displacement per pinion angle; recovered C-factor alias only where supported |
| `QTY-STEER-0006` | Left global projected road-wheel heading; total and incremental forms separate |
| `QTY-STEER-0007` | Right global projected road-wheel heading; total and incremental forms separate |
| `QTY-STEER-0010` | Local steering-wheel-to-selected-road-wheel derivative ratio |
| `QTY-STEER-0011` | Secant steering-wheel-to-selected-road-wheel finite ratio |
| `QTY-STEER-0012` | Tie-rod joint-center distance, separate from physical tube and thread dimensions |
| `QTY-STEER-0013` | Exact low-speed Ackermann outside-wheel incremental magnitude reference |
| `QTY-STEER-0014` | Actual minus reference outside-wheel incremental magnitude |
| `QTY-STEER-0015` | Turning radius with mandatory named path reference |
| `QTY-ALIGN-0001` | Left side-local static toe-out angle at rack center |
| `QTY-ALIGN-0002` | Right side-local static toe-out angle at rack center |

## Frozen sign and zero decisions

- Body frame is `+x` forward, `+y` left, `+z` up.
- Global wheel heading is positive toward vehicle left.
- Static toe is stored side-locally: positive means toe-out.
- Left global centered heading equals left toe; right global centered heading equals negative right toe.
- Incremental wheel heading subtracts the same-side centered total heading.
- Steering-wheel, shaft, pinion, and rack zeros are assigned by a named configuration or measurement session rather than assumed equivalent.
- `inside` and `outside` are turn-direction aliases, not fixed side names.

## Deliberately deferred records

- `QTY-STEER-0008`, mean road-wheel angle: no averaging rule is approved.
- `QTY-STEER-0009`, equivalent single-track angle: no curvature/path construction is approved.
- normalized Ackermann percentage/coefficient: no single definition is approved.

These deferred quantities are prohibited as implicit aliases for left/right wheel headings or ratio denominators.

## Geometry and result contracts

The freeze also reviews:

- point, directed axis-line, wheel-plane, and reference-configuration required metadata;
- total versus incremental heading;
- fit-domain, residual, source-hash, and no-extrapolation metadata;
- explicit invalid-geometry, branch, singularity, unavailable-output, and out-of-domain failure states;
- path-qualified turning-radius identity.

## Freeze rule

Definition freeze is project-wide for this steering subset. Numerical parameters, setup values, installed state, calibrations, and requirement roles remain configuration-specific.

Reopen only for a semantic change to frame, sign, zero, quantity meaning, projection, Ackermann error, turning-path identity, or result/failure schema.
