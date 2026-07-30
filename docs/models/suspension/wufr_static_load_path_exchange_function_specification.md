# MOD-SUSP-0011 WUFR static load-path screening exchange function specification

## Purpose

`MOD-SUSP-0011` is a source-preserving exchange layer for the accepted WUFR setting-1/1 static design-intent result chain. It packages the existing vehicle-equilibrium, carrier-wrench, Level-1 suspension-interface, and incomplete rocker included-load records into one deterministic canonical JSON packet.

It is not a new statics model. It introduces no force law, equilibrium equation, load distribution, frame transform, or structural fidelity. The model may only validate, copy, classify, index, hash, and serialize accepted upstream values.

## Governing authorization and source record

- authorization: `AUTH-SUSP-0019`
- source contract: `WUFR27_STATIC_LOAD_PATH_EXCHANGE_V0`
- result label: `uncorrelated_design_intent_static_load_path_screening_exchange`
- configuration: `WUFR27_SUSPENSION_BASELINE_V0`
- static state: `WUFR26_DRIVER_NO_FUEL_DESIGN_INTENT_REFERENCE`
- corner order: `front_left`, `front_right`, `rear_left`, `rear_right`

## Required upstream records

1. `MOD-VEH-0007` / `AUTH-VEH-0010`
   - `benchmarks/vehicle/wufr_static_equilibrium_result_v0.2.0.json`
2. `MOD-VEH-0008` / `AUTH-VEH-0011`
   - `benchmarks/vehicle/wufr_static_carrier_wrench_result_v0.1.0.json`
3. `MOD-SUSP-0009` / `AUTH-SUSP-0017`
   - `benchmarks/suspension/wufr_static_level1_interface_loads_result_v0.1.0.json`
4. `MOD-SUSP-0010` / `AUTH-SUSP-0018`
   - `benchmarks/suspension/wufr_static_rocker_included_loads_result_v0.1.0.json`

All four records must be successful and must agree exactly on configuration, static state, fixed corner order, and explicit setting identities. Each governing file is identified by path and SHA-256.

## Canonical packet

The governing output is canonical JSON in SI units. The packet contains:

1. `packet_identity`
2. `source_manifest`
3. `vehicle_static_state`
4. `carrier_external_wrenches`
5. `level1_interface_loads`
6. `rocker_included_loads`
7. `missing_and_deferred_loads`
8. `diagnostics`
9. `fidelity_and_use_boundaries`

No optional CSV, solver deck, CAD coordinate transform, or FEA-specific projection is part of v0.1.

## Source manifest

For every governing source file, retain:

- repository-relative path;
- SHA-256;
- model ID;
- authorization ID;
- result label;
- record version;
- configuration and static-state IDs;
- declared status;
- corner order where applicable.

Every copied field in the packet must identify its source file and exact source-field path.

## Load-record contract

Each serialized force/wrench/interface entry carries at minimum:

- unique record ID;
- corner ID;
- load role;
- acting-on body ID;
- counterparty body ID;
- frame ID;
- named application point or wrench reference;
- exact point/reference coordinates;
- signed force vector;
- signed moment vector, with zero stored explicitly where the source is a point force;
- source model and authorization IDs;
- source result path and source-field path;
- source sign convention;
- fidelity label;
- completeness for the named source record.

Signed axial scalars remain available alongside source-owned action/reaction vectors where the upstream result provides both.

## No relocation or transformation

`MOD-SUSP-0011` does not transform loads into a new frame. It retains the exact source frame and point/reference identity. Distinct source points remain distinct, including:

- carrier wrench references and road-contact points;
- upper and lower spherical interfaces;
- lateral-link endpoints;
- actuation body and rocker-side endpoints;
- equivalent upper/lower hinge references;
- spring rocker eyes;
- ARB rocker pickups;
- rocker pivots.

The model may not merge these points, move a force to a more convenient point, or create a nodal distribution.

## Action/reaction handling

Only action/reaction pairs already explicit in an upstream result may be represented as such. The exchange model does not create:

- chassis-side nodal loads from an arm resultant;
- forward/aft A-arm joint splits;
- rocker-bearing shares;
- welded-member internal loads;
- FEA constraints or load distributions.

## Required payload content

### Vehicle state

Retain the accepted body coordinates, wheel coordinates, road reactions, contact points, explicit ARB settings, and physical-closure diagnostics.

### Carrier wrenches

Retain each complete-for-authorized-static-gravity carrier wrench, its exact reference, road-normal and unsprung-gravity component provenance, and wrench-transport/four-corner reconstruction diagnostics.

### Level-1 interface loads

Retain per corner:

- front tie-rod or rear toe-link axial force and endpoints;
- front pullrod or rear pushrod axial force and endpoints;
- upper/lower spherical force vectors and explicit action/reaction records;
- upper/lower equivalent inboard hinge net force and perpendicular moment;
- body residuals, condition number, and pivot diagnostics.

The current equivalent hinge resultant does not authorize individual forward/aft inboard-joint loads.

### Rocker included loads

Retain per corner:

- distinct push/pull, conservative-spring, and physical-ARB point loads;
- included resultant force and moment about the exact rocker pivot;
- ideal-revolute partial support force and perpendicular-moment contribution;
- signed unrepaired free-axis moment residual;
- `KW_V5_non_spring_static_force` as a required missing load;
- per-unit hypothetical damper-force influence with no actual force applied.

The rocker result remains incomplete.

## Failure behavior

The model fails closed with no load records when any required source is unavailable, unsuccessful, stale, hash-mismatched, cross-configured, reordered, incomplete, nonfinite, or missing a required field/point/frame/source identity. It also fails when a prohibited authority flag is true or a required missing/deferred item is omitted.

A failed output may contain a diagnostic manifest identifying the failed source, section, and field, but it may not contain a partial load packet.

## Determinism

Canonical serialization must be deterministic. The implementation freezes:

- the canonical JSON packet;
- its SHA-256;
- a compact TOML manifest/summary.

Regeneration in CI must reproduce the packet within `1e-12` for parsed numeric values and byte-identically after canonical serialization.

## Fidelity boundary

The packet is complete only as an exchange of the named accepted upstream records. It is useful for:

- sign and source review;
- four-corner interface comparison;
- CAD point/frame/interface audits;
- preliminary structural-model planning;
- measurement and fidelity-gap identification.

It is not authorized as:

- a complete physical hardware load case;
- a complete rocker or bearing reaction;
- a complete chassis pickup load set;
- a solver-specific or FEA boundary-condition set;
- a member-force, stress, buckling, fatigue, weld, compliance, or factor-of-safety result;
- a maneuver, durability, correlated, installed/as-built, design-release, or production result.

## Promotion path

A later FEA export requires separate authorization of frame transforms, application/nodal mappings, load distributions, constraint strategy, and intended fidelity. Complete rocker loads require satisfying `AUTH-SUSP-0015`, integrating the actual damper force upstream, re-solving the vehicle equilibrium, and separately authorizing the complete rocker composition. Individual wishbone pickup/member loads require a higher-fidelity topology and load-sharing model.
