# WUFR-26 Steering Force, Backlash, Compliance, and Instrumentation Evidence

**Status:** Source-linked Phase 0 evidence packet; calculated loads and historical tests are not automatically active validation values  
**Related model:** `MOD-STEER-0001`  
**Related risk:** `RISK-STEER-0002`  
**Related task:** `P0-STR-011`

## Purpose

This packet links the already-existing steering force calculations, historical compliance/free-play test, current installed free-play observation, bevel-gear evidence, and available instrumentation into the software repository. It prevents existing evidence from being misclassified as wholly missing while retaining the distinction between calculation, supplier specification, historical test, current whole-system observation, and future staged correlation.

## Source identities

### Suspension Calculations 2026

- Google Sheet title: `Suspension Calculations 2026`
- Google Drive file ID: `1mW6JVHnSgvJJmXwYGV9AZV3ybRiolN9vPI8NAJjdvLA`
- current inspected revision: `249`
- inspected modified time: `2026-07-20T00:03:14Z`
- relevant sheets: `Steering Forces`, `Steering Column Forces`
- role: calculation workbook; not independent validation evidence

### Steering Compliance Test

- Google Doc title: `Steering Compliance Test`
- Google Drive file ID: `1-v5CJDZ8OCKXtyIP1dahvR50OqjGEUocytBonaA_tCQ`
- role: historical physical test-method and point-observation evidence
- stated scope: WUFR-25 steering system tested during WUFR-26 development

### WUFR-27 Steering PDR

- Google Doc title: `WUFR-27 Steering PDR`
- Google Drive file ID: `11oA3n8DkVLHVNrADySI0-5wMeEYW0cistUdlketEXHQ`
- role: later design-review recap of WUFR-26 service history, free-play issue, and planned instrumentation

## Calculation-workbook cell map

The following values are linked to exact workbook cells. Signs retain the workbook convention; magnitudes must not be silently substituted into a different load case.

### Steering Forces

| Cell | Value | Role |
|---|---:|---|
| `Steering Forces!D97` | `43.10956069 N*m` | maximum listed total corner-entry steering-axis moment before the 1.5 factor in the column sheet |
| `Steering Forces!D122` | `-106.09301145 N*m` | combined parked tire-scrub steering-axis moment before factor of safety |
| `Steering Forces!E122` | `-159.13951717 N*m` | parked tire-scrub moment with `1.5` factor of safety |

The parked value is calculated from tire load, friction coefficient, scrub radius, pneumatic trail, mechanical trail, caster, and toe terms. It is a conservative structural/load-case input, not a measured driver torque.

### Steering Column Forces

| Cell | Value | Role |
|---|---:|---|
| `Steering Column Forces!C8` | `2221.68808 N` | parked total rack force derived from `Steering Forces!E122` and the steering-arm distance |
| `Steering Column Forces!C9` | `35.54700928 N*m` | parked column reaction moment with the workbook factor of safety |
| `Steering Column Forces!C10` | `23.69800619 N*m` | parked column reaction moment with the `1.5` factor removed |
| `Steering Column Forces!C14` | `902.7550054 N` | cornering total rack force |
| `Steering Column Forces!C15` | `14.44408009 N*m` | cornering column reaction moment |
| `Steering Column Forces!C41` | `2113.626358 N` | bevel-gear tangential force, parked case |
| `Steering Column Forces!C42` | `858.8454842 N` | bevel-gear tangential force, cornering case |
| `Steering Column Forces!C45` | `-382.4307700 N` | convex axial component, parked case |
| `Steering Column Forces!F45` | `-155.3959329 N` | convex axial component, cornering case |
| `Steering Column Forces!C46` | `1710.572930 N` | concave axial component, parked case |
| `Steering Column Forces!F46` | `695.0697933 N` | concave axial component, cornering case |
| `Steering Column Forces!C48` | `1710.572930 N` | convex radial component, parked case |
| `Steering Column Forces!F48` | `695.0697933 N` | convex radial component, cornering case |
| `Steering Column Forces!C49` | `-382.4307700 N` | concave radial component, parked case |
| `Steering Column Forces!F49` | `-155.3959329 N` | concave radial component, cornering case |

