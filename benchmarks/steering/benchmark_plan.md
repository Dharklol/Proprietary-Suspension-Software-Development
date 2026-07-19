# Steering Geometry Benchmark Plan

**Status:** Proposed; WUFR-26 benchmark source designated but not frozen  
**Primary targets:** `MOD-STEER-0001`, future steering mechanism equations, `BENCH-STEER-0001`

## Purpose

This plan defines the evidence needed before the rigid steering evaluator or inverse-design workflow can be authorized for implementation or design decisions.

A benchmark result must identify geometry revision, conventions, model layer, input domain, expected outputs, tolerances, and evidence role. Matching an external tool does not by itself establish physical correctness.

## Recovered legacy evidence hierarchy

The WUFR-26 legacy comparison must use the following authority hierarchy:

1. **Mechanism source:** `GEOMETRY FINAL.SLDPRT`, Box file ID `1971276311204`, is the team-designated final WUFR-26 geometry and primary SolidWorks benchmark source.
2. **Design-selection record:** the steering FDR table identifies the final chosen design/result. It must be recovered and hashed before the selected CSV can be frozen.
3. **Raw response evidence:** six CSV files in the same Box directory are exports from different studies performed with the second SolidWorks motion study to graph Ackermann curves. One contains the selected WUFR-26 curve.
4. **Alternative-design record:** `Steering Length Optimization Tests.xlsx` records candidate tests and tradeoffs but is not final design authority.
5. **Historical calculator evidence:** the `Steer Ratio` sheet contains WUFR-24 and WUFR-25 SolidWorks exports only. It is not the WUFR-26 source.
6. **Historical objective evidence:** WUFR-25 `Steering_range_optimization.m` is a steering-range/effort scalar trade study, not a geometry solver or Ackermann model.

The source manifest is `data_catalog/steering_box_source_manifest.toml`. No source is considered benchmark-frozen until immutable bytes have project SHA-256 hashes and all input/output definitions are resolved.

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

#### `BENCH-STEER-0001` — WUFR-26 final SolidWorks comparison

**Designated parent source:** `GEOMETRY FINAL.SLDPRT`  
**Selection authority:** steering FDR final-results table  
**Expected raw response source:** one of the six second-motion-study CSVs

Required frozen inputs:

- downloaded parent CAD bytes and SHA-256;
- SolidWorks version and file version;
- active configuration and suppression state;
- external references, equations, and design tables;
- vehicle/steering revision;
- reference ride height, alignment, and rack center;
- exact motion-study name and driver quantity;
- sweep start, stop, direction, and resolution;
- left and right output definitions, signs, and zero;
- selected CSV, its parent relationship, and SHA-256;
- solver/motion-study warnings;
- expected table with source numerical resolution.

The comparison report includes raw curves, residual curves, maximum absolute error, RMS error, center-region derivative error, full-lock error, tie-rod closure residual, and any branch or discontinuity differences.

#### Alternative-study regression set

The five non-selected CSVs remain useful as separate regression cases. They should test whether the evaluator can reproduce multiple geometry configurations without tuning implementation constants to the final design. Each requires a configuration map from the reference workbook/FDR/CAD dimensions.

#### WUFR-24 and WUFR-25 historical curves

The calculator `Steer Ratio` data may become historical Level E cases after its original CAD revision and export definitions are established. Copied polynomial coefficients are never the primary expected result; comparisons use raw table values where available.

Possible additional comparisons:

- OptimumK steering map with identical hardpoints;
- ADAMS or another multibody mechanism model;
- a separately rebuilt SolidWorks motion study from reviewed canonical geometry.

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

### `GEO-STEER-WUFR25-HIST-001`

Purpose: reproduce the WUFR-25 SolidWorks curve and separate it from the WUFR-25 MATLAB range/effort trade study.

Required lineage:

- parent CAD geometry and configuration;
- original SolidWorks export used by the calculator;
- calculator-import transformation;
- exact distinction between road-wheel map and aggregate steering-range objective.

### `GEO-STEER-WUFR26-FINAL-001`

Purpose: reproduce the final WUFR-26 SolidWorks steering mechanism.

Parent source is fixed as `GEOMETRY FINAL.SLDPRT`. The geometry set remains unfrozen until:

- the FDR table identifies the selected test;
- the selected CSV is mapped;
- hardpoints and axes are exported in a declared frame;
- the reference configuration is documented;
- SHA-256 hashes are recorded;
- output quantity definitions are resolved.

### `GEO-STEER-WUFR26-ALT-001` through `-005`

Purpose: preserve the non-selected WUFR-26 design studies as tradeoff and optimizer-regression cases. These are not failed data and must not be averaged together.

## Acceptance metrics

Exact numerical tolerances are deferred until geometry scales and source resolution are known. The report must include at least:

- mechanism closure residual;
- road-wheel-angle absolute error;
- local derivative error;
- Ackermann-reference error difference;
- left/right mirror residual;
- minimum singularity margin;
- constraint-status agreement;
- interpolation error where a sampled map is used;
- extrapolation attempts, which must fail explicitly.

Tolerances distinguish:

- analytical floating-point tolerance;
- independent-implementation tolerance;
- CAD solver/export resolution;
- physical measurement uncertainty.

## Circular-validation controls

1. Geometry read directly from the CAD file may be evaluated against the CSV from the same CAD study as a cross-tool reproduction test.
2. Geometry inferred or adjusted from that CSV makes the CSV identification data, not independent validation data.
3. The FDR table selects the design but does not independently validate its curve.
4. The reference workbook may explain test inputs but cannot validate the result it summarizes.
5. Polynomial fits in the calculator cannot be used to validate the raw curve from which they were fitted.
6. A physical sweep or separately constructed analytical/independent model is required for stronger evidence beyond legacy reproduction.

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
8. tolerance-robust case showing improved worst-case margin relative to nominal-only optimization;
9. alternative WUFR-26 configurations reproduced without configuration-specific hidden constants.

## Authorization gate

Prototype implementation may begin only when:

- the steering canonical subset is reviewed sufficiently to write unambiguous tests;
- `GEO-STEER-BASIC-001` is frozen;
- Level A and B expected results are approved;
- at least one independent Level C or D calculation is defined;
- the FDR/CSV mapping and CAD definitions needed for the intended legacy reproduction scope are recovered or explicitly deferred;
- result and failure schemas are approved.

Production design authority additionally requires the agreed Level E and/or Level F evidence and model-maturity review.
