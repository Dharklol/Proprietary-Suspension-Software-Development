# Phase 3 review — WUFR static load-path screening exchange authorization

## Decision

Approve `AUTH-SUSP-0019` for implementation after merge.

The authorized model, `MOD-SUSP-0011`, is a deterministic source-preserving exchange layer. It may assemble the accepted setting-1/1 WUFR static result chain into one canonical machine-readable load-path packet, but it may not create or alter physical loads and may not promote the current ideal/incomplete results into an FEA or structural-release claim.

## Why this gate is needed

The project now has separate reviewed results for:

- whole-vehicle static equilibrium and road reactions;
- complete-for-the-authorized-static-gravity carrier external wrenches;
- four synchronized Level-1 suspension interface solves;
- four synchronized incomplete rocker included-load contributions.

Those records are useful individually, but downstream review currently requires navigating multiple files, frames, points, sign conventions, and fidelity boundaries. Program B4 calls for a source-preserving exchange packet. A separate authorization is necessary because merely collecting the values can otherwise hide point relocation, sign changes, incomplete load paths, or accidental promotion into FEA boundary conditions.

## Authorized source chain

The exchange is limited to the exact accepted records:

| Layer | Model / authorization | Governing result |
|---|---|---|
| Vehicle static state | `MOD-VEH-0007` / `AUTH-VEH-0010` | `wufr_static_equilibrium_result_v0.2.0.json` |
| Carrier external wrench | `MOD-VEH-0008` / `AUTH-VEH-0011` | `wufr_static_carrier_wrench_result_v0.1.0.json` |
| Level-1 suspension interfaces | `MOD-SUSP-0009` / `AUTH-SUSP-0017` | `wufr_static_level1_interface_loads_result_v0.1.0.json` |
| Rocker included loads | `MOD-SUSP-0010` / `AUTH-SUSP-0018` | `wufr_static_rocker_included_loads_result_v0.1.0.json` |

All inputs must match the exact configuration, static state, explicit settings, and fixed FL/FR/RL/RR order. The packet records the path and SHA-256 of every governing source.

## Mechanics review

No new mechanics are introduced. `MOD-SUSP-0011` may:

- validate source status and identities;
- copy exact values;
- attach source-field paths;
- classify records by load role and acting-on/counterparty bodies;
- retain source frames and points;
- serialize deterministically;
- compute hashes, counts, and packet-level diagnostics.

It may not:

- rerun equilibrium or kinematics;
- reconstruct forces from summary values or scalar motion ratios;
- infer omitted loads;
- change signs or apply absolute values;
- mirror corners;
- transform frames;
- move application/reference points;
- create action/reaction counterparts not already explicit upstream;
- distribute resultants to bearings, joints, nodes, or members;
- add balancing loads.

## Packet review

The canonical JSON packet must contain:

1. packet identity;
2. source manifest;
3. vehicle static state;
4. carrier external wrenches;
5. Level-1 interface loads;
6. rocker included loads;
7. missing and deferred loads;
8. diagnostics;
9. fidelity and use boundaries.

Every load record retains its source model, authorization, file path, field path, frame, point/reference, acting-on body, counterparty, sign convention, and exact numeric value.

Optional CSV or solver-specific views are intentionally not authorized in v0.1 because flattening can discard reference-point, moment, provenance, or fidelity information.

## Critical incompleteness review

The packet must explicitly preserve the following gaps:

- unavailable `KW_V5_non_spring_static_force`;
- incomplete rocker equilibrium and no total pivot/bearing reaction;
- no rocker-bearing split;
- no individual forward/aft A-arm inboard-joint split;
- no welded wishbone member-force distribution or bending;
- no bearing, joint, chassis, or member compliance;
- no maneuver tire, brake, drive, aero, inertial, gyroscopic, curb, impact, or durability loads;
- no as-built geometry/setup/tire/damper correlation.

The existing per-unit damper influence may be copied as geometry-only sensitivity. It cannot be converted to an actual load by selecting or assuming a damper force.

## Permitted use

The packet may support:

- load-path sign and source review;
- four-corner interface-force comparison;
- CAD point/frame/interface audit;
- preliminary structural-model planning;
- identification of missing tests, measurements, and model fidelity.

## Prohibited use

The packet may not be represented or used as:

- a complete physical hardware or chassis-pickup load case;
- direct FEA boundary conditions;
- a complete rocker/bearing reaction;
- individual A-arm pickup or member loads;
- authorized stress, buckling, fatigue, weld, bearing, compliance, or factor-of-safety output;
- a maneuver, durability, setup, correlated, installed/as-built, design-release, or production result.

## Verification plan

### BENCH-SUSP-0035

Verify exact source, hash, field-path, point, frame, body identity, sign, and value preservation from all four upstream records.

### BENCH-SUSP-0036

Freeze the canonical JSON and compact manifest, require every section and all four corners, verify unique record IDs and full traceability, and require deterministic regeneration.

### BENCH-SUSP-0037

Inject missing, failed, stale, reordered, hash-mismatched, altered, nonfinite, and over-promoted inputs. Verify that the model publishes no partial load records and preserves every fidelity and prohibited-use flag.

## Review conclusion

`AUTH-SUSP-0019` closes the source-contract gate for Program B4 at the current low-fidelity static state. It creates a safer bridge between reviewed mechanics and later CAD/structural workflows without falsely claiming that the available interface resultants are complete FEA loads.

Implementation may begin only after this authorization is merged. Solver-specific exports, complete rocker loads, individual pickup/member loads, and maneuver structural cases remain separate future authorization gates.
