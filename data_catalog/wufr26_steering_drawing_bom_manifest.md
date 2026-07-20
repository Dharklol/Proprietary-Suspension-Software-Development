# WUFR-26 Steering Drawing and BOM Authority Manifest

**Status:** Source hierarchy and current rack-family identities established; active geometry export remains open  
**Related IDs:** `MIG-STR-0001`, `MOD-STEER-0001`, `BENCH-STEER-0001`, `PAR-STEER-0001` through `PAR-STEER-0003`, `RISK-STEER-0001`

## Purpose

This manifest records how WUFR-26 steering assembly numbers, part numbers, Box folders, drawings, CAD files, design geometry, and BOM tables relate. It prevents an old drawing, incomplete BOM, similarly named copy, or scalar specification from silently becoming parameter authority.

It does not yet freeze mechanism hardpoints, steering-axis lines, installed rack travel, tie-rod joint-center length, or nominal setup.

## Drawing-number convention

The WUFR-26 drawing standard uses the general form:

```text
SYSTEM-ASSEMBLYCOMPONENT-REVISION
```

For steering assemblies, `ST-A0603-AA` denotes steering subsystem, assembly marker, assembly family/component group, and revision. Part drawings omit the assembly marker, for example `ST-60305-AA`. Number identity must be paired with revision, source file, date, and assembly context.

## Steering-system hierarchy

The Box root is:

```text
WashURacing/
  6. WUFR-26/
    WUFR-26 CAD AND DRAWINGS/
      6. STEERING/
```

The top-level `FSA STEERING.pdf` maps:

| Assembly number | Component group | Box folder |
|---|---|---|
| `ST-A0601-AA` | Steering wheel | `601. STEERING WHEEL` |
| `ST-A0602-AA` | Quick release | `602. QUICK RELEASE` |
| `ST-A0603-AA` | Steering rack | `603. STEERING RACK` |
| `ST-A0604-AA` | Steering column | `604. STEERING COLUMN` |
| `ST-A0605-AA` | Tie rods | `605. TIE RODS` |
| `ST-A0606-AA` | Sensor mounts | no separate numbered root folder observed |

Top-level sources:

| Artifact | Box ID | Provider SHA-1 | Role |
|---|---:|---|---|
| `FSA STEERING.pdf` | `2173006511727` | `858830e3a9e21196ac1f2b5d66a6c3ee41a2069e` | Top-level BOM and identity |
| `FSA STEERING.SLDASM` | `1966633770970` | `148077e46af721cda86aba59ec563779a7d0bbe6` | Top-level CAD candidate |
| `FSA STEERING.SLDDRW` | `2173006542918` | `ba623bce14ba30b4f1965c7174efbea42576b97b` | Drawing source |

Provider SHA-1 supports discovery. Freeze requires immutable-byte capture and project SHA-256.

## Authority rules

### Component identity and assembly membership

1. Current reviewed assembly CAD and active configuration.
2. Matching current assembly drawing/BOM.
3. Current part drawing with matching part and revision.
4. System-level assembly drawing.
5. Folder and filename.
6. Historical copies and email-suffixed files.

### Manufacturing features and tolerances

1. Current released part drawing.
2. Drawing note or model-based definition referenced by that drawing.
3. CAD for undimensioned geometry only where the drawing makes CAD controlling.
4. Assembly measurement as a consistency check.

### Steering mechanism geometry

1. Active WUFR-26 vehicle/steering assembly configuration for the real installed reference state.
2. `GEOMETRY FINAL.SLDPRT` as the selected Test 3 mechanism-study component within the fuller linkage subassembly.
3. Current rack, tie-rod, upright, and mounting drawings for manufactured features and tolerances.
4. `2026Ackermann.csv` for final motion-response comparison.
5. Design specifications and scalar summaries as consistency evidence.

A part drawing may control a feature while the installed hardpoint still depends on mates, shims, adjustment, and setup.

## Steering-rack assembly

The preferred current assembly candidate is:

| Artifact | Box ID | Provider SHA-1 | Last modified |
|---|---:|---|---|
| `ST-A0603-AA STEERING RACK.SLDASM` | `1966632771950` | `65c463472819d7c467b5117ba4f687326c9620ab` | 2026-07-01 |

Older creator-email-suffixed copies remain historical until proven identical.

Current rack-family drawings are:

| Part number | Identity |
|---|---|
| `ST-60301-AA` | Top rack mount |
| `ST-60302-AA` | Bottom rack mount |
| `ST-60303-AA` | Rack tab right |
| `ST-60304-AA` | Rack tab left |
| `ST-60305-AA` | Steering rack stop |
| `ST-60306-AA` | Steering rack |
| `ST-60307-AA` | Steering pinion |
| `ST-60308-AA` | Rack housing |
| `ST-60309-AA` | Steering potentiometer extension |
| `ST-60310-AA` | Steering potentiometer mount |

The user-confirmed current folder listing and the individual drawings establish these identities. The rack is purchased and treated as one assembly in the steering BOM, while the cost report requires the purchased rack to be costed through separate component drawings. Therefore omission of `60306` through `60310` from the assembly BOM is a scope/version limitation, not evidence of obsolete current identities.

The older January rack assembly PDF remains historical/incomplete identity evidence. It cannot override the current drawing family. The active assembly reference export is still needed to prove which files and configurations are instantiated.

The design-spec C-factor remains inactive. Rack, pinion, and `13T` names do not alone establish effective displacement per revolution, sign, backlash, or installed travel.

