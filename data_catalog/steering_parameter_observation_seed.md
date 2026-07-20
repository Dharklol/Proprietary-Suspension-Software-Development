# WUFR-26 Steering Parameter-Observation Seed

**Status:** Candidate observations; no value is active by appearing here  
**Primary source:** `CAT-STEER-SPEC-0001`  
**Vehicle revision:** WUFR-26  
**Related model:** `MOD-STEER-0001`

## Purpose

This seed converts steering-relevant values from the WUFR-26 design specification into traceable observations while preserving source definitions and unresolved mappings. The specification is useful design-intent evidence. It does not replace CAD geometry, drawings, setup records, or physical measurement.

## Direct canonical candidates

| Observation | Source-native value | Canonical candidate | Authority state | Main restriction |
|---|---:|---:|---|---|
| `PAR-GEO-0001` wheelbase | `1562 mm` | `1.562 m`, `QTY-GEO-0001` | Inactive observation | Built/setup uncertainty not provided |
| `PAR-ALIGN-0001` front axle sum toe | `-1.00 deg` | `-0.017453292519943295 rad`, `QTY-ALIGN-0003` | Inactive observation | Does not determine left/right split |
| `PAR-STEER-0001` rack displacement per pinion angle | `88.9 mm/rev` | `0.014148874440869498 m/rad`, `QTY-STEER-0005` | Inactive observation | Reconcile with rack geometry or measurement |
| `PAR-STEER-0002` center handwheel ratio | `3.12:1` | `3.12`, `QTY-STEER-0010` candidate | Inactive observation | Confirm derivative, average, toe, and column definitions |

The C-factor conversion is:

```text
88.9 mm/rev = 0.0889 m / (2*pi rad) = 0.014148874440869498 m/rad
```

This is a unit conversion of the same observation, not independent evidence.

## Source-native observations retained without direct active mapping

| Source field | Value | Use | Why not active yet |
|---|---:|---|---|
| Front track | `1232 mm` | Geometry evidence | Defined at tread centers, not steering-axis ground intersections |
| Static Ackermann | `67.7%` | Historical/report comparison | Percentage definition and evaluation angle unresolved |
| Steering-arm length | `69.9 mm` | Packaging and consistency check | Scalar length does not replace axis and point geometry |
| Caster | `2.51 deg` | Steering-axis consistency check | Insufficient without an axis point and frame |
| KPI | `8.6 deg` | Steering-axis consistency check | Same limitation as caster |
| Kinematic trail | `6.89 mm` | Future geometry/effort check | Reference construction requires confirmation |
| Scrub radius | `5.06 mm` | Future geometry/effort check | Setup state and sign not established |
| Spindle offset | `22.0 mm` | Geometry consistency check | Frame and sign remain incomplete |
| Ackermann adjustable | `No` | Configuration statement | Does not define the actual geometry or metric |

## Important non-equivalences

- Tread-center front track is not Ackermann track.
- Axle sum toe is not two per-wheel toe values.
- A center ratio is not the complete steering map.
- A recovered C-factor definition is not yet a validated installed value.
- Agreement with a design specification is consistency evidence, not physical validation.

## Recommended resolution order

1. Check wheelbase against the current CAD axle-center definition.
2. Reconcile C-factor with rack/pinion CAD, drawings, BOM-linked part identity, or direct measurement.
3. Derive center steering ratio from the reviewed transmission plus mechanism and compare it with `3.12:1`.
4. Recover actual left/right static toe or approve a named symmetric setup assumption.
5. Derive steering-axis ground-intersection track from the steering-axis lines and road plane.
6. Keep `67.7% Ackermann` as an unresolved legacy/specification observation until its metric is recovered.

## Downstream restrictions

These observations may populate review and benchmark tables. They may not silently become active solver inputs. The evaluator may use them only through a reviewed configuration/active-value record, and the optimizer may not target the reported Ackermann percentage until that metric is defined.
