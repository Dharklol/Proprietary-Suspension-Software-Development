# Steering-Angle and Steer-Ratio Fit Reconstruction

**Status:** Historical calculator transformation reconstructed; WUFR-26 reference angle and signal identities remain proposed pending CAD review  
**Related IDs:** `MIG-STR-0001`, `MIG-SC26-SR-001`, `MIG-SC26-SR-003`, `BENCH-STEER-0001`, `MOD-STEER-0001`

## Purpose

This note reconstructs how the historical `Steer Ratio` calculator converted SolidWorks angular-monitor outputs into a signed road-wheel curve and then into the plotted quantity called `Steer Ratio`. It also records the provisional processing of the WUFR-26 `2026Ackermann.csv` export.

The reconstruction separates four operations that had been visually combined in the spreadsheet:

1. angular-branch unwrapping;
2. subtraction of the straight-ahead reference angle;
3. curve fitting or interpolation;
4. differentiation and ratio-definition conversion.

## Recovered historical transformation

The WUFR-25 source exports preserve both the raw angular monitor and the converted wheel output, which makes the legacy operation identifiable.

### `WUFR_25.csv`

The relation is, within the exported rounding,

```text
wheel_output_deg = Dimension2_deg - 32.9 deg
```

Examples:

| Steering input | Raw `Dimension2` | `WHEEL OUTPUT` | Check |
|---:|---:|---:|---:|
| -90 deg | 0.10 deg | -32.80 deg | `0.10 - 32.90` |
| 0 deg | 31.90 deg | -1.00 deg | `31.90 - 32.90` |
| 90 deg | 55.56 deg | 22.66 deg | `55.56 - 32.90` |

### `3.5INREV_WUFR25.csv`

The relation is, within the exported rounding,

```text
wheel_output_deg = Dimension2_deg - 33.0 deg
```

The spreadsheet note commonly interpreted as “making angles negative” therefore represents reference-angle subtraction, not an arbitrary sign assignment. Negative road-wheel angles occur because the raw monitored angle is below the straight-ahead reference angle.

Some SolidWorks angular dimensions additionally return an unsigned or acute-angle branch. When that branch crosses zero, it must first be unwrapped before the reference angle is subtracted.

## WUFR-26 `2026Ackermann.csv`

### Source metadata

- Box file ID: `2357045252883`
- Box file version ID: `2611346929683`
- Box SHA-1: `69d71c0977287a13385683204344e78816b48512`
- Parent directory: `6. STEERING/998. GEOMETRY`
- Source rows: `Steer Input` and monitored `Dimension2` in degrees
- Scenario domain: `-102 deg` through `+102 deg` in `1 deg` increments
- Point count: `205`

The file was team-provided as the WUFR-26 final-geometry second-motion-study result. It is a derived SolidWorks export, not independent physical validation.

### Angular unwrapping

The raw `Dimension2` values approach `0.17 deg` at steering-input values `-77 deg` and `-76 deg`, then increase on both sides. This is consistent with an angular monitor crossing its zero branch between those samples rather than with a physical reversal of steering motion.

The provisional continuous monitored angle is therefore

```text
unwrapped_angle = -Dimension2,  for Steer Input <= -77 deg
unwrapped_angle = +Dimension2,  for Steer Input >= -76 deg
```

The branch crossing is provisionally bracketed by `[-77 deg, -76 deg]`. Linear interpolation of the rounded values places it near `-76.5 deg`, but that value is not a frozen mechanism zero because the export is rounded to `0.01 deg` and the SolidWorks measurement definition has not been inspected.

### Straight-ahead reference subtraction

Road-wheel steer angle is obtained from

```text
road_wheel_angle = unwrapped_angle - reference_angle
```

The correct `reference_angle` is the unwrapped monitored angle at the reviewed straight-ahead/rack-center configuration. It must come from the CAD study definition or an approved setup definition, not from a visual curve shift.

For a provisional reconstruction only, taking `Steer Input = 0 deg` as straight ahead gives

```text
reference_angle_provisional = 20.57 deg
```

and therefore

