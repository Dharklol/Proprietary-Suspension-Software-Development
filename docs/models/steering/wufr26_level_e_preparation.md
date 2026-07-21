# WUFR-26 Steering Level E Comparison

**Status:** Frozen descriptive nominal design-source consistency  
**Result:** `WUFR26-STEER-LEVEL-E-TEST3-V0`  
**Model:** `MOD-STEER-0001`  
**Authorization:** `AUTH-STEER-0001`

## Frozen scope

The WUFR-26 nominal rigid steering evaluator has been compared with the selected Test 3 projected-wheel-angle fit over the recovered 205-point `-102 deg` to `+102 deg` input domain. The comparison uses the exact wheel-plane-normal rotation and road-plane intersection quantity rather than upright rotation or the folded `Dimension2` monitor.

The team reviewed the numerical result on 2026-07-21 and accepted it for nominal design-source steering development. The result is descriptive only: no physical pass/fail tolerance is inferred from the observed residuals.

## Source and input mapping

The design-source steering assembly is `FSA STEERING`, with `GEOMETRY FINAL.SLDPRT` as the geometry component and `Design Study 1` as the recovered study.

```text
rack_displacement_m = Steer_Input_deg * 3.5 in/rev * 0.0254 m/in / 360 deg/rev
                    = Steer_Input_deg * 0.00024694444444444446 m/deg
```

The exported `-102 deg` to `+102 deg` range maps to approximately `-25.1883 mm` to `+25.1883 mm`. The nominal study representation permits `1.00 in` to either side of center. The moving rack points are the inboard tie-rod pickup points and translate rigidly along the rack axis.

The team supplied the centered SolidWorks coordinate:

```text
SW native [lateral, vertical, longitudinal] = [0.000, 162.865, -79.298] mm
canonical [forward, left, up]               = [-0.079298, 0.000000, 0.162865] m
```

This exactly confirms the existing rack-axis origin and coordinate adapter.

## Static alignment and symmetry

The nominal setup uses the values in `WUFR-26 FINAL 8.21.2025.xlsx`:

```text
static camber = -2.25 deg per side
static toe    = -1.00 deg per side
```

Positive side-local toe is toe-out. The team confirms that the SolidWorks setup follows this setup sheet.

The team also confirms that the nominal CAD left hardpoints are a perfect reflection of the right hardpoints. Exact reflection is therefore authoritative for the nominal design model. It remains an assumption for the fabricated car until physical measurements test as-built symmetry.

## Historical full-curve reference

The selected Test 3 fit is:

```text
left_total(x) = -2e-8*x^4 + 3e-6*x^3 - 2e-4*x^2 + 0.2427*x - 1.1394 deg
right_total(x) = -left_total(-x)
```

The canonical-to-historical adapter is frozen as:

- historical input maps directly to the reviewed Design Study input;
- left/right side identities are retained;
- historical incremental response orientation is the negative of canonical signed heading;
- canonical and historical static values are preserved separately.

## Frozen numerical result

| Metric | Left | Right |
|---|---:|---:|
| Canonical static heading | `-1.0000 deg` | `+1.0000 deg` |
| Historical static heading | `-1.1394 deg` | `+1.1394 deg` |
| Incremental mean residual | `-0.32312 deg` | `+0.32312 deg` |
| Incremental RMSE | `0.55323 deg` | `0.55323 deg` |
| Incremental maximum absolute residual | `1.36194 deg` | `1.36194 deg` |
| Total RMSE | `0.48519 deg` | `0.48519 deg` |
| Total maximum absolute residual | `1.22254 deg` | `1.22254 deg` |

Residual is candidate minus the historical Test 3 reference. The residual is mirror-antisymmetric, small near center, and increasingly gain-shaped toward full travel.

## FDR projected endpoint cross-check

The team identified projected full-input wheel-turn values in the WUFR-26 FDR:

```text
less-steered / right wheel = 22.22 deg
more-steered / left wheel  = 32.81 deg
```

The nominal model predicts:

```text
less-steered = 22.33142 deg  -> +0.11142 deg, +0.501 percent
more-steered = 32.96278 deg  -> +0.15278 deg, +0.466 percent
```

This is a strong design-intent endpoint check. It does not replace physical validation because the FDR values are design-review evidence rather than independent measurements.

## `Dimension2` remains supplementary

`Dimension2` is an unsigned or branch-folded included angle between two hub-centered construction rays. It is not a continuously signed road-wheel-heading output. Its diagnostic reconstruction remains useful for source archaeology, but it is not used as the primary Level E road-wheel-angle reference.

## CAD screenshot observations

The 2026-07-21 screenshots show the rack, tie rods, column path, steering-wheel envelope, reference planes, and named sketches `Full Steering`, `Front Axel`, `Rack ACTUAL`, and `Tie Rod ACTUAL`. Several column dimensions are legible, including `269.65 mm`, `57.91 mm`, `50.80 mm`, and `6.35 mm`, but selected entities are not sufficiently clear to promote those values into active parameters.

The full observation record is `docs/models/steering/wufr26_cad_observations_2026-07-21.md`.

## Acceptance and authority

The Level E result is frozen for future nominal steering-system development. It supports the recovered geometry, rack input mapping, wheel-plane projection, side convention, and overall steering response.

It does **not** establish:

- installed rack center or physical stops;
- installed steering-wheel-to-pinion-to-rack transmission;
- as-built left/right hardpoint symmetry;
- compliance, backlash, friction, hysteresis, or repeatability;
- a physical validation tolerance;
- Level F validation.

## Next gate

The next verification work is `P0-STR-011`: physical Level F correlation and uncertainty characterization. The protocol is `docs/verification/steering/wufr26_level_f_measurement_protocol.md`.

Physical testing must explicitly include rack, gear mesh, rod ends, tie rods, steering column, quick release, supporting structures, wheel bearings, wheels, and measurement fixtures in the compliance/backlash budget.
