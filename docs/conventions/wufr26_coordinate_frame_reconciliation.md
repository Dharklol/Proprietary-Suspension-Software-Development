# WUFR-26 Coordinate-Frame Reconciliation

**Status:** Proposed, review ready  
**Related source:** `CAT-STEER-GEO-0001`

## Purpose

This document reconciles the final WUFR-26 OptimumK suspension export, the raw SolidWorks steering-study coordinates, and the steering FDR pickup table. Standard and software names do not replace an explicit basis, handedness, origin, unit, and transform.

## Sources

| Artifact | Box ID | Version ID | Provider SHA-1 | Role |
|---|---:|---:|---|---|
| `WUFR-26 FINAL 8.21.2025.xlsx` | `2014803790843` | `2224178574043` | `15eadfb93369192038888da92ebaa6674db56cfa` | Final suspension hardpoints used for `SU-00001-AA 2026 SUSPENSION GEOMETRY.SLDPRT` |
| `Steering Length Optimization Tests.xlsx` | `1939770957296` | `2140326128861` | `2069922fc3dac8889d84a92275e35486caef3284` | Test 3 raw steering-study coordinates and design intent |
| Steering FDR final table | pending exact file metadata | pending | pending | Selected final tie-rod pickup coordinates |

The OptimumK workbook records the user coordinate matrix `[[1,0,0],[0,-1,0],[0,0,1]]`. Its exported table uses positive lateral coordinates for the right side and negative values for the left side.

## Frames and transforms

### `OPTK_WUFR26_EXPORT`

Observed order is longitudinal, lateral-positive-right, vertical-positive-up, in millimetres.

### `SW_WUFR26_STEERING_STUDY_RAW`

The raw steering-study triplets are in inches. The recovered mapping to the OptimumK export is:

```text
[x_optk, y_optk, z_optk] = 25.4 * [z_sw, x_sw, y_sw]
```

### `CANONICAL_ISO8855_BODY`

The project calculation frame is right-handed: `+x` forward, `+y` vehicle left, `+z` upward. The source adapters are:

```text
[x_can, y_can, z_can] = 0.001 * [x_optk, -y_optk, z_optk]
[x_can, y_can, z_can] = 0.0254 * [z_sw, -x_sw, y_sw]
```

No translation was required for the recovered comparison points. This does not imply that every SolidWorks model shares the same origin.

## Transform check

Test 3 inner point:

```text
raw study:       [8.70, 6.28, -2.62] in
mapped:          [-66.548, 220.980, 159.512] mm
OptimumK final:  [-66.598, 220.980, 159.562] mm
residual:        [-0.050, 0.000, +0.050] mm
```

The residual is consistent with worksheet rounding.

Test 3 outer point:

```text
raw study:       [21.63, 7.57, -2.39] in
mapped:          [-60.706, 549.402, 192.278] mm
OptimumK final:  [-58.767, 549.504, 193.427] mm
residual:        [+1.939, +0.102, +1.149] mm
```

The same axis mapping is supported, but the outer pickup was revised after the Test 3 worksheet values were recorded.

## Final source merge

Right-side OptimumK final values, in the OptimumK export frame:

| Object | x (mm) | y (mm) | z (mm) |
|---|---:|---:|---:|
| Lower upright point | 0.000 | 587.096 | 157.117 |
| Upper upright point | -6.487 | 564.662 | 305.056 |
| Tie-rod inner point | -66.598 | 220.980 | 159.562 |
| Tie-rod outer point | -58.767 | 549.504 | 193.427 |

The steering FDR final table reports:

```text
Tie Rod Inner = [-79.298, 220.980, 162.865] mm
Tie Rod Outer = [-61.933, 549.102, 192.223] mm
```

The FDR joint-center distance is `329.890 mm`, or `12.9878 in`, consistent with the selected nominal 13-in tie rod.

FDR minus OptimumK tie-rod points:

```text
inner = [-12.700, 0.000, +3.303] mm
outer = [ -3.166, -0.402, -1.204] mm
```

The inner longitudinal difference is exactly 0.500 in rearward. It is a steering-specific geometry revision, not merely a coordinate-frame difference.

## Authority rule

For the WUFR-26 nominal steering design configuration:

1. use `WUFR-26 FINAL 8.21.2025.xlsx` for upper and lower upright points and the steering-axis construction;
2. use the steering FDR final table for the selected tie-rod inner and outer pickups;
3. use Test 3 as transform and design-intent evidence;
4. use `GEOMETRY FINAL.SLDPRT` and `2026Ackermann.csv` for response reproduction;
5. use active assembly export or physical measurement for installed-state validation.

The generic OptimumK tie-rod points must not overwrite the later FDR steering points. The FDR tie-rod table does not replace the OptimumK upright points.

## Canonical nominal right-side candidate

| Object | x (m) | y (m) | z (m) | Source |
|---|---:|---:|---:|---|
| Lower steering-axis point | 0.000000 | -0.587096 | 0.157117 | OptimumK final |
| Upper steering-axis point | -0.006487 | -0.564662 | 0.305056 | OptimumK final |
| Rack inner joint | -0.079298 | -0.220980 | 0.162865 | Steering FDR |
| Upright outer joint | -0.061933 | -0.549102 | 0.192223 | Steering FDR |

A symmetric left side may be derived by changing the sign of `y`, but it remains an explicit nominal-symmetry assumption until checked independently.

The mirrored inner joints imply a rack-center point `[-0.079298, 0, 0.162865] m`, rack direction `[0,+1,0]`, and inner-joint spacing `0.441960 m`.

## Remaining gates

This is enough for an explicitly labeled nominal-design incremental steering evaluator. It does not establish installed hardpoints, static-toe split and wheel-plane basis, shim stack and ride height, actual stop states, pinion-to-rack transmission, tolerances, compliance, or active assembly warning state.

The project should retain one ISO 8855-style right-handed simulation frame. CAD may use an ISO 4130-oriented vehicle reference, but every CAD model still requires a source-specific adapter; a standard label cannot authorize an unverified axis permutation, sign change, or origin shift.