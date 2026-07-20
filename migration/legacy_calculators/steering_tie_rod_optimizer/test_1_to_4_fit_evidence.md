# WUFR-26 Test 1–4 Fit Evidence

**Status:** Historical Desmos expressions captured from team-provided screenshots; source tables and signal identities still require benchmark freeze  
**Related IDs:** `MIG-STR-0001`, `MIG-SC26-SR-001`, `BENCH-STEER-0001`, `MOD-STEER-0001`

## Purpose

This note separates the SolidWorks angular monitor, the processed signed wheel-output row, and the later polynomial representation used to compare WUFR-26 steering candidates. The Desmos graph at `https://www.desmos.com/calculator/ehsquoulhs` is historical design-process evidence. Team-provided screenshots captured the displayed expressions and comparison graph on 2026-07-19.

The equations are useful for reproducing the historical comparison. They do not supersede immutable SolidWorks tables as mechanism-response evidence and do not provide independent physical validation.

## Candidate context

The reference workbook records the following candidate summaries in its native definitions:

| Candidate | Rack offset | Rack displacement | Tie-rod length | Steering-arm length | Right turn | Left turn | Input |
|---|---:|---:|---:|---:|---:|---:|---:|
| Test 1 | 3.62 | 1.25 | 13.5 | 2.85 | 25.5 | 32.75 | 112.5 |
| Test 2 | 3.62 | 1.275 | 13.5 | 2.95 | 25.12 | 31.52 | 115 |
| Test 3 | 2.62 | 1 | 13 | 2.70 | 22.43 | 32.08 | 102 |
| Test 4 | 2.62 | 1.2 | 13.5 | 2.7 | 25.85 | 31.73 | 108 |

Units, coordinate frame, endpoints, and output identities remain legacy definitions until separately frozen.

## Captured Desmos equations

The screenshot labels each directly fitted branch as `Left` and constructs the opposite branch by reflection:

```text
W_Right(x) = -W_Left(-x)
```

This enforces left-right mirror symmetry. It is not an independently fitted second-wheel response. For a geometrically symmetric car it can generate both road-wheel branches from one side, but any real left-right asymmetry is excluded by construction.

### Test 1

```text
W_TEST1Left(x) =
    -1.0e-8 x^4
    +2.0e-6 x^3
    -3.0e-4 x^2
    +0.2450 x
    -1.2479

W_TEST1Right(x) = -W_TEST1Left(-x)
```

The graph also contains `W_TEST1Left(110.3*x)`. This appears to be an endpoint or normalized-input evaluation helper, not the regression definition itself. The value `110.3 deg` conflicts with the workbook summary input `112.5 deg` and must remain an explicit open discrepancy.

### Test 2

```text
W_TEST2Left(x) =
    -7.0e-9 x^4
    +1.0e-6 x^3
    -2.0e-4 x^2
    +0.2344 x
    -0.9946

W_TEST2Right(x) = -W_TEST2Left(-x)
```

The graph evaluates `W_TEST2Left(115*x)`.

### Test 3

```text
W_TEST3Left(x) =
    -2.0e-8 x^4
    +3.0e-6 x^3
    -2.0e-4 x^2
    +0.2427 x
    -1.1394

W_TEST3Right(x) = -W_TEST3Left(-x)
```

The graph evaluates `W_TEST3Left(102*x)`.

### Test 4

```text
W_TEST4Left(x) =
    -6.0e-9 x^4
    +1.0e-6 x^3
    -2.0e-4 x^2
    +0.2348 x
    -0.9889

W_TEST4Right(x) = -W_TEST4Left(-x)
```

No separate normalized-input helper for Test 4 was visible in the supplied screenshots.

### Previous-year comparison

```text
W_lastyear(x) =
    -2.0e-8 x^4
    +3.0e-6 x^3
    -3.0e-4 x^2
    +0.2796 x
    -1.0131
```

The graph evaluates `W_lastyear(90*x)` and displays its derivative. A graph note states that the previous-year Ackermann result was constrained by retaining the upright, so the limit angles are not directly comparable. Another note assigns approximately plus or minus 1 degree error to the motion-study process.

## Important toe interpretation

All captured left-branch fits have a center intercept near `-1 deg`, while the mirrored right branch has the opposite center value:

```text
W_Left(0)  approximately -1 deg
W_Right(0) approximately +1 deg
```

This is strong evidence that the historical curves describe **toe-inclusive wheel heading**, not incremental steer angle forced to zero at rack center. It is consistent with recovered WUFR-25 and WUFR-26 candidate exports whose processed wheel-output rows retain approximately `-1 deg` at zero steering input.

The canonical replacement must therefore distinguish:

```text
total road-wheel heading = static toe + incremental steering displacement
incremental steering displacement = total heading - rack-center heading
```

Differentiation removes the constant toe offset, so local steering gain is unaffected. Ackermann, inside/outside wheel maps, setup reporting, and CAD comparisons are not unaffected and must state whether they use toe-inclusive or incremental angles.

## Recovered raw transformations

### Test 1

- Source: `Test_1.csv`
- Driver row: `STEERING INPUT`
- Driver domain in export: `-115 deg` through `+115 deg`
- Raw monitor: `Dimension1`
- Processed row: `WHEEL OUTPUT`

Within exported rounding:

```text
wheel_output_deg = Dimension1_deg - 91.46 deg
```

The monitor-specific reference is not a universal steering zero.

### Test 2

- Source: `Test_2.csv`
- Driver row: `STEERING INPUT`
- Driver domain in export: `-115 deg` through `+115 deg`
- Raw monitor: `Dimension2`
- Processed row: `Wheel Output`

