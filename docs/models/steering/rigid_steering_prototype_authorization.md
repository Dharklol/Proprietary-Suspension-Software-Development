# Rigid Steering Prototype Authorization

**Authorization ID:** `AUTH-STEER-0001`  
**Status:** Proposed for approval; effective only when this pull request is merged  
**Affected model:** `MOD-STEER-0001`  
**Affected equations:** `EQ-STEER-0001` through `EQ-STEER-0007`  
**Authorized configuration classes:** `GEO-STEER-BASIC-001` and `WUFR26_DESIGN_NOMINAL_V0`

## 1. Decision

This packet authorizes development of a bounded, experimental rigid steering-mechanism evaluator after merge. It does not authorize the inverse-design optimizer, production design authority, or an as-built WUFR-26 model.

The prototype exists to demonstrate that the documented equations, branch controls, failure semantics, and benchmark fixtures can be implemented correctly before adding optimization, user interfaces, tire objectives, or higher-fidelity effects.

## 2. Evidence supporting authorization

The bounded authorization is based on the following reviewed and merged evidence:

- canonical steering quantity and reference-state definitions;
- recovered WUFR-26 design-selection lineage and SolidWorks motion-study response;
- equation cards and function specification for rigid translation, steering-axis rotation, tie-rod closure, transmission staging, ratios, Ackermann reference/error, and turning-radius constructions;
- frozen analytical and synthetic benchmark expectations in `benchmarks/steering/preimplementation_freeze_packet.md` and `GEO-STEER-BASIC-001.toml`;
- WUFR-26 coordinate-frame reconciliation and nominal hardpoint source merge;
- explicit separation of imported nominal static toe, incremental upright rotation, projected wheel heading, and absolute toe-inclusive heading;
- documented unresolved installed-state and physical-correlation gates.

## 3. Permitted implementation scope

The first implementation may contain only the following functional layers.

### 3.1 Geometry and validation

- immutable point, axis, frame, side, source-role, and configuration records;
- finite-value, dimension, unit, axis-normalization, and nondegeneracy checks;
- explicit left/right identities and named symmetry assumptions;
- no silent unit conversion or source-frame inference inside the mechanism solver.

### 3.2 Rigid mechanism operations

- rack translation along a declared rack axis;
- rigid rotation of the upright outer joint around a declared steering-axis line using an exact axis-angle rotation;
- tie-rod joint-center distance closure;
- deterministic solution of upright rotation for a requested rack displacement;
- continuation on the intended assembly branch from a declared reference state;
- separate root residual, physical length residual, branch, and singularity diagnostics.

### 3.3 Derived outputs where their prerequisites exist

For `GEO-STEER-BASIC-001`, the prototype may calculate:

- left/right total and incremental road-wheel heading;
- inside/outside aliases for both turn directions;
- local road-wheel gain and secant steering ratio;
- exact low-speed Ackermann reference and Ackermann error;
- named turning-radius constructions;
- analytical and limiting-case benchmark results.

For `WUFR26_DESIGN_NOMINAL_V0`, the prototype may calculate:

- front-left and mirror-derived front-right upright rotation relative to the imported centered state;
- rack-displacement sweeps over the provisional declared domain;
- tie-rod closure, branch continuity, feasibility, and singularity margins;
- quantities that depend only on the reviewed hardpoints and explicit nominal-symmetry assumption.

The WUFR-26 case may not report projected road-wheel heading, absolute toe-inclusive wheel heading, steering-wheel ratio, Ackermann error, or turning radius as authoritative until the missing wheel-plane, toe, transmission, and reference-path prerequisites are supplied. The software may return those fields as unavailable with a reason code.

## 4. Numerical-method authorization

The physical constraint is the rigid tie-rod length equation documented by `EQ-STEER-0002`. The position solution is a scalar root in upright rotation on a declared mechanism branch.

The implementation must use a safeguarded bracket-preserving method. Acceptable first implementations are:

- bisection with documented termination rules; or
- a reviewed Brent-Dekker-type method that preserves the bracket.

An unconstrained Newton or secant solve is not an authorized default because it can cross a fold, lose the intended branch, or converge to another assembly solution. A library routine is permitted only when its exact package, version range, function contract, tolerances, and failure behavior are documented in the implementation pull request.

The numerical method must:

