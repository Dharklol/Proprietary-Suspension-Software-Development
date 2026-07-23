# Steering Optimizer Architecture

**Model split:** `MOD-STEER-0001` is the authoritative rigid steering evaluator. `MOD-STEER-0002` is the inverse-design orchestration layer.

## Purpose

The final steering workflow is intended to replace the historical sequence of separate geometry calculations, CAD motion studies, copied response curves, spreadsheets, and manual ranking with one traceable inverse-design environment. The final environment begins with fixed vehicle geometry, selected design freedoms, packaging and hardware boundaries, performance targets, operating states, and uncertainty definitions. It returns multiple feasible steering geometries with complete kinematic maps, state-dependent response, constraint margins, sensitivities, ranking explanations, and exportable evidence.

Development proceeds by adding fidelity around one verified steering kernel. The nominal optimizer, suspension-pose provider, and operating-state target layer all retain the same geometry generator and `MOD-STEER-0001` closure/projection implementation. Tire target generation, effort, robustness, and physical identification remain separate providers.

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

Suspension-state evaluation extends that same path:

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

`P1-STR-006C` adds targets after that evaluation rather than changing it:

```text
complete multi-state analyzer response
        +
OperatingStateTargetSet
(explicit state roles, curves, weights, authority)
        |
        v
per-state raw RMS objective J_k
        |
        v
per-state normalized contribution W_k * J_k / S_k
        |
        v
visible aggregate used by the existing deterministic search
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

The code resolves these roles from data. No coordinate is permanently hard-coded as fixed or variable. A future study can freeze the steering arm while varying only rack placement, fix the rack and vary one upright hole, enumerate racks or rod ends, or enable independent sides through a separately reviewed requirement set.

Operating-state targets use the same principle at the state level. A suspension state is explicitly `objective` or `report_only`; the existence of a nominal target does not assign a target to another pose.

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

The provider therefore supplies the location and orientation of the upright reference frame before the tie rod resolves the steering degree of freedom. Steering axes, outer tie-rod pickups, and wheel-plane references move with the upright transform. Rack geometry and rack inner joints remain chassis-fixed. `MOD-STEER-0001` then solves tie-rod closure at rack center and across the requested rack sweep.

A source that already contains tie-rod-induced toe or bump-steer response is not a valid unresolved pose input because feeding it into the closure solver would double count steering. Such a source can instead be retained as comparison or validation evidence.

The provider is intentionally source-agnostic. Reviewed OptimumK exports, CAD motion results, explicit lookup tables, or a future native suspension solver may all feed the same contract after their coordinate frame, steering-DOF treatment, state definitions, and authority are documented.

## Target-provider interfaces

The optimizer receives targets through providers rather than embedding one design philosophy.

### Nominal/sampling target

A `SteeringTarget` contains:

- input coordinate and unit;
- rack sampling domain;
- left/right requested response for a nominal target study;
- sample weights;
- normalization and objective weight;
- alignment/convention adapter;
- source and authority.

The corrected WUFR-26/27 response remains a regression and audit fixture, not a permanent optimum. Alternative providers may supply geometric Ackermann, manually specified wheel maps, ratio or gain bands, turning-capability requirements, and later tire-informed targets.

For suspension-state studies the existing `SteeringTarget` may provide only the shared rack sampling and nominal alignment basis. Its requested wheel-angle values are not automatically applied to non-nominal poses.

### Operating-state target set

An `OperatingStateTargetSet` identifies the pose set and assigns each targeted state:

- role: `objective` or `report_only`;
- left/right requested incremental heading curves;
- sample weights;
- normalization scale `S_k`;
- objective/state weight `W_k`;
- convention sign adapter;
- optional monotonicity rule;
- source type, source path, authority, and provenance.

The first contract requires:

```text
unlisted_state_role = report_only
```

so omission never copies the nominal target into another state.

For objective state `k`, the raw two-wheel weighted RMS is

```text
J_k = sqrt(
    sum_i w_ki * 0.5 * [
        (delta_L_ki - delta_L_ki*)^2
      + (delta_R_ki - delta_R_ki*)^2
    ]
    / sum_i w_ki
)
```

and the current convenience aggregate is

```text
J_total = sum_k W_k * (J_k / S_k)
```

Every `J_k`, `W_k`, `S_k`, domain, residual summary, and authority remains visible. This aggregate is a documented team optimization method, not a claim that the chosen weights are a physical law or a complete Pareto representation.

## Provider interfaces and current status

| Provider | Responsibility | Current behavior |
|---|---|---|
| Suspension pose | Zero-steer upright pose, steering-axis transform, wheel-plane transform, and upright-bound pickup transform for named suspension states | Provider-neutral contract implemented; synthetic identity/bump/opposed-travel states only |
| Steering target | Nominal or state-indexed wheel-heading targets, weights, operating domains, and source authority | Historical/analyzer nominal targets plus explicit/analyzer-generated operating-state target sets implemented |
| Tire/vehicle target generation | Generate reviewed operating-state steering targets and weights from tire/vehicle objectives | Not implemented; future provider |
| Rack load / effort | Rack force or column torque envelope by operating state | Unavailable and excluded from score |
| Uncertainty | Parameter distributions or bounded perturbations | Unavailable; no robustness claim |
| Physical parameter | Calibrated transmission, deadband, compliance, and as-built offsets | Explicitly deferred; rigid outputs remain uncorrected |

Native suspension, tire, load, or measurement models may later implement these contracts. The steering optimizer does not depend on their internal formulation.

## Constraint treatment

Mechanism closure, branch continuity, no singularity crossing, monotonicity where explicitly required, rack travel, and numerical domain are hard constraints. Packaging, articulation, thread engagement, physical stops, and manufacturing bounds become hard constraints only after their geometry and authority are supplied. Missing evidence returns an unavailable constraint rather than a fictional margin.

All states in a supplied `SuspensionPoseSet` remain mechanism-feasibility checks, even when their target role is report-only. A failed state makes the candidate infeasible; target performance at other states cannot offset it.

The current supplemental hardware constraints screen nominal retained candidates. They do not yet act on every multi-state search evaluation. Hardware-feasible multi-state optimization remains gated on reviewed hardware geometry and limits.

## Search and candidate comparison

The first optimizer uses deterministic constrained methods and multi-start exploration. The implementation documents algorithm version, tolerances, scaling, initialization, failure behavior, and benchmark evidence.

`run_operating_state_inverse_design` reuses the nominal bounded coordinate-pattern search helpers. The variable normalization, starts, polling, step contraction, infeasible handling, and termination rules are unchanged. Only the candidate-evaluation adapter changes from one nominal target to the explicit state-objective aggregate.

The workflow returns a candidate set. It may provide a convenience ranking, but each candidate keeps its individual state objectives, units, normalization, state weights, constraint margins, pose-state results, and source provenance. A future true multiobjective/Pareto layer remains separate from the current scalar convenience ranking.

## Verification ladder

1. **Geometry generation:** zero offsets reproduce the baseline evaluator geometry exactly.
2. **Evaluator preservation:** a generated baseline candidate produces tolerance-identical `MOD-STEER-0001` results.
3. **Synthetic nominal recovery:** known target curves generated from a synthetic geometry are recovered within reviewed tolerances.
4. **Historical recovery:** the optimizer reproduces the WUFR-26/27 response with one or more feasible candidates and reports nonuniqueness rather than assuming hardpoint identity.
5. **Constraint benchmarks:** deliberate invalid candidates fail with named margins and no objective score promotion.
6. **Repeatability:** fixed configuration and seed return the same candidate archive and ranking.
7. **Pose identity:** the identity suspension pose reproduces the nominal analyzer sweep.
8. **Pose transformation:** synthetic suspension translations move upright-bound geometry while leaving the rack and tie-rod design length unchanged.
9. **Multi-state closure:** each synthetic pose is solved through `MOD-STEER-0001`, producing explicit dynamic-toe and singularity results without a second steering model.
10. **Target-role isolation:** omitted states remain report-only and do not inherit a nominal objective.
11. **State objective decomposition:** each objective state preserves its raw RMS, normalization, state weight, residual summary, and authority.
12. **Synthetic multi-state recovery:** the shared deterministic search recovers a known source geometry from several state targets with a frozen candidate archive.
13. **Later source comparison:** a reviewed OptimumK/CAD/native-solver pose adapter is compared against the same canonical contract.
14. **Later vehicle/tire target comparison:** reviewed tire/vehicle target generation replaces synthetic targets without changing the steering kernel.
15. **Later physical correlation:** 2027 measurements assess installed transmission and wheel response without redefining the rigid equations.

## Literature basis

The rigid geometry and derived steering quantities continue to use the equation-level sources already frozen for `MOD-STEER-0001`. Guiggiani, *The Science of Vehicle Dynamics*, Sections 3.4.1-3.4.3 support exact low-speed Ackermann as a reference while distinguishing it from the best steering geometry for actual tire operating conditions.

Guiggiani Section 3.14.6 explicitly makes wheel steer a function of steering input and suspension roll angle when roll steer exists, while Gillespie Chapter 8 describes steering geometry errors, toe change, and roll steer from suspension motion. These sources support state-indexed steering evaluation.

Guiggiani Sections 3.4.2-3.4.3 also explain that static/dynamic toe alter tire slips and lateral-force directions and that the relative front-tire slips depend on the vehicle velocity-center position. This supports a replaceable operating-state target provider rather than a universal Ackermann target.

Romano, *Multi-Body Modelling and Mechanical Analysis of a Steering System*, supports the staged sequence of verified steering assembly -> configuration comparison -> suspension integration -> full-vehicle validation.

Huang et al., “Find Optimal Suspension Kinematics Targets for Vehicle Dynamics Using Reinforcement Learning,” notes that kinematic target achievement does not itself establish physical feasibility. Mechanism, packaging, articulation, manufacturing, and robustness therefore remain separate gates.

Milliken and Milliken and Pacejka remain the planned basis for later race-car tire operating targets, load sensitivity, combined slip, and handling tradeoffs. Those future models generate target-provider outputs; they do not replace the rigid steering mechanism equations.

## Promotion boundary

The current steering optimizer, pose-provider, and operating-target work are exploratory engineering tools after their code and benchmark gates pass. Synthetic suspension poses and state weights establish software composition only. WUFR-28 selection still requires reviewed suspension-state inputs, vehicle/tire target authority, packaging, hardware, manufacturing, effort/load, robustness, and later physical-correlation evidence plus focused release authority.
