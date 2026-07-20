# Steering Source-Recovery Log

**Status:** WUFR-26 final configuration, final-motion export, historical angle/ratio transformation, and current design-spec steering definitions located  
**Related IDs:** `MIG-STR-0001`, `MOD-STEER-0001`, `BENCH-STEER-0001`, `CAT-STEER-SPEC-0001`, `CAT-EXT-0001` through `CAT-EXT-0004`, `CAT-EXT-0016`, `CAT-EXT-0025`

## Purpose

This log distinguishes mechanism sources, design-selection records, candidate-study exports, final-motion exports, design-spec observations, calculator transformations, and independent validation evidence.

## Evidence states

- **Candidate located:** possibly relevant artifact; identity or lineage unresolved.
- **Source located:** original item and provider metadata found; project hash or internal metadata may remain open.
- **Export recovered:** derived table or result found; source configuration may remain open.
- **Selection mapping established:** FDR selection, candidate record, export, and parent model linked.
- **Definition recovered:** a source term has an explicit definition, without automatically accepting its numerical value as active.
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

The raw angular output crosses its measurement branch between inputs `-77 deg` and `-76 deg`. Recovered candidate exports and Desmos equations show that the historical process then subtracts a monitor-specific angular datum to obtain a toe-inclusive wheel heading. Rack-center heading is subtracted only when an incremental steering curve is required.

The exact reconstruction is documented in `migration/legacy_calculators/steering_tie_rod_optimizer/steer_ratio_fit_reconstruction.md`.

### `SRCH-STEER-0005` — WUFR-26 design specification

The current design specification was located and catalogued as `CAT-STEER-SPEC-0001`:

| Field | Value |
|---|---|
| File | `2026_FSAE_Design_IC_Spec_Sheet_WashU_Racing.xlsx` |
| Box file ID | `2149814001036` |
| Box file version ID | `2510738677599` |
| Box SHA-1 | `588669d320ff8097ec0bc85a85a970640d5a4d38` |
| Size | `45432` bytes |
| Path | `WashURacing/6. WUFR-26/Spec Sheet/` |
| Modified | `2026-06-06T04:43:43Z` |

The source explicitly defines:

- wheelbase `1562 mm`;
- front track `1232 mm`, defined as tread-center to tread-center;
- front sum toe `-1.00 deg`, with positive toe-in and negative toe-out;
- through-center steering ratio `3.12:1`, handwheel angle divided by average left/right road-wheel angle;
- C-factor `88.9 mm/rev`, defined as effective rack travel per revolution of the steering input/pinion shaft;
- steering-arm length `69.9 mm`, defined as kingpin-axis to outer tie-rod-center distance;
- static Ackermann `67.7 percent`, with the percentage definition still unresolved.

This recovers the WUFR-26 **C-factor definition** and creates a candidate canonical conversion of `0.014148874440869498 m/rad`. The observation remains inactive until reconciled with rack/pinion CAD, drawing, or measurement.

The design sheet is evidence of reported design intent. It is not independent measurement or physical validation.

## Final WUFR-26 authority hierarchy

1. **Design-selection authority:** WUFR-26 steering FDR final-geometry table.
2. **Selected configuration:** `Test 3`.
3. **Relative rack-placement intent:** 0.5 in rearward from the previous-year placement.
4. **Mechanism source:** `GEOMETRY FINAL.SLDPRT`, Box ID `1971276311204`.
5. **Primary final-motion response:** `2026Ackermann.csv`, Box ID `2357045252883`.
6. **Selection-era cross-check:** `Test_3.csv`, Box ID `1938821987892`.
7. **Design-intent reference:** `Steering Length Optimization Tests.xlsx`, Test 3 column.
8. **Current reported parameter source:** `CAT-STEER-SPEC-0001`.

The detailed geometry-selection mapping is `data_catalog/wufr26_test3_selected_lineage.md`. The parameter seed is `data_catalog/steering_parameter_observation_seed.md`.

## Reconstructed calculator logic

The WUFR-25 exports retain both raw and converted output rows:

```text
WUFR_25.csv:
wheel_output = Dimension2 - 32.9 deg

3.5INREV_WUFR25.csv:
wheel_output = Dimension2 - 33.0 deg
```

The resulting zero-input value is approximately `-1 deg`; the transformed quantity is toe-inclusive wheel heading, not an incremental angle forced through zero. Where a SolidWorks monitor crosses its own angular branch, the raw values must first be oriented into one continuous angle.

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
| `CAT-STEER-SPEC-0001` | WUFR-26 design specification | Source located; observations seeded | Reconcile values and create reviewed active selections only where justified |

## Benchmark-freeze requirements

1. Catalog the exact FDR file, version, table location, and SHA-256.
2. Compute SHA-256 for `GEOMETRY FINAL.SLDPRT`, `2026Ackermann.csv`, `Test_3.csv`, the reference workbook, and the design specification.
3. Record SolidWorks version, active configuration, dependencies, equations, study settings, and warnings.
4. Map `Steer Input`, `Dimension2`, `Steer_Angle`, and `Measurement1` to canonical quantities.
5. Confirm angular-branch orientation, monitor datum, rack-center heading, and static-toe treatment.
6. Declare physical steering limits; do not assume every exported scenario is operational.
7. Compare transformed raw points before comparing polynomial fits.
8. Retain the non-selected candidate CSVs as separate regression cases.
9. Reconcile design-spec C-factor and center ratio against the current mechanism/transmission.
10. Obtain independent physical or analytical evidence for validation beyond CAD reproduction.

## Decision rules

- The FDR selects the configuration but does not validate its curve.
- `0.5 inch back` is relative design intent, not an absolute coordinate.
- `2026Ackermann.csv` is the primary final-motion export; `Test_3.csv` remains a cross-check.
- A polynomial fitted to an export cannot independently validate that export.
- The design specification is a candidate-observation source, not an automatic active-value source.
- Front tread-center track is not steering-axis ground-intersection track.
- Axle sum toe does not define the left/right split.
- Provider SHA-1 supports discovery; project SHA-256 is required for freeze.