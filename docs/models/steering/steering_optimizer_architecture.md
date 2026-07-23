# Steering Optimizer Architecture

**Model split:** `MOD-STEER-0001` is the authoritative rigid steering evaluator. `MOD-STEER-0002` is the inverse-design orchestration layer.

## Purpose

The final steering workflow is intended to replace the historical sequence of separate geometry calculations, CAD motion studies, copied response curves, spreadsheets, and manual ranking with one traceable inverse-design environment. The final environment begins with fixed vehicle geometry, selected design freedoms, packaging and hardware boundaries, performance targets, and uncertainty definitions. It returns multiple feasible steering geometries with complete kinematic maps, constraint margins, sensitivities, ranking explanations, and exportable evidence.

The first optimizer release was deliberately narrower than that end state. It operated at one nominal suspension pose with rigid links and joints. The next provider layer retains the same geometry and evaluator contracts while permitting a candidate to be evaluated at externally supplied suspension poses. Tire targets, effort, robustness, and physical-identification layers remain separate later providers.

## Cohesive model composition

The optimizer is not permitted to contain another steering model. Its nominal execution path is:

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
candidate archive, alternatives, and transparent ranking
```

Suspension-state evaluation extends that same path rather than replacing it:

```text
generated nominal candidate
        +
canonical SuspensionPoseSet
(zero-steer upright poses only)
        |
        v
apply left/right rigid upright transforms
        |
        v
posed SteeringGeometry
(rack remains chassis-fixed)
        |
        v
MOD-STEER-0001 tie-rod closure and sweep
        |
        v
