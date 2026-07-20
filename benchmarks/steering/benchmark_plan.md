# Steering Geometry Benchmark Plan

**Status:** Analytical preimplementation packet proposed; WUFR-26 Level E benchmark remains open  
**Primary targets:** `MOD-STEER-0001`, `EQ-STEER-0001` through `EQ-STEER-0007`, `BENCH-STEER-0001` through `BENCH-STEER-0008`

## Purpose

This plan defines the evidence required before the rigid steering evaluator or inverse-design workflow can be authorized for design decisions. Matching SolidWorks is a cross-tool reproduction test, not proof of physical correctness.

The immediate implementation gate is defined in:

- `docs/models/steering/rigid_steering_function_specification.md`;
- `benchmarks/steering/preimplementation_freeze_packet.md`;
- `benchmarks/steering/GEO-STEER-BASIC-001.toml`;
- equation records `EQ-STEER-0001` through `0007`;
- benchmark records `BENCH-STEER-0002` through `0008`.

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

## Stable benchmark records

| Stable ID | Level | Scope |
|---|---|---|
| `BENCH-STEER-0001` | E | Final WUFR-26 SolidWorks comparison |
| `BENCH-STEER-0002` | C | Exact Ackermann analytical pairs |
| `BENCH-STEER-0003` | A | Reference tie-rod closure and branch |
| `BENCH-STEER-0004` | B | Sweep, symmetry, continuity, and singularity behavior |
| `BENCH-STEER-0005` | A | Steering transmission identity and unit conversion |
| `BENCH-STEER-0006` | B | Local derivative, gain, and ratio verification |
| `BENCH-STEER-0007` | B | Turning-radius reconstruction and mismatch reporting |
| `BENCH-STEER-0008` | B | Ackermann error sign, inside/outside aliases, and toe treatment |

The previous descriptive A/B/C case names remain useful subcases, but the stable records above are the durable references.

## Benchmark hierarchy

### Level A — dimensional and algebraic

Required cases include:

- zero input at rack center reproduces declared static left/right toe;
- inner-to-outer distance equals nominal tie-rod length;
- `m/rad`, `mm/rev`, and steering-wheel/pinion conversions agree;
- implicit/analytical derivatives agree with finite differences;
- every point links to geometry, model, solver, and source revision;
- angular branch unwrapping, monitor-datum subtraction, and toe handling remain separate operations.

### Level B — limiting, symmetry, and topology

Required cases include:

- mirrored geometry and opposite sweeps mirror left/right outputs;
- parallel-steer and exact Ackermann reference cases;
- zero-track and small-angle limits;
- singularity approach degrades the condition metric and stops the solver before branch crossing;
- reversed rack direction transforms signs through convention rather than hidden fixes;
- intended unequal tie rods/asymmetry remain visible;
- total toe-inclusive heading and incremental steering displacement remain separately available.

### Level C — analytical and published mechanisms

- exact no-slip Ackermann angle/radius pairs;
- independently computed planar rack/tie-rod closure;
- published trapezoidal-linkage cases only when definitions are complete;
- reviewed rack steering relation with joint-center geometry and input identity.

Published cases are adopted only when definitions can be translated without ambiguity.

### Level D — independent implementation

A separately authored implementation compares rack displacement, left/right wheel heading, closure, local derivatives, inner/outer relation, Ackermann error, radius outputs, branch identity, and failure states. Tolerances are set before comparison.

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
- vehicle state, ride height, static alignment, rack center, and installed stops;
- previous-year rack datum and canonical meaning of the 0.5-in rearward change;
- exact motion-study name, driver quantity, sweep domain, and operational subset;
- definitions, signs, zero, and wheel identity for `Steer Input`, `Dimension2`, `Steer_Angle`, and `Measurement1`;
- reviewed angular branch orientation, monitor datum, and static-toe treatment;
- raw transformed expected table and source resolution.

The comparison report includes raw and transformed curves, interpolation residuals, maximum and RMS angle error, center derivative error, full-lock error, closure residual, symmetry residual, branch handling, and discontinuities.

#### Final-export transformation check

`2026Ackermann.csv` has 205 samples from `-102` to `+102 deg`. Its raw angular monitor crosses a measurement branch between `-77` and `-76 deg`. The benchmark must reproduce the reviewed branch orientation before converting the monitor to a wheel quantity.

The unwrapped monitor is `20.57 deg` at exported input zero. That number is an observation, not automatically the datum to subtract. The historical WUFR fits retain approximately one degree of static toe, so the controlled transformation must separately record:

```text
unwrapped angular monitor
-> monitor-specific datum subtraction
-> total toe-inclusive wheel heading
-> subtraction of rack-center heading when incremental steer is required
```

A forced-zero transformation is allowed only as a separately named incremental normalization. It is not the historical total-heading curve.

#### Historical calculator comparison

The calculator's `Steer Ratio` quantity is road-wheel gain,

```text
Delta road-wheel angle / Delta steering input
```

not conventional steering ratio. The reciprocal is conventional ratio only when the input is steering-wheel angle. The benchmark reports both quantities with explicit names.

#### Alternative regression set

The five non-selected candidate CSVs remain separate configurations. They test whether the evaluator reproduces multiple geometries without hidden constants tuned to Test 3.

### Level F — physical steering sweep

The physical benchmark measures steering-wheel and shaft angle where available, rack displacement, left/right road-wheel heading, sweep direction, repeated cycles, setup, load, calibration, synchronization, and uncertainty. Both sweep directions are required to expose backlash, hysteresis, compliance, and zero uncertainty.

## Geometry sets

### `GEO-STEER-BASIC-001`

The fully specified synthetic fixture is stored in `GEO-STEER-BASIC-001.toml`. It freezes:

- exact frame and geometry;
- tie-rod length;
- five solved rack positions;
- mirror behavior;
- center derivatives;
- Ackermann references/errors;
- rear-axle-center radii;
- tolerances;
- deliberate branch-failure states.

It is a planar special case of the spatial model and is not a WUFR parameter set.

### `GEO-STEER-WUFR25-HIST-001`

Historical WUFR-25 CAD/export case, separate from the WUFR-25 MATLAB effort/range objective.

### `GEO-STEER-WUFR26-FINAL-001`

Final WUFR-26 Test 3 geometry. Parent source is `GEOMETRY FINAL.SLDPRT`; primary response is `2026Ackermann.csv`; `Test_3.csv` is a cross-check. Freeze requires hardpoints/axes, source hashes, study metadata, quantity definitions, total/incremental angle transformation, and physical domain.

### `GEO-STEER-WUFR26-ALT-001` through `-005`

Non-selected WUFR-26 studies preserved for tradeoff and optimizer-regression testing.

## Acceptance metrics

- mechanism closure residual;
- road-wheel-heading absolute and RMS error;
- total-heading and incremental-steer distinction;
- local road-wheel-gain error;
- conventional-ratio error where defined;
- Ackermann-reference error difference;
- left/right mirror residual;
- minimum singularity margin;
- constraint-status agreement;
- angular-branch, monitor-datum, and static-toe agreement;
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

A bounded evaluator prototype may be considered only after review accepts the function specification, equation records, `GEO-STEER-BASIC-001`, Level A/B/C expected results, result/failure schema, and branch-control behavior.

WUFR-26 cross-tool maturity additionally requires the Level E source and signal freeze. Production design authority requires agreed Level E and/or Level F evidence and a model-maturity review.