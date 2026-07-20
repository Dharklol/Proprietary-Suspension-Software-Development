# Steering-Angle and Steer-Ratio Fit Reconstruction

**Status:** Historical calculator transformation reconstructed; WUFR-26 monitor datum, static toe, and signal identities remain proposed pending CAD review  
**Related IDs:** `MIG-STR-0001`, `MIG-SC26-SR-001`, `MIG-SC26-SR-003`, `BENCH-STEER-0001`, `MOD-STEER-0001`

## Purpose

This note reconstructs how the historical `Steer Ratio` calculator converted SolidWorks angular-monitor outputs into signed road-wheel curves and then into the plotted quantity called `Steer Ratio`. It also records provisional processing of the WUFR-26 `2026Ackermann.csv` export.

The reconstruction separates five operations that had been visually combined:

1. angular-branch unwrapping;
2. subtraction of a monitor-specific angular datum;
3. retention or removal of static toe;
4. curve fitting or interpolation;
5. differentiation and ratio-definition conversion.

The distinction between toe-inclusive wheel heading and incremental steer is required. Earlier provisional work forced the WUFR-26 zero-input output to zero. The recovered Desmos equations show that the historical process generally retained about one degree of static toe, so that forced-zero transformation is no longer preferred.

## Recovered historical transformation

The WUFR-25 source exports preserve both the raw angular monitor and the converted wheel output.

### `WUFR_25.csv`

Within exported rounding:

```text
wheel_output_deg = Dimension2_deg - 32.9 deg
```

| Steering input | Raw `Dimension2` | `WHEEL OUTPUT` | Check |
|---:|---:|---:|---:|
| -90 deg | 0.10 deg | -32.80 deg | `0.10 - 32.90` |
| 0 deg | 31.90 deg | -1.00 deg | `31.90 - 32.90` |
| 90 deg | 55.56 deg | 22.66 deg | `55.56 - 32.90` |

### `3.5INREV_WUFR25.csv`

Within exported rounding:

```text
wheel_output_deg = Dimension2_deg - 33.0 deg
```

The spreadsheet note interpreted as “making angles negative” therefore represents datum subtraction, not arbitrary sign assignment. Negative values occur because the monitored angle is below the chosen monitor datum.

Critically, zero steering input produces approximately `-1 deg`, not zero. The processed quantity is therefore a toe-inclusive signed wheel heading for one side. Under the historical mirror relation, the opposite side is approximately `+1 deg` at rack center.

Some SolidWorks angular dimensions additionally return an unsigned or acute-angle branch. When that branch crosses zero, it must be unwrapped before datum subtraction.

## Canonical angle separation

The replacement must represent at least two distinct quantities:

```text
total wheel heading:
    delta_total(input)

static toe at rack center:
    delta_static = delta_total(input_center)

incremental wheel steer:
    delta_incremental(input) = delta_total(input) - delta_static
```

The historical Desmos fits appear to represent `delta_total`. A steering-ratio derivative may use either total or incremental angle because the constant static-toe term differentiates to zero. Ackermann comparisons, inside/outside angle maps, setup outputs, and CAD reproduction must state which representation is used.

## WUFR-26 `2026Ackermann.csv`

### Source metadata

- Box file ID: `2357045252883`
- Box file version ID: `2611346929683`
- Box SHA-1: `69d71c0977287a13385683204344e78816b48512`
- Parent directory: `6. STEERING/998. GEOMETRY`
- Source rows: `Steer Input` and monitored `Dimension2` in degrees
- Scenario domain: `-102 deg` through `+102 deg` in `1 deg` increments
- Point count: `205`

The file is the team-provided WUFR-26 final-geometry second-motion-study result. It is a derived SolidWorks export, not independent physical validation.

### Angular unwrapping

The raw `Dimension2` values approach `0.17 deg` at steering-input values `-77 deg` and `-76 deg`, then increase on both sides. This is consistent with an angular monitor crossing its zero branch rather than physical reversal.

The provisional continuous monitored angle is:

```text
unwrapped_angle = -Dimension2,  for Steer Input <= -77 deg
unwrapped_angle = +Dimension2,  for Steer Input >= -76 deg
```

The crossing is provisionally bracketed by `[-77 deg, -76 deg]`. Linear interpolation of rounded values places it near `-76.5 deg`, but that is not a frozen mechanism zero.

### Monitor datum and static toe

The total left-wheel heading should be represented as:

```text
delta_total_left = unwrapped_angle - monitor_datum
```

The correct `monitor_datum` must be recovered from the SolidWorks measurement definition or from an approved transformation record. It is not necessarily the unwrapped angle at rack center because the historical output retains static toe.

At exported input zero:

```text
unwrapped_angle = 20.57 deg
```

Two distinct provisional normalizations can be shown, but neither is parameter authority:

```text
incremental-only normalization:
    delta_incremental_provisional = unwrapped_angle - 20.57 deg

historical-style toe-inclusive example, assuming left static toe = -1.00 deg:
    monitor_datum_example = 21.57 deg
    delta_total_left_example = unwrapped_angle - 21.57 deg
```

The `21.57 deg` value is only an illustrative consequence of a `-1 deg` toe assumption. It must not be frozen without the WUFR-26 static-toe specification and CAD monitor definition.

## Independent cubic audit fit

An unconstrained cubic least-squares fit to the complete **unwrapped monitored angle** table gives, with `x` in exported input degrees:

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

Subtracting `20.57 deg` gives an incremental-angle audit fit:

```text
delta_incremental_hat(x) =
    2.62594499e-6 x^3
  - 4.24498175e-4 x^2
  + 2.25972043e-1 x
  + 1.39324317e-1
```

The nonzero intercept results from the unconstrained global regression. It should not be interpreted as the historical static toe.

A toe-inclusive fit uses the same nonconstant coefficients and a different reviewed intercept. For example, a `21.57 deg` monitor datum would give an intercept near `-0.86068 deg`, close to the historical Desmos pattern, but that example remains unapproved.

The independent cubic is audit evidence, not the canonical mechanism model. The canonical implementation should preserve the transformed raw table and use a shape-preserving interpolant inside the approved physical domain.

## Captured historical Desmos behavior

The WUFR-26 candidate comparison uses quartic left-wheel functions and constructs the right wheel as:

```text
W_Right(x) = -W_Left(-x)
```

The displayed center intercepts are approximately `-0.99 deg` to `-1.25 deg`. This confirms that the historical plotted curves retain toe or another rack-center wheel-heading offset. Detailed coefficients and source comparisons are recorded in `test_1_to_4_fit_evidence.md`.

The mirror equation enforces geometric symmetry. It does not independently identify or validate both physical wheel responses.

## What the calculator calls `Steer Ratio`

The historical spreadsheet computes a point-to-point slope of wheel angle versus steering input:

```text
g = Delta(road-wheel angle) / Delta(steering input)
```

This is local **road-wheel gain**, not conventional steering ratio. Static toe has no effect on this derivative.

When the input is confirmed to be steering-wheel angle:

```text
conventional steering ratio =
    Delta(steering-wheel angle) / Delta(road-wheel angle)
  = 1 / g
```

The WUFR-24 and WUFR-25 spreadsheet blocks use inconsistent forward/backward finite-difference placement, shifting the displayed gain horizontally by about half a sample. The replacement should use a centered difference for interior sampled data or the verified derivative of the interpolant, with explicit one-sided boundary handling.

Differentiating the WUFR-26 independent cubic gives:

```text
g_hat(x) =
    7.87783497e-6 x^2
  - 8.48996350e-4 x
  + 2.25972043e-1
```

The corresponding reciprocal is:

```text
R_hat(x) = 1 / g_hat(x)
```

only after `Steer Input` is confirmed as steering-wheel angle. If the driver is a shaft, pinion, mate, or sketch angle, the missing upstream transmission must be applied separately.

## Recommended canonical processing chain

```text
immutable CAD export
  -> schema and point-count validation
  -> angular-branch unwrapping
  -> reviewed monitor-datum subtraction
  -> toe-inclusive left/right wheel-heading map
  -> explicit rack-center static-toe extraction
  -> optional incremental-steer map
  -> shape-preserving interpolation within physical limits
  -> verified derivative
  -> local road-wheel gain
  -> reciprocal conventional ratio where defined
```

The historical polynomial and finite-difference curves remain useful for legacy reproduction, but neither is the source of truth.

## Required benchmark checks

1. Confirm the SolidWorks definition and orientation of `Dimension2`.
2. Confirm whether `Steer Input` is steering-wheel, shaft, pinion, mate, or sketch angle.
3. Confirm rack-center input and WUFR-26 left/right static toe.
4. Recover the monitor datum used to convert `Dimension2` into signed wheel heading.
5. Confirm the branch-unwrapping rule from the CAD measurement orientation.
6. Identify whether `2026Ackermann.csv` monitors the physical left wheel, right wheel, inside branch, or outside branch.
7. Restrict the benchmark to declared physical steering limits.
8. Compare raw transformed points, toe-inclusive maps, incremental maps, derivatives, and reciprocal ratios separately.
9. Retain `Test_3.csv` as selection-era cross-check evidence.
10. Do not use a fitted curve as independent validation of the geometry that generated it.