pose-dependent wheel heading, dynamic toe,
gain, branch, and singularity diagnostics
```

The geometry generator and pose adapter may create or transform points, axes, wheel references, roles, and metadata. They may not calculate steering response themselves. Closure, branch continuation, singularity diagnostics, wheel-plane projection, local gain, ratio, Ackermann reference/error, and turning-path quantities remain functions of `MOD-STEER-0001`. Candidate and pose-state reports retain the evaluator outputs rather than only reduced scores.

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

The code resolves these roles from data. No coordinate is permanently hard-coded as fixed or variable. A future study can therefore freeze the steering arm while varying only rack placement, fix the rack and vary one upright hole, enumerate racks or rod ends, or enable independent sides through a separately reviewed requirement set.

## First geometry boundary

The first release fixes wheel centers, wheel-plane references, steering-axis lines, upright poses, suspension hardpoints, wheelbase, steering-axis track definition, static alignment, and rack-axis direction. It varies rack longitudinal and vertical location, rack inner-joint half-spacing, and the outer tie-rod pickup in an upright-local coordinate system.

The outer pickup uses three local coordinates, but depth is tightly bounded. The default development requirement set permits only a small depth change because unconstrained movement normal to the intended steering-arm region can create kinematically attractive but structurally or geometrically implausible concepts. The same coordinate can be set to `fixed_parameter` in a study where the upright and steering arm are carried over.

Left and right design geometry are exact reflections in the first implementation. The schema retains side identity and can support separately parameterized sides later, but intentional design asymmetry requires a new requirement set and explicit engineering rationale. Operating suspension poses may be asymmetric because independent wheel travel is a vehicle state rather than an intentional left/right design asymmetry.

Tie-rod joint-center length is derived at the nominal reference state:

```text
L_TR,j = ||p_out,j - p_in,j||
```

That length remains fixed when a suspension pose is applied. At a non-nominal suspension pose the transformed zero-steer upright geometry is not required to satisfy tie-rod closure at zero steering rotation; the steering rotation required to restore the fixed tie-rod length is solved by `MOD-STEER-0001`.

## Suspension-pose provider interface

A `SuspensionPoseSet` contains named operating states. Each state supplies:

- left and right rigid transforms from the nominal upright reference frame;
- named state coordinates and units, such as left/right wheel vertical displacement, heave, roll, or pitch descriptors;
- source type, source path, revision/authority metadata;
- an explicit steering-DOF declaration.

The mandatory first-provider rule is:

```text
upright_reference_pose_excludes_tie_rod_steering_rotation
```

The provider therefore supplies the location and orientation of the upright reference frame before the tie rod resolves the steering degree of freedom. Steering axes, outer tie-rod pickups, and wheel-plane references move with the upright transform. Rack geometry and rack inner joints remain chassis-fixed. `MOD-STEER-0001` then solves the tie-rod closure at rack center and across the requested rack sweep.

A source that already contains tie-rod-induced toe or bump-steer response is not a valid unresolved pose input because feeding it into the closure solver would double count steering. Such a source can instead be retained as comparison or validation evidence.

The provider is intentionally source-agnostic. Reviewed OptimumK exports, CAD motion results, explicit lookup tables, or a future native suspension solver may all feed the same contract after their coordinate frame, steering-DOF treatment, state definitions, and authority are documented.

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

The suspension-pose benchmark may reuse an existing target's rack sample domain and nominal alignment basis without applying that target's requested wheel-angle values as objectives at non-nominal poses. A later multi-state target contract will explicitly identify which operating states carry objective weights.

## Provider interfaces and current status

| Provider | Responsibility | Current behavior |
|---|---|---|
| Suspension pose | Zero-steer upright pose, steering-axis transform, wheel-plane transform, and upright-bound pickup transform for named suspension states | Provider-neutral contract implemented; synthetic identity/bump/opposed-travel states only |
| Steering target | Wheel-heading targets, weights, and operating domains | Historical and analyzer-generated targets implemented |
| Rack load / effort | Rack force or column torque envelope by operating state | Unavailable and excluded from score |
| Uncertainty | Parameter distributions or bounded perturbations | Unavailable; no robustness claim |
| Physical parameter | Calibrated transmission, deadband, compliance, and as-built offsets | Unavailable; rigid outputs remain uncorrected |

Native suspension, tire, load, or measurement models may later implement these contracts. The steering optimizer does not depend on their internal formulation.

## Constraint treatment

Mechanism closure, branch continuity, no singularity crossing, monotonicity where required, rack travel, and numerical domain are hard constraints. Packaging, articulation, thread engagement, physical stops, and manufacturing bounds become hard constraints only after their geometry and authority are supplied. Missing evidence returns an unavailable constraint rather than a fictional margin.

A hard-constraint violation makes a candidate infeasible. It cannot be offset by target accuracy or hidden inside a weighted penalty. Candidate diagnostics must identify the constraint, evaluated state, value, limit, margin, and source.

The current supplemental hardware constraints screen nominal retained candidates. They do not yet act on every multi-state search evaluation. Hardware-feasible multi-state optimization remains gated on reviewed hardware geometry and limits.

## Search and candidate comparison

The first optimizer uses deterministic constrained methods and multi-start exploration. The implementation documents algorithm version, tolerances, scaling, initialization, failure behavior, and benchmark evidence.

The workflow returns a candidate set. It may provide a convenience ranking, but each candidate keeps its individual objective values, units, normalization, constraint margins, sensitivity information, and pose-state results where evaluated. Nondominated or separated alternatives remain visible so engineering tradeoffs are not hidden in one scalar score.

The first pose-provider PR evaluates candidate behavior over states but does not yet add multi-state objective terms to the coordinate-pattern search. That separation prevents an arbitrary synthetic pose fixture from becoming a design target merely because it exists.

## Verification ladder

1. **Geometry generation:** zero offsets reproduce the baseline evaluator geometry exactly.
2. **Evaluator preservation:** a generated baseline candidate produces tolerance-identical `MOD-STEER-0001` results.
3. **Synthetic recovery:** known target curves generated from a synthetic geometry are recovered within reviewed tolerances.
4. **Historical recovery:** the optimizer reproduces the WUFR-26/27 response with one or more feasible candidates and reports nonuniqueness rather than assuming hardpoint identity.
5. **Constraint benchmarks:** deliberate invalid candidates fail with named margins and no objective score promotion.
6. **Repeatability:** fixed configuration and seed return the same candidate archive and ranking.
7. **Pose identity:** the identity suspension pose reproduces the nominal analyzer sweep.
8. **Pose transformation:** synthetic suspension translations move upright-bound geometry while leaving the rack and tie-rod design length unchanged.
9. **Multi-state closure:** each synthetic pose is solved through `MOD-STEER-0001`, producing explicit dynamic-toe and singularity results without a second steering model.
10. **Later source comparison:** a reviewed OptimumK/CAD/native-solver pose adapter is compared against the same canonical contract.
11. **Later physical correlation:** 2027 measurements assess installed transmission and wheel response without redefining the rigid equations.

## Literature basis

The rigid geometry and derived steering quantities continue to use the equation-level sources already frozen for `MOD-STEER-0001`. Guiggiani, *The Science of Vehicle Dynamics*, supports exact low-speed Ackermann as a reference and distinguishes it from the best steering geometry for tire operating conditions. Gillespie, *Fundamentals of Vehicle Dynamics*, supports explicit rack-and-pinion linkage geometry, trapezoidal steering behavior, steering ratio, steering geometry errors, and state-specific wheel-alignment terminology.

Gillespie's definition of toe at a specified wheel load or relative wheel-center position supports treating toe as suspension-state dependent when wheel position changes. Guiggiani's handling treatment identifies roll steer and toe as setup/suspension parameters that influence axle behavior. These sources support explicit suspension-state steering maps rather than folding all behavior into one nominal curve.

Romano, *Multi-Body Modelling and Mechanical Analysis of a Steering System*, compares steering configurations using steering-angle and steering-ratio functions and then applies the steering model in suspension/full-vehicle validation. This supports the staged sequence of verified steering assembly -> candidate comparison -> suspension-state integration -> later full-vehicle and physical correlation.

Huang et al., “Find Optimal Suspension Kinematics Targets for Vehicle Dynamics Using Reinforcement Learning,” notes that kinematic target achievement does not itself establish physical feasibility. This continues to support separate mechanism, packaging, articulation, manufacturing, and later robustness gates.

Milliken and Milliken and Pacejka remain the planned basis for later race-car tire operating targets, load sensitivity, combined slip, and handling tradeoffs. Those sources belong to the future target-provider layer, not the rigid pose adapter.

## Promotion boundary

The current steering optimizer and pose-provider work are exploratory engineering tools after their code and benchmark gates pass. Synthetic suspension poses establish software composition only. WUFR-28 selection still requires reviewed suspension-state inputs, packaging, hardware, manufacturing, tire/effort, robustness, and later physical-correlation evidence plus focused release authority.
