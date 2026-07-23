# Steering Optimizer Architecture

**Model split:** `MOD-STEER-0001` is the authoritative rigid steering evaluator. `MOD-STEER-0002` is the inverse-design orchestration layer.

## Purpose

The final steering workflow is intended to replace the historical sequence of separate geometry calculations, CAD motion studies, copied response curves, spreadsheets, and manual ranking with one traceable inverse-design environment. The final environment begins with fixed vehicle geometry, selected design freedoms, packaging and hardware boundaries, performance targets, and uncertainty definitions. It returns multiple feasible steering geometries with complete kinematic maps, constraint margins, sensitivities, ranking explanations, and exportable evidence.

The first optimizer release is deliberately narrower than that end state. It operates at one nominal suspension pose with rigid links and joints, but its interfaces and result schema are chosen so suspension-state, tire-target, effort, robustness, and physical-identification layers can be added without replacing the geometry or evaluator contracts.

## Cohesive model composition

The optimizer is not permitted to contain another steering model. Its execution path is:

```text
named baseline geometry
+ named requirement set
+ candidate design vector
        |
        v
role resolver and parametric geometry generator
        |
        v
public SteeringGeometry contract from MOD-STEER-0001
        |
        v
existing rigid analyzer sweep and diagnostics
        |
        v
constraint evaluation and target comparison
        |
        v
candidate archive, nondominated set, and transparent ranking
```

The geometry generator may create points, axes, roles, and derived tie-rod lengths. It may not calculate wheel response itself. Closure, branch continuation, singularity diagnostics, wheel-plane projection, local gain, ratio, Ackermann reference/error, and turning-path quantities remain functions of `MOD-STEER-0001`. A candidate report must retain the evaluator outputs rather than only a reduced optimization score.

This composition preserves the verification already completed for `EQ-STEER-0001` through `EQ-STEER-0007` and prevents later optimizer work from drifting into a separate convention or numerical implementation.

## Parameter-role architecture

Every parameter has one role inside a named requirement set:

| Role | Meaning in one study |
|---|---|
| `fixed_parameter` | Held at the stated value. |
| `bounded_design_variable` | Changed continuously within explicit bounds. |
| `discrete_option` | Selected from a named finite set. |
| `derived_output` | Calculated from the selected geometry and not independently specified. |
| `hard_equality` | Must be met within a stated numerical tolerance. |
| `hard_lower_bound` / `hard_upper_bound` | May not be violated. |
| `acceptable_band` | Preference with a visible penalty outside the band. |
| `target_value` / `target_curve` | Objective contribution with units, normalization, domain, and authority. |
| `report_only` | Calculated for review but not used for ranking. |
| `evidence_only` | Historical or physical evidence that does not become a solver input by presence alone. |

The code must resolve these roles from data. No coordinate is permanently hard-coded as fixed or variable. A future study can therefore freeze the steering arm while varying only rack placement, fix the rack and vary one upright hole, enumerate racks or rod ends, or enable independent sides through a separately reviewed requirement set.

## First geometry boundary

The first release fixes wheel centers, wheel-plane references, steering-axis lines, upright poses, suspension hardpoints, wheelbase, steering-axis track definition, static alignment, and rack-axis direction. It varies rack longitudinal and vertical location, rack inner-joint half-spacing, and the outer tie-rod pickup in an upright-local coordinate system.

The outer pickup uses three local coordinates, but depth is tightly bounded. The default development requirement set permits only a small depth change because unconstrained movement normal to the intended steering-arm region can create kinematically attractive but structurally or geometrically implausible concepts. The same coordinate can be set to `fixed_parameter` in a study where the upright and steering arm are carried over.

Left and right geometry are exact reflections in the first implementation. The schema retains side identity and can support separately parameterized sides later, but intentional asymmetry requires a new requirement set and explicit engineering rationale.

Tie-rod joint-center length is derived at the reference state:

```text
L_TR,j = ||p_out,j - p_in,j||
```

This is the same reference-length definition used by the existing evaluator specification. The workflow must not accept arbitrary reference joint coordinates and a contradictory independent tie-rod length without returning an inconsistency.

## Target-provider interface

The optimizer receives targets through a provider rather than embedding one design philosophy. A target response contains:

- left/right or inside/outside signal identities;
- input coordinate and unit;
- target values or bands;
- point or operating-state weights;
- validity domain and no-extrapolation rule;
- source and revision;
- whether the target is historical regression, exact geometric reference, manually authored intent, or later tire-informed output.

The first development target is the corrected WUFR-26/27 nominal response used in the audit. It is a regression and recovery fixture, not a permanent optimum. Alternative providers may supply geometric Ackermann, manually specified wheel maps, ratio or gain bands, turning-capability requirements, and later tire-informed targets.

