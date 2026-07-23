# Steering Operating-State Target Aggregation v0.1.0

**Task:** `P1-STR-006C`  
**Authorization:** `AUTH-STEER-0002`  
**Evaluator:** `MOD-STEER-0001`  
**Optimizer orchestration:** `MOD-STEER-0002`

## Purpose

This layer turns the provider-neutral suspension poses introduced by `P1-STR-006A/006B` into an explicit optimization domain. It does not create suspension kinematics or tire-optimal steering targets. Instead, it defines how an external or manually authored target provider can assign a requested steering response, weight, normalization, convention adapter, and authority to a named suspension state.

The execution path is:

```text
named steering candidate
        |
        v
provider-neutral suspension pose set
        |
        v
MOD-STEER-0001 complete rack sweep at every pose
        |
        v
explicit operating-state target table
        |
        v
per-state objective contributions
        |
        v
transparent weighted aggregate used by the existing deterministic search method
```

No steering closure, suspension motion, wheel-plane projection, tire-force, effort, or compliance equation is introduced in this layer.

## Literature basis

### Steering response depends on suspension state

Guiggiani, *The Science of Vehicle Dynamics* (2022), Section 3.14.6, writes the wheel steer angles with roll steer as

```text
delta_ij = delta_ij(delta_v, phi_is)
```

and Eq. (3.210) adds the suspension roll-steer term to static toe, steering ratio, and Ackermann/dynamic-toe terms. Chapter 7 carries the same dependence into handling analysis, where the wheel steer angles may depend on steering input and lateral acceleration through suspension roll. This directly supports treating suspension state as an explicit argument of the steering response rather than assuming one nominal steer curve applies everywhere.

Gillespie, *Fundamentals of Vehicle Dynamics*, Chapter 8, `Steering Geometry Error`, states that suspension motion can generate steering action because the body-mounted relay/tie-rod linkage and the wheel steering arm follow different motion paths. The `Toe Change` and `Roll Steer` subsections describe toe and systematic steer changes with jounce, rebound, and body roll. Gillespie's terminology section also defines static toe at a specified wheel load or relative wheel-center position. Together these support attaching steering targets and results to declared suspension states.

### The best target is not one universal Ackermann curve

Guiggiani, Sections 3.4.2 and 3.4.3, notes that selecting the best steering-geometry coefficients is not simple because static and dynamic toe alter tire slips, lateral-force values, and force directions. The relative front-tire slip angles depend on the vehicle velocity-center position, and the discussion distinguishes race-car operating conditions from low-lateral-acceleration road-car operation. This supports an architecture in which future tire/vehicle models generate state targets rather than hard-coding geometric Ackermann as the permanent objective.

Romano's staged steering workflow remains the integration precedent already recorded in the literature concordance: steering assembly behavior is established before suspension/full-vehicle integration. `P1-STR-006C` preserves that sequence by consuming the verified pose/evaluator outputs instead of replacing them.

## Target roles

Every supplied suspension state has one explicit role:

| Role | Meaning |
|---|---|
| `objective` | The state carries left/right target curves and contributes to ranking. |
| `report_only` | The state must still complete the analyzer sweep, but it contributes no target error. |

The first contract requires `unlisted_state_role = "report_only"`. Therefore omission can never silently copy the nominal target into another suspension state.

An objective state records:

- state ID;
- output quantity and unit;
- left and right requested response arrays;
- per-sample weights;
- normalization scale;
- state/objective weight;
- canonical-to-provider sign adapter;
- optional monotonic-response requirement and tolerance;
- source type, source path, authority, and provenance.

The shared rack sampling and nominal alignment definition continue to come from an explicit `SteeringTarget`. This keeps input-domain and alignment conventions synchronized with the existing steering evaluator while allowing the requested output to vary by suspension state.

## Objective calculation

For state `k` and rack sample `i`, let the provider-requested incremental headings be

```text
delta_L_ki* , delta_R_ki*
```