- begin from a valid sign-changing bracket on the intended branch;
- stop on declared residual and interval criteria;
- reject nonfinite values;
- report failure rather than substitute another root;
- prevent continuation across the singularity threshold;
- produce deterministic results independent of sweep direction within benchmark tolerance.

## 5. Function-source and validity requirements

Every implemented public calculation must link to its equation record and human-readable specification. At minimum, implementation documentation must state:

| Function family | Basis | Validity boundary |
|---|---|---|
| Point translation | Euclidean vector addition | Declared rigid frame and rack axis |
| Axis-angle rotation | Rodrigues rigid-body rotation | Fixed, nonzero steering axis and rigid upright |
| Tie-rod closure | Holonomic joint-center distance constraint | Rigid links and spherical joint centers |
| Ackermann reference | Exact low-speed no-slip geometry | Reference only; not universal race objective |
| Local gain | Implicit differentiation or verified numerical derivative | Away from singular and zero-gain states |
| Ratio chain | Explicit chain rule through named signals | Signal identities and transmission data supplied |
| Turning radius | Named geometric reference path | Required wheel headings and track/wheelbase definitions supplied |

No empirical polynomial from a CAD export may replace the mechanism equations. Imported curves remain comparison evidence.

## 6. Required failure semantics

The prototype must return a structured failure or warning state for at least:

- invalid geometry or nonfinite input;
- zero-length or ill-defined axis;
- rack input outside the declared domain;
- no real closure solution on the intended branch;
- missing or invalid root bracket;
- branch ambiguity or branch change;
- near-singular mechanism/Jacobian;
- root nonconvergence;
- unavailable derived output because prerequisite metadata is missing;
- unsupported extrapolation request.

Clipping, hidden fallback values, silent averaging of inconsistent radius constructions, and alternate-root substitution are prohibited.

## 7. Mandatory implementation tests

The first code pull request must implement and pass the frozen expectations for:

- `BENCH-STEER-0002`: exact Ackermann analytical pairs;
- `BENCH-STEER-0003`: reference closure and branch selection;
- `BENCH-STEER-0004`: sweep, mirror, branch, monotonicity, and singularity behavior;
- `BENCH-STEER-0005`: staged transmission identity;
- `BENCH-STEER-0006`: local and secant ratio calculations;
- `BENCH-STEER-0007`: named turning-radius constructions;
- `BENCH-STEER-0008`: Ackermann-error sign and static-toe treatment.

Registry CI validates structure only. The implementation pull request must show benchmark outputs and test results; passing CI alone is not engineering verification.

## 8. Provenance and result contract

Every accepted result point must retain:

- geometry/configuration ID and version;
- source-role metadata for direct, transformed, mirrored, derived, and provisional values;
- model and equation revisions;
- input quantity identity and SI value;
- solved upright rotation and any projected heading separately;
- closure residuals and root bracket;
- branch identifier and continuation predecessor;
- singularity/Jacobian diagnostic;
- solver status, warning codes, and failure code;
- availability status for each derived output.

## 9. Explicitly prohibited scope

This authorization does not permit:

- hardpoint or tie-rod optimization;
- automatic relaxation of constraints;
- design ranking or production release decisions;
- tire-force, slip-angle, aligning-moment, or tire-utilization objectives;
- steering effort, trail-force, friction, backlash, or column-load calculations;
- compliance, bump steer, suspension travel, or chassis motion;
- manufacturing tolerance or robustness claims;
- collision or rod-end articulation verification unless separately modeled and authorized;
- claiming the nominal WUFR geometry is the installed/as-built geometry;
- claiming CAD reproduction is independent physical validation;
- UI work beyond minimal developer-facing inputs and reports needed to run tests.

## 10. Promotion gates

The bounded evaluator may advance beyond experimental use only after:

1. all frozen synthetic and analytical tests pass;
2. implementation and numerical-method review is complete;
3. WUFR-26 wheel-plane, toe, rack-stop, and pinion/rack definitions are recovered for the requested outputs;
4. raw `2026Ackermann.csv` response is reproduced within an approved Level E tolerance;
5. a physical steering sweep or equivalent independent evidence is reviewed for Level F claims;
6. a separate authorization pull request explicitly permits optimizer or production use.

## 11. Review decision

Merging this packet records authorization to begin the bounded prototype described above. It does not certify that future code is correct. Each implementation pull request remains subject to benchmark, source, numerical, and scope review before merge.
