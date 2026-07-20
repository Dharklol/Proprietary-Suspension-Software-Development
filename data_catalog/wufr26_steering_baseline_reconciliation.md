# WUFR-26 Steering Baseline Reconciliation

**Status:** Nominal design geometry recovered; installed-state correlation remains open  
**Vehicle:** WUFR-26  
**Related IDs:** `MOD-STEER-0001`, `BENCH-STEER-0001`, `CAT-STEER-SPEC-0001`, `CAT-STEER-GEO-0001`, `PAR-STEER-0001` through `PAR-STEER-0003`, `RISK-STEER-0001`

## Purpose

This packet records the intended WUFR-26 steering reference model, recovered nominal geometry, current setup evidence, prohibited values, source authority, and the remaining installed-state export requirements. It does not activate an as-built configuration or authorize unbounded physics implementation.

## Baseline model intent

The eventual active WUFR-26 model represents the real/as-built or competition-intended steering assembly at a declared setup.

`GEOMETRY FINAL.SLDPRT` is instantiated inside the fuller linkage subassembly. It remains the selected Test 3 mechanism-study source and parent of the final motion response. The final OptimumK suspension workbook supplies the nominal upright geometry, while the steering FDR final table supplies the later steering-specific front-left tie-rod pickups.

The design-source configuration and installed-state configuration are connected evidence layers. Agreement must be checked rather than assumed.

## Primary specification source

| Field | Value |
|---|---|
| File | `2026_FSAE_Design_IC_Spec_Sheet_WashU_Racing.xlsx` |
| Box file ID | `2149814001036` |
| Box file version ID | `2510738677599` |
| Provider SHA-1 | `588669d320ff8097ec0bc85a85a970640d5a4d38` |
| Modified | `2026-06-06T04:43:43Z` |
| Size | `45432` bytes |
| Evidence role | Reported design/setup intent; not automatic as-built authority |

Project SHA-256 remains pending immutable-byte capture.

## Final suspension geometry source

| Field | Value |
|---|---|
| File | `WUFR-26 FINAL 8.21.2025.xlsx` |
| Box file ID | `2014803790843` |
| Box file-version ID | `2224178574043` |
| Provider SHA-1 | `15eadfb93369192038888da92ebaa6674db56cfa` |
| Modified | `2025-10-13T16:51:15Z` |
| Related CAD | `SU-00001-AA 2026 SUSPENSION GEOMETRY.SLDPRT` |
| Evidence role | Nominal final suspension hardpoints, steering-axis construction, and nonzero static-toe reference state |

The workbook records coordinate matrix `[[1,0,0],[0,-1,0],[0,0,1]]`. Its right-side points use positive lateral coordinates and its left-side points use negative lateral coordinates. The reviewed adapter converts this export into the project right-handed body frame by negating lateral position and converting millimetres to metres.

## Recovered reference observations

| Item | Reported value | Current treatment |
|---|---:|---|
| Wheelbase | `1562 mm` spec; `1562.400 mm` OptimumK | Reconciliation required before active selection |
| Front tread-center track | `1232 mm` | Consistency evidence; not Ackermann track |
| Front axle sum toe | `-1.00 deg` in spec | Exact relationship to OptimumK side fields unresolved |
| OptimumK static toe | `-1.00 deg` in each front-side field | Nonzero toe reference state confirmed; exact per-wheel heading convention inactive |
| Front static camber | `-2.25 deg` | Shim stack unresolved |
| Caster / KPI | `2.51 deg / 8.6 deg` | Steering-axis consistency evidence |
| Trail / scrub radius | `6.89 mm / 5.06 mm` | Derived-geometry consistency evidence |
| Steering-arm length | `69.9 mm` | Scalar consistency evidence only |
| C-factor | `88.9 mm/rev` | Inactive pending rack/pinion verification |
| Static Ackermann | `67.7%` | Unresolved metric; not an optimizer target |
| Nominal ride height | Not recovered | Required installed/reference-configuration field |

A quick CAD inspection independently confirms the presence of static toe in the centered geometry by showing different near/far distances from a wheel-ring reference to the vehicle center plane. That inspection is qualitative consistency evidence; it does not replace a numerical wheel-plane export.

## Coordinate reconciliation

The recovered source adapters are defined in `docs/conventions/wufr26_coordinate_frame_reconciliation.md`.

For raw Test 3 steering-study triplets in inches:

```text
[x_optk, y_optk, z_optk] = 25.4 * [z_sw, -x_sw, y_sw]
```

For the final OptimumK export in millimetres:

```text
[x_can, y_can, z_can] = 0.001 * [x_optk, -y_optk, z_optk]
```

For the steering FDR SolidWorks vehicle-order coordinates in millimetres:

```text
[x_can, y_can, z_can] = 0.001 * [x_fdr, y_fdr, z_fdr]
```

The Test 3 front-left inner pickup maps within `0.05 mm` of the final OptimumK left-side value. The outer pickup differs by approximately `2.25 mm` vector magnitude, showing a later geometry revision rather than a failed axis mapping.

## Nominal steering geometry source merge

### Steering-axis construction

Front-left final OptimumK export points, millimetres:

```text
Lower upright point = [ 0.000, -587.096, 157.117]
Upper upright point = [-6.487, -564.662, 305.056]
```

These points define the nominal steering-axis line. Their canonical front-left values are:

