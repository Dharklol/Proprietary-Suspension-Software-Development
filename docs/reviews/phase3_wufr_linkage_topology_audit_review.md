# Phase 3 WUFR linkage topology source-audit review

## Scope

This review records the source/topology audit requested after the provider-neutral linkage statics kernel was authorized and implemented in PRs #68/#69.

No WUFR member loads are calculated in this PR. The intended outcome is to identify what is source-backed, reject unsafe legacy shortcuts, propose the next solver boundary, and stop at the first genuine topology-authority gap.

## Reviewed evidence

### Repository authority

- `docs/models/suspension/suspension_geometry_contract_v0.1.0.md`
- `authorizations/suspension/AUTH-SUSP-0003.toml`
- `authorizations/suspension/AUTH-SUSP-0010.toml`
- current MOD-SUSP-0001 through MOD-SUSP-0006 records and their source fixtures

The repository already freezes the most consequential fact: front actuation belongs to the upper A-arm and rear actuation belongs to the lower A-arm.

### WUFR26 physical source evidence

Box source review included:

- `SU-A0701-AA FRONT CORNERS.pdf`, file `2120119871272`, SHA-1 `a1aedb29a997535435af7b613499448715cac926`;
- `SU-A0702-AA REAR CORNERS.pdf`, file `2142858842201`, SHA-1 `ebf896e9924541c63e364ca352c9aee860f089f9`;
- front/rear rocker drawings/assemblies already frozen by AUTH-SUSP-0003;
- front pullrod and rear pushrod drawing families;
- current WUFR26 suspension CAD/drawing folder structure.

Google Drive design-review evidence included:

- WUFR-26 Linkages FDR, document `1VRVNGEJYCK1TXYTNQ7yD3O7_zlvJ4Z_fz5s3hqWU6iU`;
- WUFR-26 In-Board Suspension FDR, document `1_zLUOdFNOuKtiOFQlCcENggb9AWQssjY8x6jlKwF050`;
- WUFR-26 Upright/Hub FDR, document `1dyxnKNOUtDxUqQ6HOKDrql5qcbHaQvbnZPWTGyQdf94`;
- historical Load Case List with Load Matrices, document `1zEUDueYdDvRcimGq8Me7ICJswRREzkVDnExDIg-Wt40`.

### WUFR27 status evidence

- WUFR-27 Linkages & Loads PDR, document `1zogjzSuwyGg96bJFc3XR4rFGPdvSZhZ6xkYsqjtAvOc`;
- WUFR27 Box suspension folder `391771444276` and front-corner folder `391771067613`.

The current WUFR27 sources are not yet complete enough to establish current hardware topology. The PDR remains a work in progress, and the front-corner CAD scaffold did not contain a current production part set at audit time.

## Findings

### Accepted source-backed constraints

1. A direct six-links-to-upright WUFR reduction is physically inconsistent with the frozen actuation ownership.
2. Upper/lower A-arms must remain separate load-path bodies or be replaced only by a separately reviewed equivalent structural abstraction.
3. Front tie rod and rear toe link remain separate role-specific links.
4. The rocker is a separate downstream load-path body connected to actuation, spring/damper, ARB, and chassis support.
5. The braking/drive load path must preserve hub/bearing/caliper/rotor/halfshaft torque effects in the external wrench/interface contract.
6. Signed compression/tension is mandatory; the legacy negative-to-zero rule is rejected.

### Rejected legacy authority

The historical load-matrix instruction to set all negative member-force values to zero is incompatible with AUTH-SUSP-0010. That document is retained as negative/lineage evidence only.

The WUFR26 upright review also records missing caliper-bolt forces and tire moments in older analysis. Therefore old OptimumK/load-matrix member-force tables are not a suitable ground truth for the new statics path.

### Candidate architecture, not yet authorization

A multi-rigid-body graph appears to be the correct next abstraction:

- upright/corner body;
- rigid upper A-arm;
- rigid lower A-arm;
- axial tie/toe link;
- axial push/pull rod;
- rigid rocker;
- chassis ground.

The most promising first support reduction for each A-arm is an equivalent revolute joint about the already-frozen two-pickup hinge axis. This would preserve the arm-mounted actuation point and align the statics representation with the existing kinematic arm-rotation model.

However, that idealization requires explicit hardware/joint review. It is not inferred from hardpoint coordinates alone.

## Structural-output boundary discovered

The source audit exposed a useful architectural distinction:

- a rigid-body graph can target **net interface reactions**;
- it cannot automatically provide unique forward/aft chassis-joint load sharing;
- it cannot automatically provide welded A-arm tube axial/bending loads.

The latter outputs need additional structural information, such as a reviewed joint load-sharing convention or beam/FE stiffness. This should be a deliberate later fidelity layer rather than an invisible assumption inside the first WUFR statics solver.

## Authorization decision

`AUTH-SUSP-0011` is created as a **WUFR adapter implementation hold**.

It does not revoke or weaken AUTH-SUSP-0010. The generic six-link solver remains implemented and valid in its provider-neutral scope.

The hold applies to current-car WUFR adaptation until the following are reviewed:

1. WUFR27 carryover/change status;
2. endpoint-by-endpoint joint type and axis;
3. desired A-arm output fidelity;
4. brake and rear-drive external-wrench interfaces;
5. spring/ARB-to-rocker structural-force interface.

## Review recommendation

Merge this audit only as a source/architecture control record. Do not begin WUFR member-force implementation from it.

After the team answers the topology questions, prepare a new authorization for the chosen multi-body graph and its analytical/rank benchmarks before writing the current-car adapter.
