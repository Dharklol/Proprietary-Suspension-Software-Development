# Phase 1 Steering Inverse-Design Authorization Review

**Authorization:** `AUTH-STEER-0002`  
**Models:** `MOD-STEER-0001`, `MOD-STEER-0002`  
**Migration:** `MIG-STR-0001`  
**Status:** Review packet for nominal-height inverse-design prototype

## Review purpose

This review moves the steering vertical slice from a verified rigid evaluator into a bounded inverse-design development track while keeping the WUFR-26/27 physical-correlation tasks open. The physical tasks continue to block installed and as-built claims, but they do not block generic geometry generation, constrained search, target recovery, or candidate-report development.

## Decisions

1. `MOD-STEER-0001` remains the sole rigid steering analyzer. No optimization module may duplicate its closure, branch, projection, ratio, Ackermann, or turning calculations.
2. `MOD-STEER-0002` is a separate orchestration model responsible for parameter roles, candidate geometry, constraint assessment, target comparison, search, and reporting.
3. The first geometry boundary fixes steering axes, upright poses, suspension hardpoints, wheel centers, wheelbase, steering-axis track, static alignment, and rack-axis direction.
4. The first active variables are rack longitudinal position, rack vertical position, rack inner-joint half-spacing, and upright-local outer-pickup coordinates. Outer-pickup depth is tightly bounded.
5. Exact left/right reflection symmetry is enforced in the first implementation.
6. Tie-rod joint-center length is derived from the reference joint coordinates.
7. The corrected WUFR-26/27 response is the initial regression target, while alternative target-provider modes remain available for future WUFR-28 studies.
8. Development bounds are broad workflow-test limits and are not packaging or manufacturing authority.
9. The optimizer must return multiple feasible or nondominated candidates where tradeoffs exist and preserve transparent ranking information.
10. Suspension pose, tire target, effort/load, uncertainty, and physical parameter layers are future provider interfaces and are not implemented under this authorization.

## Analyzer integration gate

The geometry-generator implementation is not accepted unless a zero-offset candidate reconstructs `WUFR27_STEERING_BASELINE_V0`, converts to the public `SteeringGeometry` contract, and produces analyzer results identical within frozen numerical tolerances to direct evaluation of `WUFR26_DESIGN_NOMINAL_V0`. Candidate reports must retain the complete analyzer diagnostics.

## Literature review

The authorization preserves the exact kinematic basis from Guiggiani Chapter 3 and Gillespie Chapter 8. Ackermann remains a low-speed reference rather than a universal race-car objective. Romano's steering-system modeling and configuration-comparison workflow supports validating the steering subsystem before coupling it to suspension and full-vehicle tests. Huang et al. (2026) supports the explicit separation between optimized kinematic targets and physical packaging feasibility; therefore packaging and mechanism feasibility are hard constraints rather than inferred from target score.

The first implementation remains deterministic and benchmarkable. Reinforcement-learning or other learned search methods remain later research options and must be compared against the deterministic baseline before authorization.

## Review conclusion requested

Approve `AUTH-STEER-0002` for the documented bounded prototype. After merge, the next code pull request may implement only the role resolver and parametric geometry generator. Search, ranking, robustness, and higher-fidelity physics remain separately gated by the authorization packet.
