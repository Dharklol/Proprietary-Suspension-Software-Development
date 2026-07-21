# Steering Requirement-Role Matrix

**Status:** Reviewed and frozen for the WUFR-26 nominal benchmark scope  
**Task:** `P0-STR-003`  
**Machine-readable set:** `configurations/steering/WUFR26_STEERING_REQUIREMENT_ROLES_V0.toml`  
**Related model:** `MOD-STEER-0001`  
**Review record:** `docs/reviews/phase0_steering_definition_role_closeout.md`

## Purpose

This matrix prevents historical observations, active geometry, solver variables, constraints, targets, and outputs from being entered as interchangeable spreadsheet values.

The frozen WUFR-26 requirement set is an **evaluation-only benchmark set**. It does not authorize inverse design. A future WUFR-27 or later optimizer must create a new requirement-set ID with reviewed numerical bounds, targets, objective weights, packaging evidence, uncertainty treatment, and focused authorization.

## Role rules

1. One item has exactly one active solver role in one requirement set.
2. Multiple observations may support one selected fixed value without becoming duplicate solver inputs.
3. A derived output is not entered independently for the same configuration.
4. Evidence and report-only values never move the solution.
5. A hard constraint is never relaxed silently.
6. Missing packaging or installed-state evidence is reported as unverified rather than passed.
7. Static toe, incremental steer, free play, elastic compliance, and rigid kinematic residual remain separate.
8. The frozen benchmark set is immutable; design studies fork it into a new requirement set.

## Role vocabulary

| Role | Meaning | Solver treatment |
|---|---|---|
| Evidence only | Historical, supplier, design-intent, or validation observation | Never changes solution directly |
| Fixed parameter | Reviewed value for the selected configuration | Held constant |
| Bounded design variable | Continuous design freedom with hard bounds | Varied only in an authorized study |
| Discrete option | Architecture, rack, hole, or hardware choice | Enumerated only in an authorized study |
| Hard equality | Required relationship or state identity | Feasibility residual |
| Hard lower/upper bound | Non-negotiable capability or limit | Feasibility constraint |
| Acceptable band | Preferred interval that may be left with penalty | Soft constraint/objective |
| Target value/curve | Preferred point or function | Weighted objective |
| Derived output | Mechanism result | Reported only |
| Report-only | Comparison metric not used to choose design | Reported only |

## Frozen WUFR-26 nominal benchmark roles

| Item | Canonical object | Frozen role | Source and restriction |
|---|---|---|---|
| Wheelbase | `QTY-GEO-0001` | Fixed parameter | Nominal OptimumK design observation; not as-built authority |
| Steering-axis track | `QTY-GEO-0004` | Derived output | Derived from the mirrored steering-axis lines and named road plane; not tread-center track |
| Left steering axis | Geometry object | Fixed parameter | Final nominal OptimumK source |
| Right steering axis | Geometry object | Fixed parameter | Exact CAD reflection for the design model; not as-built symmetry evidence |
| Rack axis and center | Geometry object | Fixed parameter | Team-confirmed CAD center and nominal rack axis |
| Rack inner-joint spacing | Geometry object | Fixed parameter | Centered nominal rack points |
| Rack displacement minimum | `QTY-STEER-0004` | Hard lower bound | `-0.0254 m`; nominal design-study domain only |
| Rack displacement maximum | `QTY-STEER-0004` | Hard upper bound | `+0.0254 m`; no extrapolation and not installed stop authority |
| Design-study input-to-rack map | `QTY-STEER-0005` | Fixed parameter | Historical CAD signal mapping; not installed steering-wheel transmission |
| Left outer tie-rod joint | Geometry object | Fixed parameter | Steering FDR front-left final geometry |
| Right outer tie-rod joint | Geometry object | Fixed parameter | Exact nominal CAD reflection |
| Left/right static toe | `QTY-ALIGN-0001/0002` | Fixed parameters | Side-local toe-out convention; separate from incremental steer |
| Left/right static camber | Wheel-plane inputs | Fixed parameters | Side-local top-out convention |
| Tie-rod closure | `EQ-STEER-0002` | Hard equality | Required throughout the evaluated domain |
| Mechanism branch | Branch identity | Hard equality | No silent branch switching or alternate-root substitution |
| Left/right tie-rod joint-center lengths | `QTY-STEER-0012` | Derived outputs | Physical tube and adjustment records remain separate |
| Left/right total and incremental headings | `QTY-STEER-0006/0007` | Derived outputs | Canonical wheel-plane/road-plane projection |
| Test 3 projected curve | `BENCH-STEER-0001` | Evidence only | Descriptive nominal design-source comparison, not a target or tolerance |
| FDR 22.22°/32.81° endpoints | Design-intent evidence | Evidence only | Endpoint cross-check only |
| Level E residual metrics | Frozen report | Report-only | No objective weight or pass/fail threshold inferred |
| Approximate 4° whole-system free play | `QTY-STEER-0016` | Evidence only | Installed-system total; no component attribution or rigid correction |
| Historical directional compliance | `QTY-STEER-0017` | Evidence only | Preserve directions and setup; do not average |
| Reported 3.12:1 ratio | Rejected observation | Evidence only | Retained for lineage and prohibited numerically |

