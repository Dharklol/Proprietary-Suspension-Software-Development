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

Indexed project sources and GitHub were searched. Historical calculator tables were found, but Drive search was unavailable and the exact CAD source was not yet identified.

### `SRCH-STEER-0002` — 2026-07-19

Box steering directories were searched. `GEOMETRY FINAL.SLDPRT`, six candidate-study CSVs, `Steering Length Optimization Tests.xlsx`, supporting SolidWorks parts, and WUFR-25 `Steering_range_optimization.m` were located.

### `SRCH-STEER-0003` — final selection clarification

The WUFR-26 steering FDR table beneath `SO EVERYONE KNOWS, here is the FINAL geometry specifications:` selects Test 3. `0.5 inch back` means 0.5 in rearward relative to the previous-year rack placement.

This links the FDR selection, Test 3 reference-workbook column, `Test_3.csv`, and `GEOMETRY FINAL.SLDPRT`.

### `SRCH-STEER-0004` — final-motion export and calculator transformation

`2026Ackermann.csv` was identified as the final-geometry second-motion-study export.

| Field | Value |
|---|---|
| Box file ID | `2357045252883` |
| Box file version ID | `2611346929683` |
| Box SHA-1 | `69d71c0977287a13385683204344e78816b48512` |
| Size | `8270` bytes |
| Input | `Steer Input`, `-102` through `+102 deg`, `1 deg` step |
| Output | `Dimension2`, monitored angle in degrees |
| Points | `205` |

The angular output crosses a measurement branch between inputs `-77 deg` and `-76 deg`. Historical exports establish that the monitor must be continuously oriented and referenced before fitting. The calculator's `Steer Ratio` calculation is road-wheel gain unless reciprocated and referenced to actual steering-wheel input.

### `SRCH-STEER-0005` — production drawing and BOM hierarchy

The top-level steering, rack, tie-rod, and front-upright assemblies and drawings were reviewed. The system mapping includes `ST-A0601-AA` through `ST-A0606-AA` and `WT-A0802-AA`.

An older rack assembly PDF and the current component-drawing family differ in scope. The right-thread tie-rod end-cap also contains an apparent `SU` versus `ST` title-block prefix mismatch.

### `SRCH-STEER-0006` — baseline and rack-family clarification

The team clarified:

- the active WUFR-26 model represents the real/as-built geometry;
- `GEOMETRY FINAL.SLDPRT` is a component inside the fuller linkage subassembly;
- rack center is the midpoint between equal left/right stop limits;
- current reported rack travel is 1.00 in total, provisionally interpreted as `+/-0.50 in` from center;
- `ST-60306` through `ST-60310` are current rack-family drawings required for cost-report decomposition even though the purchased rack is represented as one assembly in the steering BOM;
- the design-spec `3.12:1` steering ratio is wrong.

The specification source was located:

| Field | Value |
|---|---|
| File | `2026_FSAE_Design_IC_Spec_Sheet_WashU_Racing.xlsx` |
| Box file ID | `2149814001036` |
| Version ID | `2510738677599` |
| Provider SHA-1 | `588669d320ff8097ec0bc85a85a970640d5a4d38` |
| Modified | `2026-06-06T04:43:43Z` |

The wrong `3.12:1` value is preserved as a rejected observation. The 1.00-in total-travel statement is preserved as a provisional observation pending active CAD/stop confirmation.

### `SRCH-STEER-0007` — final suspension geometry and coordinate reconciliation

`WUFR-26 FINAL 8.21.2025.xlsx` was located as the final OptimumK suspension geometry export used for `SU-00001-AA 2026 SUSPENSION GEOMETRY.SLDPRT`.

| Field | Value |
|---|---|
| Box file ID | `2014803790843` |
| Version ID | `2224178574043` |
| Provider SHA-1 | `15eadfb93369192038888da92ebaa6674db56cfa` |
| Modified | `2025-10-13T16:51:15Z` |
| User coordinate matrix | `[[1,0,0],[0,-1,0],[0,0,1]]` |

The final OptimumK export uses longitudinal, lateral-positive-right, vertical-positive-up coordinates in millimetres. The raw Test 3 steering-study triplets use lateral-positive-left, vertical-positive-up, longitudinal-positive-forward coordinates in inches.

Recovered adapter:

```text
[x_optk, y_optk, z_optk] = 25.4 * [z_sw, -x_sw, y_sw]
```

The Test 3 front-left inner point maps within `0.05 mm` of the final OptimumK left-side point. The outer point differs by approximately `2.25 mm` vector magnitude, indicating a later geometry revision rather than a failed transform.

The team confirmed the steering FDR tie-rod pair is the front-left corner when viewed from behind facing the nose. The FDR frame is longitudinal, lateral-positive-left, vertical-positive-up, in millimetres. Its canonical adapter is therefore direct unit conversion:

```text
[x_can, y_can, z_can] = 0.001 * [x_fdr, y_fdr, z_fdr]
```

The FDR front-left inner pickup is exactly `12.700 mm` rearward of the final OptimumK front-left tie-rod inner point after both are expressed in one frame. This is the selected 0.5-in steering revision, not a coordinate conversion.

### `SRCH-STEER-0008` — nominal static-toe reference state

