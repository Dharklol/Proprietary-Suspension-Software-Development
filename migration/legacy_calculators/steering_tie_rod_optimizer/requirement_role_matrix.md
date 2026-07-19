# Steering Inverse-Design Requirement-Role Matrix

**Status:** Proposed for WUFR review  
**Related model:** `MOD-STEER-0001`  
**Purpose:** Make every steering-design input explicit as evidence, fixed geometry, design freedom, hard feasibility, acceptable range, target, or derived output.

## Rules

1. A value has exactly one active solver role in one requirement set.
2. The same physical quantity may have observations from multiple sources, but one configuration-specific active value or reconciliation model is selected.
3. A hard constraint is never relaxed silently.
4. A soft band outside its preferred range remains visible in the objective breakdown.
5. A derived output is not independently entered for the same configuration.
6. Unknown or unverified packaging constraints are reported as unverified, not passed.
7. The role matrix is versioned separately from the vehicle geometry because design freedom changes between design studies.

## Role vocabulary

| Role | Meaning | Solver treatment |
|---|---|---|
| Evidence only | Historical or validation observation | Never changes the solution directly |
| Fixed parameter | Authoritative value for the selected configuration | Held constant |
| Bounded design variable | Continuous value available to optimization | Varied within hard bounds |
| Discrete option | Rack, steering arm hole, rod end, or architecture choice | Enumerated or mixed-variable search |
| Hard equality | Required relationship | Feasibility residual |
| Hard lower bound | Minimum permitted value | Feasibility constraint |
| Hard upper bound | Maximum permitted value | Feasibility constraint |
| Acceptable band | Preferred interval that may be left with penalty | Objective/soft constraint |
| Target value | Preferred point | Weighted objective |
| Target curve | Preferred function over a declared domain | Weighted curve objective |
| Derived output | Result of the mechanism and requirement set | Reported only |
| Report-only metric | Comparison value not used to choose the design | Reported only |

## Proposed WUFR matrix

The `Proposed role` column is deliberately not frozen. The member performing the current Ackermann study should replace the proposal with a reviewed role and evidence source.

