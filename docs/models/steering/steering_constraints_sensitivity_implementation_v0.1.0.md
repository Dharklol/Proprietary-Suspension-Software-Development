# Steering Constraint Screening, Sensitivity, and Candidate Comparison v0.1.0

**Authorization:** `AUTH-STEER-0002`  
**Models:** `MOD-STEER-0001`, `MOD-STEER-0002`  
**Task:** `P1-STR-004`  
**Status:** Implemented for review

## Purpose

This release extends the nominal inverse-design prototype with three connected capabilities:

1. a named constraint-provider contract that distinguishes active, failed, and unavailable requirements;
2. analyzer-composed local finite-difference sensitivity around one candidate; and
3. a comparison layer that keeps objective-ranked but visibly different candidates available with geometry, constraint, and evidence differences.

It does not add steering-kinematics equations. The generated candidate and complete target sweep still come from the existing geometry generator and `MOD-STEER-0001` evaluator.

## Constraint-provider contract

`STEERING_CONSTRAINT_PROVIDER_DEV_V0` contains three active workflow-development constraints:

- tie-rod joint-center length within a broad `0.20 m` to `0.45 m` band;
- minimum analyzer singularity ratio of `0.01`; and
- the existing tightly bounded outer-pickup depth interval of `-0.005 m` to `+0.005 m`.

These values test the workflow. They are not selected hardware, packaging, manufacturing, or released design criteria.

Six constraints are present but unavailable:

- rod-end articulation;
- thread engagement;
- steering-arm material envelope;
- rack housing and inner-joint clearance;
- wheel, brake, chassis, and tire clearance; and
- installed physical-stop margin.

Each unavailable result includes the missing evidence and remains nonblocking. The software does not describe missing evidence as a passed constraint.

A screened candidate retains its original `CandidateEvaluation`. Supplemental screening adds a separate record. When an active blocking supplemental constraint fails, the screened candidate has no objective available for ranking, but the original analyzer result remains attached for diagnosis.

### Current search boundary

The v0.1.0 supplemental constraints screen the retained nominal-search candidate set. They do not yet steer the coordinate-pattern polling path. This is intentional while the only active values are development checks and the hardware constraints remain unavailable. Before a future hardware-feasible optimization claim, reviewed constraints must be evaluated inside every search candidate disposition so the search can navigate their feasible region rather than only screen an archive afterward.

## Local sensitivity method

`analyze_local_sensitivity` perturbs each selected bounded variable inside its requirement-set bounds. Every perturbed point is:

```text
role-resolved
-> regenerated through the parametric geometry generator
-> evaluated through the complete MOD-STEER-0001 target sweep
-> screened through the selected constraint set
```

A central difference is used when both sides of the perturbation are inside bounds and feasible. A forward or backward difference is used at a bound. If insufficient feasible perturbations exist, the derivative is reported unavailable rather than fabricated.

For a response `f` and variable `q`, the central local derivative is:

```text
(df/dq) ~= [f(q+h) - f(q-h)] / (2h)
```

The report includes the physical derivative per variable unit and a normalized derivative multiplied by the full declared variable span. Numeric base and supplemental constraint margins are differentiated through the same perturbations.

Fornberg (1988), “Generation of Finite Difference Formulas on Arbitrarily Spaced Grids,” supports the finite-difference formulation. Saltelli et al. (2008), *Global Sensitivity Analysis: The Primer*, supports keeping local derivative information distinct from uncertainty-based global sensitivity. This implementation is local only; it is not tolerance propagation or robustness analysis.

## Candidate comparison

`build_candidate_comparison` applies the named constraint set to the retained search candidates, preserves objective order, and filters near-duplicate geometry using an explicit normalized design-space distance:

```text
d(q_a, q_b) = sqrt[(1/n) sum_i (qbar_a,i - qbar_b,i)^2]
```

where each `qbar` is normalized by its requirement-set bounds.

For each selected candidate the report includes:

- objective and objective difference from the best screened candidate;
- normalized design distance from the best and previously selected candidates;
- complete candidate values and normalized values;
- rack-axis origin and outer tie-rod pickup;
- tie-rod length and difference from the best candidate;
- base and supplemental constraint margins;
- unavailable constraint IDs; and
- a plain-language ranking explanation.

This is a transparent alternative-selection aid. It is not a Pareto-front calculation and does not establish global optimality.

## Frozen benchmark result

CI run `30000023252` produced the frozen `STEERING-CONSTRAINT-SENSITIVITY-BENCHMARKS-V0` result.

The WUFR-27 reference candidate:

- passes all three active development constraints;
- retains the historical regression objective of `0.6259259771798616`;
- reports all six future hardware constraints as unavailable.

The rack-longitudinal sensitivity uses a central `0.0003 m` step and returns:

```text
objective derivative = -7.244456509246101 per m
normalized derivative over the full declared span = -2.17333695277383
```

The comparison benchmark screens twenty retained candidates, keeps four candidates above the `0.005` normalized design-distance threshold, and excludes four near-duplicates encountered before the four-candidate limit is reached.

## Promotion boundary

This implementation supports development studies and review of workflow behavior. It does not authorize:

- rod-end, tie-rod, rack, upright, steering-arm, wheel, brake, chassis, or tire packaging claims;
- manufacturing or thread-engagement claims;
- installed-stop or as-built claims;
- tolerance, uncertainty, or robustness claims;
- multiobjective Pareto or global-optimality claims;
- suspension-state, tire-informed, load, effort, compliance, or transient behavior; or
- WUFR-28 production geometry selection.
