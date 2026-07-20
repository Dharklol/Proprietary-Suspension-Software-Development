# WUFR-26 `Dimension2` Ray-Construction Diagnostic

**Status:** Evidence narrows the monitor construction, but the exact second selected ray remains unresolved  
**Source response:** `2026Ackermann.csv`, `Design Study 1`  
**Model:** `MOD-STEER-0001`

## Evidence separation

Two SolidWorks studies must remain distinct.

1. The `STEERING GEOMETRY 2` optimizer uses right- and left-turn-angle goals. Team Slack evidence states that these turn angles were constructed from the intersection of the wheel-center plane with the ground plane and measured against the SolidWorks x-axis.
2. The `STEERING ACKERMAN CALC` response study exports `Steer Input` and the monitor named `Dimension2`. The supplied screenshot shows two magenta construction rays sharing the hub/steering-pivot point. At least one ray is connected to the tie-rod/steering-arm construction. The optimizer turn-angle definition must not be assigned automatically to this different monitor.

## What the screenshot establishes

The monitor is visually associated with the included angle between two magenta rays that share the outboard pivot. Green construction lines include the true imported tie rod and additional tie-rod-optimization references. The current evidence supports the following classification:

- `Dimension2` is an unsigned or branch-folded included-angle monitor;
- one ray is associated with the steering-arm/tie-rod construction;
- the exact identity and orientation of the second ray are not yet frozen;
- it is not safe to label the raw monitor as toe, absolute road-wheel heading, or upright rotation.

## Raw-curve branch evidence

The raw response has these characteristic values:

| Steer Input | `Dimension2` |
|---:|---:|
| `-102 deg` | `10.24 deg` |
| `-77 deg` | `0.17 deg` |
| `-76 deg` | `0.17 deg` |
| `0 deg` | `20.57 deg` |
| `+102 deg` | `41.84 deg` |

The near-zero double minimum followed by increasing values on both sides is the signature of an unsigned included angle crossing through alignment. It is not the shape of a continuously signed wheel-heading output.

## Diagnostic-only branch reconstruction

A continuity reconstruction can be formed for diagnosis only:

```text
phi_signed = -Dimension2  for Steer Input <= -77 deg
phi_signed = +Dimension2  for Steer Input >= -76 deg
q_diagnostic = phi_signed - 20.57 deg
```

This gives:

- `q_diagnostic(-102 deg) = -30.81 deg`;
- `q_diagnostic(0 deg) = 0 deg`;
- `q_diagnostic(+102 deg) = +21.27 deg`.

Against the nominal rigid evaluator quantity `-left upright rotation` over all 205 source scenarios, the diagnostic reconstruction gives:

- mean residual, evaluator minus diagnostic: `-0.1444028734 deg`;
- RMSE: `0.9197095305 deg`;
- maximum absolute residual: `2.4685599616 deg`, at `-102 deg` input.

The curve tracks steering motion closely, but the residual has a systematic gain-shaped trend. That behavior is consistent with an internal ray angle whose two references do not reduce to the evaluator's single upright-rotation coordinate. These numbers are not a Level E validation result and must not be assigned an acceptance tolerance.

## Remaining closure item

Freeze either:

- the exact two SolidWorks entities selected by `Dimension2`, including order and angular branch behavior; or
- a direct wheel-plane/ground-intersection versus x-axis result from the turn-angle goal construction.

The team-directed video location is `WUFR-27 / Suspension / PDR-FDR / Steering / Design Study Tutorials`, second tutorial, approximately `1:15` through `2:00`. The video bytes and timestamped frames have not yet been frozen into the source catalog.
