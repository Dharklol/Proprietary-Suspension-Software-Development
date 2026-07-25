# WUFR-26 suspension actuation source audit

**Scope:** source review for `AUTH-SUSP-0003` / `MOD-SUSP-0003`  
**Decision:** source package is sufficient for a bounded rigid actuation-kinematics prototype; no team input is required at this gate.

## 1. Primary kinematic authority

The existing frozen OptimumK snapshot already contains the nominal actuation geometry for all four corners:

- front actuation attachment role: **upper arm**;
- rear actuation attachment role: **lower arm**;
- arm-side push/pull attachment;
- fixed coilover chassis attachment;
- rocker pivot and rocker-axis point;
- rocker push/pull-rod attachment;
- rocker coilover attachment.

Primary source remains `WUFR-26 FINAL 8.21.2025.xlsx` (Box `2014803790843`, version `2224178574043`, provider SHA-1 `15eadfb93369192038888da92ebaa6674db56cfa`). The canonical snapshot is `data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml`.

Nominal source scalars reconstructed by the OptimumK result are:

| axle | push/pull length | coilover length | actuation arm |
|---|---:|---:|---|
| front | 315.385 mm | 164.600 mm | upper A-arm |
| rear | 326.999 mm | 164.611 mm | lower A-arm |

These are ideal joint-center quantities, not installed metrology.

## 2. Cross-tool motion evidence

`WUFR-26 8.21 Heaves 1inch.xlsx` (Box `2014806871001`, provider SHA-1 `4f2d1202d3bbd4be1b42f6e1c552919572078f67`; previously frozen raw SHA-256 `db071b7e696149ec82213e9ed05aa557349d18d19debe7925e7e01058534e4b8`; OptimumK Result v2.3.0) exposes the channels needed for an independent implementation comparison:

- coilover chassis / rocker points;
- rocker pivot / axis;
- push/pull rocker / outboard points;
- push/pull length;
- coilover length;
- coilover displacement;
- historical `Motion Ratio Heave`.

The source has eleven unique pure-heave states from `-25.4 mm` through `+25.4 mm`. `benchmarks/suspension/WUFR26_OPTIMUMK_ACTUATION_V0.toml` freezes front/rear coilover length/displacement and the historical ratio channel for those states.

For point-coordinate comparison the same result-frame rule already reviewed for suspension kinematics applies: subtract the source `[0,0,heave_mm]` chassis translation before the project OptimumK-to-canonical orientation/unit transform. Scalar lengths and displacements do not require this translation.

## 3. Hardware corroboration

The following WUFR-26 drawings/CAD records corroborate that the modeled pickups correspond to physical rocker/damper architecture:

- front rocker `SU-70401-AA - FRONT ROCKER.pdf`, Box `2127681297030`, version `2351794211430`, SHA-1 `6efe2f2e65f6231a3e1e24926f5225bd652caa9d`;
- front rocker assembly `SU-A0704-AA FRONT ROCKERS.pdf`, Box `2127683470999`, version `2351796282199`, SHA-1 `0a4c77ebca6a92618e0546f77059120359922c01`;
- rear rocker `SU-A070601-AA REAR ROCKER.pdf`, Box `2127710951300`, version `2351825113700`, SHA-1 `542ad39a590bffce378d7826b2bd1e2aed842859`;
- front rocker-fixed OptimumK file `WUFR-26 Front FINAL 8.22.25 Rocker Fix.O2Sus`, Box `1962894525462`, version `2166066613382`, SHA-1 `26f58276a19c61009b5a6412367e87ab9c43b67e`.

The front rocker drawing explicitly calls out damper and bearing/shaft fitment features; the rear rocker drawing similarly calls out damper and rod-end fitment. Those drawings are **corroborating physical architecture evidence only**. They do not override the frozen OptimumK joint-center geometry or establish installed bearing play, joint-center metrology, compliance, or travel limits.

## 4. Motion-ratio convention audit

The historical `WUFR-26 Inboard Suspension Calculator` contains:

```text
MR_f = 1.22
MR_r = 1
IR_f = 1/MR_f
IR_r = 1/MR_r
wheel spring stiffness = spring stiffness * IR^2
```

That is consistent with a historical wheel-travel-over-damper-travel style scalar. OptimumK also exports `Motion Ratio Heave` near `1.22` front and `1.00` rear at nominal.

Neither source is adopted as the canonical project definition because the historical OptimumK heave coordinate is not the same quantity as `MOD-SUSP-0002` body-frame wheel-center vertical displacement.

`EQ-SUSP-0012` therefore freezes the new project quantity explicitly as

```text
rho_dw = d(delta_L_d) / d(delta_z_wc_body)
```

with:

- `delta_L_d > 0`: coilover extension;
- `delta_z_wc_body > 0`: wheel center moves upward relative to the body;
- sign retained;
- reciprocal reported only when well-conditioned.

The source `Motion Ratio Heave` remains comparison evidence and must never be silently substituted for `rho_dw`.

## 5. Authority boundary

The source package is sufficient to authorize **ideal rigid actuation kinematics** only. It does not establish:

- usable damper shaft stroke;
- bump/droop stops or top-out;
- rod-end/spherical-bearing articulation limits;
- packaging or tire/chassis clearance;
- spring or damper force law;
- ARB coupling or stiffness;
- loads, friction, compliance, backlash, or durability;
- installed/as-built geometry.

The `+/-25.4 mm` OptimumK sweep is a verification domain, not installed travel authority.
