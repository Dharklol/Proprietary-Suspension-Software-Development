# Steering Suspension-Pose Provider and Multi-State Evaluation v0.1.0

**Authorization:** `AUTH-STEER-0002`  
**Models:** `MOD-STEER-0001`, `MOD-STEER-0002`  
**Tasks:** `P1-STR-006A`, `P1-STR-006B`  
**Benchmarks:** `BENCH-STEER-0014`, `BENCH-STEER-0015`

## Purpose

This release extends the steering vertical slice from one nominal suspension pose to a provider-neutral set of suspension operating poses without implementing a suspension kinematics solver and without changing the authoritative steering mechanism equations.

The central composition rule remains unchanged: `MOD-STEER-0001` is the only solver for tie-rod closure, mechanism branch, singularity diagnostics, and steering response. The pose layer only transforms upright-bound geometry into a named suspension state.

## Canonical pose contract

A pose state supplies left and right rigid transforms from the nominal upright reference frame together with named state coordinates, units, source metadata, and authority.

The required steering-DOF declaration is:

```text
upright_reference_pose_excludes_tie_rod_steering_rotation
```

This means the provider supplies the suspension pose of the upright before the tie rod resolves steering rotation. Steering-axis position/orientation, outer tie-rod pickup, and wheel-plane reference move with the upright transform. Rack geometry and rack inner joints remain chassis-fixed. The nominal tie-rod joint-center length remains fixed.

A source that already contains tie-rod-induced bump steer or toe cannot be consumed as an unresolved pose input because doing so would apply the steering response twice. Such a source belongs on the validation/comparison side of the contract.

## Pose application

For each side, the rigid transform maps a nominal upright-bound point or direction into the state:

```text
p_state = R p_nominal + t
v_state = R v_nominal
```

where `R` is a reviewed right-handed orthonormal rotation and `t` is a translation in the canonical body frame.

The pose adapter transforms:

- steering-axis point and direction;
- outer tie-rod joint;
- wheel-forward basis when available;
- wheel-plane reference used by the canonical projection layer.

It does not transform:

- rack axis or rack housing reference;
- rack inner joints;
- tie-rod design length.

At a non-nominal suspension pose, the transformed mechanism is not expected to close at zero steering rotation. `MOD-STEER-0001` solves the upright rotation that satisfies the fixed tie-rod length.

## Feasibility semantics

Pose validity and steering-state feasibility are separate.

An invalid pose definition includes nonfinite transforms, nonorthonormal rotations, duplicate state coordinates, or a steering-DOF declaration that already includes tie-rod steering response.

A valid pose may still make the steering mechanism impossible to close. In that case the pose remains valid and the steering operating state is reported infeasible using the existing `MOD-STEER-0001` failure semantics. This distinction is required for later real suspension-state sweeps.

## Multi-state evaluator

`evaluate_candidate_over_pose_set` performs:

1. the existing role resolution and nominal parametric geometry generation;
2. one pose transform per named state;
3. a complete `MOD-STEER-0001` rack sweep at every state;
4. wheel-plane projection through the existing canonical projection functions;
5. centered heading comparison relative to the named nominal pose;
6. side-local dynamic toe change reporting;
7. minimum singularity-ratio reporting and complete analyzer-state retention.

The first release permits asymmetric left/right operating poses even though the design geometry remains exactly symmetric. This is necessary for independent wheel travel and roll-like operating states and does not constitute intentional steering-design asymmetry.

## Target boundary

The current historical target provider is reused only for:

- rack sample locations/domain;
- nominal static toe and camber values used to construct the wheel-plane reference.

Historical requested wheel-angle values are not applied as objectives at non-nominal suspension poses in this release. A later operating-state target contract must explicitly identify which states carry targets and weights before multi-state optimization is authorized.

## Synthetic verification fixture

`STEERING_SYNTHETIC_POSE_SET_V0` contains:

- identity nominal pose;
- symmetric +5 mm vertical upright translation;
- opposed +5 mm left / -5 mm right vertical upright translation.

These are deliberately simple rigid transforms. They verify interface composition and state-dependent closure; they are not intended to reproduce the actual WUFR suspension path.

Frozen review results are stored in `benchmarks/steering/steering_pose_provider_result_v0.1.0.toml`.

## Literature basis

Gillespie defines static toe at a specified wheel load or relative wheel-center position with respect to the sprung mass, supporting explicit state labeling when wheel position changes. Guiggiani treats roll steer and toe-in/toe-out as suspension/setup parameters affecting axle characteristics, supporting state-dependent toe/steering maps rather than one nominal scalar. Romano's staged steering-system analysis supports validating the steering assembly before applying it through suspension and full-vehicle states.

These sources support the separation used here but do not define the repository's exact software interface. The provider schema and no-double-counting rule are project architecture choices derived from the need to preserve one authoritative steering closure model.

## Explicit exclusions

This release does not implement or authorize:

- native suspension kinematics;
- OptimumK-specific or CAD-specific steering dependencies;
- an authoritative WUFR suspension pose map;
- physical bump-steer or roll-steer correlation;
- tire-informed multi-state targets;
- rack force or steering effort;
- compliance, backlash, friction, or installed-state corrections;
- manufacturing tolerance or robustness analysis;
- hardware packaging or collision feasibility;
- production geometry selection.

## Next engineering gate

The next nonphysical extension may either add a reviewed external suspension-pose adapter/data set or add an operating-state target aggregation contract. Physical-parameter integration remains deferred until the required measurements exist.