The team confirmed that the final OptimumK geometry is recorded at the listed nonzero static-toe state rather than at zero toe. The workbook displays `Static Toe = -1.000 deg` in each front-side field. A quick CAD inspection also confirms nonzero toe qualitatively through unequal near/far distances from a wheel-ring reference to the vehicle center plane.

This establishes that zero mechanism rotation means the imported nominal static-toe state. Incremental steering evaluation is unblocked. Absolute toe-inclusive road-wheel heading remains gated on a numerical wheel-plane basis and reconciliation of the OptimumK side-field definition with the specification's axle-sum-toe wording.

## Final design-study hierarchy

1. WUFR-26 steering FDR final-geometry table.
2. Selected configuration: Test 3.
3. Relative rack-placement intent: 0.5 in rearward from previous year.
4. Mechanism-study component: `GEOMETRY FINAL.SLDPRT`, Box ID `1971276311204`.
5. Final response: `2026Ackermann.csv`, Box ID `2357045252883`.
6. Selection-era cross-check: `Test_3.csv`, Box ID `1938821987892`.
7. Design-intent reference: `Steering Length Optimization Tests.xlsx`, Test 3.

## Active-geometry hierarchy

1. Active WUFR-26 vehicle/steering assembly configuration and declared setup.
2. `GEOMETRY FINAL.SLDPRT` component instance within that linkage assembly.
3. Final OptimumK workbook for suspension hardpoints and steering-axis construction.
4. Steering FDR final table for selected front-left tie-rod pickups.
5. Current assembly references and matching drawings for rack, tie rods, uprights, and mounts.
6. Final motion-study response for cross-tool comparison.
7. Specification values as scalar consistency evidence, excluding rejected values.
8. Historical drawings, copied CAD files, and prior-car exports.

The design-study and active-assembly chains are connected. The nominal design geometry is sufficient for a bounded incremental evaluator. Native configuration state is still required before installed/as-built geometry is frozen.

## Current artifact status

| Catalog ID | Artifact | Current state | Next action |
|---|---|---|---|
| `CAT-EXT-0001` | Legacy steering optimization process | Selection mapping established | Retain historical objective/bounds evidence |
| `CAT-EXT-0002` | WUFR-24 motion study | Calculator export only | Recover parent CAD only if historical regression is needed |
| `CAT-EXT-0003` | WUFR-25 motion study | Raw/converted export and CAD candidates located | Freeze CAD-to-export lineage if used |
| `CAT-EXT-0004` | WUFR-26 final CAD and motion study | Source and final export designated | Export active configuration, driver, monitor, domain, and warnings for Level E correlation |
| `CAT-EXT-0016` | Steering active geometry | Nominal design geometry merged; installed state open | Export active assembly references, opposite-side hardpoints, wheel planes, stops, and setup |
| `CAT-EXT-0025` | Physical steering sweep | Not identified | Recover a test or define a fixture plan |
| `CAT-STEER-SPEC-0001` | WUFR-26 specification | Source metadata located; ratio rejected | Capture immutable bytes; use remaining values as observations only |
| `CAT-STEER-GEO-0001` | Final OptimumK suspension geometry | Source and adapter located | Capture SHA-256 and retain as nominal suspension geometry authority |

## Benchmark-freeze requirements

1. Catalog the exact FDR version/table and project SHA-256.
2. Compute project SHA-256 for final CAD, final CSV, Test 3 CSV, reference workbook, and final OptimumK geometry workbook.
3. Record SolidWorks version, active configurations, dependencies, equations, study settings, warnings, and component suppression state.
4. Export the exact `GEOMETRY FINAL.SLDPRT` component instance inside the active linkage assembly.
5. Map SolidWorks drivers and monitors to canonical quantities.
6. Export or measure the front-right hardpoints to test the nominal symmetry assumption.
7. Export wheel-plane bases and reconcile the exact per-wheel static-toe convention before claiming absolute wheel headings.
8. Confirm rack-center definition and the reported 1.00-in total travel against both stop states.
9. Record camber shim stack, ride height, wheel/tire state, tie-rod adjustment, and absence/presence of compliance load.
10. Derive the correct center steering ratio; do not use `3.12:1` as expected evidence.
11. Compare transformed raw points before comparing polynomial fits.
12. Retain non-selected candidate CSVs as regression cases.
13. Obtain independent physical or analytical evidence beyond CAD reproduction.

The exact installed-state export request is `data_catalog/wufr26_steering_baseline_reconciliation.md`.

## Decision rules

- The FDR selects a configuration but does not validate its curve.
- `0.5 inch back` is relative intent, not an absolute coordinate.
- `2026Ackermann.csv` is the primary final response; `Test_3.csv` is a cross-check.
- A fitted polynomial cannot independently validate its source export.
- A manufacturing drawing controls stated features, not the installed hardpoint by itself.
- BOM scope may differ from cost-report drawing scope for a purchased assembly.
- Rejected observations remain preserved but are numerically prohibited downstream.
- The front-left FDR point set must not be mislabeled as front-right.
- Static toe is embedded in the imported nominal reference state and must not be removed by changing hardpoint coordinates.
- Provider SHA-1 supports discovery; project SHA-256 is required for freeze.
