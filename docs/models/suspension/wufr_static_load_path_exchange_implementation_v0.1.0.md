# WUFR static load-path screening exchange implementation v0.1.0

## Scope

`MOD-SUSP-0011` implements the source-preserving exchange authorized by `AUTH-SUSP-0019`. It reads the four accepted setting-1/1 static result records:

- `MOD-VEH-0007` static vehicle equilibrium;
- `MOD-VEH-0008` carrier external wrenches;
- `MOD-SUSP-0009` Level-1 suspension interface loads; and
- `MOD-SUSP-0010` incomplete rocker included loads.

It does not rerun any of those models. The implementation only validates, copies, classifies, indexes, hashes, and canonically serializes accepted values.

## Canonical output

The governing output is:

`benchmarks/suspension/wufr_static_load_path_exchange_result_v0.1.0.json`

The compact manifest is:

`benchmarks/suspension/wufr_static_load_path_exchange_result_v0.1.0.toml`

The JSON is serialized with sorted keys, compact separators, UTF-8 encoding, no nonfinite numeric values, and one trailing newline. The frozen packet is 177,956 bytes with SHA-256:

`29cf33d213d89e43189c9d0e993f259ec51b93af437d4a5e437698b178c28a65`

The packet contains the nine sections frozen by `AUTH-SUSP-0019`:

1. `packet_identity`;
2. `source_manifest`;
3. `vehicle_static_state`;
4. `carrier_external_wrenches`;
5. `level1_interface_loads`;
6. `rocker_included_loads`;
7. `missing_and_deferred_loads`;
8. `diagnostics`; and
9. `fidelity_and_use_boundaries`.

## Source preservation

The source manifest freezes each exact governing file path, byte count, model ID, authorization ID, result label, and SHA-256. The accepted source hashes are:

| Source | SHA-256 |
|---|---|
| Vehicle equilibrium | `13ed891980992022c31fe730cbfa328d4eb759bf25beefc6fa8b04fa19b2d9fb` |
| Carrier wrench | `2daa3d2084c49c3d0abe10937c5f829f12b5461c295520cd39b2d7108819ca2f` |
| Level-1 interface loads | `4fa895734419e29408a91c1b3e823ad4a913ab7b4cb084dbd53dc84fd0015fb5` |
| Rocker included loads | `e09a4007106bd3317d70cc450a4e4ea12e4cae9c2abb6174d99854d26eb3a185` |

The full accepted corner records are copied into their corresponding packet sections without numeric modification.

## Normalized load records

The exchange adds source-field-traceable records organized by corner rather than a solver-specific flat table:

- 4 carrier external-wrench records;
- 40 Level-1 interface records; and
- 16 incomplete rocker records.

Every record carries the fields required by `AUTH-SUSP-0019`, including acting-on and counterparty identities, exact source frame, exact point or reference, signed force and moment, source path, source-field path, source model and authorization, sign convention, fidelity label, and named-source completeness.

Only action/reaction counterparts already explicit in the governing source are represented. The implementation does not derive chassis nodes by negation, split equivalent A-arm hinge resultants between forward and aft pickups, split rocker bearings, transform loads to a CAD or FEA frame, or relocate application points.

## Validation and fail-closed behavior

Before publication, the implementation checks:

- exact model, authorization, result-label, configuration, static-state, setting-1/1, and FL/FR/RL/RR identities;
- successful upstream status for all four records and all four corners;
- finite source values;
- required frames and points;
- retained KW V5 missing-force declaration;
- prohibited authority flags remaining false;
- unique load-record identities; and
- complete required packet sections.

A failure returns a structured failed result with no packet. Tests cover missing sources, failed sources, reordered corners, configuration and static-state mismatches, setting mismatch, nonfinite values, missing frames or points, missing KW V5 declaration, and attempted authority promotion.

## Verification results

`BENCH-SUSP-0035` verifies exact source hashes, complete exact-copy sections, complete load-record fields, and source-field traceability.

`BENCH-SUSP-0036` verifies all nine sections, fixed corner order, record uniqueness, deterministic regeneration, and byte-stable canonical serialization.

`BENCH-SUSP-0037` verifies fail-closed behavior and the retained fidelity/use boundary. All three benchmarks pass in the frozen result.

## Fidelity and use boundary

The packet is complete only for exchange of the four named accepted upstream records. It remains:

- `complete_physical_hardware_load_case=false`;
- `complete_rocker_equilibrium=false`;
- `complete_chassis_pickup_load_set=false`;
- `structural_load_case_authority=false`;
- `fea_boundary_condition_authority=false`;
- `structural_release_authority=false`;
- `installed_as_built_authority=false`; and
- `production_authority=false`.

The KW V5 non-spring static force remains unavailable. Its existing unit influence is copied only as geometric sensitivity and is never multiplied by an assumed force.

The packet is suitable for load-path sign/source review, four-corner interface comparison, CAD point/frame/interface auditing, preliminary structural-model planning, and identification of missing evidence. It is not an authorized FEA load set, stress result, maneuver load case, setup recommendation, correlated prediction, design release, or production decision.