```text
road_wheel_angle_provisional = unwrapped_angle - 20.57 deg
```

This provisional offset makes the raw point at zero input equal to zero road-wheel angle. It is not yet parameter authority. A different reviewed rack-center input would change only the vertical offset of the wheel-angle curve; it would not change its local derivative or the steering-ratio calculation.

## Historical polynomial fit

The calculator wheel-angle graphs use unconstrained cubic least-squares trendlines of signed road-wheel angle versus steering input. Reproducing the same method for the complete WUFR-26 export gives the following cubic for the **unwrapped monitored angle**, with `x` in exported input degrees:

```text
a_hat(x) =
    2.62594499e-6 x^3
  - 4.24498175e-4 x^2
  + 2.25972043e-1 x
  + 2.07093243e1
```

Fit statistics over all 205 exported points:

| Metric | Value |
|---|---:|
| R-squared | `0.99988737` |
| RMSE | `0.15304 deg` |
| Maximum absolute residual | `0.69702 deg` |

Using the provisional `20.57 deg` reference changes only the intercept:

```text
delta_hat_provisional(x) =
    2.62594499e-6 x^3
  - 4.24498175e-4 x^2
  + 2.25972043e-1 x
  + 1.39324317e-1
```

The fitted curve is not forced through the raw zero point, which explains its small nonzero intercept. That matches the historical Excel trendline behavior.

Higher-order polynomials reduce residuals, but they are not adopted as canonical models. They add global oscillation and extrapolation risk while obscuring the source table. The canonical implementation should preserve the raw transformed table and use a shape-preserving interpolant inside the approved physical domain.

## What the calculator calls `Steer Ratio`

The historical spreadsheet computes a point-to-point slope of road-wheel angle versus steering input:

```text
g = Delta(road-wheel angle) / Delta(steering input)
```

This is a local **road-wheel gain**, with units of road-wheel degrees per input degree. It is the inverse of the conventional steering ratio when the input is steering-wheel angle:

```text
conventional steering ratio =
    Delta(steering-wheel angle) / Delta(road-wheel angle)
  = 1 / g
```

The WUFR-24 and WUFR-25 spreadsheet blocks use inconsistent forward/backward placement of the finite difference, which shifts the displayed gain horizontally by approximately half a sample. A centered difference should be used for interior points in the replacement implementation, with explicit one-sided treatment at the domain boundaries.

Differentiating the WUFR-26 historical cubic gives

```text
g_hat(x) =
    7.87783497e-6 x^2
  - 8.48996350e-4 x
  + 2.25972043e-1
```

The corresponding conventional ratio is

```text
R_hat(x) = 1 / g_hat(x)
```

only after `Steer Input` is confirmed to be steering-wheel angle. If the SolidWorks driver is a shaft, pinion, mate, or sketch angle, `g_hat` is only the local ratio between that driver and the monitored wheel angle. The missing upstream transmission must then be applied separately.

## Recommended canonical processing chain

```text
immutable CSV
  -> schema and point-count validation
  -> angular-branch unwrapping
  -> reviewed straight-ahead reference subtraction
  -> signed left/right road-wheel quantity mapping
  -> shape-preserving interpolation within physical lock limits
  -> analytical or numerically verified derivative
  -> local road-wheel gain
  -> reciprocal conventional ratio where well-conditioned
```

The original cubic and finite-difference curves remain useful for legacy reproduction, but the polynomial is not the source of truth.

## Required benchmark checks

1. Confirm the SolidWorks definition and orientation of `Dimension2`.
2. Confirm whether `Steer Input` is steering-wheel, shaft, pinion, mate, or sketch angle.
3. Confirm the straight-ahead/rack-center input and reference angle.
4. Confirm the branch-unwrapping rule from the CAD measurement orientation.
5. Restrict the benchmark to the physical steering range declared by the FDR/CAD stops rather than assuming every exported scenario is operational.
6. Compare raw transformed points, interpolated values, derivatives, and reciprocal ratios separately.
7. Retain `Test_3.csv` as selection-era cross-check evidence rather than silently replacing it.
8. Do not use the fitted curve as independent validation of the geometry that generated it.
