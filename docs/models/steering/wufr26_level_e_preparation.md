# WUFR-26 Steering Level E Preparation

**Status:** Direct left/right wheel-angle fits are available from the historical Desmos work; canonical comparison now waits on the reviewed wheel-plane projection and convention adapter  
**Model:** `MOD-STEER-0001`  
**Authorization:** `AUTH-STEER-0001`

## Work sequence decision

The evaluator and comparison infrastructure were completed before requesting CAD measurements. Team screenshots, the recovered `2026Ackermann.csv`, the steering-length test workbook, the OptimumK final setup, the historical Desmos equations, and the existing coordinate adapter now resolve the design-source input and response paths without reopening the native SolidWorks model.

## Added infrastructure

`src/pssd_steering/comparison.py` provides traceable signal records, periodic normalization, domain-limited interpolation, residual metrics, and explicit unavailable states.

`src/pssd_steering/solidworks.py` provides native Design Study CSV parsing and the reviewed steering-input-to-rack mapping.

`src/pssd_steering/legacy_fits.py` provides traceable evaluation of the recovered Desmos wheel-angle polynomials, preserving total, static and incremental definitions and the historical right-side mirror relation.

## Recovered SolidWorks input state

The design-source steering assembly is `FSA STEERING`, with `GEOMETRY FINAL.SLDPRT` as the steering geometry component. The relevant SolidWorks Design Study is named `Design Study 1`.

Team evidence records:

- SolidWorks 2025 SP3.2 Academic Use Only;
- the reference chassis model suppressed;
- no reported errors or warnings;
- `Steer Input` swept from `-102 deg` through `+102 deg`;
- rack equation `Rack Length = 8.7 + Steer Input * rack ratio`;
- `rack ratio = 3.5 / 360` inches per input degree;
- a reported 1:1 steering-wheel-to-pinion relation for the design assembly.

The reviewed coordinate adapter maps increasing native rack length to canonical `+y` rack translation:

```text
rack_displacement_m = Steer_Input_deg * 3.5 in/rev * 0.0254 m/in / 360 deg/rev
                    = Steer_Input_deg * 0.00024694444444444446 m/deg
```

The exported `-102 deg` to `+102 deg` range maps to approximately `-25.1883 mm` to `+25.1883 mm`.

## Rack-travel correction

The nominal design study permits approximately **1.00 in to either side of center**, or **2.00 in total**. The configuration domain is now `-25.4 mm` to `+25.4 mm`; the historical CSV samples the slightly smaller range produced by its `+/-102 deg` limits.

This is design-study authority only. Installed physical stops, backlash, compliance and operational margin still require CAD inspection or measurement.

## Direct wheel-angle reference from Desmos

The historical Desmos graphs provide the actual fitted left and right wheel-angle response versus steering input. This removes the need to identify `Dimension2` before performing the intended wheel-angle cross-tool comparison.

The frozen selected Test 3 fit is:

```text
left_total(x) = -2e-8*x^4 + 3e-6*x^3 - 2e-4*x^2 + 0.2427*x - 1.1394 deg
right_total(x) = -left_total(-x)
```

with `x` in degrees of the historical steering-input convention.

The center values are:

```text
left_static  = -1.1394 deg
right_static = +1.1394 deg
```

and incremental wheel angle is defined side-by-side as total angle minus that side's center value.

The fits are frozen in `benchmarks/steering/wufr26_desmos_wheel_angle_fits.toml`. Test 3 is the primary selected-geometry fit. Tests 1, 2 and 4 remain historical design candidates, and the previous-year fit remains a baseline.

### Source role and limitations

These curves are the primary available **projected road-wheel-angle response reference** for the selected Test 3 geometry. They are more appropriate than `Dimension2` for comparison with the wheel-plane/ground-plane intersection angle used by the optimizer goals.

They remain fit-derived evidence:

- the underlying raw goal samples are not frozen;
- the polynomial itself is not independent validation;
- the mirrored right branch enforces ideal symmetry;
- a reviewed historical-to-canonical sign and side adapter is still required;
- physical Level F validation remains separate.

## Wheel-plane basis recovered from OptimumK

`WUFR-26 FINAL 8.21.2025.xlsx` records the nominal front setup as:

```text
static camber = -2.25 deg per side
static toe    = -1.00 deg per side
```

The team convention is positive toe-out. Therefore the centered ground-plane wheel directions and full wheel-plane normals can be constructed from side, toe, camber and the canonical body frame.

The next implementation must use the exact geometric quantity described by the optimizer setup:

1. construct the nominal wheel plane from static toe and camber;
2. rotate its normal with the upright about the steering axis;
3. intersect the rotated wheel plane with the road plane;
4. select the forward branch of that intersection line;
5. calculate the signed angle against canonical `+x`;
6. apply the explicit historical Desmos side/sign adapter;
7. compare total and incremental left/right curves.

Rotating only a nominal forward vector is not accepted as a substitute because an inclined steering axis and nonzero camber can make that differ from the wheel-plane/ground-plane intersection.

## `Dimension2` remains supplementary

The follow-up screenshot and raw CSV establish that `Dimension2` is an unsigned or branch-folded included angle between two magenta hub-centered construction rays. It reaches `0.17 deg` near `-77 deg` input, then increases on both sides. It is not a continuously signed road-wheel-heading output.

The diagnostic branch reconstruction and its residuals remain useful for source archaeology, but `Dimension2` is no longer the critical path for the direct wheel-angle comparison. Its exact second ray is needed only to finish interpreting that separate internal monitor.

The full diagnostic is recorded in `docs/models/steering/wufr26_dimension2_ray_diagnostic.md`.

## Numerical consistency already established

At the exact source endpoint rack displacement of `25.1883 mm`, the nominal rigid model predicts upright-rotation magnitudes of approximately:

- `33.27856 deg` on the inner/more-steered nominal side;
- `22.45550 deg` on the outer/less-steered nominal side.

The historical Test 3 response and visible optimizer results are close to these values, supporting the recovered geometry and input scaling. Formal residuals must nevertheless use projected wheel heading rather than upright rotation.

## Revised comparison sequence

1. Freeze the historical Desmos Test 3 total and incremental wheel-angle curves.
2. Construct the nominal left/right wheel-plane normals from the reviewed static toe and camber.
3. Implement exact wheel-plane/road-plane projection after upright rotation.
4. Freeze the historical-to-canonical input, side and output-sign adapter.
5. Generate the same projected quantity over the shared input domain.
6. Report left/right point residuals, mean error, RMSE and maximum absolute error.
7. Review residual shape before setting a Level E tolerance.
8. Keep the `Dimension2` diagnostic and physical Level F validation separate.

The nominal geometry remains design-source mechanism evidence, not an installed/as-built claim.
