# WUFR-26 Coordinate-Frame Reconciliation

**Status:** Reviewed and frozen for the nominal WUFR-26 design-source configuration; installed-state validation remains open  
**Related source:** `CAT-STEER-GEO-0001`

## Purpose

This document reconciles the final WUFR-26 OptimumK suspension export, the raw SolidWorks steering-study coordinates, the steering FDR pickup table, and the later team-supplied CAD observations. Standard and software names do not replace an explicit basis, handedness, origin, unit, and transform.

## Sources

| Artifact | Box ID | Version ID | Provider SHA-1 | Role |
|---|---:|---:|---|---|
| `WUFR-26 FINAL 8.21.2025.xlsx` | `2014803790843` | `2224178574043` | `15eadfb93369192038888da92ebaa6674db56cfa` | Final suspension hardpoints and setup values used for the nominal geometry |
| `Steering Length Optimization Tests.xlsx` | `1939770957296` | `2140326128861` | `2069922fc3dac8889d84a92275e35486caef3284` | Test 3 raw steering-study coordinates and design intent |
| Steering FDR final table | pending exact file metadata | pending | pending | Selected final front-left tie-rod pickup coordinates and projected endpoint turn-angle observations |
| Team CAD observations dated 2026-07-21 | project conversation | n/a | n/a | Rack-center coordinate, exact left/right design reflection, setup-sheet authority, rack-point motion rule, and screenshots of geometry/column sketches |

The OptimumK workbook records the user coordinate matrix `[[1,0,0],[0,-1,0],[0,0,1]]`. Its exported table uses positive lateral coordinates for the right side and negative values for the left side.

## Frames and transforms

### `OPTK_WUFR26_EXPORT`

Observed order is longitudinal, lateral-positive-right, vertical-positive-up, in millimetres.

### `SW_WUFR26_STEERING_STUDY_RAW`

The raw Test 3 triplets are in inches with observed order lateral-positive-left, vertical-positive-up, longitudinal-positive-forward. The recovered mapping to the OptimumK export is:

```text
[x_optk, y_optk, z_optk] = 25.4 * [z_sw, -x_sw, y_sw]
```

### `SW_WUFR26_FDR_VEHICLE_MM`

The steering FDR table is a SolidWorks vehicle-order export in millimetres: longitudinal, lateral-positive-left, vertical-positive-up. The team confirmed that the listed pair is the front-left corner when viewed from behind the vehicle facing the nose.

```text
[x_optk, y_optk, z_optk] = [x_fdr, -y_fdr, z_fdr]
```

### `CANONICAL_ISO8855_BODY`

The project calculation frame is right-handed: `+x` forward, `+y` vehicle left, `+z` upward. The source adapters are:

```text
[x_can, y_can, z_can] = 0.001 * [x_optk, -y_optk, z_optk]
[x_can, y_can, z_can] = 0.0254 * [z_sw, x_sw, y_sw]
[x_can, y_can, z_can] = 0.001 * [x_fdr, y_fdr, z_fdr]
```

No translation was required for the recovered comparison points. This does not imply that every SolidWorks model shares the same origin.

## Direct rack-center confirmation

The team supplied the centered CAD rack coordinate in the steering-study axis order:

```text
SolidWorks native [lateral, vertical, longitudinal] = [0.000, 162.865, -79.298] mm
```

Applying the frozen adapter gives:

```text
canonical [forward, left, up] = [-0.079298, 0.000000, 0.162865] m
```

This exactly matches the rack-axis origin already used by `WUFR26_DESIGN_NOMINAL_V0`. The observation therefore confirms the axis permutation, signs, and center location for the nominal design-source geometry.

## Transform check

Test 3 front-left inner point:

```text
raw study:              [8.70, 6.28, -2.62] in
mapped to OptimumK:     [-66.548, -220.980, 159.512] mm
OptimumK final left:    [-66.598, -220.980, 159.562] mm
OptimumK minus mapped:  [-0.050, 0.000, +0.050] mm
```

The residual is consistent with worksheet rounding.

Test 3 front-left outer point:

```text
raw study:              [21.63, 7.57, -2.39] in
mapped to OptimumK:     [-60.706, -549.402, 192.278] mm
OptimumK final left:    [-58.767, -549.504, 193.427] mm
OptimumK minus mapped:  [+1.939, -0.102, +1.149] mm
```

The same axis mapping is supported, but the outer pickup was revised after the Test 3 worksheet values were recorded.

## Final source merge

Front-left OptimumK final values, in the OptimumK export frame:

| Object | x (mm) | y (mm) | z (mm) |
|---|---:|---:|---:|
| Lower upright point | 0.000 | -587.096 | 157.117 |
| Upper upright point | -6.487 | -564.662 | 305.056 |
| Tie-rod inner point | -66.598 | -220.980 | 159.562 |
| Tie-rod outer point | -58.767 | -549.504 | 193.427 |

The steering FDR final table reports front-left SolidWorks vehicle-order coordinates:

```text
Tie Rod Inner = [-79.298, 220.980, 162.865] mm
Tie Rod Outer = [-61.933, 549.102, 192.223] mm
```

Converted to the OptimumK export frame, these are:

```text
Tie Rod Inner = [-79.298, -220.980, 162.865] mm
Tie Rod Outer = [-61.933, -549.102, 192.223] mm
```

The FDR joint-center distance is `329.890 mm`, or `12.9878 in`, consistent with the selected nominal 13-in tie rod.

FDR minus OptimumK tie-rod points, after both are expressed in the OptimumK frame:

```text
inner = [-12.700, 0.000, +3.303] mm
outer = [ -3.166, +0.402, -1.204] mm
```

The inner longitudinal difference is exactly 0.500 in rearward. It is a steering-specific geometry revision, not merely a coordinate-frame difference.

## Nominal reference state and setup-sheet authority

The OptimumK geometry was exported at its listed nonzero static-toe and static-camber settings. The workbook displays `Static Toe = -1.000 deg` and `Static Camber = -2.250 deg` for both front-side fields. The team confirms that the SolidWorks steering setup is based on this setup sheet.

For the rigid evaluator:

- zero solved upright rotation means the imported nominal static-alignment mechanism state;
- the closure solver's primary angular output is rotation of the upright about its steering axis;
- projected road-wheel heading is obtained from the reviewed wheel-plane basis and road-plane intersection;
- incremental road-wheel heading is reported relative to each side's centered projected heading;
- total toe-inclusive heading retains the canonical setup-sheet static datum;
- static toe and camber must not be subtracted from hardpoint geometry as though the points were recorded at zero alignment.

## Left/right reflection authority

The team confirms that the nominal design CAD left-side hardpoints are a perfect reflection of the right-side hardpoints. For the design-source model, changing the sign of canonical `y` is therefore an authoritative CAD construction rule rather than an unverified nominal assumption.

This does **not** establish as-built symmetry. Welding, fixturing, setup, rod-end adjustment, rack centering, and compliance can break the CAD reflection. Physical or metrology evidence is still required for installed-state claims.

## Rack-point motion rule

The modeled rack points are the inboard tie-rod pickup points at the centered state. They translate rigidly along the rack axis by up to `1.00 in` to either side in the nominal design study. This is the correct rigid mechanism representation even though the old fitment trackers are no longer reliable.

The `+/-1.00 in` value remains a design-study motion bound, not proof of the installed hardware stop positions or operational margin.

## Authority rule

For the WUFR-26 nominal steering design configuration:

1. use `WUFR-26 FINAL 8.21.2025.xlsx` for upper and lower upright points, steering-axis construction, static toe, and static camber;
2. use the steering FDR final table for the selected front-left tie-rod inner and outer pickups;
3. reflect canonical `y` exactly for the nominal right-side CAD geometry;
4. use Test 3 as transform and design-intent evidence;
5. use `GEOMETRY FINAL.SLDPRT`, the Test 3 fit, and the FDR projected endpoint values for nominal response comparison;
6. use active assembly metrology or physical measurement for installed-state validation.

The generic OptimumK tie-rod points must not overwrite the later FDR steering points. The FDR tie-rod table does not replace the OptimumK upright points.

## Canonical nominal front-left configuration

| Object | x (m) | y (m) | z (m) | Source |
|---|---:|---:|---:|---|
| Lower steering-axis point | 0.000000 | 0.587096 | 0.157117 | OptimumK final |
| Upper steering-axis point | -0.006487 | 0.564662 | 0.305056 | OptimumK final |
| Rack inner joint | -0.079298 | 0.220980 | 0.162865 | Steering FDR and direct CAD center confirmation |
| Upright outer joint | -0.061933 | 0.549102 | 0.192223 | Steering FDR |

The mirrored inner joints imply rack-center point `[-0.079298, 0, 0.162865] m`, rack direction `[0,+1,0]`, and inner-joint spacing `0.441960 m`.

## Reported uncertainty and remaining gates

The team reports a CAD angular export tolerance of `+/-0.1 deg`. The reported length tolerance was phrased as `+/-0.005 thou`; its intended unit must be clarified before conversion or use as an acceptance band. The team expects 2026 welding-induced hardpoint error to be no larger than the CAD tolerance, but no as-built measurement currently supports that estimate.

The nominal design-source frame, symmetry rule, rack center, static alignment, and Level E comparison are now frozen. Remaining installed-state gates are:

- exact installed rack-center and left/right stop measurement;
- installed steering-wheel/pinion/rack transmission measurement;
- physical left/right hardpoint or wheel-angle measurement;
- backlash, compliance, hysteresis, and repeatability characterization;
- interpretation of the visible `->?` external-reference indicators in the supplied feature-tree screenshot;
- confirmation of the intended CAD length-tolerance unit;
- Level F acceptance criteria based on independent measurement uncertainty.

The project retains one ISO 8855-style right-handed simulation frame. CAD may use an ISO 4130-oriented vehicle reference, but every CAD model still requires a source-specific adapter; a standard label cannot authorize an unverified axis permutation, sign change, or origin shift.