The workbook also contains primary- and secondary-shaft bearing reactions. The sheet itself notes a sign mistake in the bearing-force section, so those bearing-force signs remain research/review evidence rather than frozen design loads until the equilibrium and axis conventions are independently checked.

## Bevel-gear identity and backlash

The steering BOM identifies the installed pair as KHK `MMSG2-20R` and `MMSG2-20L`, a 1:1 right-/left-hand module-2, 20-tooth spiral-miter pair. The force workbook uses 20 teeth, module 2, 20-degree pressure angle, 35-degree spiral angle, approximately 40 mm reference diameter, and 9 mm face width, consistent with that family.

The team identifies the supplier backlash range as `0.04 to 0.10 mm` at the gear mesh. This supplier/component value is not added to a measured whole-system steering-wheel free-play observation. The exact KHK catalog PDF or immutable product-page capture should be stored before treating the range as a frozen supplier record.

## Physical free-play and compliance observations

### Current installed whole-system free play

The latest team clarification records approximately `4.0 deg` total steering-wheel free play with the front tires scrub-constrained. This is stored as `PAR-STEER-0004`.

This observation includes all engaged interfaces and effects in series, potentially including the quick release, column couplings, bevel gears, rack and pinion, rack support, rod ends, tie rods, uprights, wheel bearings, tire scrub, and measurement threshold. It must not be decomposed by subtracting nominal supplier clearances without a staged measurement.

### Historical cross-checks

The historical `Steering Compliance Test` records:

- total free play: `2.35 deg`;
- first-direction compliance: `0.26 deg/N*m`, stored as `PAR-STEER-0005`;
- opposite-direction compliance: `0.47 deg/N*m`, stored as `PAR-STEER-0006`.

The WUFR-27 PDR separately reports approximately `5 deg` measured free play associated with set-screw coupling slip. These observations refer to different dates, states, or procedures and are retained separately rather than averaged.

## Available and planned instrumentation

### Available

- installed steering-rack linear potentiometer: `SNS-STEER-0001`;
- torque-rig/digital-force-gauge method with a measured lever arm;
- digital angle gauge;
- calipers.

### Planned

- primary-shaft rotary potentiometer: `SNS-STEER-0002`.

With the rack and primary-shaft potentiometers, the next useful automated channel pair is primary-shaft angle versus measured rack displacement. Manual digital-angle-gauge points can then add left/right projected wheel heading without waiting for dedicated wheel-angle encoders.

## Evidence classification and no-double-counting rules

1. The parked and cornering forces are calculated load cases from the 2026 workbook.
2. The KHK backlash range is a supplier/component specification.
3. The `4 deg` value is a current approximate whole-system installed observation.
4. The `2.35 deg`, `0.26 deg/N*m`, and `0.47 deg/N*m` values are historical test observations.
5. The PDR's approximately `5 deg` value is a later state/service-history observation.
6. Supplier gear backlash must not be added to or subtracted from whole-system free play without staged shaft/rack measurements.
7. Elastic compliance slopes must be calculated after the free-play limit is engaged and must remain directional when the response differs by approach direction.
8. The rigid kinematic model is not corrected by a constant backlash or compliance offset; physical response is compared as a separate layer.

## Immediate next reduction

After the primary-shaft rotary potentiometer is installed and calibrated, acquire synchronized primary-shaft angle and rack displacement during slow bidirectional sweeps. Report:

- shaft-to-rack gain;
- reversal deadband in primary-shaft degrees and rack millimetres;
- approach-direction hysteresis;
- repeatability;
- left/right manual wheel-heading residuals at selected rack positions;
- setup, surface, tire pressure, and applied-torque threshold.

This is sufficient to begin separating upper-column/coupling behavior from rack-to-wheel behavior with the equipment already available.
