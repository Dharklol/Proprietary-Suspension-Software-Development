# Steering Geometry and Tie-Rod Optimizer — Phase 0 Transition Specification

**Migration ID:** `MIG-STR-0001`  
**Proposed model ID:** `MOD-STEER-0001`  
**Status:** Documentation and source recovery  
**Implementation priority:** First legacy-calculator migration candidate after its documentation gate is satisfied  
**Authority status:** Not authoritative

## 1. Purpose

The current steering-design process uses a separate tie-rod-length optimizer and a CAD motion study as intermediary steps between vehicle-level steering requirements and the `Ackerman Steering` and `Steer Ratio` sheets in `Suspension Calculations 2026`.

The replacement should be one steering-kinematics inverse-design workflow that:

1. accepts fixed geometry, selectable design variables, hard constraints, acceptable ranges, and performance preferences;
2. solves the steering linkage directly rather than using a manually transferred motion-study curve;
3. returns the installed tie-rod length and the complete steering map;
4. reports the inner- and outer-road-wheel relationship, Ackermann reference/error, steering ratio, turning-radius capability, constraint margins, and sensitivity;
5. preserves CAD or external multibody motion studies as independent evidence rather than required runtime dependencies.

The term **tie-rod-length optimizer** is retained as the legacy name. The canonical scope is broader because tie-rod length alone does not uniquely define steering behavior.

## 2. Why this is a reasonable first migration

This workflow is bounded enough to verify analytically and against the existing CAD motion study, but broad enough to exercise the canonical schema, units, frames, constraint classification, optimization interface, result lineage, external-adapter strategy, and benchmark process.

It is also a natural vertical slice:

```text
vehicle and upright geometry
→ steering mechanism definition
→ parameter/constraint classification
→ exact kinematic sweep
→ optimizer
→ steering-wheel/rack/road-wheel maps
→ Ackermann and turning metrics
→ exported evidence and calculator replacement
```

The first implementation must remain a rigid kinematic model. Tire-force-informed target selection, suspension travel, compliance, and transient steering behavior are later model layers using the same interface.

## 3. Legacy process inventory

### 3.1 Observed or team-described inputs

- rack ratio or rack `C-factor`;
- steering-rack longitudinal distance from the front axle;
- ideal left and right turn angles;
- maximum left and right turn angles;
- steering-arm length;
- sweep or boundary definitions used by the optimizer.

### 3.2 Legacy derived result

- nominal tie-rod length.

### 3.3 Legacy external step

A quick CAD motion study sweeps the steering input and exports steering response. The resulting curve is manually transferred into `Suspension Calculations 2026`, where the `Steer Ratio` data and polynomial fits feed the `Ackerman Steering` sheet.

### 3.4 Unresolved source questions

The following must be recovered before the legacy result can be treated as a benchmark:

- exact optimizer file, script, workbook, or CAD design-study definition;
- author, date, software version, and vehicle revision;
- input values and sweep resolution;
- exact meaning and units of `C-factor`;
- whether steering input is steering-wheel angle, pinion angle, primary-shaft angle, or rack displacement;
- whether reported wheel angles are left/right road-wheel angles, inner/outer angles, or upright rotations;
- nominal ride height, toe, camber, caster, KPI, and steering-axis state;
- tie-rod center-to-center definition and adjustment state;
- rack inner-joint locations, rack width, axis orientation, and travel limits;
- steering-arm pickup coordinates and whether arm length is measured in 2D or 3D;
- whether left/right symmetry was imposed;
- whether the motion study included suspension motion, compliance, clearances, or joint articulation.

Until these are recovered, the legacy motion-study curves are evidence with incomplete provenance, not ground truth.

## 4. Canonical terminology

The UI and data model must not use ambiguous phrases such as `steering input`, `steering output`, or `wheel angle` without qualification.

Required distinct quantities include:

- steering-wheel angle;
- primary-shaft angle;
- pinion angle;
- rack displacement;
- left road-wheel steer angle;
- right road-wheel steer angle;
- inside road-wheel steer angle;
- outside road-wheel steer angle;
- mean road-wheel steer angle;
- equivalent single-track steer angle;
- local steering ratio;
- secant steering ratio;
- Ackermann reference angle;
- Ackermann error or coefficient;
- nominal tie-rod center-to-center length;
- physical tie-rod body length;
- installed adjustment length.

