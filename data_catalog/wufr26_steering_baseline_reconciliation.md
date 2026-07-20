# WUFR-26 Steering Baseline Reconciliation

**Status:** Baseline intent and scalar observations reconciled; active spatial geometry export required  
**Vehicle:** WUFR-26  
**Related IDs:** `MOD-STEER-0001`, `BENCH-STEER-0001`, `CAT-STEER-SPEC-0001`, `PAR-STEER-0001` through `PAR-STEER-0003`, `RISK-STEER-0001`

## Purpose

This packet records the intended WUFR-26 reference model, current setup evidence, prohibited values, the relationship between the final geometry study and the real assembly, and the exact SolidWorks export required before active geometry can be frozen. It does not activate geometry or authorize physics implementation.

## Baseline model intent

The active WUFR-26 steering model is intended to represent the real/as-built or competition-intended steering assembly at a declared nominal setup.

`GEOMETRY FINAL.SLDPRT` is a component inside the fuller linkage subassembly rather than an unrelated standalone concept. It remains the selected Test 3 mechanism-study source and parent of the final motion response. The active assembly configuration, mates, shims, adjustable lengths, and stops determine whether the installed state exactly reproduces that study.

The design-study response and the active production geometry are connected evidence layers. Agreement must be checked, not assumed.

## Primary specification source

| Field | Value |
|---|---|
| File | `2026_FSAE_Design_IC_Spec_Sheet_WashU_Racing.xlsx` |
| Box file ID | `2149814001036` |
| Box file version ID | `2510738677599` |
| Provider SHA-1 | `588669d320ff8097ec0bc85a85a970640d5a4d38` |
| Modified | `2026-06-06T04:43:43Z` |
| Size | `45432` bytes |
| Storage | `WashURacing / 6. WUFR-26 / Spec Sheet` |
| Evidence role | Reported design/setup intent; not automatic as-built authority |

Project SHA-256 remains pending immutable-byte capture.

## Recovered reference observations

| Item | Reported value | Current treatment |
|---|---:|---|
| Wheelbase | `1562 mm` | Inactive candidate observation |
| Front tread-center track | `1232 mm` | Consistency evidence; not Ackermann track |
| Front axle sum toe | `-1.00 deg` | Left/right split unresolved |
| Front static camber | `-2.25 deg` | Shim stack unresolved |
| Caster / KPI | `2.51 deg / 8.6 deg` | Axis consistency evidence |
| Trail / scrub radius | `6.89 mm / 5.06 mm` | Derived-geometry consistency evidence |
| Spindle offset | `22.0 mm` | Geometry consistency evidence |
| Steering-arm length | `69.9 mm` | Scalar consistency evidence only |
| C-factor | `88.9 mm/rev` | Inactive pending rack/pinion verification |
| Static Ackermann | `67.7%` | Unresolved metric; not an optimizer target |
| Front wheel | `10 x 7 in`, `22 mm offset` | Reference wheel evidence |
| Front tire | `18 x 7.5-10 Hoosier R20` | Reference tire envelope |
| Camber adjustment | Shims | Nominal stack unresolved |
| Nominal ride height | Not recovered | Required reference-configuration field |

## Rejected steering-ratio value

The specification's `3.12:1` steering ratio is known to be wrong. It is retained as `PAR-STEER-0002` solely for discrepancy lineage. It cannot be used as an active parameter, benchmark expectation, optimizer target, validation reference, or substitute for the full steering map.

The replacement ratio must be derived from explicit transmission definitions and the local mechanism derivative at a declared rack-center state.

## Rack center and travel

Rack center is the midpoint between equal left and right displacement limits imposed by the installed stops. The team reports `1.00 in` current total rack travel. The provisional interpretation is:

```text
total travel = 1.00 in = 25.4 mm
one-sided displacement = 0.50 in = 12.7 mm
provisional signed domain = [-0.0127 m, +0.0127 m]
```

This is recorded as `PAR-STEER-0003`. It remains inactive until active CAD or direct measurement confirms total versus one-sided meaning, mechanical versus operational travel, equal stop contact, the displacement reference feature, and tolerance.

## Rack-family identity clarification

Current individual drawings establish:

| Drawing | Identity |
|---|---|
| `ST-60306-AA` | Steering rack |
| `ST-60307-AA` | Steering pinion |
| `ST-60308-AA` | Rack housing |
| `ST-60309-AA` | Steering potentiometer extension |
| `ST-60310-AA` | Steering potentiometer mount |

The rack is purchased as one assembly for the steering BOM, while the cost report requires separate component drawings. Their omission from the assembly BOM is therefore a scope issue, not evidence that the current identities are invalid. Older assignments remain historical evidence. The active assembly reference export is still required to establish the exact instantiated files and configurations.

## Supplemental-source status

A 2026 suspension design binder and 2026 design briefing were identified as supplemental sources. Direct Google Drive search was unavailable during this reconciliation, and no reliable exact Box match was established. These sources do not block the current packet.

## SolidWorks export blocker

The remaining blocker is native assembly state. Export from the active WUFR-26 vehicle/steering configuration:

### Identity and configuration

- SolidWorks version;
- top-level and steering-subassembly filenames;
- active configuration names;
- component references and suppression states;
- exact `GEOMETRY FINAL.SLDPRT` component instance;
- rebuild warnings or missing references;
- units and coordinate-system definition.

### Geometry in one declared right-handed vehicle frame

| Object | Required export |
|---|---|
| Left/right steering axes | two points each, or point plus unit direction |
| Left/right outer tie-rod joints | spherical-joint centers at nominal setup |
| Rack axis | point plus directed unit vector |
| Left/right inner tie-rod joints | centers at rack center |
| Left/right stop states | rack displacement and contacting features |
| Pinion relation | pinion angle and signed rack displacement, preferably a small sweep |
| Left/right wheel planes | forward and normal vectors at rack center |
| Road plane | origin and normal, or three points |
| Axle centers | front and rear reference-center construction |
| Installed tie rods | left/right joint-center distances |

### Setup metadata

- left/right toe and camber;
- camber-shim stack;
- ride height and wheel-travel state;
- roll, pitch, and heave state;
- wheel/tire configuration;
- tie-rod adjustment and thread engagement;
- rack-center construction;
- whether compliance loads are absent.

A CSV or XLSX is sufficient. Coordinate rows should include object ID, side, role, x/y/z in millimetres, frame, configuration, source feature, source file, and notes. Screenshots may supplement but cannot replace numerical coordinates.

## Work status

Source cleanup, rejected-value controls, analytical benchmarks, CSV transformation definitions, physical sweep planning, and authorization drafting remain unblocked. Active car-specific geometry, CAD reproduction, and code using WUFR-26 hardpoints remain blocked until this export is reviewed.
