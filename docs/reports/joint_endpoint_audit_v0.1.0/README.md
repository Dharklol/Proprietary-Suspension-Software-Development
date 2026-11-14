# Joint endpoint and source compatibility checkpoint

Owner clarification: the pickup geometry has not changed since that year's
redesign, so an intervening revision is not the explanation. A direct read of
the frozen OptimumK workbook confirms the exported pickup coordinates. The
18.284 mm result below compares that hardpoint with inferred COM references;
it is not a confirmed physical pickup displacement. A component CG is not a
ball center, and repeating a part name does not itself prove the inferred offset.
The owner confirms that geometry pickup points are the CAD ball centers and are used for CAD assembly. Intended reference identity is established; COM instance/configuration consistency remains open.

Reproduce: `PYTHONPATH=src python scripts/run_joint_endpoint_audit.py`.
Registry: BENCH-VEH-0028; related MOD-VEH-0013/0014 and BENCH-VEH-0027.

Ten audit checks pass for 36 source rows: 28 rod ends and eight HAB-4TG bearings.
Each has a distinct nearest nominal endpoint candidate. This is not confirmation
of rigid ownership, endpoint identity, clamping or whole-joint tensor rotation.
The separate joint ownership gate remains false.

## Unresolved reference correspondence: front arm-side pullrod joint

The two front XML4 instances (COM SU116/117) are 25.923 mm from the native arm
pickup; repeated rear arm-side XML4 copies have a CG offset of about 7.636 mm.
The front fastener CGs in SU45/44, projected onto the rod axis, independently
indicate the same alternative location to within 0.00461 mm.

| Source / inference | Left joint location, y/z (mm) |
|---|---|
| Frozen OptimumK arm pickup | 519.405 / 277.800 |
| COM fastener CG projected onto rod | 503.652 / 268.519 |
| Repeated XML4 CG-offset inference | 503.657 / 268.519 |

Right-side y coordinates mirror these. The projected fastener is 18.284 mm along
the rod from the native pickup. Projection of a fastener CG and inference from a
repeated part are diagnostics, not measured ball-center coordinates. Do not edit
the governing geometry, scale mass, shorten the rod or move CGs to make it close.
The owner rules out an intervening geometry change. Check actual CAD joint centers,
assembly transforms and reference-point identity rather than assuming the COM is
older. Both sources' axes already agree; no sign-convention correction is inferred.

This matters to the prior rod study: matching a CG to the infinite rod line and
preserving endpoint distances under an assumed transform do not establish that
the COM assembly uses those endpoint locations. BENCH-VEH-0027 remains conditional
kinematic/gravity verification; front source-compatible composition is blocked.

## Direct drawing inspection

Visual inspection of the front corner assembly (Box 2120119871272, sheets 1–2),
pullrod connector detail (2027093106513) and welding jig assembly (2212895915302)
confirms the attachment topology: the front pullrod connects through two
SU-70110 tabs on the SU-70111 connector of the upper wishbone. The jig BOM
identifies upper fore/aft tubes SU-70105/70106 and housing SU-70103. The corner
BOM identifies the LH rod end as QA1 XML4. These observations support the existing
welded-arm grouping; they do not establish a numerical joint center.

The connector drawing dimensions the plate and tab slots, but none of these
inspected views supplies the ball center in the vehicle coordinate frame.
Drawing pixels are not used as coordinate metrology. Source hashes, links and
limits are recorded in `data_catalog/wufr26_joint_visual_evidence_v0.json`.

The owner subsequently confirmed that the pickup points are the ball centers used
for CAD assembly. A separate ball-center export is therefore no longer requested.
The remaining discrepancy belongs to the COM instance/configuration audit.

## COM instance and label audit

Eight rod-end/endcap pairs are screened by proximity to the declared rod endpoints,
within each axle and side. All eight rod-end rows and eight cap rows are unique.
This is a positional diagnostic, not a verified mating relationship.

| Corner | Arm-side rod/cap rows | Label hands | Rocker-side rod/cap rows | Label hands |
|---|---|---|---|---|
| Front left | 116 / 106 | LH / RH | 118 / 107 | RH / LH |
| Front right | 117 / 104 | LH / RH | 119 / 105 | RH / LH |
| Rear left | 210 / 195 | LH / LH | 211 / 194 | RH / RH |
| Rear right | 213 / 196 | LH / RH | 212 / 197 | RH / RH |

Five of eight pairs have inconsistent thread labels. Targeted read-only reads of
live WUFR-26 COM tab SU on 2026-11-14 confirm the front tube/cap/rod-end names,
masses and CG coordinates in rows 98–107 and 116–119, plus rear cap rows 194–197,
match the committed inventory. Thus these particular labels and front coordinates
are not a transcription error in the inventory. Source:
https://docs.google.com/spreadsheets/d/1gUrRtNkEQ4w44esKezqMjeMxAnAau1kG8DxIGr_S-6I/edit

This does not prove incorrect physical threads or explain the 18.284 mm diagnostic.
Renamed/reused CAD parts, exported configuration or row associations require
inspection of assembly component identities/transforms. No labels, parts, CGs or
pickups are swapped to force agreement. The owner-confirmed joint definition is
retained independently of these source inconsistencies.

## Other candidates and static bearing treatment

An explicit diagnostic band of 6–9 mm screens the repeated-source rod-end CG
offsets, while bearings require <50 micrometres to an upright joint. These are
screening criteria, not supplier tolerances or a rule assigning owners by distance.
Only the two front XML4 instances fail this screen. Other 34 candidates still
need endpoint and clamping evidence; none is promoted as source-confirmed.

All eight bearing CGs fall within 50 micrometres of their candidate joint center.
A static point-mass-at-center approximation would have a summed pose-wise
potential difference bounded by 9.415e-6 J for these nominal offsets under rigid
rotation. This is an eligibility calculation only; no mass is reassigned or CG
snapped in the governing model. The bound does not qualify force/rate/trajectory
errors, prove the internal mass split, or authorize dynamic tensor rotation.
Centered inner-ball mass is independent of spin for gravity, but rod-end shank
ownership and clamp stacks must still be established before composition.

## Verification and next action

The script checks exact unique counts, distinct nearest candidates, bearing
eligibility, explicit preservation of the two front conflicts, independent
fastener/repeated-part agreement and absence of ownership promotion. Exact COM
snapshots and geometry remain unchanged. No new user assumptions are silently
introduced. Results retain source hashes and the false composition gate.

The next necessary evidence is the COM component instance/configuration correspondence. After that,
continue the hardware clamping map and compatible no-driver gravity composition,
then solve static spring/ARB/road equilibrium before a native bump case. This is
the G3/G5a analytical priority. Full native equilibrium remains open; further
isolated energy tests cannot resolve the source position conflict.
