# Steering Source-Recovery Log

**Status:** WUFR-26 final configuration and final-motion export located; angle/ratio transformation reconstructed  
**Related IDs:** `MIG-STR-0001`, `MOD-STEER-0001`, `BENCH-STEER-0001`, `CAT-EXT-0001` through `CAT-EXT-0004`, `CAT-EXT-0016`, `CAT-EXT-0025`

## Purpose

This log distinguishes mechanism sources, design-selection records, candidate-study exports, final-motion exports, calculator transformations, and independent validation evidence.

## Evidence states

- **Candidate located:** possibly relevant artifact; identity or lineage unresolved.
- **Source located:** original item and provider metadata found; project hash or internal metadata may remain open.
- **Export recovered:** derived table or result found; source configuration may remain open.
- **Selection mapping established:** FDR selection, candidate record, export, and parent model linked.
- **Benchmark source designated:** team-selected mechanism/result source identified.
- **Benchmark frozen:** immutable bytes, definitions, expected outputs, domain, and tolerances approved.

## Search history

### `SRCH-STEER-0001` — 2026-07-18

Indexed project sources and GitHub were searched. Historical calculator tables were found, but Drive search was unavailable and the exact CAD source was not yet identified.

### `SRCH-STEER-0002` — 2026-07-19

Box steering geometry directories were searched. `GEOMETRY FINAL.SLDPRT`, six candidate-study CSVs, `Steering Length Optimization Tests.xlsx`, supporting SolidWorks parts, and WUFR-25 `Steering_range_optimization.m` were located.

### `SRCH-STEER-0003` — final selection clarification

The WUFR-26 steering FDR table beneath `SO EVERYONE KNOWS, here is the FINAL geometry specifications:` selects `Test 3`. The phrase `0.5 inch back` means 0.5 in rearward relative to the previous-year rack placement.

This links:

- FDR selection: `Test 3`;
- reference workbook: `Test 3` column;
- selection-era export: `Test_3.csv`;
- parent source: `GEOMETRY FINAL.SLDPRT`.

### `SRCH-STEER-0004` — final-motion export and calculator transformation

The team added `2026Ackermann.csv` to the WUFR-26 geometry directory as the export from the final-geometry second motion study.

Recovered metadata:

| Field | Value |
|---|---|
| Box file ID | `2357045252883` |
| Box file version ID | `2611346929683` |
| Box SHA-1 | `69d71c0977287a13385683204344e78816b48512` |
| Size | `8270` bytes |
| Input row | `Steer Input`, `-102` through `+102 deg`, `1 deg` step |
| Output row | `Dimension2`, monitored angle in degrees |
| Point count | `205` |

The raw angular output crosses its measurement branch between inputs `-77 deg` and `-76 deg`. Historical WUFR-25 exports show that the calculator then subtracts a fixed straight-ahead reference angle before fitting the road-wheel curve.

The exact reconstruction is documented in `migration/legacy_calculators/steering_tie_rod_optimizer/steer_ratio_fit_reconstruction.md`.

## Final WUFR-26 authority hierarchy

1. **Design-selection authority:** WUFR-26 steering FDR final-geometry table.
2. **Selected configuration:** `Test 3`.
3. **Relative rack-placement intent:** 0.5 in rearward from the previous-year placement.
4. **Mechanism source:** `GEOMETRY FINAL.SLDPRT`, Box ID `1971276311204`.
5. **Primary final-motion response:** `2026Ackermann.csv`, Box ID `2357045252883`.
6. **Selection-era cross-check:** `Test_3.csv`, Box ID `1938821987892`.
7. **Design-intent reference:** `Steering Length Optimization Tests.xlsx`, Test 3 column.

The detailed mapping is `data_catalog/wufr26_test3_selected_lineage.md`.

## Reconstructed calculator logic

The WUFR-25 exports retain both raw and converted output rows:

```text
WUFR_25.csv:
wheel_output = Dimension2 - 32.9 deg

3.5INREV_WUFR25.csv:
wheel_output = Dimension2 - 33.0 deg
```

Therefore the historical angle conversion is a straight-ahead reference subtraction. Where the SolidWorks angle monitor crosses its zero branch, the raw values must first be oriented into one continuous angle.

The spreadsheet quantity labeled `Steer Ratio` is the point-to-point slope

```text
Delta road-wheel angle / Delta steering input
```

which is local road-wheel gain. Conventional steering ratio is the reciprocal only when the input is steering-wheel angle. WUFR-24 and WUFR-25 use inconsistent forward/backward difference placement, so the replacement model requires an explicit derivative convention.

## Current artifact status

| Catalog ID | Artifact | Current state | Next action |
|---|---|---|---|
| `CAT-EXT-0001` | Legacy steering optimization process | Selection mapping established | Recover objective, bounds, final variable definitions, and study settings |
| `CAT-EXT-0002` | WUFR-24 motion study | Calculator export only | Recover parent CAD only if historical regression is needed |
| `CAT-EXT-0003` | WUFR-25 motion study | Raw/converted export and CAD candidates located | Freeze CAD-to-export lineage |
| `CAT-EXT-0004` | WUFR-26 final CAD and motion study | Source and final export designated | Hash bytes and record SolidWorks configuration, driver, monitor, domain, and warnings |
| `CAT-EXT-0016` | Steering geometry source | Final/supporting CAD located | Export hardpoints and axes in a declared frame |
| `CAT-EXT-0025` | Physical steering sweep | Not identified | Recover a test or define a fixture plan |

## Benchmark-freeze requirements

1. Catalog the exact FDR file, version, table location, and SHA-256.
2. Compute SHA-256 for `GEOMETRY FINAL.SLDPRT`, `2026Ackermann.csv`, `Test_3.csv`, and the reference workbook.
3. Record SolidWorks version, active configuration, dependencies, equations, study settings, and warnings.
4. Map `Steer Input`, `Dimension2`, `Steer_Angle`, and `Measurement1` to canonical quantities.
5. Confirm the angular-branch orientation and straight-ahead reference.
6. Declare physical steering limits; do not assume every exported scenario is operational.
7. Compare transformed raw points before comparing polynomial fits.
8. Retain the non-selected candidate CSVs as separate regression cases.
9. Obtain independent physical or analytical evidence for validation beyond CAD reproduction.

## Decision rules

- The FDR selects the configuration but does not validate its curve.
- `0.5 inch back` is relative design intent, not an absolute coordinate.
- `2026Ackermann.csv` is the primary final-motion export; `Test_3.csv` remains a cross-check.
- A polynomial fitted to an export cannot independently validate that export.
- Provider SHA-1 supports discovery; project SHA-256 is required for freeze.
