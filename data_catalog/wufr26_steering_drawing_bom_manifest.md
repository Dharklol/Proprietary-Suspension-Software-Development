# WUFR-26 Steering Drawing and BOM Authority Manifest

**Status:** Reviewed hierarchy and extraction path; Phase 0 task complete  
**Related IDs:** `MIG-STR-0001`, `MOD-STEER-0001`, `BENCH-STEER-0001`, `RISK-STEER-0001`  
**Review record:** `docs/reviews/phase0_steering_review_closeout.md`

## Purpose

This manifest records how WUFR-26 steering assembly numbers, part numbers, drawings, CAD files, design geometry, and BOM tables relate. It prevents an old drawing, incomplete BOM, copied CAD file, title-block typo, or scalar specification from silently becoming parameter authority.

The hierarchy and extraction path are now reviewed. Installed-state confirmation and immutable source hashing remain separate open controls.

## Drawing-number convention

The WUFR-26 drawing standard generally uses:

```text
SYSTEM-ASSEMBLYCOMPONENT-REVISION
```

For steering assemblies, `ST-A0603-AA` identifies the steering-rack assembly family. Part drawings omit the assembly marker, for example `ST-60305-AA`. Number identity must always be paired with revision, source file, date, and assembly context.

## Steering-system hierarchy

The reviewed top-level assembly mapping is:

| Assembly number | Component group |
|---|---|
| `ST-A0601-AA` | Steering wheel |
| `ST-A0602-AA` | Quick release |
| `ST-A0603-AA` | Steering rack |
| `ST-A0604-AA` | Steering column |
| `ST-A0605-AA` | Tie rods |
| `ST-A0606-AA` | Sensor mounts |

Top-level source candidates:

| Artifact | Box ID | Provider SHA-1 | Role |
|---|---:|---|---|
| `FSA STEERING.pdf` | `2173006511727` | `858830e3a9e21196ac1f2b5d66a6c3ee41a2069e` | Top-level BOM and identity |
| `FSA STEERING.SLDASM` | `1966633770970` | `148077e46af721cda86aba59ec563779a7d0bbe6` | Top-level CAD candidate |
| `FSA STEERING.SLDDRW` | `2173006542918` | `ba623bce14ba30b4f1965c7174efbea42576b97b` | Drawing source |

Provider SHA-1 supports discovery and provider-version lineage. Project freeze still requires immutable-byte capture and project SHA-256.

## Authority rules

### Component identity and assembly membership

1. Reviewed active assembly configuration and component-reference export.
2. Matching current assembly drawing/BOM.
3. Current part drawing with matching part and revision.
4. System-level assembly drawing.
5. Folder and filename.
6. Historical or email-suffixed copies.

### Manufacturing features and tolerances

1. Current released part drawing.
2. Drawing note or model-based definition referenced by that drawing.
3. CAD for undimensioned geometry only where the drawing makes CAD controlling.
4. Assembly or physical measurement as a consistency check.

### Steering mechanism geometry

1. Active installed assembly or physical measurement for as-built claims.
2. Frozen `WUFR26_DESIGN_NOMINAL_V0` for nominal design-source development.
3. `GEOMETRY FINAL.SLDPRT`, final OptimumK geometry, and the FDR final tie-rod table under the reviewed source-merge rule.
4. Current rack, tie-rod, upright, and mounting drawings for manufactured features and tolerances.
5. `2026Ackermann.csv`, Test 3 fits, and FDR endpoint values for design-source response comparison.
6. Scalar specifications only as supporting consistency evidence.

A part drawing may control a feature while the installed hardpoint still depends on mates, shims, adjustment, welding, and setup.

## Steering-rack assembly

Preferred current assembly candidate:

| Artifact | Box ID | Provider SHA-1 | Last modified |
|---|---:|---|---|
| `ST-A0603-AA STEERING RACK.SLDASM` | `1966632771950` | `65c463472819d7c467b5117ba4f687326c9620ab` | 2026-07-01 |

Current rack-family drawings:

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

The purchased rack appears as one assembly in the steering BOM, while the cost report requires separate component drawings. Omission of `60306` through `60310` from an assembly BOM is a scope/version limitation, not evidence that the current identities are obsolete.

