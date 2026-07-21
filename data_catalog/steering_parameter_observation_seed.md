# WUFR-26 Steering Parameter-Observation Seed

**Status:** Reviewed Phase 0 observation seed; task complete  
**Primary source:** `CAT-STEER-SPEC-0001`  
**Vehicle revision:** WUFR-26  
**Related model:** `MOD-STEER-0001`  
**Review record:** `docs/reviews/phase0_steering_review_closeout.md`

## Purpose

This seed records how steering-relevant source values enter the project as observations without becoming authoritative merely because they appear in a specification, workbook, drawing, CAD model, test note, or conversation. Active values are selected only through a reviewed configuration or parameter record.

## Observation classes now represented

| Class | Examples | Rule |
|---|---|---|
| Inactive design-intent observation | wheelbase, axle sum toe, C-factor | Preserve source value, units, definition, and mapping restrictions. |
| Rejected observation | reported `3.12:1` steering ratio | Preserve lineage but prohibit downstream numerical use. |
| Active nominal-design value | WUFR-26 hardpoints, static alignment, nominal rack-study domain | Authoritative only for `WUFR26_DESIGN_NOMINAL_V0`, not the installed vehicle. |
| Historical physical observation | directional compliance and earlier free-play results | Preserve test state and direction; do not average across different states. |
| Current installed-system observation | approximately `4 deg` whole-system steering-wheel free play under parked tire scrub | Treat as a system total without component attribution. |
| Supplier/component observation | KHK gear identity and backlash range | Keep separate from whole-system measurements and require source capture for freeze. |

## Direct design-spec observations

| Observation | Source-native value | Canonical mapping | Current authority |
|---|---:|---:|---|
| `PAR-GEO-0001` wheelbase | `1562 mm` | `1.562 m`, `QTY-GEO-0001` | Inactive specification observation; nominal configuration uses the reviewed OptimumK value where stated. |
| `PAR-ALIGN-0001` front axle sum toe | `-1.00 deg` | `-0.017453292519943295 rad`, `QTY-ALIGN-0003` | Inactive axle-sum observation; it does not define two per-wheel headings. |
| `PAR-STEER-0001` rack displacement per pinion revolution | `88.9 mm/rev` | `0.014148874440869498 m/rad`, `QTY-STEER-0005` | Design-source transmission observation; installed staged measurement remains open. |
| `PAR-STEER-0002` through-center ratio | `3.12:1` | none accepted | Rejected historical observation. |

## Corrected nominal rack-study observation

The original seed interpreted `1.00 in` as total rack travel and derived `+/-0.50 in`. That interpretation is obsolete.

The team clarified that the nominal CAD design study permits approximately:

```text
one-sided displacement = +/-1.00 in = +/-25.4 mm = +/-0.0254 m
total nominal span      = 2.00 in = 50.8 mm = 0.0508 m
```

`PAR-STEER-0003` is active for the nominal design-source study domain. The exported `-102 deg` to `+102 deg` scenarios cover approximately `-25.1883 mm` to `+25.1883 mm`. Neither value proves the installed physical stop positions.

## Frozen nominal geometry and alignment

`WUFR26_DESIGN_NOMINAL_V0` contains the current nominal-design authority:

- steering-axis construction from the final OptimumK source;
- steering-specific tie-rod points from the FDR final table;
- exact mirrored CAD right-side geometry;
- centered rack point `[-0.079298, 0, 0.162865] m` in the canonical frame;
- static toe `-1.00 deg` per side under the reviewed local-side toe-out convention;
- static camber `-2.25 deg` per side;
- CAD export tolerances of `+/-0.005 in` and `+/-0.1 deg` as source/export tolerances only.

These values are frozen for nominal steering-system development. They are not installed or as-built measurements.

## Physical observations

### Whole-system free play

`PAR-STEER-0004` records the latest approximate observation:

```text
4.0 deg total at the steering wheel
vehicle stationary with the front tires scrub-constrained
```

This value may include quick release, column couplings, bevel gears, rack/pinion, rack support, rod ends, tie rods, upright/bearing motion, tire scrub, and measurement threshold. Supplier backlash must not be added to it.

### Historical compliance

`PAR-STEER-0005` and `PAR-STEER-0006` preserve directional historical values:

```text
0.26 deg/N*m
0.47 deg/N*m
```

The directional difference is retained. These values are benchmark/test-method evidence until setup, calibration, repeatability, and state are fully recovered.

## Baseline setup observations retained without active mapping

| Source field | Value | Use | Restriction |
|---|---:|---|---|
| Front tread-center track | `1232 mm` | Geometry consistency | Not steering-axis ground-intersection track. |
| Front static camber | `-2.25 deg` | Nominal setup source | Installed shim stack and measured state remain separate. |
| Caster / KPI | `2.51 deg / 8.6 deg` | Axis consistency | Scalars do not replace the reviewed steering-axis line. |
| Trail / scrub radius | `6.89 mm / 5.06 mm` | Geometry and force cross-check | Setup and sign definitions must stay explicit. |
| Steering-arm length | `69.9 mm` | Packaging consistency | Does not replace axis and outer-joint coordinates. |
| Static Ackermann | `67.7%` | Historical/report evidence | Percentage definition remains unresolved. |
| Front wheel/tire | `10 x 7 in`, `18 x 7.5-10` | Envelope/setup evidence | Installed revision, pressure, and load state remain required for physical testing. |

## Important non-equivalences

- Tread-center track is not Ackermann track.
- Axle sum toe is not two per-wheel toe values.
- A center ratio is not the complete steering map.
- C-factor is not installed steering-wheel-to-wheel ratio.
- Nominal CAD travel is not installed stop travel.
- CAD export tolerance is not fabrication uncertainty or validation tolerance.
- Supplier gear backlash is not whole-system steering free play.
- Deadband is not elastic compliance.
- Agreement with design sources is not physical validation.

## Current resolution path

1. Keep the nominal geometry and Level E result frozen for design-source development.
2. Calibrate and link the installed rack linear potentiometer.
3. Select, install, and calibrate the primary-shaft rotary potentiometer.
4. Measure installed stops and staged primary-shaft-to-rack behavior.
5. Measure left/right wheel heading at selected rack positions with the digital angle gauge.
6. Retain directional deadband, hysteresis, compliance, and repeatability separately.
7. Define a Level F acceptance rule independently of observed residuals.

## Closeout decision

The observation seed exit criterion is satisfied: recovered values are preserved with source role, units, uncertainty, applicability, and explicit active-value boundaries. New measurements may add or supersede parameter records without reopening the observation-governance seed unless the governance model itself changes.
