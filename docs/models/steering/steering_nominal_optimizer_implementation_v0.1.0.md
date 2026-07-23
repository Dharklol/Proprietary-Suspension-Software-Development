# Nominal Steering Optimizer Implementation v0.1.0

**Authorization:** `AUTH-STEER-0002`  
**Evaluator:** `MOD-STEER-0001`  
**Orchestrator:** `MOD-STEER-0002`  
**Requirement set:** `STEERING_INVERSE_DESIGN_DEV_V0`

## Purpose and scope

This implementation is the first deterministic inverse-design layer built around the verified rigid steering analyzer. It searches role-selected rack and tie-rod geometry at one nominal suspension pose. It does not contain a second steering model. Each candidate is resolved from the requirement set, generated through the parametric geometry layer, converted into the public `SteeringGeometry` contract, and evaluated across the complete target domain by `MOD-STEER-0001`.

The release supports historical response regression, analyzer-generated synthetic recovery, user-selected active-variable subsets, explicit hard infeasibility, deterministic seeded multistart, and comparison of several retained feasible candidates. It does not authorize tire-optimal targets, effort optimization, suspension-travel behavior, physical packaging, manufacturing feasibility, robustness, as-built prediction, or production geometry selection.

## Target providers

A target provider supplies left and right incremental projected wheel headings, input coordinates, rack mapping, point weights, units, normalization, source authority, and the validity domain. The optimizer does not embed one permanent Ackermann or tire philosophy.

`WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0` evaluates the selected Test 3 polynomial at fifteen frozen steering-input points. The reviewed Level E adapter maps historical input directly to canonical rack travel and maps canonical incremental heading into the historical angular orientation with an output sign of `-1`. This target is fit-derived design evidence and is only a regression reference.

`STEERING_SYNTHETIC_RECOVERY_V0` defines a known source candidate and generates its target through `MOD-STEER-0001`. It is Level A software verification, not independent model evidence. The first recovery fixture identifies only `rack_longitudinal_offset`; every other parameter remains at its requirement-set reference.

## Candidate evaluation

The evaluator first applies the requirement-set roles and bounds, generates symmetric geometry, derives reference tie-rod length, and performs the centered-state analyzer preflight. The target rack domain must lie within the named rack domain. Both sides are then solved across every target state using the analyzer's branch-preserving continuation and singularity behavior.

For each accepted state, projected wheel heading is calculated through the existing wheel-plane projection functions using the target's stated static alignment. The historical or synthetic target adapter is then applied. No polynomial or response surrogate is used to predict a candidate.

The first objective is the weighted left/right wheel-heading error

```text
J_raw = sqrt(
    sum_j w_j * [e_L,j^2 + e_R,j^2] / [2 * sum_j w_j]
)
```

where `e_L,j` and `e_R,j` are target-convention incremental-heading residuals in degrees. The reported normalized objective is

```text
J_norm = J_raw / s_heading
J_contribution = weight_heading * J_norm
```

The target record freezes the raw unit, normalization scale, weight, and sweep domain. Individual left and right RMS values and the maximum absolute residual remain visible in the objective message.

## Hard infeasibility

The implementation treats candidate generation, rack domain, complete analyzer sweep, projected-heading availability, and required monotonic response as hard constraints. A failed candidate receives a named failure code and constraint record but no objective value. The search never assigns a large penalty to a broken mechanism, substitutes another assembly root, clips a failed response, or extrapolates beyond the target or rack domain.

The result object retains the analyzer `PositionResult` for both sides and every evaluated rack state. It therefore preserves closure residual, branch signature, local gain, singularity ratio, branch margin, warnings, failure code, and source role rather than reducing the mechanism to one score.

## Variable selection and scaling

The active design variables are selected by identifier for each search. Any bounded variable not selected remains at its requirement-set reference. This allows the same solver to optimize rack placement while carrying over a steering arm, optimize an outer pickup while fixing a rack, or test a reduced identification problem without changing generator code.

Each active bounded variable is mapped to a normalized coordinate

```text
q_hat = (q - q_min) / (q_max - q_min)
```

and the search operates on `0 <= q_hat <= 1`. This prevents metres-scale variables with very different physical ranges from dominating exploratory step sizes. Reports retain the physical value, reference, delta, unit, and bounds.

## Numerical method

The first numerical baseline is `bounded_coordinate_pattern_search_v0.1.0`. The reference geometry is always the first start. Additional starts are deterministic perturbations around the normalized reference, generated by Python's versioned pseudorandom implementation using the recorded integer seed. An infeasible start is moved repeatedly toward the reference before being abandoned.

At each local-search iteration, the method evaluates positive and negative coordinate moves of the current normalized step along every active dimension. It accepts the best feasible improving trial. When no improving coordinate trial exists, the normalized step is multiplied by the contraction factor. The search terminates when the step falls below the recorded minimum or the iteration limit is reached.

The method is intentionally transparent and dependency-free. Its lineage is the direct-search family represented by Hooke and Jeeves (1961) and reviewed by Lewis, Torczon, and Trosset (2000). The implementation does not claim global convergence or global optimality. It is the deterministic benchmark against which future constrained, global, mixed-discrete, surrogate-assisted, or learned methods must be compared.

## Candidate retention and ranking

All feasible evaluations are kept during one search. The current one-objective release retains the requested number of candidates with the lowest normalized wheel-heading error and reports their full geometry, variable deltas, objective terms, constraints, analyzer states, and provenance. This is a transparent convenience ranking rather than a Pareto claim. Later multiobjective work must retain nondominated alternatives and cannot replace failed hard constraints with weighted penalties.

## Verification

`BENCH-STEER-0010` covers the historical target contract and reference-candidate evaluation. The expected result is a feasible complete sweep with a finite, nonzero regression residual; the historical fit is not expected to match the analyzer exactly.

`BENCH-STEER-0011` covers synthetic recovery, deterministic repeatability, active-variable selection, candidate retention, and method metadata. The source rack longitudinal offset is `0.020 m`. The best candidate must recover it within `0.001 m`, and the target residual must be no greater than `0.001 deg RMS` using the frozen benchmark settings.

Deliberate out-of-domain evaluation verifies that an infeasible candidate has no objective. Unit tests also patch the public analyzer sweep to verify composition rather than duplicate optimizer physics. CI generates a complete JSON report and a compact summary for each pull request and push to `main`.

## Literature grounding

The steering geometry and projection remain governed by the literature and equation records already attached to `MOD-STEER-0001`, including Guiggiani Chapter 3 and Gillespie Chapter 8. Romano's staged steering-configuration comparison and validation workflow supports the analyzer-first architecture. Huang et al. supports separating target achievement from physical feasibility and motivates later high-dimensional methods without superseding the deterministic benchmark.

The numerical search is grounded in the direct-search literature:

- R. Hooke and T. A. Jeeves, “Direct Search Solution of Numerical and Statistical Problems,” *Journal of the ACM*, 1961.
- R. M. Lewis, V. Torczon, and M. W. Trosset, “Direct Search Methods: Then and Now,” *Journal of Computational and Applied Mathematics*, 2000.

These sources support a transparent derivative-free baseline. They do not establish that this implementation has solved the future steering-design problem globally.

## Remaining development gates

The next layer must expand candidate reports and constraints using reviewed steering-arm envelopes, articulation limits, thread engagement, rack hardware, physical stops, clearances, and manufacturing rules. Tire-target, effort, pose, uncertainty, and physical-parameter providers remain separate gates. WUFR-28 production selection remains prohibited until those layers and their evidence are reviewed under a later authorization.