`Inside` and `outside` are maneuver-dependent aliases. Left/right quantities remain the stored canonical outputs.

## 5. Mechanism definition

### 5.1 Minimum geometry required

A steering arm cannot be represented canonically by length alone. The model requires enough geometry to reconstruct the linkage:

- vehicle wheelbase and front track under the selected definition;
- left and right steering-axis lines;
- nominal wheel-center and upright poses;
- left and right steering-arm outer-joint points;
- rack axis origin and direction;
- left and right rack inner-joint points at rack center;
- rack travel limits;
- nominal toe and rack-center definition;
- tie-rod joint types and articulation limits;
- steering-wheel-to-pinion and pinion-to-rack transmission definitions.

A planar abstraction may derive some coordinates from rack distance, rack width, steering-arm length, and steering-arm angle, but those derived assumptions must be explicit.

### 5.2 Tie-rod length

For a rigid model, tie-rod length is the center-to-center distance between the specified inner and outer spherical-joint centers in the reference configuration. The record must also state:

- whether left and right lengths are constrained equal;
- nominal adjustment position;
- available adjustment range;
- minimum thread engagement;
- tolerance and uncertainty;
- whether static toe is established by tie-rod adjustment or another feature.

### 5.3 Rack `C-factor`

`C-factor` is not accepted as a canonical name until its source definition is recovered. The expected interpretation is rack displacement per pinion revolution, but the implementation must store an explicit quantity and unit such as `m/rad`, `mm/rev`, or an equivalent gear relation. It must not be conflated with steering-wheel-to-road-wheel ratio.

## 6. Requirement and variable classification

Every user-entered value receives one role. The optimizer must never infer the role from where a value appears in the UI.

| Role | Meaning | Solver treatment |
|---|---|---|
| Fixed parameter | Known value for the selected vehicle/configuration | Held constant |
| Design variable | Value the solver may change | Bounded continuous variable |
| Discrete option | Catalog part, rack, hole, or architecture choice | Enumerated or mixed-variable search |
| Hard equality | Must be met within numerical tolerance | Feasibility constraint |
| Hard lower/upper bound | Must never be violated | Feasibility constraint |
| Acceptable band | Preferred range; values outside are allowed only with an explicit penalty | Soft constraint |
| Target value | Preferred point with weighting and tolerance | Objective contribution |
| Target curve | Preferred relationship across a sweep or operating envelope | Objective contribution |
| Derived output | Calculated, never independently entered for the same configuration | Reported result |
| Report-only metric | Used for comparison or review, not optimization | Reported result |

An acceptable band may be promoted to a hard band. A hard constraint must never be silently relaxed by the solver.

## 7. Initial parameter-role recommendations

These are recommendations, not frozen classifications.

| Legacy item | Recommended canonical treatment |
|---|---|
| Rack `C-factor` | Fixed parameter, bounded design variable, or discrete rack choice depending on procurement freedom |
| Rack distance from front axle | Body-frame rack coordinate; fixed or bounded design variable |
| Ideal left/right turn angles | Low-speed reference or target curve, not automatically a hard requirement |
| Maximum left/right turn angles | Separate maximum allowed angle, minimum required capability, or target band; the user must select which |
| Steering-arm length | Derived from pickup geometry or bounded design variable; length alone is insufficient |
| Tie-rod length | Usually a derived output; may be bounded by available hardware and adjustment range |
| Minimum turning radius | Hard maximum radius or minimum turning capability for rules/packaging |
| Ackermann percentage | Reported comparison metric only until its definition is frozen |
| Steering ratio | Derived function of input; a desired range may be a soft or hard requirement |

## 8. Solver modes

### 8.1 Evaluate

Evaluate one defined geometry over the requested input sweep. No optimization.

### 8.2 Legacy reproduction

Use recovered legacy inputs and reproduce the CAD motion-study maps. This mode exists for migration verification and must preserve the external artifact revision.