Older creator-email-suffixed CAD copies and the earlier rack assembly PDF remain historical until matched to the active component-reference export.

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
| `ST-60501-AA TIE ROD CARBON TUBE.pdf` | `2149965223032` | `a1c857848e718651c3c3972b9d53a6635b1a166e` | Tube drawing |
| `ST-60502-AA ... RIGHT THD.pdf` | `2074338764725` | `22a9f0cda2858fae59be39f83487e6b0d6dffbdd` | Right-thread end cap |
| `ST-60503-AA ... LEFT THD.pdf` | `2074343903141` | `652b4077ec7bdbc3cb749c26b9eca174374d7b2e` | Left-thread end cap |

The assembly is adjustable. Tube length is not installed joint-center length. End caps, rod ends, thread engagement, jam nuts, and toe determine the installed value.

The right-thread end-cap title block appears to show `SU-60502-AA`, while the file and assembly BOM use `ST-60502-AA`. This likely prefix error remains tracked under `RISK-STEER-0001` pending source-CAD confirmation.

## Front uprights and outer pickups

| Artifact | Box ID | Provider SHA-1 | Role |
|---|---:|---|---|
| `WT-A0802-AA FRONT UPRIGHTS.SLDASM` | `1966638198050` | `dee3e4b7add775e55c43013338e483ff30471c9b` | Preferred upright assembly candidate |
| `WT-A0802-AA FRONT UPRIGHTS.pdf` | `2173006792564` | `b3eba618789b2a53df432e81cb556a35efc2958e` | Assembly BOM |
| `WT-80201-ZZ CNC UPRIGHT, FRONT, RIGHT.pdf` | `2071451248395` | `74a6afa2b8d712f240a84f2b864f1771cb382491` | Right upright drawing |
| `WT-80204-ZZ CNC UPRIGHT, FRONT, LEFT.pdf` | `2090703733428` | `cb4ce8110264ac73b2e798befa536e3976e17078` | Left upright drawing |

The upright drawings defer undimensioned features to CAD. Steering inputs are the steering-axis lines and outer joint centers, not the reported steering-arm scalar.

## Final study and nominal-model relationship

The reviewed design-source lineage is:

1. The steering FDR selects Test 3.
2. `GEOMETRY FINAL.SLDPRT` is the selected mechanism-study component.
3. Final OptimumK geometry supplies steering-axis/upright points.
4. The FDR final table supplies the later steering-specific front-left tie-rod points.
5. The nominal CAD right side is an exact reflection of the left.
6. `2026Ackermann.csv` and the Test 3 wheel-angle fit provide the dense response comparison.
7. FDR endpoints `22.22 deg` and `32.81 deg` provide an additional design-review cross-check.
8. Active assembly export or physical measurement remains required for installed-state authority.

## Rack center and travel

The nominal design-source configuration uses:

```text
rack center, canonical = [-0.079298, 0, 0.162865] m
one-sided study bound  = +/-1.00 in = +/-0.0254 m
total study span       = 2.00 in = 0.0508 m
```

The moving rack points are the inboard tie-rod joints. This is frozen for the nominal CAD study only. Installed stops, stop-contact component, operating margin, and physical center remain open measurements.

## Active-geometry extraction path

The required path is defined even though not all steps are complete:

1. Export active configurations, component references, suppression states, and warnings from vehicle, steering, rack, tie-rod, and upright assemblies.
2. Match every active component to part number, revision, source file, and provider hash.
3. Confirm current rack-family and end-cap identities in native CAD.
4. Export or measure left/right steering-axis lines, rack axis, inner joints, and outer tie-rod centers.
5. Export or measure installed stop states and pinion/primary-shaft-to-rack relation.
6. Record installed tie-rod joint-center lengths and safe adjustment/thread-engagement limits.
7. Record toe, camber, shim stack, ride height, wheel/tire, rack center, and test load state.
8. Capture immutable source bytes and project SHA-256 for the final installed benchmark package.

## Use restrictions

- Folder organization and filenames are discovery aids, not installed-geometry authority.
- A BOM establishes identity only for its stated scope and revision.
- Cost-report component drawings may legitimately be absent from a purchased-assembly BOM.
- A part drawing does not establish installed hardpoints without assembly state and adjustment.
- The rejected `3.12:1` steering ratio cannot be used downstream.
- Provider SHA-1 is not the project freeze hash.
- The frozen nominal configuration does not certify the fabricated or installed vehicle.

## Closeout decision

The drawing/BOM Phase 0 exit criterion is satisfied: the hierarchy, conflicts, authority rules, and active-geometry extraction path are documented. Remaining native-reference checks, source hashes, and installed measurements remain open in their dedicated risk and Level F tasks.
