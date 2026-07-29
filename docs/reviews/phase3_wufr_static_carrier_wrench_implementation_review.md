# Phase 3 WUFR static carrier external wrench implementation review

## Outcome

`MOD-VEH-0008` is implemented under `AUTH-VEH-0011` and freezes four source-preserving outboard-carrier external wrenches for the accepted WUFR static-gravity verification state.

The implementation closes the interface between the accepted whole-vehicle road reactions and the already implemented Level-1 suspension statics input contract without yet publishing linkage loads.

## Mechanics implemented

Each corner contains exactly two external point-load contributions:

- recovered road-normal reaction at the exact current contact point;
- prototype unsprung gravity at the exact current physical wheel center.

The resultant is assembled at the current carrier reference, defined as the midpoint of the exact current upper and lower outboard spherical centers. The result contains no added spring, ARB, push/pull, tie/toe, ball-joint, or chassis load because those are internal suspension reactions.

The use of the entire 5 kg-per-corner prototype unsprung lump at the wheel center is source preserving for this model, but it remains explicitly nonphysical as component-level mass distribution authority.

## Upstream consistency controls

The implementation requires the accepted `MOD-VEH-0007` identity, assumptions, result labels, canonical corner/wheel order, successful contact state, finite nonnegative reactions, exact points, and physical closure. It recomputes current road/contact geometry from the accepted generalized state and fails if the points disagree.

Altered source/configuration labels, reordered coordinates, incomplete success state, nonfinite or negative reactions, changed physical points, and changed accepted closure are structured failures.

## Frame and reference controls

The adapter reconstructs the exact Level-1-to-road placement using reviewed axle source placement, source-to-body translation, and the converged body pose. It does not assume the body, road, source, and Level-1 frames are identical.

The frozen state has nonzero roll and pitch, so the equivalent Level-1 wrenches correctly contain small longitudinal/lateral components and z moments even though the road-frame force is vertical. Road/Level-1 round-trip residuals remain below `1e-10 N` and `1e-10 N*m`.

A separate bounded nonzero pose probe verifies the same transform functions independently of the frozen carrier values. Exact reference-point transport is also verified.

## Frozen integrated result

The four road-frame carrier vertical resultants are approximately:

- FL: `741.9331 N`;
- FR: `730.5456 N`;
- RL: `677.3889 N`;
- RR: `657.5076 N`.

Their nonzero carrier-reference moments are retained in the full record rather than reduced to scalar wheel loads.

Adding the matching sprung gravity once reconstructs the accepted whole-vehicle closure to:

- `5.1893e-08 N` maximum force residual;
- `4.6146e-08 N*m` maximum moment residual.

The reconstructed vector matches the accepted upstream closure componentwise to approximately `2.13e-13 N` and `1.75e-14 N*m`.

## Verification artifacts

- implementation: `src/pssd_vehicle/wufr_static_carrier_wrench.py`;
- benchmark runner: `scripts/run_wufr_static_carrier_wrench_benchmarks.py`;
- full result: `benchmarks/vehicle/wufr_static_carrier_wrench_result_v0.1.0.json`;
- compact result: `benchmarks/vehicle/wufr_static_carrier_wrench_result_v0.1.0.toml`;
- mechanics tests: `tests/test_wufr_static_carrier_wrench.py`;
- failure tests: `tests/test_wufr_static_carrier_wrench_failures.py`;
- frozen-record test: `tests/test_wufr_static_carrier_wrench_result_record.py`.

## Restrictions retained

This implementation does not authorize:

- synchronized four-corner `MOD-SUSP-0007` output publication;
- rocker reaction completion;
- maneuver tire, brake, drive, aero, inertia, gyroscopic, or alternate-contact loads;
- component-level unsprung mass distribution;
- structural packets, stress, FEA, fatigue, or factors of safety;
- physical correlation, setup selection, installed/as-built prediction, or production release.

## Next review gate

The next PR must separately authorize the synchronized composition:

```text
four MOD-VEH-0008 carrier wrenches
+ matching current suspension/steering/actuation geometry
-> four MOD-SUSP-0007 Level-1 interface solutions
```

Only after that result is reviewed should the resulting push/pull forces be propagated into the existing incomplete rocker-reaction model.