### 8.3 Constrained inverse design

Find geometry satisfying hard constraints while minimizing weighted target errors.

### 8.4 Robust inverse design

Evaluate tolerances, setup uncertainty, and manufacturing variation. Optimize nominal geometry with constraint margins rather than only nominal feasibility.

### 8.5 Multiobjective exploration

Return a Pareto set where tradeoffs are real, such as Ackermann-curve tracking versus steering-ratio variation, packaging margin, joint articulation, or tolerance sensitivity. The software should not hide these tradeoffs in one unexplained scalar score.

## 9. Objective hierarchy

The optimizer must support progressively more useful targets without changing its geometry interface.

### Level 0 — mechanism closure

- rigid link lengths close;
- correct mechanism branch is maintained;
- output is continuous and monotonic where required;
- no singularity or invalid geometry occurs.

### Level 1 — low-speed kinematic target

- match ideal Ackermann or another specified inner/outer relation;
- satisfy minimum-turning-radius capability;
- satisfy maximum wheel-angle and rack-travel limits.

### Level 2 — prescribed steering map

- match a user-defined inner-versus-outer or road-wheel-versus-input target curve;
- control local steering-ratio variation;
- preserve left/right symmetry or a documented intended asymmetry.

### Level 3 — tire-informed operating envelope

- minimize front-tire slip or force mismatch across weighted operating points;
- permit parallel or anti-Ackermann behavior where justified by tire loads and slips;
- retain low-speed turning capability as a boundary condition.

Level 3 depends on reviewed tire and vehicle operating-point models and is not part of the first implementation authorization.

## 10. Hard-constraint candidates

The model must support, where applicable:

- rack travel and housing limits;
- minimum and maximum road-wheel angles;
- minimum turning capability;
- tie-rod available length and adjustment range;
- minimum thread engagement;
- rod-end or spherical-joint articulation limits;
- steering-arm, wheel, brake, upright, rack, and chassis clearance;
- no linkage singularity or branch switch;
- monotonic road-wheel response;
- required left/right symmetry at rack center;
- allowable static toe at rack center;
- rack, arm, and pickup packaging envelopes;
- manufacturing and serviceability bounds;
- applicable competition-rule constraints.

Clearance constraints require geometry evidence or an external CAD adapter. A scalar placeholder must not be presented as verified clearance.

## 11. Soft-target candidates

- target inner/outer curve;
- Ackermann reference error over a selected low-speed range;
- desired local or secant steering-ratio band;
- steering-ratio smoothness;
- desired rack travel usage;
- preferred tie-rod length or catalog hardware;
- preferred rack and steering-arm locations;
- tolerance robustness;
- later: tire-force utilization and slip-angle mismatch over weighted operating points.

Each objective term must expose its units, normalization, weighting, sweep domain, and reason for inclusion.

## 12. Required outputs

The first integrated workflow should directly report:

### Geometry result

- complete selected/optimized geometry;
- nominal left and right tie-rod center-to-center lengths;
- adjustment range and constraint margin;
- selected rack `C-factor` or gear relation;
- rack coordinates, width, and travel;
- steering-arm pickup coordinates and derived arm length;
- active assumptions and model revision.

### Steering maps

- steering-wheel angle versus rack displacement;
- rack displacement versus left and right road-wheel steer angle;
- steering-wheel angle versus left and right road-wheel steer angle;
- inside road-wheel angle versus outside road-wheel angle for both turn directions;
- local derivatives and secant ratios;
- valid interpolation range and extrapolation prohibition.

### Ackermann and turning metrics

- ideal low-speed Ackermann reference;
- absolute and normalized Ackermann error versus input;
- any retained Ackermann coefficient with its exact definition;
- turning radius versus steering input under stated kinematic assumptions;
- full-lock and required-turning-radius margins.

### Optimization diagnostics

- feasibility status;
- active and violated constraints;
- margin to every hard constraint;
- objective contributions before and after optimization;
- initialization and solver status;
- alternative feasible solutions or Pareto candidates;
- parameter sensitivities and tolerance robustness.

