# WUFR static carrier external wrench implementation v0.1.0

## Scope

`MOD-VEH-0008` implements the `AUTH-VEH-0011` adapter between the accepted WUFR static-gravity vehicle result and the existing `MOD-SUSP-0007` Level-1 suspension-interface statics contract.

It consumes the accepted `MOD-VEH-0007` state and creates one prescribed external wrench on each outboard-carrier boundary. A successful output is complete only for the exact spring-plus-Z-bar-plus-gravity, centered-rack, flat-rigid-road, all-four-active model represented upstream.

The implementation does not solve the Level-1 linkage, propagate rocker loads, create a structural packet, or add maneuver forces.

## Source-preserving load composition

For each corner, the only applied loads are:

1. the recovered road-normal reaction at the exact current rigid-circle contact point;
2. the `ASM-VEH-0003` prototype unsprung gravity point force at the exact current physical wheel center.

At the current carrier reference `O_i`,

```text
F_C,i = lambda_i n_road + F_u,i
M_C,O_i = (r_contact,i-r_O_i) x lambda_i n_road
          + (r_wc,i-r_O_i) x F_u,i
```

Both inputs are retained as separate `AppliedWrench` records. No free couple is introduced. Spring, anti-roll-bar, push/pull-rod, tie/toe-link, spherical-joint, and chassis reactions are not added because they are internal forces to be solved by `MOD-SUSP-0007`.

The complete 5 kg-per-corner prototype unsprung lump remains at the wheel center exactly as represented by `MOD-VEH-0005`. The implementation does not redistribute that mass among the wheel, upright, brake, links, damper, half-shaft, or chassis.

## Accepted upstream state

The adapter requires the accepted `MOD-VEH-0007` machine-readable record to retain:

- `AUTH-VEH-0010` and `MOD-VEH-0007` identities;
- `WUFR27_SUSPENSION_BASELINE_V0` and the driver/no-fuel static-state identity;
- the canonical FL/FR/RL/RR wheel order;
- the five governing upstream assumption IDs;
- successful all-four-active static road reactions;
- finite, nonnegative reactions;
- exact current contact and wheel-center road points;
- successful physical force/moment closure;
- no historical scale reconstruction or installed/as-built authority.

The implementation recomputes the current physical points from the accepted body and wheel coordinates and rejects disagreement with the frozen record. The accepted result is therefore not treated as an unverified list of loads.

## Carrier reference and current geometry

The reference point is reconstructed from the same current suspension geometry used by the Level-1 statics stack:

```text
r_carrier = 0.5 * (r_upper_spherical + r_lower_spherical)
```

The upper and lower outboard spherical centers are recovered at each accepted current suspension state. The implementation does not use a nominal upright origin, wheel center, contact patch, track-width shortcut, or fixed scalar offset as the carrier reference.

## Frame transformation

The exact reviewed placement chain is retained:

```text
Level-1 axle-local
-> add reviewed front/rear axle source x-position
-> reviewed source-to-body translation
-> converged BodyPose using Rz(psi) Ry(theta) Rx(phi)
-> road frame
```

The converged body roll and pitch are nonzero. Consequently, a road-vertical carrier resultant develops small nonzero Level-1 x/y force components and a nonzero Level-1 z moment. Those components are preserved rather than erased by assuming road and Level-1 axes are identical.

Road-to-Level-1 pullback and the reverse pushforward use exact rigid rotation at the same physical carrier reference. Changing the reference point is permitted only through exact wrench transport.

## Four-corner reconstruction

The implementation independently transports the four carrier resultants to a named vehicle reference, adds the matching sprung gravity point load exactly once, and reconstructs the accepted whole-vehicle physical closure.

For the frozen setting-1/1 verification fixture:

- maximum force residual: `5.189258445170708e-08 N`;
- maximum moment residual: `4.6145622656368346e-08 N*m`;
- componentwise force mismatch from the accepted `MOD-VEH-0007` closure: `2.1316282072803006e-13 N`;
- componentwise moment mismatch: `1.7541523789077473e-14 N*m`.

No balancing wrench, clipping, redistribution, fitted offset, or historical corner-load fallback is used.

## Frozen carrier resultants

The road-frame resultants at the current carrier references are:

| Corner | Force `[Fx,Fy,Fz]` N | Moment `[Mx,My,Mz]` N*m |
|---|---:|---:|
| FL | `[0, 0, 741.933101538]` | `[31.129448072, -2.555868201, 0]` |
| FR | `[0, 0, 730.545626103]` | `[-30.668690762, -2.516892988, 0]` |
| RL | `[0, 0, 677.388934540]` | `[40.332401822, -0.006115117, 0]` |
| RR | `[0, 0, 657.507613919]` | `[-39.169486962, -0.005157107, 0]` |

These values are verification outputs, not setup recommendations, measured corner loads, or structural release loads.

## Verification

`BENCH-VEH-0015` verifies:

- canonical source/corner/point ownership;
- direct force and cross-product moment composition;
- current carrier-reference construction;
- reference-point transport;
- exact road/Level-1 round trip at the accepted state;
- a separate bounded nonzero pose transform probe.

`BENCH-VEH-0016` freezes the four carrier wrenches and whole-vehicle reconstruction.

`BENCH-VEH-0017` verifies structured failure for upstream-state, reaction, point, source, frame, gravity-allocation, transport, and closure disagreements.

The full record is `benchmarks/vehicle/wufr_static_carrier_wrench_result_v0.1.0.json`; its compact gate record and full-result digest are in the matching TOML file.

## Fidelity boundary and next gate

Every success remains:

```text
result_label = uncorrelated_design_intent_static_carrier_wrench
complete_for_authorized_static_gravity_case = true
complete_physical_hardware_wrench = false
maneuver_complete = false
installed_as_built_authority = false
integrated_level1_linkage_result_authority = false
```

A separate authorization is still required to synchronously feed these four wrenches into `MOD-SUSP-0007` and publish the resulting tie/toe, push/pull, spherical-interface, and equivalent hinge loads. Rocker propagation remains a later composition and retains its missing KW V5 non-spring static-force boundary.
