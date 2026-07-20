# Steering Source-Recovery Log

**Status:** WUFR-26 nominal design geometry and coordinate adapters recovered; installed SolidWorks state remains a correlation gate  
**Related IDs:** `MIG-STR-0001`, `MOD-STEER-0001`, `BENCH-STEER-0001`, `CAT-EXT-0001` through `CAT-EXT-0004`, `CAT-EXT-0016`, `CAT-EXT-0025`, `CAT-STEER-SPEC-0001`, `CAT-STEER-GEO-0001`, `RISK-STEER-0001`

## Purpose

This log distinguishes mechanism sources, design-selection records, candidate exports, final-motion exports, nominal suspension geometry, production drawings, active assembly state, calculator transformations, setup observations, and independent validation evidence.

## Evidence states

- **Candidate located:** possibly relevant artifact; identity or lineage unresolved.
- **Source located:** original item and provider metadata found; project hash or internal metadata may remain open.
- **Export recovered:** derived table or result found; source configuration may remain open.
- **Selection mapping established:** FDR selection, candidate record, export, and parent model linked.
- **Coordinate reconciled:** source frames and numerical transforms are supported by common points.
- **Nominal design geometry merged:** reviewed source hierarchy supplies a complete bounded design-source geometry subset.
- **Production identity mapped:** assembly, drawing, BOM, and folder hierarchy located; active native configuration may remain open.
- **Baseline reconciled:** intended model state, scalar observations, rejected values, and remaining gates recorded.
- **Benchmark frozen:** immutable bytes, definitions, expected outputs, domain, and tolerances approved.

## Search and clarification history

### `SRCH-STEER-0001` — 2026-07-18

Indexed project sources and GitHub were searched. Historical calculator tables were found, but the exact CAD source was not yet identified.

### `SRCH-STEER-0002` — 2026-07-19

Box steering directories were searched. `GEOMETRY FINAL.SLDPRT`, six candidate-study CSVs, `Steering Length Optimization Tests.xlsx`, supporting SolidWorks parts, and WUFR-25 `Steering_range_optimization.m` were located.

### `SRCH-STEER-0003` — final selection clarification

The WUFR-26 steering FDR final-geometry table selects Test 3. `0.5 inch back` means 0.5 in rearward relative to the preceding rack placement. This links the FDR selection, Test 3 workbook column, `Test_3.csv`, and `GEOMETRY FINAL.SLDPRT`.

### `SRCH-STEER-0004` — final-motion export and calculator transformation

`2026Ackermann.csv` was identified as the final-geometry second-motion-study export.

| Field | Value |
|---|---|
| Box file ID | `2357045252883` |
| Box file version ID | `2611346929683` |
| Box SHA-1 | `69d71c0977287a13385683204344e78816b48512` |
| Input | `Steer Input`, `-102` through `+102 deg`, `1 deg` step |
| Output | `Dimension2`, monitored angle in degrees |
| Points | `205` |

Historical exports establish that the angle monitor must be continuously oriented and referenced before fitting. The calculator's `Steer Ratio` calculation is road-wheel gain unless reciprocated and referenced to actual steering-wheel input.

### `SRCH-STEER-0005` — production drawing and BOM hierarchy

The top-level steering, rack, tie-rod, and front-upright assemblies and drawings were reviewed. The system mapping includes `ST-A0601-AA` through `ST-A0606-AA` and `WT-A0802-AA`.

An older rack assembly PDF and the current component-drawing family differ in scope. The right-thread tie-rod end-cap also contains an apparent `SU` versus `ST` title-block prefix mismatch.

### `SRCH-STEER-0006` — baseline and rack-family clarification

The team clarified that the model ultimately represents the real geometry, `GEOMETRY FINAL.SLDPRT` is inside the fuller linkage assembly, rack center is the midpoint between equal stop limits, reported total rack travel is 1.00 in, `ST-60306` through `ST-60310` are current cost-report decomposition drawings, and the design-spec `3.12:1` ratio is wrong.

The specification source was cataloged as `CAT-STEER-SPEC-0001`. The wrong ratio is preserved as a rejected observation, and the travel statement is provisional pending stop verification.

### `SRCH-STEER-0007` — OptimumK, SolidWorks, and FDR coordinate reconciliation

The final suspension workbook was located:

| Field | Value |
|---|---|
| File | `WUFR-26 FINAL 8.21.2025.xlsx` |
| Box file ID | `2014803790843` |
| Version ID | `2224178574043` |
| Provider SHA-1 | `15eadfb93369192038888da92ebaa6674db56cfa` |
| Related CAD | `SU-00001-AA 2026 SUSPENSION GEOMETRY.SLDPRT` |

