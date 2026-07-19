# Steering Geometry Benchmark Plan

**Status:** Proposed  
**Primary targets:** `MOD-STEER-0001`, future steering mechanism equations, `BENCH-STEER-0001`

## Purpose

This plan defines the evidence needed before the rigid steering evaluator or inverse-design workflow can be authorized for implementation or design decisions.

A benchmark result must identify geometry revision, conventions, model layer, input domain, expected outputs, tolerances, and evidence role. Matching an external tool does not by itself establish physical correctness.

## Benchmark hierarchy

### Level A — dimensional and algebraic checks

| Benchmark ID | Case | Expected result |
|---|---|---|
| `BENCH-STEER-A001` | Zero input at rack center | Defined static left/right toe; no unexplained offset |
| `BENCH-STEER-A002` | Tie-rod closure at every sweep point | Inner-to-outer joint distance equals nominal link length within tolerance |
| `BENCH-STEER-A003` | Transmission-unit conversions | `m/rad`, `mm/rev`, steering-wheel/pinion ratio conversions agree |
| `BENCH-STEER-A004` | Function differentiation | Analytical/automatic derivatives agree with central finite differences in well-conditioned regions |
| `BENCH-STEER-A005` | Result lineage | Every map point links to geometry, requirement set, model, and solver revision |

### Level B — limiting, symmetry, and topology checks

| Benchmark ID | Case | Expected result |
|---|---|---|
| `BENCH-STEER-B001` | Left/right mirrored geometry | Opposite-direction sweeps mirror left/right outputs under the project sign convention |
| `BENCH-STEER-B002` | Parallel-steer construction | Left and right road-wheel angles remain equal apart from declared static toe |
| `BENCH-STEER-B003` | Ideal Ackermann construction | Inner/outside relation matches the exact low-speed Ackermann reference over the tested domain |
| `BENCH-STEER-B004` | Zero track limit | Left/right road-wheel curves converge appropriately |
| `BENCH-STEER-B005` | Large turn-radius/small-angle limit | Exact and small-angle Ackermann expressions converge within stated error |
| `BENCH-STEER-B006` | Approach to mechanism singularity | Condition metric degrades and solver stops before branch crossing |
| `BENCH-STEER-B007` | Reversed rack direction | Output signs transform according to the declared axis, not by hidden sign fixes |
| `BENCH-STEER-B008` | Left/right unequal tie rods | Intended asymmetry is represented and symmetry test fails visibly rather than being averaged away |

### Level C — analytical and published mechanism cases

| Benchmark ID | Case | Source role |
|---|---|---|
| `BENCH-STEER-C001` | Exact no-slip Ackermann angles for selected wheelbase, steering-axis track, and turn radius | Analytical reference |
| `BENCH-STEER-C002` | Reviewed planar rack/tie-rod geometry with hand-computed closure | Independent derivation |
| `BENCH-STEER-C003` | Published trapezoidal linkage example with sufficient dimensions | Literature comparison |
| `BENCH-STEER-C004` | Chalmers-style rack steering relation using tie-rod length, steering-arm length, rack-to-axis distance, and rack displacement | Literature comparison; equation/sign audit required |

Published cases are adopted only when their coordinate, angle, and length definitions can be translated without ambiguity.

### Level D — independent implementation

`BENCH-STEER-D001` uses a separately authored spreadsheet, script, or hand-derived mechanism fixture that does not share production code. It compares:

- rack displacement;
- left/right road-wheel angle;
- tie-rod closure;
- local derivatives;
- inside/outside relation;
- Ackermann error.

Agreement tolerances are set before comparison.

### Level E — external-tool and legacy comparison

#### `BENCH-STEER-0001` — recovered legacy CAD motion study

Required frozen inputs:

- source CAD assembly/configuration and hash;
- vehicle/steering revision;
- reference ride height, alignment, and rack center;
- exact input quantity and sweep resolution;
- output wheel-angle definitions and signs;
- raw export before polynomial fitting;
- solver/motion-study warnings;
- expected table with uncertainty or numerical resolution.

The comparison report includes raw curves, residual curves, maximum absolute error, RMS error, center-region derivative error, full-lock error, and any branch or discontinuity differences.

Possible additional comparisons:

- OptimumK steering map with identical hardpoints;
- ADAMS or another multibody mechanism model;
- current SolidWorks motion study rebuilt from reviewed geometry.

External models are benchmark evidence, not runtime dependencies or automatic truth.

### Level F — physical steering sweep

`BENCH-STEER-F001` requires a fixture or vehicle measurement of:

- steering-wheel and primary-shaft angle where available;
- rack displacement;
- left/right road-wheel steer angles;
- sweep direction and repeated cycles;
- setup/alignment and tire state;
- loading condition;
- calibration, synchronization, and uncertainty.

The physical test should include clockwise and counterclockwise sweeps to expose backlash, hysteresis, compliance, and zero uncertainty. The rigid model is compared primarily with an unloaded or documented low-load centerline response; loaded differences are retained for future compliance models rather than tuned away.

## First benchmark geometry sets

### `GEO-STEER-BASIC-001` — idealized symmetric planar fixture

Purpose: exercise closure, signs, symmetry, derivatives, and exact Ackermann references without WUFR geometry uncertainty.

Required values:

- wheelbase;
- steering-axis track;
- rack axis and center;
- rack inner-joint positions;
- steering-axis points;
- steering-arm outer-joint positions;
- tie-rod lengths;
- rack travel domain.

Values will be frozen in a versioned benchmark data file after definition review.

### `GEO-STEER-WUFR-HIST-001`

Purpose: reproduce the best-documented historical WUFR motion-study export.

Selection rule: choose the historical vehicle for which the source CAD configuration and raw export can first be recovered. Do not choose solely because its pasted polynomial is easiest to fit.

### `GEO-STEER-WUFR-CURRENT-001`

Purpose: represent the current steering design under review.

This geometry cannot become a benchmark until its hardpoint source, reference configuration, and revision are frozen. It may initially be a design-study input set rather than validation evidence.

## Acceptance metrics

Exact numerical tolerances are deferred until geometry scales and source resolution are known. The report must include at least:

- mechanism closure residual;
- road-wheel-angle absolute error;
- local derivative error;
- Ackermann-reference error difference;
- left/right mirror residual;
- minimum singularity margin;
- constraint status agreement;
- interpolation error where a sampled map is used;
- extrapolation attempts, which must fail explicitly.

Tolerances should distinguish:

- analytical floating-point tolerance;
- independent-implementation tolerance;
- CAD solver/export resolution;
- physical measurement uncertainty.

## Optimizer verification

The optimizer is verified only after the evaluator passes its benchmark gate.

Required optimizer cases:

1. known feasible design recovered from its own target curve;
2. intentionally infeasible hard constraints with a clear infeasibility report;
3. multiple initial guesses converging to the same local solution where expected;
4. a multimodal case returning alternatives or documenting initialization sensitivity;
5. hard-bound activity with nonnegative reported margin;
6. soft-band violation visible in objective decomposition;
7. discrete rack or steering-arm options compared without mixing variables;
8. tolerance-robust case showing improved worst-case margin relative to nominal-only optimization.

## Authorization gate

Prototype implementation may begin only when:

- the steering canonical subset is reviewed sufficiently to write unambiguous tests;
- `GEO-STEER-BASIC-001` is frozen;
- Level A and B expected results are approved;
- at least one independent Level C or D calculation is defined;
- the legacy source is recovered or the lack of recovery is explicitly accepted for prototype scope;
- result and failure schemas are approved.

Production design authority additionally requires the agreed Level E and/or Level F evidence and model-maturity review.
