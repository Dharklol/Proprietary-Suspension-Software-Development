# Rigid Steering Prototype Authorization

**Authorization ID:** `AUTH-STEER-0001`  
**Status:** Active, reviewed, and frozen for the bounded evaluator  
**Affected model:** `MOD-STEER-0001`  
**Affected equations:** `EQ-STEER-0001` through `EQ-STEER-0007`  
**Authorized configurations:** `GEO-STEER-BASIC-001` and `WUFR26_DESIGN_NOMINAL_V0`  
**Review record:** `docs/reviews/phase0_steering_review_closeout.md`

## 1. Decision

This packet authorizes the bounded experimental rigid steering-mechanism evaluator implemented under PR #10. The authorization was merged before the implementation began and has now been reviewed against the implemented scope.

It does not authorize the inverse-design optimizer, production release decisions, a compliance-corrected rigid model, or an installed/as-built WUFR-26 claim.

## 2. Evidence supporting authorization

The bounded authorization is supported by:

- canonical steering quantity and reference-state definitions;
- recovered WUFR-26 design-selection lineage and SolidWorks response evidence;
- equation cards and the rigid steering function specification;
- frozen analytical and synthetic expectations in `benchmarks/steering/preimplementation_freeze_packet.md` and `GEO-STEER-BASIC-001.toml`;
- WUFR-26 coordinate-frame reconciliation and nominal hardpoint source merge;
- explicit separation of upright rotation, projected road-wheel heading, static toe, and incremental steer;
- automated `BENCH-STEER-0002` through `0008` tests;
- the frozen descriptive WUFR-26 Level E comparison;
- documented physical-evidence and Level F boundaries.

## 3. Permitted implementation scope

### 3.1 Geometry and validation

- immutable point, axis, frame, side, source-role, and configuration records;
- finite-value, dimension, unit, axis-normalization, and nondegeneracy checks;
- explicit left/right identities and named symmetry assumptions;
- no silent unit conversion or source-frame inference inside the mechanism solver.

### 3.2 Rigid mechanism operations

- rack translation along a declared rack axis;
- rigid rotation of upright-fixed points around a declared steering-axis line using exact axis-angle rotation;
- tie-rod joint-center distance closure;
- deterministic solution of upright rotation for requested rack displacement;
- continuation on the intended assembly branch from a declared reference state;
- separate root residual, physical length residual, branch, and singularity diagnostics.

### 3.3 Synthetic fixture outputs

For `GEO-STEER-BASIC-001`, the evaluator may calculate:

- left/right total and incremental road-wheel heading;
- inside/outside aliases;
- local road-wheel gain and secant steering ratio;
- exact low-speed Ackermann reference and Ackermann error;
- named turning-radius constructions;
- analytical and limiting-case benchmark results.

### 3.4 WUFR-26 nominal outputs

For `WUFR26_DESIGN_NOMINAL_V0`, the evaluator may calculate:

- left and right upright rotation;
- rack-displacement sweeps over the frozen nominal design-source domain;
- tie-rod closure, branch continuity, feasibility, and singularity margins;
- canonical wheel-plane projection;
- total toe-inclusive and incremental projected road-wheel headings;
- the frozen descriptive nominal Level E comparison.

Steering-wheel-input maps, Ackermann error, and turning-radius outputs remain conditional on their explicit transmission and reference-path prerequisites.

## 4. Numerical-method authorization

The physical constraint is the rigid tie-rod length equation. The position solution is a scalar root in upright rotation on a declared mechanism branch.

The implementation must use a safeguarded bracket-preserving method, such as:

- bisection with documented termination rules; or
- a reviewed Brent-Dekker-type method that preserves the bracket.

An unconstrained Newton or secant solve is not an authorized default. Alternate-root substitution, hidden clipping, and extrapolation are prohibited.

The numerical method must:

- begin from a valid sign-changing bracket on the intended branch;
- stop on declared residual and interval criteria;
- reject nonfinite values;
- report failure rather than substitute another root;
- prevent continuation across the singularity threshold;
- produce deterministic results within benchmark tolerance.

