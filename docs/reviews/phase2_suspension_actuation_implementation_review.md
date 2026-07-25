# Phase 2 suspension actuation implementation review

**Model:** `MOD-SUSP-0003`  
**Authorization:** `AUTH-SUSP-0003`, merged in PR #43  
**Implementation PR:** #44  
**Implementation package:** `src/pssd_suspension/actuation.py`

## Decision

**Accepted for review as a bounded prototype implementation of `EQ-SUSP-0009` through `EQ-SUSP-0012`.**

The implementation remains restricted to rigid ideal actuation kinematics and the explicitly signed local displacement derivative authorized by `AUTH-SUSP-0003`. Nothing in this review upgrades spring/damper, anti-roll-bar, load, compliance, packaging, physical travel, installed/as-built, or optimization authority.

## 1. Authorization conformance

The implementation preserves the source ownership frozen in PR #43:

- front push/pull attachment is transported with the **upper A-arm** rotation;
- rear push/pull attachment is transported with the **lower A-arm** rotation;
- rocker motion is one rotational DOF about the source-frozen chassis axis;
- push/pull length is invariant;
- coilover displacement is current ideal eye-to-eye length minus nominal length, extension positive;
- `rho_dw` is `d(delta_L_d)/d(delta_z_wc_body)` with sign retained;
- OptimumK `Motion Ratio Heave` is comparison-only historical evidence.

The public result contract explicitly records `installed_limits_evaluated = false`.

## 2. Numerical-method review

The rocker closure is implemented by reducing the invariant-length equation to an exact trigonometric scalar form,

```text
A cos(theta_R) + B sin(theta_R) + C = 0.
```

This satisfies the authorization allowance for an "algebraically equivalent branch-controlled geometric closure." All real roots inside the reviewed rocker-angle domain are enumerated. The branch choice is not hidden in a nonlinear optimizer: the implementation selects the unique root nearest the previous accepted rocker angle and rejects tied continuation choices as `rocker_branch_ambiguity`.

The solver also rejects:

- degenerate rocker axes;
- unreachable arm-attachment states;
- roots outside the declared rocker domain;
- excessive post-solve push/pull length residual.

The coilover eye is then transported by the same rigid axis rotation and checked geometrically.

The local derivative wrapper obtains neighboring states through the reviewed `MOD-SUSP-0002` body-frame wheel-center coordinate. It uses a centered physical-coordinate difference where possible, a labelled one-sided difference only at a domain boundary, and reports the actual coordinate separation. Reciprocal `rho_wd` is unavailable when `rho_dw` is too small to invert robustly.

## 3. Independent analytical benchmark — BENCH-SUSP-0007

The synthetic fixture verifies a known rocker angle, exact push/pull closure, signed derivative convention, unreachable closure behavior, and alternate-root ambiguity.

Frozen implementation result:

| Quantity | Result |
|---|---:|
| rocker-angle error | `5.551115123125783e-16 rad` |
| push/pull residual | `2.220446049250313e-16 m` |
| expected `rho_dw` | `-0.2` |
| computed `rho_dw` | `-0.19999999999999998` |
| unreachable case | `no_rocker_root` |
| tied multi-root case | `rocker_branch_ambiguity` |

`BENCH-SUSP-0007` passes.

## 4. WUFR cross-tool benchmark — BENCH-SUSP-0008

The external benchmark composes the native suspension/wheel-reference/actuation chain against the frozen WUFR-26 OptimumK pure-heave result for:

- front and rear;
- left and right source-mirrored corners;
- all 11 historical source states from `-25.4 mm` to `+25.4 mm`;
- 44 unique corner states total.

Each branch begins at nominal and continues outward so both the suspension and rocker solvers receive explicit continuation history.

Frozen result:

| Quantity | Maximum / value | Acceptance |
|---|---:|---:|
| coilover length error | `1.264475856466163e-06 m` | `1.0e-04 m` |
| coilover displacement error | `6.515528464430542e-07 m` | `1.0e-04 m` |
| push/pull length residual | `5.551115123125783e-17 m` | `1.0e-09 m` |
| nominal front-left `rho_dw` | `-0.8272377682304447` | signed finite result |
| conditioned reciprocal `rho_wd` | `-1.2088422922699882` | descriptive only |
| historical OptimumK Motion Ratio Heave | `+1.221` | comparison only |

The opposite sign between the native canonical derivative and the historical source channel is intentional and demonstrates why the source scalar must not be substituted for `rho_dw`.

`BENCH-SUSP-0008` passes.

## 5. Rear source-state recovery note

The authorization fixture originally contained the source scalar actuation outputs but not a rear internal `q_L` driver. PR #44 therefore freezes a bounded external-benchmark adapter:

1. take each historical rear lower-upright result point from the reviewed Box text representation;
2. apply the already reviewed pure-heave body re-reference;
3. compute signed lower-arm rotation about the frozen fore-to-aft hinge with the same angle convention as `EQ-SUSP-0001`;
4. use those values only to drive the historical cross-tool benchmark.

The Box result coordinates are available to 0.001 mm, so the recovered rear `q_L` values are not promoted to nominal geometry or installed-state authority. The observed cross-tool error remains approximately two orders of magnitude inside the frozen `0.10 mm` acceptance tolerance.

## 6. CI evidence

The first full implementation workflow on PR #44, GitHub Actions run `30151540072`, completed the focused suspension test suite, generated all suspension reports including the new actuation report, and uploaded the report artifact successfully.

The frozen benchmark metrics in `benchmarks/suspension/suspension_actuation_result_v0.1.0.toml` are taken directly from that report artifact.

A final clean workflow run is still required on the completed PR head before merge.

## 7. Remaining restrictions

The following remain separate authorization problems:

- spring and damper constitutive behavior;
- wheel rate, ride rate, damping ratio, or effective damping;
- anti-roll-bar geometry, stiffness, preload, or coupling;
- tire stiffness and tire-force effects;
- vehicle roll, pitch, load transfer, or equilibrium;
- compliance, backlash, bearing/joint play;
- pushrod/rocker/damper member loads or stress;
- physical bump/droop stops and usable damper stroke;
- joint articulation, thread engagement, packaging, serviceability, and manufacturing feasibility;
- installed/as-built correlation;
- optimization or production geometry selection.

## 8. Next gate

After PR #44 review and merge, `MOD-SUSP-0003` may serve as the source-bounded ideal actuation-state provider for later suspension R&D. Any model that converts this geometry into wheel rate, damping, anti-roll stiffness, loads, or vehicle roll/ride behavior requires its own authorization packet and benchmarks rather than extending this implementation implicitly.
