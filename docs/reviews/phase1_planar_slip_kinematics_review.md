# Phase 1 planar wheel-slip kinematics / motion-aware steering review

**PR:** #33  
**Vehicle model:** `MOD-VEH-0002`  
**Vehicle benchmark:** `BENCH-VEH-0002`  
**Steering benchmark:** `BENCH-STEER-0023`  
**Authorizations:** `AUTH-VEH-0002`, `AUTH-STEER-0004`  
**Review state:** implementation in progress; final benchmark freeze and CI confirmation pending

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

## Synthetic benchmark interpretation

BENCH-STEER-0023 deliberately holds the same synthetic tire branches and full-steer force demands fixed while changing only the supplied velocity-center position.

The full-steer force inversion gives approximately:

- inside required slip: `2.5 deg`;
- outside required slip: `9.714285714 deg`.

At the benchmark's synthetic curvature, placing the velocity center on the rear axle creates enough geometric inner/outer velocity-heading split that the final full-steer pair is pro-Ackermann. Moving the same motion state's velocity center longitudinally to `S=a1` makes the front wheel-center velocity headings equal; the same unequal tire-required slips then produce anti-Ackermann.

This is the specific software-level demonstration of the concern that motivated the user discussion: tire load sensitivity can point toward anti-Ackermann while the final steering regime still depends on the vehicle velocity field.

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

The PR is review-ready when:

- equation/model/authorization/benchmark records validate;
- exact kinematic limiting cases pass;
- the same-slip/different-velocity-center regime result is frozen;
- the reference candidate completes MOD-STEER-0001 evaluation;
- all prior steering/vehicle tests and report stages remain green;
- new benchmark reports are uploaded by CI.