Within exported rounding:

```text
wheel_output_deg = Dimension2_deg - 32.75 deg
```

The file also contains design notes comparing approximately `0.2792` with `0.2344` and describing about 16 percent steering-effort reduction. The Desmos previous-year center slope is `0.2796`, not `0.2792`; both values remain historical observations until their source precision is resolved.

### Test 3

- Source: `Test_3.csv`
- Driver row: `Steer_Angle`
- Raw monitor: `Measurement1`
- Populated input visible in the export: approximately `-102 deg` through `+115 deg`

`Measurement1` is already signed in the export and no separate processed `WHEEL OUTPUT` row is present. The historical fit likely used `Measurement1` directly, but the SolidWorks monitor identity still requires review.

### Test 4

- Source: `Test_4.csv`
- Driver row: `Steering Input`
- Driver domain in export: `-108 deg` through `+108 deg`
- Raw monitor: `Dimension4`
- Processed row: `WHEEL OUTPUT`

Within exported rounding:

```text
wheel_output_deg = Dimension4_deg - 32.75 deg
```

The Test 4 monitor and output sequences reproduce Test 2 over their shared domain. One processed point near input `-5 deg` appears inconsistent with direct subtraction and must not be silently repaired or omitted.

## Derivatives and center gains

The displayed derivative expressions correspond to local road-wheel gain with respect to the Desmos input.

```text
g_TEST1(x) = -4.0e-8 x^3 + 6.0e-6 x^2 - 6.0e-4 x + 0.2450
g_TEST2(x) = -2.8e-8 x^3 + 3.0e-6 x^2 - 4.0e-4 x + 0.2344
g_TEST3(x) = -8.0e-8 x^3 + 9.0e-6 x^2 - 4.0e-4 x + 0.2427
g_TEST4(x) = -2.4e-8 x^3 + 3.0e-6 x^2 - 4.0e-4 x + 0.2348
g_lastyear(x) = -8.0e-8 x^3 + 9.0e-6 x^2 - 6.0e-4 x + 0.2796
```

At the graph origin:

| Curve | Center road-wheel gain | Reciprocal, only if input is steering-wheel angle |
|---|---:|---:|
| Test 1 | 0.2450 | 4.0816 |
| Test 2 | 0.2344 | 4.2662 |
| Test 3 | 0.2427 | 4.1203 |
| Test 4 | 0.2348 | 4.2589 |
| Previous year | 0.2796 | 3.5765 |

The Test 2 center gain is about 16.2 percent lower than the displayed previous-year center gain. That explains the historical approximate 16 percent effort statement only under the simplified assumption that steering effort scales with the inverse kinematic leverage and that other force, friction, trail, compliance, and efficiency terms are unchanged.

## Endpoint and source-consistency observations

The displayed coefficients are rounded and should not be expected to reproduce raw tables exactly. Tests 2–4 are broadly consistent with their recovered exports within the stated motion-study error and coefficient precision. Test 1 is not:

- the Test 1 polynomial differs materially from the recovered `Test_1.csv` wheel-output endpoints;
- its Desmos helper uses `110.3 deg`, while the workbook lists `112.5 deg`;
- therefore the Test 1 equation may come from another export, another wheel, another study revision, or a manually adjusted dataset.

Test 1 must remain unfrozen until its exact source table is identified. It is not acceptable to force the recovered CSV to agree with the equation.

## Reconstructed historical pipeline

```text
SolidWorks design-study driver
  -> raw angular monitor
  -> angular branch unwrapping where required
  -> monitor-specific datum subtraction
  -> toe-inclusive signed left-wheel heading
  -> quartic polynomial representation
  -> mirrored right-wheel branch, W_Right(x) = -W_Left(-x)
  -> derivative for local road-wheel gain
  -> reciprocal only when the driver is confirmed as steering-wheel angle
```

The polynomial was not constrained through zero. The nonzero center intercept appears intentional because static toe is retained.

## Graph interpretation

The supplied comparison graph includes:

- vertical comparison lines at `x = -115` and `x = +115`;
- horizontal bands `24 < y < 25` and `-33 < y < -32`;
- multiple candidate curves on common steering-input and wheel-output axes;
- a note that motion-study results may carry approximately plus or minus 1 degree error.

Those bands are comparison aids, not model-validity bounds or optimizer constraints until their design intent is recovered.

## Evidence hierarchy

1. Immutable SolidWorks response table for the sampled legacy response.
2. Documented transformation from monitor angle to toe-inclusive signed wheel heading.
3. Historical Desmos regression for process reproduction.
4. Independent refit for audit comparison.
5. Physical steering sweep for stronger validation.

The Desmos fit can be historically authoritative without being mechanically or physically authoritative.

## Required closure

Before these fits are frozen:

- identify the exact source table for each Desmos polynomial, especially Test 1;
- confirm whether the fitted `Left` quantity is the physical left wheel, one turn branch, or a relabeled inside/outside curve;
- confirm the Desmos input identity and upstream column/rack transmission;
- preserve the screenshots or calculator state in a controlled evidence location with hashes;
- resolve the `110.3 deg` versus `112.5 deg` Test 1 discrepancy;
- resolve `0.2792` versus `0.2796` for the previous-year center gain;
- document static toe and whether each output is total wheel heading or incremental steer;
- verify the Test 4 anomalous point;
- compute residuals against immutable CSV bytes using the displayed coefficient precision;
- prohibit extrapolation outside the reviewed mechanism and steering-stop domain.