## Tie-rod assembly

`ST-A0605-AA TIE RODS.pdf` maps:

| Part or hardware | Quantity | Role |
|---|---:|---|
| `ST-60501-AA` carbon tube | 2 | Structural tube |
| `ST-60502-AA` right-thread end cap | 2 | Bonded/threaded insert |
| `ST-60503-AA` left-thread end cap | 2 | Bonded/threaded insert |
| McMaster `94450A220` | 2 | Left-hand jam nut |
| McMaster `91847A429` | 2 | Right-hand jam nut |
| QA1 `XML4`, 0.25-28 LH | 2 | Left-hand rod end |
| QA1 `XMR4`, 0.25-28 RH | 2 | Right-hand rod end |

Source artifacts:

| Artifact | Box ID | Provider SHA-1 | Observation |
|---|---:|---|---|
| `ST-A0605-AA TIE RODS.pdf` | `2149995344555` | `b9e3efdbbbe192dfb4e429f797ddab4223601a24` | Assembly BOM |
| `ST-60501-AA TIE ROD CARBON TUBE.pdf` | `2149965223032` | `a1c857848e718651c3c3972b9d53a6635b1a166e` | 10.68-in tube dimension |
| `ST-60502-AA ... RIGHT THD.pdf` | `2074338764725` | `22a9f0cda2858fae59be39f83487e6b0d6dffbdd` | Right-thread end cap |
| `ST-60503-AA ... LEFT THD.pdf` | `2074343903141` | `652b4077ec7bdbc3cb749c26b9eca174374d7b2e` | Left-thread end cap |

The assembly is adjustable. Tube length is not installed joint-center length. End caps, rod ends, thread engagement, jam nuts, and toe determine `QTY-STEER-0012`.

The extracted right-thread end-cap title block appears to show `SU-60502-AA`, while the file and assembly BOM use `ST-60502-AA`. This remains a likely title-block prefix error pending source-CAD confirmation.

## Front upright and outer pickup

| Artifact | Box ID | Provider SHA-1 | Role |
|---|---:|---|---|
| `WT-A0802-AA FRONT UPRIGHTS.SLDASM` | `1966638198050` | `dee3e4b7add775e55c43013338e483ff30471c9b` | Preferred upright assembly candidate |
| `WT-A0802-AA FRONT UPRIGHTS.pdf` | `2173006792564` | `b3eba618789b2a53df432e81cb556a35efc2958e` | Assembly BOM |
| `WT-80201-ZZ CNC UPRIGHT, FRONT, RIGHT.pdf` | `2071451248395` | `74a6afa2b8d712f240a84f2b864f1771cb382491` | Right upright drawing |
| `WT-80204-ZZ CNC UPRIGHT, FRONT, LEFT.pdf` | `2090703733428` | `cb4ce8110264ac73b2e798befa536e3976e17078` | Left upright drawing |

The upright drawings defer undimensioned features to CAD. The authoritative steering inputs are the steering-axis lines and outer joint centers, not the reported 69.9-mm steering-arm scalar.

## Final study and real assembly relationship

The selected lineage is:

1. Steering FDR selects Test 3.
2. `GEOMETRY FINAL.SLDPRT` is the selected mechanism-study source and is a component within the fuller linkage subassembly.
3. `2026Ackermann.csv` is the primary final motion response.
4. `Test_3.csv` is a selection-era cross-check.
5. `Steering Length Optimization Tests.xlsx` records supporting design intent.
6. The active assembly/configuration defines the real/as-built reference state.

The design-study and installed-assembly chains are linked, but mates, shims, stops, adjustments, and final setup must be exported before identity becomes active geometry.

## Rack-center and travel observation

Rack center is the midpoint between equal left/right stop-limited displacement. The team reports 1.00 in total rack travel. `PAR-STEER-0003` records the provisional symmetric interpretation of `+/-0.50 in` (`+/-0.0127 m`). It is not active until the installed or active-CAD stop state confirms the meaning and tolerance.

## Required reconciliation before active geometry

1. Export active configurations, component references, suppression states, and warnings from the vehicle, steering, rack, tie-rod, and upright assemblies.
2. Match every active component to part number, revision, source file, and provider hash.
3. Confirm the `ST-60306` through `ST-60310` active component references.
4. Resolve the `SU-60502-AA` versus `ST-60502-AA` title-block mismatch.
5. Export left/right steering-axis lines and outer tie-rod centers.
6. Export rack axis, centered inner joints, stop states, and pinion-to-rack relation.
7. Export installed tie-rod joint-center lengths and safe adjustment/thread-engagement limits.
8. Record nominal toe, camber, shim stack, ride height, wheel/tire, and rack-center setup.
9. Compare active assembly geometry with `GEOMETRY FINAL.SLDPRT` and explain differences.
10. Capture immutable bytes and SHA-256 for frozen sources.

The detailed export request is in `data_catalog/wufr26_steering_baseline_reconciliation.md`.

## Use restrictions

- Folder organization and filenames are discovery aids, not installed-geometry authority.
- A BOM establishes identity only for its stated scope and revision.
- Cost-report component drawings may legitimately be absent from a purchased-assembly BOM.
- A part drawing does not establish installed hardpoints without assembly state and adjustment.
- The rejected `3.12:1` steering ratio cannot be used downstream.
- Provider SHA-1 is not the project freeze hash.
- No active steering geometry is selected by this manifest.
