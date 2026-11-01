# Front-corner component ownership checkpoint

Reproduce with `PYTHONPATH=src python scripts/run_front_corner_ownership.py`.
Related model: MOD-SUSP-0013; benchmark: BENCH-SUSP-0041.

The read-only COM snapshot SU!B19:H143 enumerates all 124 bilateral A0701
instances. CAD mass and CG agree exactly with the prior pitch snapshot, and
their mass closes to 5.068 lb (2.298806 kg). Production-mass entries are retained
for provenance and excluded from this calculation. No quantity multiplication
is applied to already-instanced rows. This scope excludes the separate WT,
brake, steering and inboard suspension assemblies.

| Assignment status | Instances | CAD mass (lb) | Meaning |
|---|---:|---:|---|
| Verified nominal tubes | 8 | 1.798 | Existing BENCH-SUSP-0040 contribution |
| Source-supported housing owner | 4 | 0.582 | Upper/lower arm; tensor and motion gates still pending |
| Candidate owner | 24 | 1.286 | Endcaps, pullrod parts and attachments; attachment review required |
| Joint split required | 16 | 0.736 | Bearings and rod ends span relatively moving bodies |
| Unresolved hardware | 72 | 0.666 | Clamping-stack ownership is not established |

The full row-by-row map, candidates, reasons and checks are in results.json.
Candidate endcap assignments are explicit review hypotheses based on named
parts and source positions, not nearest-point authorizations. A source-supported
housing owner is not a verified inertia contribution. Only the existing eight
tubes retain nominal-contribution verification; no native transient authority
is granted by this inventory audit.

## Source evidence and discrepancies

- COM: https://docs.google.com/spreadsheets/d/1gUrRtNkEQ4w44esKezqMjeMxAnAau1kG8DxIGr_S-6I/edit
- Front assembly drawing: https://app.box.com/file/2120119871272
  (SU-A0701-AA, prior SHA-1 a1aedb29a997535435af7b613499448715cac926).
  Text read on 2026-11-01 confirms the part families/counts. This pass did not
  visually inspect exploded-view callouts and does not claim clamping-stack proof.
- Existing topology evidence:
  `docs/models/suspension/wufr_linkage_topology_source_audit.md` establishes
  welded steel arms with upright-end bearing housings and upper-arm front actuation.

Drawing BOM item 5 specifies ten 91847A429 thin nuts. COM contains two plus eight
91845A105 jam nuts absent from that drawing BOM. This discrepancy remains open;
neither source is silently rewritten or substituted. Drawing weight reads 5.06 lb,
while COM instance sum is 5.068 lb; use the latter for this CAD inventory only.
These differences do not block independent tube/housing work.

Whole HAB-4TG and rod-end exports cannot be assigned wholesale to an arm merely
because their centers coincide with its joint. Inner ball/race and outer body
may rotate differently. A future approximation must explicitly state the mass
split or neglected relative rotational energy and quantify its effect. No such
approximation is introduced here. Fasteners similarly require clamping ownership.

## Next implementation boundary and goal alignment

1. Recover full centroidal tensors for the four housings, apply a declared sign
   convention and check their arm transport before extending the nominal subset.
2. Resolve rigid attachment of endcaps and pullrod tabs/connectors using detail
   drawings or CAD evidence. Keep the pullrod as its own member.
3. For the already verified tube subset, implement nonzero-state tensor rotation,
   compatible Jacobians and convective inertia; verify energy before integration.
4. Extend inventory to rear members in parallel with those dependencies when useful.

This closes the front inventory enumeration, not complete front ownership or a
full vehicle dynamics release. Analytical reduced-transient work remains the
priority. No new owner information is required to proceed with the housings or
the verified tube subset. The older whole-car mass discrepancy remains separate.
Drive is unchanged.