```text
Lower = [ 0.000000, 0.587096, 0.157117] m
Upper = [-0.006487, 0.564662, 0.305056] m
```

### Selected tie-rod pickups

The team confirmed that the steering FDR table is the front-left corner when viewed from behind the vehicle facing the nose. The table reports SolidWorks vehicle-order coordinates:

```text
Tie Rod Inner = [-79.298, 220.980, 162.865] mm
Tie Rod Outer = [-61.933, 549.102, 192.223] mm
```

Canonical front-left values are:

```text
Inner = [-0.079298, 0.220980, 0.162865] m
Outer = [-0.061933, 0.549102, 0.192223] m
```

Their joint-center distance is `329.890 mm`, or `12.9878 in`, consistent with the selected 13-in Test 3 tie rod.

After the FDR points are converted into the OptimumK lateral-sign convention, the FDR inner point is exactly `12.700 mm` rearward of the final OptimumK front-left tie-rod inner point and also differs vertically. This is the documented 0.5-in steering revision, not a coordinate-system artifact. The FDR tie-rod pickups therefore supersede the generic OptimumK tie-rod points for the selected nominal steering configuration.

A symmetric front-right side may be generated by changing the sign of the canonical lateral coordinate, but it must remain labeled as a derived symmetry assumption until independently checked.

### Static-toe reference state

The hardpoints above describe the nominal mechanism in the OptimumK static-toe state, not a zero-toe wheel state. Therefore:

```text
solver upright rotation = 0
```

means the imported centered geometry at its nominal static toe. The first evaluator may calculate incremental steer relative to this state. It may not claim absolute toe-inclusive road-wheel heading until the wheel-plane basis and the exact per-wheel toe definition are reviewed.

Static toe is a reference-orientation quantity; it must not be removed by altering the imported joint coordinates.

### Derived centered-rack geometry

Under the nominal symmetry assumption:

```text
rack-center point = [-0.079298, 0.000000, 0.162865] m
rack-axis direction = [0, +1, 0]
inner-joint spacing = 0.441960 m
nominal tie-rod joint-center distance = 0.329890 m
```

This is sufficient for an explicitly labeled nominal-design, incremental rigid steering evaluator.

## Source-authority rule

1. Use the final OptimumK workbook for suspension hardpoints, steering-axis construction, and the nominal nonzero-toe reference state.
2. Use the steering FDR final table for selected front-left tie-rod inner and outer pickups.
3. Use `Steering Length Optimization Tests.xlsx`, Test 3, for transform and design-intent evidence.
4. Use `GEOMETRY FINAL.SLDPRT` and `2026Ackermann.csv` for response reproduction.
5. Use active assembly export or physical measurement for installed/as-built validation.

No source is authoritative for every question.

## Rejected steering-ratio value

The specification's `3.12:1` steering ratio is known to be wrong. It is retained as `PAR-STEER-0002` solely for discrepancy lineage. It cannot be used as an active parameter, benchmark expectation, optimizer target, validation reference, or substitute for the full steering map.

The replacement ratio must be derived from explicit transmission definitions and the local mechanism derivative at a declared rack-center state.

The OptimumK field `Rack Pinion / Steering Ratio = 101.600` is also inactive because its exact definition and units have not been recovered.

## Rack center and travel

Rack center is the midpoint between equal left and right displacement limits imposed by the installed stops. The team reports `1.00 in` current total rack travel. The provisional interpretation is:

```text
total travel = 1.00 in = 25.4 mm
one-sided displacement = 0.50 in = 12.7 mm
provisional signed domain = [-0.0127 m, +0.0127 m]
```

This is recorded as `PAR-STEER-0003`. It remains inactive until active CAD or direct measurement confirms total versus one-sided meaning, mechanical versus operational travel, equal stop contact, displacement reference, and tolerance.

## Rack-family identity clarification

Current individual drawings establish:

| Drawing | Identity |
|---|---|
| `ST-60306-AA` | Steering rack |
| `ST-60307-AA` | Steering pinion |
| `ST-60308-AA` | Rack housing |
| `ST-60309-AA` | Steering potentiometer extension |
| `ST-60310-AA` | Steering potentiometer mount |

The purchased rack is one assembly in the steering BOM, while the cost report requires separate component drawings. Omission of those subcomponents from the assembly BOM is a scope difference, not evidence that the current identities are invalid.

## Remaining installed-state export

The remaining native assembly request is now a Level E/F correlation and active-value gate rather than a blocker to the nominal-design evaluator. Export or measure:

- active assembly and subassembly configurations, component references, suppression states, and warnings;
- front-right hardpoints to test the nominal mirror assumption;
- rack-stop contact positions and actual centered state;
- pinion angle versus signed rack displacement;
- left/right wheel-plane bases and exact static-toe headings;
- camber shim stack, ride height, wheel-travel state, and tie-rod adjustment;
- installed tie-rod joint-center lengths and uncertainty.

The existing CSV template remains suitable. Screenshots may supplement but cannot replace numerical coordinates.

## Work status

The synthetic evaluator and a versioned `WUFR26_DESIGN_NOMINAL_V0` incremental-geometry case are unblocked after review of this source merge. The implementation must separate the solved upright rotation about the steering axis from projected road-wheel heading. The latter requires an initial wheel-plane basis. Absolute toe-inclusive wheel heading, production CAD reproduction, installed/as-built claims, and physical validation remain blocked until the remaining setup and assembly evidence is reviewed.
