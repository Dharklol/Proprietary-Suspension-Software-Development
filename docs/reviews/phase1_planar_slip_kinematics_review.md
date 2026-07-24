# Phase 1 planar wheel-slip kinematics / motion-aware steering review

**PR:** #33  
**Vehicle model:** `MOD-VEH-0002`  
**Vehicle benchmark:** `BENCH-VEH-0002`  
**Steering benchmark:** `BENCH-STEER-0023`  
**Authorizations:** `AUTH-VEH-0002`, `AUTH-STEER-0004`  
**Review state:** review-ready implementation; final post-freeze CI confirmation pending

## Review question

Does PR #33 add the missing planar velocity-heading/tire-slip geometry needed to turn explicit tire force-demand slips into steering targets without assuming low-speed Ackermann is the high-speed wheel-velocity baseline, while keeping vehicle response, tire force, and steering mechanism physics in their existing separate providers?

## Requested decision

Approval means the following boundary is acceptable:

1. an upstream provider supplies explicit body-frame `u`, `v`, `r` on a declared state/sample schedule;
2. explicit wheel-center body coordinates define the rigid-body velocity field;
3. MOD-VEH-0002 calculates wheel-center velocity heading and signed tire-slip geometry only;
4. PR #30 continues to supply bounded required tire-slip magnitude from reviewed force-demand branches;
5. the motion-aware steering adapter forms each wheel target independently as `delta = beta_hat + alpha_required`;
6. MOD-STEER-0001 remains the only steering mechanism evaluator and receives the resulting incremental-from-pose target through the existing `OperatingStateTargetSet` contract.

Approval does **not** authorize the synthetic motion schedules as WUFR vehicle dynamics.

## Why the PR #30 Ackermann anchor is not wrong

The new provider does not invalidate exact Ackermann. With the planar velocity center on the rear axle (`S=-a2`) and zero tire slip, the wheel-center velocity headings reduce to the classical no-slip Ackermann construction. PR #30 is therefore a valid bounded reference/limiting route.

The limitation is using that route after a different vehicle motion state is known. At nonzero body sideslip the longitudinal location `S=-v/r` changes the left/right front wheel-center velocity-heading split. Guiggiani explicitly shows that under parallel steer the relative front slips change with `S`: they are equal at `S=a1` and reverse ordering on opposite sides of that condition.

Thus the target relationship should be thought of as:

`steering heading = actual wheel-center velocity heading + tire-required slip`

not simply:

`steering heading = low-speed Ackermann heading + tire-slip correction`

whenever a reviewed motion state exists.

## Frozen planar kinematics benchmark

`BENCH-VEH-0002` freezes exact software/limiting-case evidence in:

`benchmarks/vehicle/planar_slip_kinematics_result_v0.1.0.toml`

The rear-axle velocity-center / zero-slip case reproduces the classical front-wheel headings to a maximum absolute error of `9.54166404439055e-15 deg`.

For a synthetic 5-degree parallel-steer case, the frozen left-minus-right tire-slip differences are:

- `S=0`: `-0.5484869178949107 deg` — outside/right slip is larger;
- `S=a1=0.8 m`: `0.0 deg` — front slips are equal;
- `S=1.3 m > a1`: `+0.3441491067986984 deg` — inside/left slip is larger.

No vehicle equilibrium, tire force, load transfer, or body-motion response is solved by this benchmark.

## Frozen motion-aware steering benchmark

`BENCH-STEER-0023` deliberately holds the same synthetic tire branches and full-steer force demands fixed while changing only the supplied velocity-center position. The frozen result is:

`benchmarks/steering/motion_aware_force_demand_result_v0.1.0.toml`

The full-steer force inversion gives:

- inside required slip: `2.5 deg`;
- outside required slip: `9.714285714285714 deg`.

With the synthetic velocity center on the rear axle (`S=-0.7624 m`):

- left target heading: `41.93100064746157 deg`;
- right target heading: `36.46238987720719 deg`;
- regime: `pro_ackermann`.

With the same tire demands but `S=a1=0.8 m`:

- left target heading: `2.4999999999999973 deg`;
- right target heading: `9.714285714285717 deg`;
- regime: `anti_ackermann`.

This is the specific software-level demonstration of the concern that motivated the user discussion: tire load sensitivity can point toward anti-Ackermann while the final steering regime still depends on the vehicle velocity field.

The two synthetic state schedules also freeze visibly different regime distributions:

- rear-axle velocity-center schedule: `14 pro / 1 parallel / 0 anti`;
- `S=a1` schedule: `4 pro / 1 parallel / 10 anti`.

A reference steering candidate remains mechanism-feasible through the existing MOD-STEER-0001 multi-state evaluator. Its synthetic aggregate objective is `62.46118922280387`; that number has no vehicle-performance authority.

## Static toe and pose reference

MOD-STEER-0001 evaluates incremental projected road-wheel heading from each zero-steer suspension pose. The motion-aware adapter therefore calculates its total required wheel heading first and subtracts the same transformed wheel-plane centered reference used by the evaluator.

At rack center the existing centered pose is copied exactly. The adapter does not turn the wheels by the static toe angle merely to force zero straight-line tire slip.

## Source/authority gap

No reviewed current WUFR source has yet been promoted as a synchronized `u,v,r` schedule for these steering targets. The current vehicle-state contract can carry explicit speed/acceleration and per-wheel quantities, but it does not predict body sideslip or yaw response. Current load-transfer and LLTD spreadsheets likewise are not silently used to invent `v` or `r`.

A later QSS, telemetry, multibody, or external simulation source should emit a reviewed motion schedule keyed to the same operating states used by tire demand and suspension pose.

## Prohibited interpretations

After this PR it remains prohibited to claim:

- that PR #30 was physically incorrect merely because it used Ackermann as a bounded reference;
- that one tire compound globally "wants" pro- or anti-Ackermann independent of vehicle motion;
- that the synthetic `u,v,r` schedules are WUFR predictions;
- that lateral acceleration alone uniquely specifies `u,v,r`;
- that `VehicleOperatingState.speed_mps` is automatically identical to body longitudinal velocity `u`;
- that a motion-aware target can fill missing tire force demand or missing wheel operating states;
- that this PR adds a bicycle/QSS/load-transfer model;
- production WUFR steering ranking without reviewed synchronized motion, suspension, tire, and weighting sources.

## Acceptance disposition

The frozen software result satisfies the implementation-level acceptance questions:

- equation/model/authorization/benchmark records are present;
- exact kinematic limiting cases are frozen;
- the same-slip/different-velocity-center pro/anti regime result is frozen;
- the reference candidate completes MOD-STEER-0001 evaluation;
- motion-aware benchmark report generation is implemented.

The remaining review action is final post-freeze CI confirmation on the PR head. The first successful report-source run was motion-aware workflow run `30069692374` at head `533454289d685272b7f920717b4dc103d38a955b`, artifact `8587530683`, digest `sha256:7bc072364914172db33015ceaa689007f0e181787060ea263015deeb3ae9bdef`. A final PR-head run must supersede that source run before merge.
