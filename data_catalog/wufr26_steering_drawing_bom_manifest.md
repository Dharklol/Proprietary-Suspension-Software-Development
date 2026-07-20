# WUFR-26 Steering Drawing and BOM Authority Manifest

**Status:** Source hierarchy established; geometry extraction and revision freeze remain open  
**Related IDs:** `MIG-STR-0001`, `MOD-STEER-0001`, `BENCH-STEER-0001`, `PAR-STEER-0001`, `PAR-STEER-0002`, `RISK-STEER-0001`

## Purpose

This manifest records how WUFR-26 steering assembly numbers, part numbers, Box folders, drawings, CAD files, design geometry, and BOM tables relate to one another. It prevents an old drawing, similarly named copy, or colloquial component name from silently becoming parameter authority.

The manifest is an identity and lineage document. It does not yet freeze mechanism hardpoints, steering-axis lines, rack travel, tie-rod joint-center length, or installed setup values.

## Drawing-number convention

The WUFR-26 drawing standard defines the general form:

```text
SYSTEM-ASSEMBLYCOMPONENT-REVISION
```

For steering files the observed team convention is:

```text
ST-A0603-AA
│  │ │ │  └─ revision
│  │ │ └──── steering component-group number
│  │ └────── steering system/assembly family 06
│  └──────── A indicates an assembly
└─────────── steering subsystem prefix
```

Part drawings omit the assembly marker and use the component sequence directly, for example `ST-60305-AA`. Assembly and component numbers are resolved using BOM tables and folder context rather than filename parsing alone.

The manufacturing drawing standard states that the BOM is the reference when changing a part number and that prior revisions must be preserved, especially after FDR. Therefore a part number without its revision, source file, and date is insufficient authority.

## Steering system hierarchy

The Box steering folder is:

```text
WashURacing/
  6. WUFR-26/
    WUFR-26 CAD AND DRAWINGS/
      6. STEERING/
```

The top-level steering assembly drawing `FSA STEERING.pdf` maps:

| Item | Assembly number | Component group | Box folder |
|---:|---|---|---|
| 1 | `ST-A0604-AA` | Steering column | `604. STEERING COLUMN` |
| 2 | `ST-A0605-AA` | Tie rods | `605. TIE RODS` |
| 3 | `ST-A0601-AA` | Steering wheel | `601. STEERING WHEEL` |
| 4 | `ST-A0602-AA` | Quick release | `602. QUICK RELEASE` |
| 5 | `ST-A0606-AA` | Sensor mounts | no separate numbered folder observed at the steering root |
| 6 | `ST-A0603-AA` | Steering rack | `603. STEERING RACK` |

Top-level source files:

| Artifact | Box file ID | Provider SHA-1 | Role |
|---|---:|---|---|
| `FSA STEERING.pdf` | `2173006511727` | `858830e3a9e21196ac1f2b5d66a6c3ee41a2069e` | Human-readable top-level BOM and assembly identity |
| `FSA STEERING.SLDASM` | `1966633770970` | `148077e46af721cda86aba59ec563779a7d0bbe6` | Top-level CAD assembly candidate |
| `FSA STEERING.SLDDRW` | `2173006542918` | `ba623bce14ba30b4f1965c7174efbea42576b97b` | SolidWorks drawing source |

Provider SHA-1 values support source discovery. Project benchmark freeze still requires immutable-byte capture and SHA-256.

## Source-authority hierarchy

Different source types govern different questions.

### Component identity and assembly membership

1. Current reviewed assembly CAD and its active configuration.
2. Current assembly drawing BOM matching that CAD revision.
3. Current part drawing with matching part and revision number.
4. System-level assembly drawing.
5. Folder name and filename.
6. Historical copies, email-suffixed files, and design-study files.

### Manufacturing dimensions and tolerances

1. Current released part drawing.
2. Explicit drawing note or model-based definition referenced by that drawing.
3. CAD model only for undimensioned geometry when the drawing explicitly makes the CAD model controlling.
4. Assembly-level measurement only as a consistency check.

### Steering mechanism geometry

