# Steering External Suspension-Pose Adapter v0.1.0

## Purpose

`external_rigid_upright_pose_csv_v0.1.0` is the source-neutral exchange boundary between an external suspension model and the canonical steering `SuspensionPoseSet` contract.

It adds **no suspension or steering equations**. It only validates and converts reviewed rigid-transform tables into the provider contract already consumed by `MOD-STEER-0002` and evaluated by `MOD-STEER-0001`.

## Exchange contract

One CSV row represents one named suspension state and contains:

- `state_id`;
- left/right translation in canonical body-frame metres;
- left/right full 3x3 active rotation matrices;
- any named state coordinates declared by the accompanying TOML manifest.

The manifest must identify:

- adapter/version and pose-set identity;
- nominal state;
- source type/path/revision;
- review authority;
- canonical frame identity and definition;
- translation unit;
- active rotation convention;
- steering-DOF rule;
- an explicit declaration that tie-rod steering response is not already included;
- coordinate column IDs and units.

Version 0.1 deliberately accepts only:

- translation in metres;
- `active_nominal_upright_to_state_body_frame` rotation matrices;
- `upright_reference_pose_excludes_tie_rod_steering_rotation`.

Source-specific frame conversion must occur upstream and be reviewed. The steering package does not guess vendor axes, Euler order, handedness, or sign conventions.

## Failure behavior

The import fails before steering evaluation for:

- missing source/frame/revision metadata;
- wrong steering-DOF rule;
- `tie_rod_steering_response_included=true`;
- unsupported translation or rotation convention;
- missing CSV fields;
- duplicate state IDs or coordinate definitions;
- nonfinite values;
- non-orthonormal or left-handed rotation matrices;
- missing declared nominal state.

A valid imported pose can still make the steering mechanism infeasible; that remains a `MOD-STEER-0001` operating-state result rather than an adapter error.

## Verification

`STEERING_EXTERNAL_POSE_TABLE_FIXTURE_V0` copies the existing PR #24 synthetic pose fixture into the new external exchange format. `BENCH-STEER-0018` requires:

1. exact reconstruction of all state coordinates and rigid-transform components;
2. identical multi-state steering feasibility;
3. identical rack-sweep wheel headings;
4. identical centered dynamic-toe results;
5. rejection of a source that declares tie-rod steering response already included.

The fixture proves adapter composition only. It is not suspension-model validation or WUFR motion evidence.

## Source authority

The source audit found team documentation showing SolidWorks motion-study and OptimumK/simulated-kinematics use, but did not recover a reviewed machine-readable zero-steer upright transform series. See `steering_external_pose_source_audit.md`.

A future SolidWorks, OptimumK, lookup-table, or native-solver exporter can target this same exchange format without changing steering evaluation or optimization code.

## Literature/architecture basis

No new vehicle-dynamics equations are introduced. The governing literature rationale remains the existing pose-provider basis:

- Gillespie: toe/steering geometry error changes with suspension state;
- Guiggiani: suspension/roll steer and toe are state-dependent setup/kinematic behaviors;
- Romano: steering assembly validation can be staged into suspension/full-vehicle integration.

The adapter is an implementation/data-contract decision, not a new physical model.
