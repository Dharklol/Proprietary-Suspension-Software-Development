# Steering Geometry Benchmark Plan

**Status:** Proposed; WUFR-26 final mechanism and final-motion export located, benchmark not frozen  
**Primary targets:** `MOD-STEER-0001`, future steering mechanism equations, `BENCH-STEER-0001`

## Purpose

This plan defines the evidence required before the rigid steering evaluator or inverse-design workflow can be authorized for design decisions. Matching SolidWorks is a cross-tool reproduction test, not proof of physical correctness.

## WUFR-26 authority hierarchy

1. `GEOMETRY FINAL.SLDPRT` is the final mechanism source.
2. The steering FDR table beneath `SO EVERYONE KNOWS, here is the FINAL geometry specifications:` selects `Test 3`.
3. `0.5 inch back` means the rack is 0.5 in rearward relative to the previous-year placement; it is not an absolute coordinate without its frame and datum.
4. `2026Ackermann.csv` is the primary final-geometry second-motion-study export.
5. `Test_3.csv` is a selection-era response and cross-check.
6. `Steering Length Optimization Tests.xlsx`, Test 3 column, is supporting design-intent evidence.
7. The five other candidate CSVs remain separate tradeoff/regression cases.
8. The calculator `Steer Ratio` sheet contains WUFR-24 and WUFR-25 history, not the WUFR-26 source.

The source manifest is `data_catalog/steering_box_source_manifest.toml`. The selected lineage is `data_catalog/wufr26_test3_selected_lineage.md`. The fit reconstruction is `migration/legacy_calculators/steering_tie_rod_optimizer/steer_ratio_fit_reconstruction.md`.

## Benchmark hierarchy

### Level A — dimensional and algebraic

| ID | Case | Expected result |
|---|---|---|
| `BENCH-STEER-A001` | Zero input at rack center | Declared static left/right toe and no unexplained offset |
| `BENCH-STEER-A002` | Tie-rod closure | Inner-to-outer distance equals nominal link length within tolerance |
| `BENCH-STEER-A003` | Unit conversions | `m/rad`, `mm/rev`, and steering-wheel/pinion conversions agree |
| `BENCH-STEER-A004` | Differentiation | Analytical or automatic derivatives agree with finite differences |
| `BENCH-STEER-A005` | Result lineage | Every point links to geometry, model, solver, and source revision |
| `BENCH-STEER-A006` | Angle transformation | Branch orientation and reference subtraction reproduce reviewed points |

### Level B — limiting, symmetry, and topology

| ID | Case | Expected result |
|---|---|---|
| `BENCH-STEER-B001` | Mirrored geometry | Opposite sweeps mirror left/right outputs |
| `BENCH-STEER-B002` | Parallel steer | Left/right angles remain equal apart from declared toe |
| `BENCH-STEER-B003` | Ideal Ackermann | Exact low-speed inner/outer relation is reproduced |
| `BENCH-STEER-B004` | Zero-track limit | Left/right curves converge |
| `BENCH-STEER-B005` | Small-angle limit | Exact and small-angle references converge |
| `BENCH-STEER-B006` | Singularity approach | Condition metric degrades and solver stops before branch crossing |
| `BENCH-STEER-B007` | Reversed rack direction | Signs transform by convention rather than hidden fixes |
| `BENCH-STEER-B008` | Unequal tie rods | Intended asymmetry remains visible |

### Level C — analytical and published mechanisms

- `BENCH-STEER-C001`: exact no-slip Ackermann angles.
- `BENCH-STEER-C002`: independently hand-computed planar rack/tie-rod closure.
- `BENCH-STEER-C003`: published trapezoidal-linkage case with complete definitions.
- `BENCH-STEER-C004`: reviewed rack steering relation with tie-rod length, steering-arm length, rack-to-axis distance, and rack displacement.

Published cases are adopted only when definitions can be translated without ambiguity.

### Level D — independent implementation

`BENCH-STEER-D001` uses a separately authored implementation and compares rack displacement, left/right wheel angle, closure, local derivatives, inner/outer relation, and Ackermann error. Tolerances are set before comparison.

### Level E — WUFR-26 SolidWorks comparison

#### `BENCH-STEER-0001`

| Role | Artifact |
|---|---|
| Mechanism source | `GEOMETRY FINAL.SLDPRT` |
| Selection authority | WUFR-26 steering FDR final-geometry table |
| Selected configuration | `Test 3` |
| Primary final response | `2026Ackermann.csv` |
| Selection-era cross-check | `Test_3.csv` |
| Candidate summary | `Steering Length Optimization Tests.xlsx`, Test 3 column |