1. `GEOMETRY FINAL.SLDPRT` for the selected WUFR-26 steering design study, after frame and feature identities are frozen.
2. Current installed steering/upright assembly CAD for production geometry and packaging.
3. Current manufacturing drawings for manufactured feature definitions and tolerances.
4. The selected motion-study response for cross-tool comparison.
5. Design specifications and historical scalar summaries as consistency evidence.

No one source is automatically authoritative for every purpose. A manufacturing drawing can control a part feature while the assembled hardpoint position still depends on mates, shims, adjustment, and vehicle setup.

## Steering rack assembly

The current canonical-looking assembly file is:

| Artifact | Box file ID | Provider SHA-1 | Last modified | Interpretation |
|---|---:|---|---|---|
| `ST-A0603-AA STEERING RACK.SLDASM` | `1966632771950` | `65c463472819d7c467b5117ba4f687326c9620ab` | 2026-07-01 | Preferred current assembly candidate pending active-configuration inspection |

Older copies with creator-email suffixes remain historical until proven identical. The rack assembly folder also includes `13T-17.4_NARRco_Rack_V2` assemblies and a `NARRco Rack` source folder.

The January `ST-A0603-AA STEERING RACK.pdf` BOM identifies:

- `13T-17.4_NARRco_Rack_V2`;
- top and bottom rack mounts;
- left and right rack tabs;
- two rack stops;
- NARRco rack, pinion, and simplified supplier components;
- steering potentiometer hardware.

Current rack drawing-family files include:

| Part number | Current drawing title |
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

The design-spec C-factor observation remains inactive. The NARRco component names and the `13T` label are useful identity evidence, but they do not by themselves establish pitch, effective rack displacement per pinion revolution, sign, backlash, or installed travel.

## Rack-source conflict

The January rack assembly PDF assigns `ST-60306-AA` and `ST-60307-AA` to steering-potentiometer components. The later/current drawing folder assigns those numbers to the steering rack and pinion, with potentiometer components moved to `ST-60309-AA` and `ST-60310-AA`.

This is a real revision/identity conflict, not a formatting detail. Until the active assembly CAD BOM is extracted and matched to current drawings:

- the January assembly PDF is historical identity evidence only;
- part numbers `60306` through `60310` cannot be resolved by the January PDF alone;
- no geometry or component parameter may cite those part numbers without the source date/revision;
- the current assembly CAD and current drawing family must be reconciled before active parameter selection.

## Tie-rod assembly

The tie-rod assembly drawing `ST-A0605-AA TIE RODS.pdf` maps:

| Item | Part or hardware | Quantity in axle assembly | Role |
|---:|---|---:|---|
| 1 | `ST-60501-AA` carbon tube | 2 | Main structural tube |
| 2 | `ST-60502-AA` right-thread end cap | 2 | Bonded/threaded insert |
| 3 | `ST-60503-AA` left-thread end cap | 2 | Bonded/threaded insert |
| 4 | McMaster `94450A220` | 2 | Left-hand jam nut |
| 5 | McMaster `91847A429` | 2 | Right-hand jam nut |
| 6 | QA1 `XML4`, 0.25-28 LH | 2 | Left-hand rod end |
| 7 | QA1 `XMR4`, 0.25-28 RH | 2 | Right-hand rod end |

Relevant source artifacts:

| Artifact | Box file ID | Provider SHA-1 | Observation |
|---|---:|---|---|
| `ST-A0605-AA TIE RODS.pdf` | `2149995344555` | `b9e3efdbbbe192dfb4e429f797ddab4223601a24` | Assembly BOM and hardware family |
| `ST-60501-AA TIE ROD CARBON TUBE.pdf` | `2149965223032` | `a1c857848e718651c3c3972b9d53a6635b1a166e` | Tube drawing reports 10.68-in principal length and 0.63-in nominal OD |
| `ST-60502-AA ... RIGHT THD.pdf` | `2074338764725` | `22a9f0cda2858fae59be39f83487e6b0d6dffbdd` | Right-hand end-cap geometry and fitment note |
| `ST-60503-AA ... LEFT THD.pdf` | `2074343903141` | `652b4077ec7bdbc3cb749c26b9eca174374d7b2e` | Left-hand end-cap geometry and fitment note |

