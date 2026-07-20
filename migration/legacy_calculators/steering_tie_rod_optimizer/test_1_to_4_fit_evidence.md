# WUFR-26 Test 1–4 Fit Evidence

**Status:** Raw-to-wheel-output transformation recovered; Desmos regression expressions pending direct capture  
**Related IDs:** `MIG-STR-0001`, `MIG-SC26-SR-001`, `BENCH-STEER-0001`, `MOD-STEER-0001`

## Purpose

This note separates the SolidWorks angular monitor, the processed signed wheel-output row, and the later polynomial regression for WUFR-26 steering candidate Tests 1–4. The Desmos graph at `https://www.desmos.com/calculator/ehsquoulhs` is team-provided historical fit evidence, but its expression state has not yet been captured into the controlled repository.

The Desmos equations can establish the historical polynomial order, coefficients, restrictions, and excluded points. They do not supersede the raw SolidWorks tables as mechanism-response evidence and do not provide independent physical validation.

## Candidate context

The reference workbook records the following candidate summaries in its native definitions:

| Candidate | Rack offset | Rack displacement | Tie-rod length | Steering-arm length | Right turn | Left turn | Input |
|---|---:|---:|---:|---:|---:|---:|---:|
| Test 1 | 3.62 | 1.25 | 13.5 | 2.85 | 25.5 | 32.75 | 112.5 |
| Test 2 | 3.62 | 1.275 | 13.5 | 2.95 | 25.12 | 31.52 | 115 |
| Test 3 | 2.62 | 1 | 13 | 2.70 | 22.43 | 32.08 | 102 |
| Test 4 | 2.62 | 1.2 | 13.5 | 2.7 | 25.85 | 31.73 | 108 |

Units, coordinate frame, endpoints, and output identities remain legacy definitions until separately frozen.

## Recovered transformations

### Test 1

- Source: `Test_1.csv`
- Driver row: `STEERING INPUT`
- Driver domain in export: `-115 deg` through `+115 deg`
- Raw monitor: `Dimension1`
- Processed row: `WHEEL OUTPUT`

Within the exported rounding:

```text
wheel_output_deg = Dimension1_deg - 91.46 deg
```

Checks:

| Input | Dimension1 | WHEEL OUTPUT | Reconstructed |
|---:|---:|---:|---:|
| -115 | 58.02 | -33.44 | 58.02 - 91.46 = -33.44 |
| +115 | 111.72 | 20.26 | 111.72 - 91.46 = 20.26 |

The large reference angle reflects this monitor's angular definition. It is not a universal steering offset and must not be transferred to another SolidWorks measurement.

### Test 2

- Source: `Test_2.csv`
- Driver row: `STEERING INPUT`
- Driver domain in export: `-115 deg` through `+115 deg`
- Raw monitor: `Dimension2`
- Processed row: `Wheel Output`

Within the exported rounding:

```text
wheel_output_deg = Dimension2_deg - 32.75 deg
```

The file also contains historical design notes comparing approximately `0.2792` with `0.2344`, describing a roughly 16 percent effort reduction and an input increase to 115 degrees. Those notes are design-intent evidence; their exact ratio and force definitions remain unresolved.

### Test 3

- Source: `Test_3.csv`
- Driver row: `Steer_Angle`
- Raw monitor: `Measurement1`
- Valid populated input visible in the export: approximately `-102 deg` through `+115 deg`

`Measurement1` is already signed in the export and no separate processed `WHEEL OUTPUT` row is present. The likely historical fit input is therefore `Measurement1` directly, but this remains an inference until the Desmos expressions and SolidWorks monitor identity are captured.

At exported input `+102 deg`, `Measurement1` is approximately `22.24 deg`, which is close to the workbook's Test 3 right-turn summary of `22.43 deg`. This is a consistency check, not proof of wheel identity or fit procedure.

### Test 4

- Source: `Test_4.csv`
- Driver row: `Steering Input`
- Driver domain in export: `-108 deg` through `+108 deg`
- Raw monitor: `Dimension4`
- Processed row: `WHEEL OUTPUT`

Within the exported rounding:

```text
wheel_output_deg = Dimension4_deg - 32.75 deg
```

The Test 4 monitor and output sequences reproduce the Test 2 sequence over the shared domain, indicating that Test 4 is a restricted or re-exported response based on the same angular measurement convention rather than an independent processing method.

One processed Test 4 point near input `-5 deg` appears inconsistent with direct subtraction: the row reports approximately `-1.44 deg` where the surrounding raw monitor sequence implies approximately `-1.22 deg`. This point must be checked against immutable CSV bytes and the Desmos table before any regression is frozen. It must not be silently repaired or omitted.

## Reconstructed historical pipeline

The evidence supports the following candidate-specific process:

```text
SolidWorks design-study driver
  -> raw angular monitor
  -> angular branch unwrapping where required by that monitor
  -> subtraction of that monitor's reviewed straight-ahead reference
  -> signed wheel-output table
  -> polynomial regression in Desmos or Excel
  -> derivative or finite difference for local road-wheel gain
  -> reciprocal only when the driver is confirmed as steering-wheel angle
```

The phrase previously described as “making angles negative” is therefore not one universal sign operation. Tests 1, 2, and 4 explicitly create signed wheel output by subtracting monitor-specific reference angles. Test 3 appears already signed. Other exports, including the final `2026Ackermann.csv`, may additionally require angular-branch unwrapping before reference subtraction.

## Role of the Desmos equations

The Test 1–4 regressions are potentially more authoritative than a newly generated fit for reproducing the historical design process because they can reveal:

1. polynomial degree and coefficient precision;
2. which processed row was regressed;
3. whether the fit was constrained through zero;
4. domain restrictions and operational-lock limits;
5. excluded points or manually edited table values;
6. whether separate left/right or inside/outside branches were fitted;
7. whether a derivative or a separate regression generated the displayed ratio curve.

They are not automatically more physically correct. The evidence hierarchy is:

1. immutable SolidWorks response table for legacy response;
2. documented transformation from monitor to signed road-wheel quantity;
3. historical Desmos regression for process reproduction;
4. independent refit for audit comparison;
5. physical sweep for stronger validation.

## Required capture

Before the historical fits are frozen, record:

- the four Desmos regression expressions exactly as entered;
- all table columns and variable names used by each regression;
- graph title, owner/revision where available, and capture date;
- polynomial order, coefficient precision, and restrictions;
- residual metrics against both the displayed Desmos table and immutable Box CSV;
- treatment of the Test 4 anomalous point;
- whether Test 3 uses `Measurement1` directly or another transformed list;
- whether the fits describe one road wheel, the inside wheel, the outside wheel, or an aggregate curve.

A screenshot is useful review evidence, but a text or JSON capture of the expressions and tables is required for a reproducible benchmark.