## Explicit non-roles in the frozen benchmark

The following are **not** active design variables, targets, or soft constraints in `WUFR26_STEERING_REQUIREMENT_ROLES_V0`:

- rack position, width, or C-factor;
- steering-arm pickup position, length, or orientation;
- tie-rod length;
- Ackermann percentage or error curve;
- local or secant steering ratio;
- Level E residuals;
- measured free play or compliance;
- supplier gear backlash;
- installed stops or as-built geometry.

This prevents the benchmark from turning into an optimizer merely because a value could be varied in a future study.

## Future design-study template

A future requirement set may classify the following only after bounds and authority are reviewed:

| Candidate item | Possible future role | Required evidence before activation |
|---|---|---|
| Rack longitudinal position and height | Bounded variables | Chassis/package envelope and bump-steer interaction |
| Rack inner-joint spacing or rack family | Bounded variable or discrete option | Rack housing, travel, joint, and procurement constraints |
| Steering-arm pickup coordinates or holes | Bounded variables or discrete options | Upright, wheel, brake, articulation, and manufacturing envelope |
| Column/rack transmission | Fixed function or discrete option | Shaft, gear, rack, packaging, effort, and backlash data |
| Tie-rod hardware | Discrete option with hard bounds | Adjustment, thread engagement, articulation, buckling, and procurement |
| Required turning capability | Hard constraint | Named path reference, rules/course basis, and margin |
| Tire-informed wheel-angle curve | Target curve | Reviewed tire model, operating points, weighting, and uncertainty |
| Steering-ratio behavior | Target/band or report-only | Exact numerator/denominator, domain, and driver-control basis |
| Ackermann error | Report-only or target curve | Justified performance role; ideal Ackermann is not automatically optimal |
| Steering effort | Hard limit or target band | Tire moments, scrub/trail, friction, gear ratio, wheel diameter, and driver basis |
| Tolerance/compliance robustness | Target or hard margin | Distribution or worst-case model and physical correlation |

## Activation checklist for a future optimizer

A new design-study requirement set must include:

```text
requirement_set_id
vehicle_configuration_id
geometry_revision and source evidence IDs
solver mode and authorization ID
fixed parameters
continuous variables and hard bounds
discrete options
hard equalities and lower/upper bounds
acceptable bands and target curves
objective normalization and weights
sweep domain and resolution
packaging verification method
uncertainty/tolerance treatment
expected outputs and failure states
approval owner and date
```

The current rigid evaluator remains valid for nominal mechanism evaluation while optimizer authorization remains separate.

## Reopening rules

Reopen this role freeze when:

- an item changes solver role inside the WUFR-26 benchmark;
- a source observation is promoted to an active value or target;
- a derived value is proposed as an independent input;
- the benchmark geometry/configuration changes;
- a future optimizer attempts to inherit this requirement-set ID rather than creating a new one.