The physical assembly is adjustable. Tube length, end-cap length, rod-end body length, threaded engagement, jam-nut location, and installed toe jointly determine the joint-center distance. Therefore the 10.68-in tube dimension is not `QTY-STEER-0012` nominal tie-rod joint-center distance.

The right-thread end-cap drawing title/file uses steering numbering, but its title block appears to show `SU-60502-AA`. This is treated as a likely drawing-title-block identity error until reconciled with the assembly BOM and source CAD.

## Front upright and outer tie-rod pickup

The current front upright assembly candidate is:

| Artifact | Box file ID | Provider SHA-1 | Role |
|---|---:|---|---|
| `WT-A0802-AA FRONT UPRIGHTS.SLDASM` | `1966638198050` | `dee3e4b7add775e55c43013338e483ff30471c9b` | Preferred assembly candidate for upright identity and installed component relationships |
| `WT-A0802-AA FRONT UPRIGHTS.pdf` | `2173006792564` | `b3eba618789b2a53df432e81cb556a35efc2958e` | Assembly BOM |
| `WT-80201-ZZ CNC UPRIGHT, FRONT, RIGHT.pdf` | `2071451248395` | `74a6afa2b8d712f240a84f2b864f1771cb382491` | Right upright manufacturing drawing |
| `WT-80204-ZZ CNC UPRIGHT, FRONT, LEFT.pdf` | `2090703733428` | `cb4ce8110264ac73b2e798befa536e3976e17078` | Left upright manufacturing drawing |

The upright assembly BOM includes right and left CNC uprights, front camber adapters, shims, and mounting hardware. The upright drawings state that undimensioned features are controlled relative to the CAD model, so the integrated outer tie-rod pickup may require current CAD extraction rather than reconstruction from visible drawing dimensions.

For the steering model, the authoritative quantity is the outer joint-center point relative to the upright and the steering-axis line. The design-spec steering-arm length of 69.9 mm remains a consistency observation, not a substitute for those geometric objects.

## Relationship to final design-study geometry

The selected design-study lineage remains:

1. WUFR-26 steering FDR selects `Test 3`.
2. `GEOMETRY FINAL.SLDPRT` is the selected mechanism-study source.
3. `2026Ackermann.csv` is the primary final-motion response.
4. `Test_3.csv` is selection-era cross-check evidence.
5. `Steering Length Optimization Tests.xlsx`, Test 3, records supporting design intent.

The production assembly and drawings are a separate but related evidence chain. Agreement must be demonstrated rather than assumed. The design-study geometry may omit hardware details, adjustment, final manufacturing revisions, shims, or installed offsets.

## Required reconciliation before active geometry

The following must be completed before WUFR-26 steering geometry becomes an active model configuration:

1. extract the active configurations and component references from current `FSA STEERING`, rack, tie-rod, and front-upright assemblies;
2. match every referenced component to one part number, revision, source file, and provider hash;
3. resolve the `60306`–`60310` rack-family numbering conflict;
4. resolve the `SU-60502-AA` versus `ST-60502-AA` end-cap identity conflict;
5. export the left/right steering-axis lines and outer tie-rod joint centers from the current upright/vehicle state;
6. export rack-axis direction, rack-center inner-joint points, travel stops, and pinion-to-rack relation;
7. export installed left/right tie-rod joint-center lengths and allowable adjustment/thread-engagement ranges;
8. identify nominal camber shim, toe, ride height, wheel/tire, and rack-center setup;
9. compare production geometry with `GEOMETRY FINAL.SLDPRT` and document intentional differences;
10. capture immutable bytes and SHA-256 for frozen benchmark and active-value sources.

## Use restrictions

- Folder organization and file names are discovery aids, not parameter authority.
- An assembly BOM establishes component identity only for the stated drawing revision.
- A part drawing does not establish installed hardpoints without assembly state and adjustment.
- Provider SHA-1 is not the project freeze hash.
- Historical or conflicting drawings remain preserved and explicitly classified.
- No active steering parameter is selected by this manifest.
