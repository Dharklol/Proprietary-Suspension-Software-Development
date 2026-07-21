# WUFR-26 Steering Level E Comparison

**Status:** Canonical projected-wheel-heading comparison executed and review-ready; independent validation remains open  
**Model:** `MOD-STEER-0001`  
**Authorization:** `AUTH-STEER-0001`  
**Result:** `WUFR26-STEER-LEVEL-E-TEST3-V0`

## Purpose and authority boundary

This comparison checks whether the recovered nominal rigid steering geometry, Design Study input scaling, wheel-plane projection, and historical Desmos response fit are mutually consistent. It is a cross-tool nominal-design comparison, not an installed-state or physical validation.

The historical Test 3 reference is a fitted, symmetry-enforced curve. It is useful for design-source reconciliation but cannot support an independently justified pass/fail tolerance.

## Recovered input and geometry state

The design-source steering assembly is `FSA STEERING`, with `GEOMETRY FINAL.SLDPRT` as the steering geometry component. The relevant SolidWorks Design Study is `Design Study 1`.

The recovered driver is `Steer Input`, swept from `-102 deg` through `+102 deg`. Increasing native rack length maps to canonical `+y` rack translation:

```text
rack_displacement_m = Steer_Input_deg * 3.5 in/rev * 0.0254 m/in / 360 deg/rev
                    = Steer_Input_deg * 0.00024694444444444446 m/deg
```

The source range therefore maps to approximately `-25.1883 mm` through `+25.1883 mm`. The nominal Design Study domain is approximately `+/-25.4 mm`; this remains design-source authority rather than proof of installed physical stops.

## Frozen historical wheel-angle reference

The selected Test 3 fit is:

```text
left_total(x)  = -2e-8*x^4 + 3e-6*x^3 - 2e-4*x^2 + 0.2427*x - 1.1394 deg
right_total(x) = -left_total(-x)
```

The historical static values are `-1.1394 deg` left and `+1.1394 deg` right. Incremental angle is total angle minus the same side's static value.

The fit is stored in `benchmarks/steering/wufr26_desmos_wheel_angle_fits.toml`. Its limitations remain explicit:

- the raw optimizer goal samples are not frozen;
- the polynomial is not independent validation;
- the mirrored right branch cannot reveal physical asymmetry;
- physical Level F validation is separate.

## Canonical wheel-plane construction

The nominal OptimumK setup supplies:

```text
static camber = -2.25 deg per side
static toe    = -1.00 deg per side
```

The implementation in `src/pssd_steering/projection.py`:

1. constructs the centered wheel plane from side, static toe, and static camber;
2. rotates the wheel-plane normal with the upright about the steering axis;
3. intersects the rotated wheel plane with the road plane;
4. selects the forward branch of the intersection line;
5. measures signed heading against canonical `+x`.

Rotating only a generic forward vector is not used because camber and an inclined steering axis can make it differ from the wheel-plane/road-plane intersection.

## Historical convention adapter

The reviewed adapter used for `WUFR26-STEER-LEVEL-E-TEST3-V0` is:

```text
historical input sign  = +1 * canonical Design Study input
historical side map    = same-side left/right
historical increment   = -1 * canonical signed incremental heading
```

Total curves retain the canonical OptimumK static datum. Incremental curves are centered independently. This prevents the total-angle comparison from silently replacing the canonical `+/-1.00 deg` static alignment with the historical `+/-1.1394 deg` fit datum.

## Numerical result

The comparison uses all 205 integer input points from `-102 deg` through `+102 deg`.

| Quantity | Left | Right |
|---|---:|---:|
| Canonical static heading | `-1.0000 deg` | `+1.0000 deg` |
| Historical static heading | `-1.1394 deg` | `+1.1394 deg` |
| Static difference, candidate minus reference | `+0.1394 deg` | `-0.1394 deg` |
| Incremental mean residual | `-0.32312 deg` | `+0.32312 deg` |
| Incremental RMSE | `0.55323 deg` | `0.55323 deg` |
| Incremental maximum absolute residual | `1.36194 deg` at `+102 deg` | `1.36194 deg` at `-102 deg` |
| Total mean residual | `-0.18372 deg` | `+0.18372 deg` |
| Total RMSE | `0.48519 deg` | `0.48519 deg` |
| Total maximum absolute residual | `1.22254 deg` at `+102 deg` | `1.22254 deg` at `-102 deg` |

Residual is always candidate minus historical reference.

### Residual shape

The residual is mirror-antisymmetric to numerical precision. It is small near center and grows systematically toward full rack travel:

| Shared input band | Incremental RMSE | Maximum absolute incremental residual |
|---|---:|---:|
| `+/-25 deg` | `0.06130 deg` | `0.16742 deg` |
| `+/-50 deg` | `0.18478 deg` | `0.53697 deg` |
| `+/-75 deg` | `0.35833 deg` | `1.01677 deg` |
| Full `+/-102 deg` | `0.55323 deg` | `1.36194 deg` |

At full input, the less-steered/outside branch is `22.33142 deg` incremental versus the `23.69336 deg` fit reference, a `-1.36194 deg` or `-5.75%` magnitude difference. The more-steered/inside branch is `32.96278 deg` versus `32.18469 deg`, a `+0.77809 deg` or `+2.42%` magnitude difference.

The shape is consistent with a gain or geometry-detail mismatch rather than a sign, side, center, or rack-scaling failure. Likely contributors include the fit-derived reference, the approximately recovered selected geometry, and the mirrored rather than independently exported right side.

## Acceptance disposition

No pass/fail tolerance is assigned to this fit comparison. The observed residual metrics are frozen as regression and review evidence only.

The review conclusion is:

> The recovered rigid geometry, input scaling, wheel-plane projection, and convention adapter are mutually consistent with the selected historical fit at nominal-design level, while the endpoint residual remains material enough to block tighter correlation or validation claims.

A future validation tolerance requires direct left/right projected-wheel-angle samples or physical measurements with a frozen setup state, source identity, uncertainty, and independently justified acceptance limits.

## Reproducible CLI output

A full 205-point report can be generated with:

```bash
python scripts/run_wufr26_level_e_prep.py \
  --output wufr26_level_e_report.json
```

A compact summary suitable for CI and review is:

```bash
python scripts/run_wufr26_level_e_prep.py \
  --summary \
  --output wufr26_level_e_summary.json
```

CI executes the registry validator, unit tests, and both report modes, then uploads the reports as a workflow artifact.

The frozen result metadata and reviewed metrics are stored in `benchmarks/steering/wufr26_level_e_test3_result.toml`.

## `Dimension2` remains supplementary

`Dimension2` is an unsigned or branch-folded included angle between two hub-centered construction rays. It is not the projected road-wheel heading used by the optimizer goals. Its branch reconstruction remains useful for source archaeology, but it is not part of the primary wheel-heading comparison and is not validation evidence.

## Remaining gates

The next evidence needed for stronger claims is:

- direct raw left/right projected wheel-angle samples from the relevant CAD study;
- independently exported front-right geometry;
- installed rack-stop and transmission measurements;
- setup-state and uncertainty records;
- physical steering-angle or toe measurements for Level F validation.

The nominal geometry remains design-source mechanism evidence, not an installed or as-built claim.
