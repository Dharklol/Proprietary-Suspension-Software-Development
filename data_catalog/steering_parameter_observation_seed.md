# WUFR-26 Steering Parameter-Observation Seed

**Status:** Candidate observations; no value is active by appearing here  
**Primary source:** `CAT-STEER-SPEC-0001`  
**Vehicle revision:** WUFR-26  
**Related model:** `MOD-STEER-0001`

## Purpose

This seed converts the steering-relevant values from the WUFR-26 design specification into traceable observations while preserving the source definitions and unresolved mappings. The source is a current design specification and is useful design-intent evidence. It is not a substitute for CAD geometry, drawings, setup records, or physical measurement.

## Direct canonical candidates

| Observation | Source-native value | Canonical candidate | Mapping status | Authority state | Main restriction |
|---|---:|---:|---|---|---|
| `PAR-GEO-0001` wheelbase | `1562 mm` | `1.562 m`, `QTY-GEO-0001` | Compatible with source definition of longitudinal wheel-center spacing | Inactive candidate observation | Built-car/setup uncertainty not provided |
| `PAR-ALIGN-0001` front axle sum toe | `-1.00 deg` | `-0.017453292519943295 rad`, `QTY-ALIGN-0003` | Compatible with source-defined axle sum toe and sign | Inactive candidate observation | Does not determine left/right split |
| `PAR-STEER-0001` rack displacement per pinion angle | `88.9 mm/rev` | `0.014148874440869498 m/rad`, `QTY-STEER-0005` | Definition recovered explicitly | Inactive candidate observation | Effective/installed value must be reconciled with rack geometry or measurement |
| `PAR-STEER-0002` center handwheel ratio | `3.12:1` | `3.12`, `QTY-STEER-0010` candidate | Source defines handwheel angle divided by average left/right road-wheel angle through center | Inactive candidate observation | Confirm derivative method, arithmetic averaging, toe treatment, and column/u-joint state |

The C-factor conversion is:

```text
88.9 mm/rev
= 0.0889 m / (2*pi rad)
= 0.014148874440869498 m/rad
```

This is a derived unit conversion of the same observation, not independent evidence.

## Source-native observations retained without direct active mapping

| Source field | Value | Proposed use | Why it is not yet a canonical active parameter |
|---|---:|---|---|
| Front track | `1232 mm` | Geometry evidence | Source defines center of tread to center of tread. It is not steering-axis ground-intersection track and should not feed exact Ackermann without a reviewed transformation. |
| Static Ackermann | `67.7%` | Historical/report comparison | Percentage definition and evaluation angle are unresolved. |
| Steering-arm length | `69.9 mm` | Packaging and consistency check | Scalar distance does not replace the steering-axis line and outer tie-rod joint point. |
| Caster | `2.51 deg` | Steering-axis consistency check | Caster plus KPI remains insufficient without an axis point and frame/reference plane. |
| KPI | `8.6 deg` | Steering-axis consistency check | Same limitation as caster. |
| Kinematic trail | `6.89 mm` | Future effort and geometry check | Reference plane and construction must be confirmed. |
| Scrub radius | `5.06 mm` | Future effort and geometry check | Reference tire/wheel/setup state and sign are not stated in the extracted value. |
| Spindle offset | `22.0 mm` | Geometry consistency check | Source definition is lateral kingpin-axis to wheel-center distance; frame/sign remain incomplete. |
| Ackermann adjustable | `No` | Configuration statement | Does not define the actual geometry or metric. |
| Adjustment method | tie-rod turnbuckle and rack-travel adjustment | Service/setup context | Adjustment range, thread engagement, and stops remain separate evidence items. |

## Important non-equivalences

### Front track is not Ackermann track

The specification's front track is based on tread centers. `QTY-GEO-0004` is the distance between steering-axis intersections with the selected road plane. Exact low-speed Ackermann must use the reviewed definition required by its equation card, not whichever track number is easiest to find.

### Axle sum toe is not two per-wheel values

The source reports front **sum toe** of `-1.00 deg`. No left/right split is stated. A symmetric setup would imply `-0.5 deg` per wheel only under a separately declared symmetry assumption and the project's per-wheel toe sign convention. That inferred split has not been created as an observation.

### Center ratio is not the complete steering map

`3.12:1` is a useful through-center summary. It does not replace:

- steering-wheel-to-pinion relation;
- rack displacement versus pinion angle;
- left and right road-wheel functions;
- angle-dependent local ratio;
- secant ratio over a finite interval;
- compliance/backlash/u-joint effects.

It should later become a cross-check against the derivative of the complete reviewed transmission and mechanism model.

### C-factor definition is recovered, not fully validated

The source explicitly defines C-factor as effective rack travel per revolution of the steering input/pinion shaft. This resolves the terminology question for the WUFR-26 design sheet. The numerical value remains a reported design observation until reconciled with the rack/pinion CAD, drawing, or direct measurement.

## Proposed active-value decisions

No active-value selection is made in this seed.

Recommended resolution order:

1. use the wheelbase observation as a candidate for the WUFR-26 reference configuration after checking the current CAD/spec revision;
2. reconcile C-factor with pinion/rack geometry or a measured input-to-rack sweep;
3. derive the center steering ratio from the reviewed transmission plus rigid mechanism and compare it to `3.12:1`;
4. recover the actual left/right static toe setup or declare a symmetric split for a named design configuration;
5. derive steering-axis ground-intersection track from the current steering-axis lines and road plane rather than from tread-center track;
6. retain the reported Ackermann percentage only as a legacy/specification observation until its definition is recovered.

## Downstream use restrictions

- These observations may populate review tables and benchmark comparisons.
- They may not silently become active solver inputs.
- The rigid evaluator may use them only through a reviewed configuration/active-value record.
- The optimizer may not tune geometry to reproduce the reported `67.7%` Ackermann value until that metric is defined.
- Agreement between a model and the design sheet is consistency evidence, not physical validation.