| Item | Canonical quantity or object | Proposed role | Required bounds/metadata | Notes |
|---|---|---|---|---|
| Vehicle wheelbase | `QTY-GEO-0001` | Fixed parameter | Vehicle revision, uncertainty | Do not mix historical values |
| Steering-axis track | `QTY-GEO-0004` | Fixed parameter | Reference plane and setup | Distinct from wheel-center track |
| Left/right steering-axis lines | Geometry objects | Fixed parameter | Point, direction, frame, uncertainty | Caster/KPI are derived displays |
| Wheel/upright reference poses | Geometry objects | Fixed parameter | Ride height, camber, toe, frame | Required for spatial model |
| Rack axis | Geometry object | Fixed or bounded design variable | Origin, direction, package envelope | Longitudinal distance alone is insufficient |
| Rack longitudinal coordinate | Rack-axis coordinate | Bounded design variable | Chassis/package min and max | Legacy sweep item |
| Rack lateral coordinate/height | Rack-axis coordinate | Fixed initially; later bounded | Packaging and bump-steer implications | Must be explicit even when fixed |
| Rack width | Inner-joint spacing | Fixed, bounded, or discrete rack option | Rack housing and joint limits | Strong effect on steering map |
| Rack displacement per pinion angle | `QTY-STEER-0005` | Fixed, bounded variable, or discrete rack option | Exact legacy C-factor definition; rack spec | Variable-ratio rack requires a function |
| Total rack travel | Rack limit | Hard lower capability and hard upper hardware limit | Left/right one-sided limits | Distinguish required versus available travel |
| Steering-wheel-to-pinion relation | Function | Fixed parameter initially | U-joint phase and ratio state | Later includes irregularity/compliance |
| Left/right steering-arm outer joints | Geometry objects | Bounded design variables or discrete holes | Upright/wheel/brake envelope | Authoritative over arm length alone |
| Steering-arm length | Derived geometry or bounded proxy | Derived output preferred | Exact 2D/3D definition if optimized directly | Legacy sweep item |
| Steering-arm angle/orientation | Derived or bounded design variable | Bounded design variable | Branch and packaging limits | Needed with arm length |
| Tie-rod center-to-center length | `QTY-STEER-0012` | Derived output with hard hardware bounds | Adjustment range, thread engagement | Usually not a free independent input |
| Rod-end articulation | Joint-state output | Hard upper bound | Catalog limit plus margin | Evaluate over full sweep |
| Static left/right toe | `QTY-ALIGN-0001/0002` | Hard equality or target band | Setup range and sign | May be established by tie-rod adjustment |
| Maximum road-wheel angle | `QTY-STEER-0006/0007` | Hard upper limit | Tire/wheel/upright interference | Separate from minimum required capability |
| Minimum required wheel angle | `QTY-STEER-0006/0007` | Hard lower capability | Turning course/rules basis | Both turn directions |
| Minimum turning capability | Defined turning-path metric | Hard constraint | Reference path and margin | Turning radius is not the main objective |
| Ideal low-speed Ackermann curve | `QTY-STEER-0013` | Evidence/reference or target curve | Domain and track definition | Not automatically optimal |
| Ackermann error curve | `QTY-STEER-0014` | Report-only initially; optional target | Sign and normalization | Dimensional error remains primary |
| Historical WUFR steering map | Evidence artifact | Evidence only | Source revision, units, hash | Benchmark candidate |
| Desired inner/outer curve | Function | Target curve | Input domain and weighting | Can differ from ideal Ackermann |
| Local steering ratio | `QTY-STEER-0010` | Acceptable band or report-only | Numerator/denominator and domain | Function, not one number |
| Steering-ratio smoothness | Derived function metric | Target value/band | Derivative order and normalization | Avoids abrupt response changes |
| Left/right symmetry | Function residual | Hard equality or acceptable band | Symmetric geometry expectation | Intended asymmetry must be documented |
| Mechanism closure | Residual | Hard equality | Numerical tolerance | All swept states |
| Mechanism branch | Discrete identity | Hard constraint | Branch chosen at reference state | No silent branch switching |
| Monotonicity | Derivative sign | Hard constraint or acceptable band | Declared domain | Required for predictable control |
| Singularity margin | Jacobian/geometry metric | Hard lower bound | Threshold and scaling | Report minimum location |
| Wheel/brake/upright clearance | Spatial distance | Hard lower bound | CAD source or conservative envelope | Unverified without geometry evidence |
| Chassis/rack clearance | Spatial distance | Hard lower bound | CAD source or envelope | Unverified without geometry evidence |
| Manufacturing tolerance robustness | Probability/worst-case metric | Later target or hard margin | Tolerance distributions | Not part of nominal first evaluator |
| Tire slip/force mismatch | Tire-informed objective | Later target curve/envelope | Tire model and operating points | Reserved interface, not first release |
| Steering effort | `QTY-STEER-0017` and contributors | Later target/bound | Tire, trail, scrub, friction, assistance | Gillespie warns Ackermann affects low-speed effort |
| Compliance steer | Loaded minus rigid steer map | Later target/bound | Stiffness model and load cases | Separate fidelity layer |

## Requirement-set template

Each design study should include:

```text
requirement_set_id
vehicle_configuration_id
geometry_revision
source evidence IDs
solver mode
fixed parameters
continuous design variables and bounds
discrete options
hard equalities
hard lower and upper bounds
acceptable bands
target values and curves
objective normalization and weights
sweep domain and resolution
uncertainty/tolerance treatment
expected outputs
approval owner and date
```

## First review questions

1. Is the rack already selected, making C-factor and rack width fixed or discrete rather than continuous?
2. Which rack coordinates are still physically changeable on WUFR-27?
3. Are steering-arm pickups fixed by the upright or available as alternate holes/design variables?
4. Is tie-rod length free to manufacture or constrained by an existing tube/rod-end package?
5. What exact minimum-turning requirement applies, and to which vehicle path?
6. Which steering-input range matters for tire-informed optimization versus low-speed maneuvering?
7. Are left/right asymmetries permitted or only observed manufacturing deviations?
8. Which packaging checks can be represented numerically and which require CAD evidence?
9. What steering-effort limits or preferred behavior should eventually constrain the tire-informed solution?
10. Which current Ackermann curves are targets, and which are only historical comparisons?
