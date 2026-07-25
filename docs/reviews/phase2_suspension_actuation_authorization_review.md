# Phase 2 suspension actuation authorization review

**Authorization:** `AUTH-SUSP-0003`  
**Model:** `MOD-SUSP-0003`  
**Equations:** `EQ-SUSP-0009` through `EQ-SUSP-0012`  
**Benchmarks:** `BENCH-SUSP-0007`, `BENCH-SUSP-0008`  
**Status:** review ready

## Review question

Is the current WUFR source package sufficient to authorize a bounded ideal rigid actuation prototype from solved suspension state through push/pull rod, rocker, and coilover displacement without silently importing force, ARB, packaging, or installed-state claims?

## Source findings

Yes, for the bounded ideal-kinematic slice.

The source-frozen OptimumK setup already contains explicit front/rear actuation points and roles. The front push/pull attachment is on the upper A-arm; the rear attachment is on the lower A-arm. The source also supplies fixed coilover chassis points, rocker pivot/axis, rocker rod points, and rocker coilover points.

The historical OptimumK pure-heave result independently exposes front and rear:

- push/pull length;
- coilover length and displacement;
- moving rocker/push-pull points;
- `Motion Ratio Heave`.

Eleven source states from `-25.4 mm` to `+25.4 mm` are frozen in `WUFR26_OPTIMUMK_ACTUATION_V0`.

Hardware drawings for the front rocker, front rocker assembly, and rear rocker corroborate that the source mechanism corresponds to the physical rocker/damper architecture. They are not promoted above the OptimumK joint-center geometry and do not establish installed metrology or motion limits.

## Definition decision

The project will **not** create a bare `motion_ratio` output.

The canonical new local quantity is:

```text
rho_dw = d(delta_L_d) / d(delta_z_wc_body)
```

where `delta_L_d` is ideal coilover eye-to-eye length change, extension positive, and `delta_z_wc_body` is the already reviewed body-frame wheel-center vertical displacement, upward positive.

The historical OptimumK `Motion Ratio Heave` channel and the team calculator's `MR_f=1.22`, `MR_r=1` remain provenance/comparison evidence only. They use a historical heave coordinate/convention and must not be silently substituted for `rho_dw`.

## Equation packet

### `EQ-SUSP-0009`

Rigidly transport the arm-side actuation point using the owning arm's reviewed hinge-axis rotation: front `q_U`, rear `q_L`.

### `EQ-SUSP-0010`

Rotate one rigid rocker about its frozen axis and solve push/pull-rod invariant-length closure on the branch connected to nominal `theta_R=0`.

### `EQ-SUSP-0011`

Calculate ideal coilover eye-to-eye length and `delta_L_d=L_d-L_d0`.

### `EQ-SUSP-0012`

Calculate/report the explicitly signed local damper-over-wheel derivative and only a conditioned reciprocal.

## Benchmark decision

`BENCH-SUSP-0007` provides an independent analytical mechanism test, including unreachable, ambiguous-root, degenerate-axis, and derivative-conditioning cases.

`BENCH-SUSP-0008` requires the later implementation to match the frozen WUFR-26 front/rear coilover length/displacement across all eleven source heave states. Because the Box/result text representation carries millimetric displayed precision, the cross-tool acceptance is intentionally `0.10 mm`, not an invented micrometric tolerance.

The OptimumK source heave range remains a **verification domain only**.

## Explicit exclusions

This review does not authorize:

- spring or damper force laws;
- wheel rate or damping;
- ARB kinematics/stiffness/preload;
- load transfer or vehicle roll equilibrium;
- member loads/stress;
- compliance/backlash/friction;
- bump/droop stops or usable damper stroke;
- joint articulation, packaging, or clearance;
- installed/as-built authority;
- optimization or production release.

## Decision

`AUTH-SUSP-0003` is **review ready**. After review and merge, a separate implementation PR may implement only `EQ-SUSP-0009..0012` and must pass `BENCH-SUSP-0007/0008` plus structured failure tests before `MOD-SUSP-0003` is considered implemented.

No additional team geometry or source input is required for this authorization gate.
