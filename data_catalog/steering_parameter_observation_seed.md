# WUFR-26 Steering Parameter-Observation Seed

**Status:** Candidate, rejected, and provisional observations; no value is active by appearing here  
**Primary source:** `CAT-STEER-SPEC-0001`  
**Vehicle revision:** WUFR-26  
**Related model:** `MOD-STEER-0001`

## Purpose

This seed converts steering-relevant values from the WUFR-26 design specification and team configuration clarifications into traceable observations while preserving source definitions and unresolved mappings. The specification is useful design-intent evidence. It does not replace active CAD geometry, drawings, setup records, or physical measurement.

## Direct canonical candidates

| Observation | Source-native value | Canonical candidate | Authority state | Main restriction |
|---|---:|---:|---|---|
| `PAR-GEO-0001` wheelbase | `1562 mm` | `1.562 m`, `QTY-GEO-0001` | Inactive observation | Built/setup uncertainty not provided |
| `PAR-ALIGN-0001` front axle sum toe | `-1.00 deg` | `-0.017453292519943295 rad`, `QTY-ALIGN-0003` | Inactive observation | Does not determine left/right split |
| `PAR-STEER-0001` rack displacement per pinion angle | `88.9 mm/rev` | `0.014148874440869498 m/rad`, `QTY-STEER-0005` | Inactive observation | Reconcile with rack geometry or measurement |
| `PAR-STEER-0003` one-sided rack bound | `1.00 in total travel` | provisional `+/-0.0127 m`, `QTY-STEER-0004` | Inactive provisional observation | Confirm total-versus-operational travel and installed stop state |

The C-factor conversion is:

```text
88.9 mm/rev = 0.0889 m / (2*pi rad) = 0.014148874440869498 m/rad
```

The rack-travel conversion is:

```text
1.00 in total travel = 25.4 mm total travel
centered symmetric interpretation = +/-12.7 mm = +/-0.0127 m
```

Both are unit conversions or interpretations of reported observations, not independent evidence.

## Rejected steering-ratio report value

`PAR-STEER-0002` preserves the design-spec value `3.12:1` only as a rejected historical observation. The team has confirmed that this value is wrong. It is prohibited from:

- active vehicle configurations;
- benchmark expected values;
- optimizer targets or constraints;
- validation claims;
- replacement of the full steering input-to-road-wheel map.

The replacement center ratio will be derived from the reviewed steering-wheel/shaft/pinion transmission and the rigid mechanism derivative at a declared rack-center setup.

## Baseline setup observations retained without active mapping

| Source field | Value | Use | Why not active yet |
|---|---:|---|---|
| Front track | `1232 mm` | Geometry evidence | Defined at tread centers, not steering-axis ground intersections |
| Front axle sum toe | `-1.00 deg` | Setup evidence | Per-wheel split and as-built uncertainty unresolved |
| Front static camber | `-2.25 deg` | Reference-configuration evidence | Exact shim stack and measured as-built state unresolved |
| Caster | `2.51 deg` | Steering-axis consistency check | Insufficient without an axis point and frame |
| KPI | `8.6 deg` | Steering-axis consistency check | Same limitation as caster |
| Kinematic trail | `6.89 mm` | Future geometry/effort check | Reference construction requires confirmation |
| Scrub radius | `5.06 mm` | Future geometry/effort check | Setup state and sign not established |
| Spindle offset | `22.0 mm` | Geometry consistency check | Frame and sign remain incomplete |
| Static Ackermann | `67.7%` | Historical/report comparison | Percentage definition and evaluation angle unresolved |
| Steering-arm length | `69.9 mm` | Packaging and consistency check | Scalar length does not replace axis and point geometry |
| Front wheel | `10 x 7 in`, `22 mm offset` | Reference wheel/clearance evidence | Exact installed wheel revision and coordinate reference still need confirmation |
| Front tire | `18 x 7.5-10 Hoosier R20` | Reference tire envelope | Inflation/load state not specified here |
| Front camber adjustment | `shims` | Configuration method | Does not identify nominal shim stack |
| Ackermann adjustable | `No` | Configuration statement | Does not define the actual geometry or metric |

No nominal ride-height value was recovered from the extracted specification content. Ride height remains an open reference-configuration field.

## Geometry-source clarification

The active WUFR-26 model is intended to represent the real/as-built steering geometry. `GEOMETRY FINAL.SLDPRT` is a component within the fuller linkage subassembly, so its design-study lineage and the installed-assembly lineage are connected. They still require an explicit active-configuration export because mates, shims, stops, adjustment, and vehicle setup determine the installed state.

Rack center is defined operationally as the midpoint between equal left and right displacement limits imposed by the installed stops. The current reported travel is 1.00 in total. Until the active SolidWorks assembly or a direct measurement confirms it, the resulting `+/-0.50 in` bound remains provisional.

## Important non-equivalences

- Tread-center front track is not Ackermann track.
- Axle sum toe is not two per-wheel toe values.
- The rejected `3.12:1` value is not evidence for the correct center ratio.
- A center ratio is not the complete steering map.
- A recovered C-factor definition is not yet a validated installed value.
- Total rack travel, one-sided travel, and signed displacement from center are separate quantities.
- A manufactured stop dimension is not the installed travel limit by itself.
- Agreement with a design specification is consistency evidence, not physical validation.

## Recommended resolution order

1. Export the active SolidWorks configuration, component references, and declared vehicle coordinate system.
2. Export rack axis, centered inner-joint points, left/right stop states, and pinion-to-rack relation.
3. Export steering-axis lines and outer tie-rod joint centers.
4. Record nominal toe, camber shim stack, ride height, wheel/tire state, and installed tie-rod lengths.
5. Derive the center steering ratio from the reviewed transmission plus mechanism; do not compare against `3.12:1` as an expected value.
6. Derive steering-axis ground-intersection track from the steering-axis lines and road plane.
7. Keep `67.7% Ackermann` unresolved until its metric is recovered.

## Downstream restrictions

Candidate and provisional observations may populate review and comparison tables. They may not silently become active solver inputs. Rejected observations remain preserved for lineage but cannot be used numerically downstream. The evaluator may use a value only through a reviewed configuration/active-value record, and the optimizer may not target the reported Ackermann percentage until that metric is defined.
