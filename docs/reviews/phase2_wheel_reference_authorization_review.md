# Phase 2 wheel-reference and physical-state authorization review

## Decision requested

Review `AUTH-SUSP-0002` as the next bounded suspension slice after the successful `MOD-SUSP-0001` rigid double-wishbone implementation.

The proposed model is intentionally an adapter, not a new mechanism solver. It composes the existing rigid upright state with source-backed wheel references and introduces the first physical suspension-state coordinate without renaming the internal lower-arm angle.

## Why this is now supportable

The current project sources provide stronger evidence than was available when PR38/PR39 deliberately prohibited wheel-center inference.

### 1. Nominal wheel center can be reconstructed directly from the OptimumK source

The frozen WUFR OptimumK setup records zero wheel offsets, half-track, static camber, static toe, and tire diameter. The frozen OptimumK result independently exposes the nominal wheel-center coordinates.

For the current source case, the source-backed construction

```text
x_wc = 0
y_wc = side_sign * (half_track + tire_radius*sin(static_camber))
z_wc = tire_radius*cos(static_camber)
```

reproduces the nominal front and rear result coordinates to floating-point/result precision.

This is materially different from the previously prohibited idea of guessing wheel center from half-track/tire size alone: the rule is now frozen as a **source-specific OptimumK construction and independently cross-checked against the result export**. Nonzero wheel-offset semantics remain prohibited.

### 2. Wheel-plane orientation already has a reviewed project convention

`MOD-STEER-0001` already uses source static toe/camber through `reference_from_static_alignment`. `AUTH-SUSP-0002` reuses that exact convention so suspension and steering share one wheel-plane sign definition.

### 3. Historical front source steering can be removed exactly from 3D result geometry

The pure-heave OptimumK workbook contains lower/upper upright points and the upright tie point. Comparing the actual tie point to the `EQ-SUSP-0003` minimum-twist transported reference reveals the source tie-rod-induced rotation about the current steering axis.

Applying the inverse of that reconstructed twist to the source wheel center matches the minimum-twist unresolved-steering wheel-center transport at floating-point scale over all 11 frozen states.

This resolves the former double-counting blocker without requiring a heuristic conversion from the scalar result channels.

A critical finding is that OptimumK's scalar `Steer Angle` channel is **not** the same as the three-dimensional upright twist about the current steering axis. At the `-25.4 mm` front-heave endpoint, the scalar channel is about `-0.1534 deg`, while the tie-point-derived 3D twist is about `-0.24354 deg`. The proposed authorization explicitly prohibits using scalar `Steer Angle` as the 3D unsteering rotation.

### 4. A physical state coordinate can now replace user-facing q_L

`MOD-SUSP-0001` correctly retains lower-arm angle `q_L` as an internal mechanism coordinate. The next adapter defines

```text
delta_z_wc_body = z_wc(q_L) - z_wc(0)
```

and solves the bounded inverse for `q_L`. This gives later heave/bump/rebound/state providers a physically meaningful interface while preserving exact mechanism equations underneath.

## Source authority reviewed

Primary kinematic sources:

- `WUFR-26 FINAL 8.21.2025.xlsx`, Box `2014803790843`, version `2224178574043`, SHA-1 `15eadfb93369192038888da92ebaa6674db56cfa`;
- `WUFR-26 8.21 Heaves 1inch.xlsx`, SHA-256 `db071b7e696149ec82213e9ed05aa557349d18d19debe7925e7e01058534e4b8`, OptimumK Result `2.3.0`.

Physical architecture evidence:

- front-right upright drawing Box `2071451248395`, SHA-1 `74a6afa2b8d712f240a84f2b864f1771cb382491`;
- front hub drawing Box `2013149176102`, SHA-1 `dc9777af31a179c5ef840cdb34cda39923fe5a3d`;
- front hub assembly drawing Box `2181097379981`, SHA-1 `d567e7e8b24808a4716f2ca7e95921acff46a95e`.

The drawings support the rigid idealization of the hub/wheel axis being carried by bearings in the upright, but do not provide installed play/compliance/metrology authority.

## Proposed records

- authorization `AUTH-SUSP-0002`;
- model `MOD-SUSP-0002`;
- equations `EQ-SUSP-0005` through `EQ-SUSP-0008`;
- benchmarks `BENCH-SUSP-0004` through `BENCH-SUSP-0006`;
- fixture `WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0`;
- source audit `docs/models/suspension/wheel_reference_source_audit.md`;
- function specification `docs/models/suspension/wheel_reference_function_specification.md`.

## Scope that remains deliberately outside authorization

This review does **not** authorize:

- generic nonzero OptimumK wheel-offset interpretation;
- generic contact-patch/tire-envelope construction or tire deflection;
- front steering closure inside suspension;
- whole-vehicle front/rear source-origin translation from wheelbase alone;
- pushrod/pullrod, rocker, spring, damper, ARB, or motion ratio;
- roll-center/anti geometry expansion;
- loads, compliance, vehicle equilibrium, tire forces, or aero;
- installed/as-built or production geometry claims.

## Benchmark gates before implementation can merge

`BENCH-SUSP-0004` must prove nominal four-corner wheel-center reconstruction and wheel-plane basis.

`BENCH-SUSP-0005` must prove 3D source-steering removal over all 11 front pure-heave states and ensure scalar OptimumK `Steer Angle` is never used as the rotation input.

`BENCH-SUSP-0006` must prove bounded physical displacement inversion, including out-of-domain and ambiguity failures.

## Recommended disposition

Approve `AUTH-SUSP-0002` for a separate implementation PR after this authorization merges. The evidence is sufficient for the bounded wheel-reference/state-adapter scope and no additional user-supplied geometry is required at this gate.