Required frozen inputs:

- immutable source bytes and SHA-256 for all listed artifacts;
- exact FDR file, table location, author/revision, and hash;
- SolidWorks version, file version, active configuration, suppression state, dependencies, equations, design tables, and warnings;
- vehicle state, ride height, alignment, rack center, and stops;
- previous-year rack datum and canonical meaning of the 0.5-in rearward change;
- exact motion-study name, driver quantity, sweep domain, and operational subset;
- definitions, signs, zero, and wheel identity for `Steer Input`, `Dimension2`, `Steer_Angle`, and `Measurement1`;
- reviewed angular branch orientation and straight-ahead reference;
- raw transformed expected table and source resolution.

The comparison report includes raw and transformed curves, interpolation residuals, maximum and RMS angle error, center derivative error, full-lock error, closure residual, symmetry residual, branch handling, and discontinuities.

#### Final-export transformation check

`2026Ackermann.csv` has 205 samples from `-102` to `+102 deg`. Its raw angular monitor crosses a measurement branch between `-77` and `-76 deg`. The benchmark must reproduce the reviewed branch orientation and subtract the reviewed straight-ahead reference before comparing road-wheel angle.

A provisional reference of `20.57 deg` at exported input zero is documented for reconstruction only. It is not frozen parameter authority.

#### Historical calculator comparison

The calculator's `Steer Ratio` quantity is road-wheel gain,

```text
Delta road-wheel angle / Delta steering input
```

not conventional steering ratio. The reciprocal is conventional ratio only when the input is steering-wheel angle. The benchmark reports both quantities with explicit names.

#### Alternative regression set

The five non-selected candidate CSVs remain separate configurations. They test whether the evaluator reproduces multiple geometries without hidden constants tuned to Test 3.

### Level F — physical steering sweep

`BENCH-STEER-F001` measures steering-wheel and shaft angle where available, rack displacement, left/right road-wheel angle, sweep direction, repeated cycles, setup, load, calibration, synchronization, and uncertainty. Both sweep directions are required to expose backlash, hysteresis, compliance, and zero uncertainty.

## Geometry sets

### `GEO-STEER-BASIC-001`

Idealized symmetric fixture for signs, closure, symmetry, derivatives, exact Ackermann, and singularity handling.

### `GEO-STEER-WUFR25-HIST-001`

Historical WUFR-25 CAD/export case, separate from the WUFR-25 MATLAB effort/range objective.

### `GEO-STEER-WUFR26-FINAL-001`

Final WUFR-26 Test 3 geometry. Parent source is `GEOMETRY FINAL.SLDPRT`; primary response is `2026Ackermann.csv`; `Test_3.csv` is a cross-check. Freeze requires hardpoints/axes, source hashes, study metadata, quantity definitions, angle transformation, and physical domain.

### `GEO-STEER-WUFR26-ALT-001` through `-005`

Non-selected WUFR-26 studies preserved for tradeoff and optimizer-regression testing.

## Acceptance metrics

- mechanism closure residual;
- road-wheel-angle absolute and RMS error;
- local road-wheel-gain error;
- conventional-ratio error where defined;
- Ackermann-reference error difference;
- left/right mirror residual;
- minimum singularity margin;
- constraint-status agreement;
- angular-branch and reference-offset agreement;
- interpolation error;
- missing-scenario handling;
- explicit extrapolation failure.

Tolerances distinguish floating-point, independent-implementation, CAD/export, and physical-measurement uncertainty.

## Circular-validation controls

1. Geometry read from CAD may be compared with the export as cross-tool reproduction.
2. Geometry inferred from the export makes that export identification data, not validation data.
3. The FDR selects Test 3 but does not validate the curve.
4. The workbook explains candidate inputs/summary outputs but is not independent validation.
5. Polynomial fits cannot validate the raw data used to create them.
6. `Test_3.csv` and `2026Ackermann.csv` share design lineage and are not independent evidence.
7. Physical or separately constructed analytical evidence is required beyond legacy reproduction.

## Optimizer verification

The optimizer is verified only after the evaluator passes its gate. Cases include known feasible recovery, explicit infeasibility, initialization sensitivity, multimodality, active bounds, soft-band decomposition, discrete options, tolerance robustness, and reproduction of alternative WUFR-26 configurations without configuration-specific hidden constants.

## Authorization gate

Prototype implementation requires reviewed canonical definitions, a frozen basic geometry set, approved Level A/B expectations, one independent Level C/D case, sufficiently catalogued WUFR-26 source lineage, and approved result/failure schemas.

Production design authority additionally requires agreed Level E and/or Level F evidence and model-maturity review.
