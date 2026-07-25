# MOD-SUSP-0003 rigid suspension actuation implementation v0.1.0

**Authorization:** `AUTH-SUSP-0003`, merged in PR #43  
**Implementation:** `src/pssd_suspension/actuation.py`  
**Upstream:** `MOD-SUSP-0001`, `MOD-SUSP-0002`  
**Verification:** `BENCH-SUSP-0007`, `BENCH-SUSP-0008`

## 1. Implemented boundary

This implementation adds only the ideal rigid actuation chain authorized by `AUTH-SUSP-0003`:

```text
MOD-SUSP-0001 solved arm state
    -> EQ-SUSP-0009 arm-fixed push/pull attachment
    -> EQ-SUSP-0010 one-axis rocker closure
    -> EQ-SUSP-0011 ideal coilover eye-to-eye length/displacement
MOD-SUSP-0002 body-frame wheel-center vertical state
    -> EQ-SUSP-0012 signed local rho_dw
```

Front actuation remains source-owned by the **upper A-arm**. Rear actuation remains source-owned by the **lower A-arm**. The implementation rejects a corner whose frozen attachment role does not match that source rule.

No suspension point is transformed by the upright pose merely because it belongs to the actuation chain. The outboard push/pull attachment is transported by the owning A-arm rotation from `MOD-SUSP-0001`.

## 2. Rocker closure

The rocker has one degree of freedom about the source-frozen pivot-to-axis-reference line. The frozen push/pull-rod length is

```text
L_PP = ||p_Rod,0 - p_PP,0||.
```

Rather than iterating blindly on the scalar residual, the implementation reduces the rigid closure exactly to

```text
A cos(theta_R) + B sin(theta_R) + C = 0.
```

This is algebraically equivalent to the authorized invariant-length equation and lets the implementation enumerate every real root in the reviewed rocker domain. Root choice is then explicit:

1. use `theta_R=0` as the nominal predecessor;
2. on a continued sweep, use the preceding accepted rocker angle;
3. select the unique root nearest that predecessor;
4. reject an equally near alternative as `rocker_branch_ambiguity`;
5. reject unreachable geometry rather than changing link length, clipping the state, or selecting an out-of-domain root.

The resulting point is re-evaluated with the shared rigid-axis rotation primitive, and the physical rod-length residual must remain within the configured tolerance.

## 3. Coilover state

The rocker coilover pickup is rotated by the solved `theta_R`. The chassis eye remains fixed. The ideal joint-center length is

```text
L_d = ||p_Coil(theta_R) - p_D,ch||
```

and the public displacement is

```text
delta_L_d = L_d - L_d,0.
```

Positive means **extension**; negative means **compression**. These are ideal eye-center quantities only. The implementation does not infer usable damper stroke, bump-stop/top-out position, spring preload, or internal damper travel.

## 4. Canonical local displacement derivative

The only native ratio-like quantity is explicitly ordered and signed:

```text
rho_dw = d(delta_L_d) / d(delta_z_wc_body).
```

`delta_z_wc_body` is the reviewed `MOD-SUSP-0002` physical coordinate: wheel-center z relative to the body, positive upward. `delta_L_d` is positive coilover extension.

The physical-coordinate wrapper requests neighboring `MOD-SUSP-0002` states and uses a centered difference where both branch-preserving neighbors exist. At a reviewed domain boundary it may use a labelled one-sided difference. The actual physical coordinate separation is used in the denominator; no assumed exact `2h` replacement is made.

The reciprocal `rho_wd` is exposed only when `|rho_dw|` exceeds the configured conditioning threshold. No absolute value is applied to either ratio.

The historical OptimumK `Motion Ratio Heave` channel is retained only in the external benchmark fixture. It is never used as a native input or silently relabeled as `rho_dw`.

## 5. WUFR source benchmark state drivers

`WUFR26_OPTIMUMK_ACTUATION_V0.toml` now retains the source-derived `q_L` values required to reproduce the historical 11-state pure-heave actuation sweep.

- Front-right `q_L` is inherited from the previously reviewed front kinematics fixture.
- Front-left is its source-mirrored opposite sign.
- Rear-left `q_L` is recovered from the historical result lower-upright point after the already reviewed pure-heave body re-reference, using signed rotation about the frozen lower-arm fore-to-aft hinge.
- Rear-right is its source-mirrored opposite sign.

The rear result text is available only to 0.001 mm in the reviewed Box representation; those recovered angles therefore serve only as external benchmark drivers. They do not replace the frozen nominal hardpoints and do not create installed/as-built authority.

## 6. Result and failure contract

A successful state retains at least:

- axle, side, source/configuration authority;
- solved `q_L`, `q_U`, and owning arm;
- current arm attachment;
- rocker angle, rocker rod pickup, and rocker coilover pickup;
- nominal/current push/pull length and residual;
- nominal/current coilover length and signed displacement;
- current `delta_z_wc_body` when available;
- `rho_dw`, conditioned reciprocal, derivative method, and actual step when requested;
- explicit `installed_limits_evaluated = false`.

Structured failures include invalid source role, upstream kinematic failure, degenerate arm/rocker axes, unreachable rocker closure, branch ambiguity, excessive rod residual, physical-state inversion failure, and unavailable derivative conditioning.

## 7. Explicitly excluded

This implementation does **not** authorize or calculate spring/damper constitutive behavior, wheel rate, damping ratio/effective damping, anti-roll-bar action, load transfer, tire stiffness, compliance, member loads, stress, joint articulation, packaging/clearance, physical damper travel/stops, installed/as-built behavior, optimization, or production geometry release.

The historical ±25.4 mm OptimumK sweep remains a verification domain only.