The workbook records coordinate matrix `[[1,0,0],[0,-1,0],[0,0,1]]`, and its exported right-side points have positive lateral coordinates.

Test 3 points from `Steering Length Optimization Tests.xlsx` establish the raw-study mapping:

```text
[x_optk, y_optk, z_optk] = 25.4 * [z_sw, x_sw, y_sw]
```

The Test 3 inner point maps within `0.05 mm` of the final OptimumK value. The final outer point differs beyond rounding, showing that the outer pickup was revised after the Test 3 worksheet record.

The steering FDR final table provides:

```text
Tie Rod Inner = [-79.298, 220.980, 162.865] mm
Tie Rod Outer = [-61.933, 549.102, 192.223] mm
```

The FDR inner point is exactly `12.700 mm` rearward of the OptimumK tie-rod inner point. This confirms the selected 0.5-in steering revision and prevents it from being mistaken for a coordinate transform. The FDR joint-center distance is `329.890 mm`, consistent with the nominal 13-in Test 3 tie rod.

The final source merge is documented in `docs/conventions/wufr26_coordinate_frame_reconciliation.md`.

## Final design-study hierarchy

1. WUFR-26 steering FDR final-geometry table.
2. Selected configuration: Test 3.
3. Relative rack-placement intent: 0.5 in rearward.
4. Mechanism-study component: `GEOMETRY FINAL.SLDPRT`, Box ID `1971276311204`.
5. Final response: `2026Ackermann.csv`, Box ID `2357045252883`.
6. Selection-era cross-check: `Test_3.csv`, Box ID `1938821987892`.
7. Design-intent reference: `Steering Length Optimization Tests.xlsx`, Test 3.

## Nominal geometry authority hierarchy

1. `WUFR-26 FINAL 8.21.2025.xlsx` for suspension hardpoints and steering-axis construction.
2. Steering FDR final table for selected tie-rod inner and outer pickups.
3. Test 3 workbook points for transform and design-intent evidence.
4. `GEOMETRY FINAL.SLDPRT` and `2026Ackermann.csv` for response reproduction.
5. Active assembly export or measurement for installed-state validation.

The generic OptimumK tie-rod points do not overwrite the later steering FDR points. The FDR table does not replace the OptimumK upright points.

## Current artifact status

| Catalog ID | Artifact | Current state | Next action |
|---|---|---|---|
| `CAT-EXT-0001` | Legacy steering optimization process | Selection mapping established | Retain historical objective/bounds evidence |
| `CAT-EXT-0004` | WUFR-26 final steering study and response | Source and final export designated | Freeze hashes and study metadata |
| `CAT-STEER-GEO-0001` | Final OptimumK suspension geometry | Source and transform located | Capture SHA-256; freeze reviewed nominal configuration |
| `CAT-EXT-0016` | Steering active geometry | Nominal design source merge complete | Correlate active assembly, setup, stops, and left/right state |
| `CAT-EXT-0025` | Physical steering sweep | Not identified | Recover a test or define a fixture plan |
| `CAT-STEER-SPEC-0001` | WUFR-26 specification | Source metadata located; ratio rejected | Capture immutable bytes; use remaining values as observations only |

## Benchmark-freeze requirements

1. Catalog the exact FDR file/version/table and project SHA-256.
2. Compute project SHA-256 for the final OptimumK workbook, final CAD, final response CSV, Test 3 CSV, and reference workbook.
3. Freeze the coordinate adapters and named source frames.
4. Confirm left-side geometry or explicitly approve nominal mirroring.
5. Record active SolidWorks configurations, dependencies, warnings, and suppression state for Level E correlation.
6. Map SolidWorks drivers and monitors to canonical quantities.
7. Confirm rack-center definition and the reported 1.00-in total travel against both stop states.
8. Record actual toe, wheel planes, camber, shim stack, ride height, wheel/tire state, and tie-rod adjustment.
9. Derive the correct center steering ratio; do not use `3.12:1` or the undefined OptimumK `101.600` field.
10. Compare transformed raw points before polynomial fits.
11. Obtain independent physical or analytical evidence beyond CAD reproduction.

## Decision rules

- The FDR selects a configuration but does not validate its response curve.
- The 0.5-in rearward change is a geometry revision, not a frame conversion.
- Standard names do not replace file-specific frame metadata and adapters.
- A fitted polynomial cannot independently validate its source export.
- A manufacturing drawing controls stated features, not the installed hardpoint by itself.
- Rejected or undefined ratio fields are numerically prohibited downstream.
- Provider SHA-1 supports discovery; project SHA-256 is required for freeze.