and let the headings calculated by the pose-transformed `MOD-STEER-0001` evaluation be

```text
delta_L_ki , delta_R_ki .
```

The raw state error is the weighted two-wheel RMS

```text
J_k = sqrt(
    sum_i w_ki * 0.5 * [
        (delta_L_ki - delta_L_ki*)^2
      + (delta_R_ki - delta_R_ki*)^2
    ]
    / sum_i w_ki
)
```

with units of degrees RMS.

Each state retains its own normalization scale `S_k` and objective weight `W_k`. The convenience scalar used by the current deterministic search is

```text
J_total = sum_k W_k * (J_k / S_k)
```

for objective-role states only.

The individual `J_k`, `S_k`, `W_k`, raw residual diagnostics, and target authority remain in the result. The scalar aggregate is therefore a ranking convenience, not a replacement for the state-level engineering tradeoffs.

## Feasibility rule

All states in the supplied pose set are part of the declared operating envelope, including report-only states. A candidate is infeasible if any state fails the existing steering analyzer sweep or an explicitly active state constraint.

No penalty value is assigned to an infeasible state. The candidate receives no aggregate objective.

This is intentionally distinct from target roles:

- `report_only` means no performance target is assigned;
- it does **not** mean closure, branch, singularity, or projection failures are ignored.

## Search-method reuse

`run_operating_state_inverse_design` reuses the same bounded normalized coordinate-pattern implementation used by the nominal optimizer:

- the same role-selected bounded design variables;
- the same reference normalization;
- the same deterministic seeded starts;
- the same polling directions and step contraction;
- the same infeasible-candidate handling;
- the same termination controls.

Only the evaluation adapter changes from `evaluate_candidate` to `evaluate_operating_state_candidate`. No second optimizer algorithm has been introduced, so the Hooke-Jeeves / Lewis-Torczon-Trosset method record and nominal repeatability baseline remain the numerical reference.

## Target-provider routes

Two construction routes are implemented.

### Analyzer-generated synthetic target

`build_analyzer_operating_state_target_set` evaluates a known source candidate through the complete pose/analyzer chain and freezes its state responses as a software-recovery target. This is verification evidence only.

### Explicit provider table

`load_explicit_operating_state_target_set` accepts unit-explicit state target arrays. The source may later be:

- manually authored design intent;
- geometric-Ackermann or ratio-derived targets;
- a reviewed external vehicle-dynamics calculation;
- a future tire-informed provider based on Milliken/Pacejka-style tire operating analysis;
- another reviewed tool adapter.

The loader does not confer authority on the source. Source authority remains explicit metadata and must pass the corresponding model/documentation gate before design claims are promoted.

## Frozen synthetic problem

`STEERING_SYNTHETIC_OPERATING_TARGETS_V0` uses the synthetic pose set from `P1-STR-006A/006B` and an analyzer-generated source geometry with

```text
rack_longitudinal_offset = +0.01875 m
```

The objective states are:

| State | Weight |
|---|---:|
| nominal | 1.0 |
| symmetric_bump_5mm | 0.8 |
| opposed_travel_5mm | 0.6 |

All three state responses are generated through `MOD-STEER-0001`. The 18.75 mm source value is deliberately aligned with the deterministic search refinement grid so the benchmark isolates target aggregation and search composition rather than search-resolution error.

Numerical recovery values are frozen in the benchmark result record after CI report review.

## Authority boundary

This implementation does **not** authorize:

- WUFR bump-steer or roll-steer claims from the synthetic poses;
- tire-optimal target generation;
- arbitrary operating-state weights as vehicle-dynamics truth;
- physical packaging or manufacturing feasibility;
- steering-effort or rack-load optimization;
- compliance, backlash, friction, or installed corrections;
- tolerance or robustness claims;
- Pareto completeness or global optimality;
- WUFR-28 production geometry selection.

The next fidelity layer can replace the synthetic state targets with reviewed external targets without changing the geometry generator, pose contract, analyzer, or deterministic search method.