## 5. Function-source and validity requirements

Every public calculation must link to its equation record and specification.

| Function family | Basis | Validity boundary |
|---|---|---|
| Point translation | Euclidean vector addition | Declared rigid frame and rack axis |
| Axis-angle rotation | Rodrigues rigid-body rotation | Fixed nonzero steering axis and rigid upright |
| Tie-rod closure | Holonomic joint-center distance constraint | Rigid links and joint centers |
| Wheel-plane projection | Rotated wheel-plane/road-plane intersection | Reviewed static alignment and nondegenerate planes |
| Ackermann reference | Exact low-speed no-slip geometry | Reference only; not universal race objective |
| Local gain | Implicit differentiation or verified numerical derivative | Away from singular and zero-gain states |
| Ratio chain | Explicit chain rule through named signals | Transmission identities supplied |
| Turning radius | Named geometric path construction | Required wheel headings and geometry supplied |

Historical CAD polynomials remain comparison evidence and cannot replace the mechanism equations.

## 6. Required failure semantics

Structured failures or warnings are required for:

- invalid geometry or nonfinite input;
- zero-length or ill-defined axes;
- input outside the declared domain;
- no closure solution on the intended branch;
- missing root bracket;
- branch ambiguity or branch change;
- near-singular mechanism/Jacobian;
- root nonconvergence;
- degenerate wheel/road-plane projection;
- unavailable derived output due to missing prerequisites;
- unsupported extrapolation.

## 7. Mandatory implementation tests

The implementation must continue to pass:

- `BENCH-STEER-0002`: exact Ackermann analytical pairs;
- `BENCH-STEER-0003`: reference closure and branch selection;
- `BENCH-STEER-0004`: sweep, mirror, branch, monotonicity, and singularity behavior;
- `BENCH-STEER-0005`: staged transmission identity;
- `BENCH-STEER-0006`: local and secant ratio calculations;
- `BENCH-STEER-0007`: named turning-radius constructions;
- `BENCH-STEER-0008`: Ackermann-error sign and static-toe treatment;
- WUFR-26 wheel-plane and Level E regression tests.

## 8. Provenance and result contract

Every accepted result point must retain:

- geometry/configuration ID and version;
- source-role metadata for direct, transformed, mirrored, derived, provisional, historical, and measured values where applicable;
- model and equation revisions;
- input quantity identity and SI value;
- solved upright rotation and projected heading separately;
- closure residuals and root bracket;
- branch identifier and continuation predecessor;
- singularity/Jacobian diagnostic;
- solver status, warning codes, and failure code;
- availability status for each derived output.

## 9. Explicitly prohibited scope

This authorization does not permit:

- hardpoint or tie-rod optimization;
- automatic relaxation of constraints;
- production design ranking or release decisions;
- tire-force, slip-angle, aligning-moment, or tire-utilization objectives;
- steering effort, trail-force, friction, backlash, or column-load calculations inside the rigid evaluator;
- applying a constant backlash or compliance correction to rigid outputs;
- compliance, bump steer, suspension travel, or chassis-motion models;
- manufacturing robustness claims;
- collision or rod-end articulation verification unless separately modeled and authorized;
- claiming the nominal WUFR geometry is installed/as-built;
- claiming Level E agreement is independent physical validation;
- UI work beyond minimal developer-facing execution and diagnostics.

## 10. Promotion gates

The bounded evaluator may advance beyond its current use only after the relevant gates are met:

1. frozen tests continue to pass;
2. numerical implementation review remains current;
3. installed stops and staged transmission data are measured for installed-domain or steering-wheel-input claims;
4. physical wheel-response, repeatability, backlash, compliance, and uncertainty evidence are reviewed for Level F claims;
5. an independently justified acceptance rule is defined;
6. a separate authorization explicitly permits optimizer, higher-fidelity physical modeling, or production use.

## 11. Review decision

`AUTH-STEER-0001` is effective and the implementation is consistent with its bounded scope. The Phase 0 authorization task is complete. This is a scope decision, not a certification of installed-vehicle accuracy.