## Future provider interfaces

The first release uses one nominal pose and no internal load model, but the architecture reserves the following inputs:

| Provider | Future responsibility | First-release behavior |
|---|---|---|
| Suspension pose | Upright pose, steering axis, wheel basis, and pickup transforms for heave/roll/pitch/independent travel states | Returns the baseline pose only |
| Steering target | Wheel-heading targets, weights, and operating domains | Historical or user-supplied table |
| Rack load / effort | Rack force or column torque envelope by operating state | Unavailable and excluded from score |
| Uncertainty | Parameter distributions or bounded perturbations | Unavailable; no robustness claim |
| Physical parameter | Calibrated transmission, deadband, compliance, and as-built offsets | Unavailable; rigid outputs remain uncorrected |

Native suspension, tire, load, or measurement models may later implement these contracts. The steering optimizer should not depend on their internal formulation.

## Constraint treatment

Mechanism closure, branch continuity, no singularity crossing, monotonicity where required, rack travel, and numerical domain are hard constraints. Packaging, articulation, thread engagement, physical stops, and manufacturing bounds become hard constraints only after their geometry and authority are supplied. Missing evidence returns an unavailable constraint rather than a fictional margin.

A hard-constraint violation makes a candidate infeasible. It cannot be offset by target accuracy or hidden inside a weighted penalty. Candidate diagnostics must identify the constraint, evaluated state, value, limit, margin, and source.

## Search and candidate comparison

The first optimizer uses deterministic constrained methods and multi-start exploration. The authorization does not select a final numerical package; the implementation PR must document the algorithm, version, tolerances, scaling, initialization, failure behavior, and benchmark evidence.

The workflow returns a candidate set. It may provide a convenience ranking, but each candidate keeps its individual objective values, units, normalization, constraint margins, and sensitivity information. Nondominated or near-nondominated alternatives remain visible so engineering tradeoffs are not hidden in one scalar score.

## Verification ladder

1. **Geometry generation:** zero offsets reproduce the baseline evaluator geometry exactly.
2. **Evaluator preservation:** a generated baseline candidate produces bitwise-identical or tolerance-identical `MOD-STEER-0001` results.
3. **Synthetic recovery:** known target curves generated from a synthetic geometry are recovered within reviewed tolerances.
4. **Historical recovery:** the optimizer reproduces the WUFR-26/27 response with one or more feasible candidates and reports nonuniqueness rather than assuming hardpoint identity.
5. **Constraint benchmarks:** deliberate invalid candidates fail with named margins and no objective score promotion.
6. **Repeatability:** fixed configuration and seed return the same candidate archive and ranking.
7. **Later physical correlation:** 2027 measurements assess installed transmission and wheel response without redefining the rigid equations.

## Literature basis

The rigid geometry and derived steering quantities continue to use the equation-level sources already frozen for `MOD-STEER-0001`. Guiggiani, *The Science of Vehicle Dynamics* (2022), Chapter 3, Sections 3.4.1 through 3.4.3, supports exact low-speed Ackermann as a reference and distinguishes it from the best steering geometry for tire operating conditions. Gillespie, *Fundamentals of Vehicle Dynamics*, Chapter 8, supports explicit rack-and-pinion linkage geometry, trapezoidal steering behavior, steering ratio, and steering geometry errors. These sources justify retaining exact mechanism evaluation and treating Ackermann as one possible target rather than a universal optimum.

Romano, *Multi-Body Modelling and Mechanical Analysis of a Steering System* (2022), Chapters 2 and 4, uses steering-angle and steering-ratio functions to compare configurations and then validates the steering assembly before applying it in suspension and full-vehicle tests. This supports the staged evaluator-first and configuration-comparison workflow.

Huang et al., “Find Optimal Suspension Kinematics Targets for Vehicle Dynamics Using Reinforcement Learning,” SAE International Journal of Vehicle Dynamics, Stability, and NVH 10(1), 2026, explicitly notes that generated kinematic target files do not guarantee a physically feasible suspension and that packaging checks must be considered with target generation. This supports keeping geometry feasibility and packaging as explicit constraints rather than relying only on reward or target matching. The paper also motivates reusable learned target-generation methods for later high-dimensional work, but does not replace the need for a deterministic verified baseline optimizer.

Milliken and Milliken and Pacejka remain the planned basis for later race-car tire operating targets, load sensitivity, combined slip, and handling tradeoffs. Those sources belong to the future target-provider layer, not the first rigid optimizer physics.

## Promotion boundary

The first optimizer is an exploratory engineering tool after its code and benchmark gates pass. It is not production geometry authority. WUFR-28 selection requires reviewed packaging, hardware, manufacturing, suspension-state, tire/effort, robustness, and physical-correlation evidence plus a later focused authorization.