### Evidence exports

- table export suitable for calculator migration and review;
- geometry and curve plots;
- versioned data export for CAD, OptimumK, ADAMS, or other external comparison;
- provenance linking every result to the source vehicle configuration and requirement set.

## 13. First implementation scope

The first authorized implementation should be deliberately limited to:

- rigid links and joints;
- nominal ride-height configuration;
- exact planar or reviewed spatial steering kinematics;
- symmetric rack-and-pinion architecture unless asymmetry is explicitly enabled;
- direct input sweeps without polynomial replacement of the mechanism;
- fixed, bounded, hard, soft, derived, and report-only parameter roles;
- low-speed Ackermann and user-defined target curves;
- deterministic constrained optimization;
- complete constraint and solver diagnostics;
- import of the recovered CAD motion study for comparison only.

Explicit first-release exclusions:

- suspension bump/rebound and roll sweeps;
- bump steer optimization;
- steering compliance, backlash, friction, and loads;
- tire-force-informed target generation;
- transient steering response;
- learned or reinforcement-learning optimizer;
- automatic CAD collision checking.

The interface must allow those higher-fidelity models to be added later without changing canonical quantity meanings.

## 14. Verification plan

### A — dimensional and algebraic

- all geometry and angle units are explicit;
- zero rack displacement reproduces the defined nominal toe;
- tie-rod distances close to numerical tolerance;
- steering-wheel, pinion, rack, and road-wheel ratios remain distinct.

### B — limiting and symmetry cases

- left/right mirror symmetry;
- zero steering input;
- parallel-steer linkage case;
- ideal Ackermann reference case;
- very long tie-rod or other reviewed limiting geometry;
- approach to singularity is detected and not crossed silently;
- reversing the turn direction mirrors outputs under symmetric geometry.

### C — published analytical references

- ideal Ackermann geometry at selected wheelbase and track;
- trapezoidal steering-linkage examples where sufficiently specified.

### D — independent implementation

- independent geometry calculation or hand-derived test fixture.

### E — cross-tool

- recovered SolidWorks motion-study sweep;
- optional OptimumK, ADAMS, or other mechanism model with identical geometry and conventions.

### F — physical evidence

- measured rack displacement and left/right wheel angles on the car or a steering fixture;
- uncertainty from setup, sensor calibration, compliance, and measurement method reported separately from rigid-model error.

## 15. Acceptance gate before code

No implementation work is authorized until:

1. the legacy optimizer and motion-study source artifacts are recovered or formally declared unavailable;
2. `C-factor`, steering input, road-wheel angle, tie-rod length, rack location, and steering-arm geometry definitions are resolved;
3. the reference coordinate system and signs are reviewed;
4. fixed values, design variables, hard constraints, acceptable bands, objectives, and derived outputs are assigned for the WUFR use case;
5. the intended first-release geometry fidelity is selected;
6. legacy benchmark inputs and expected output curves are frozen with provenance;
7. the Ackermann metric definitions and low-speed assumptions are documented;
8. the initial analytical and limiting-case benchmark list is reviewed;
9. known packaging and joint constraints have owners and evidence paths;
10. the result schema and failure reporting are accepted.

## 16. Relationship to other migration items

- `MIG-SC26-0001`: replaces the manual bridge between the `Steer Ratio` and `Ackerman Steering` sheets.
- Future tire model records: provide Level 3 tire-informed target curves.
- Future suspension kinematics records: add bump/rebound/roll states and bump-steer constraints.
- Future steering-force and compliance records: add loaded steering maps and steering effort without altering the rigid geometry outputs.

## 17. Literature audit direction

The steering design must not assume that ideal Ackermann is universally optimal. Literature review should separately document:

- low-speed kinematic Ackermann geometry;
- practical trapezoidal tie-rod linkage behavior;
- static and dynamic toe definitions;
- relative tire slip angles at race-car operating conditions;
- steering ratio as a function rather than one scalar;
- geometry errors produced by suspension motion;
- the distinction between unloaded kinematics and loaded/compliant steering response.

Equation-level citations and page references belong in the later model and equation records.