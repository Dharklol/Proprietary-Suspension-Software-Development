# Anti-Roll-Bar Implementation v0.1.0

**Model:** `MOD-SUSP-0005`  
**Authorization:** `AUTH-SUSP-0005` / merged PR #49  
**Implementation PR:** #50  
**Generic package:** `src/pssd_suspension/anti_roll_bar.py`  
**WUFR adapter:** `src/pssd_suspension/wufr_anti_roll_bar.py`

## Scope

PR #50 implements a conservative coupled anti-roll-bar mechanics contract while keeping the physical elastic coordinate source-defined:

`a_ARB = dU_ARB/ds`

`Q_ARB = -J_s^T a_ARB`, where `J_s = ds/dq`.

The generic architecture is unchanged by the WUFR source correction. It does not make wheel travel, body roll, blade deformation, blade angle, and axle roll angle interchangeable.

## Generic conservative law

For a reviewed linear scalar elastic coordinate `s`:

`a = k s`

`U = 0.5 k s^2`

`Q = -J_s^T a`.

`BENCH-SUSP-0011` remains the synthetic differential case `s=z_L-z_R-s0`, `J=[+1,-1]`, `k=10000 N/m`. At `z_L=+10 mm`, `z_R=-10 mm`, it produces `s=20 mm`, `a=200 N`, `U=2 J`, and generalized reactions `[-200,+200] N`.

The implementation also retains explicit zero-energy references, explicit no-bar behavior, structured source/configuration/unit/domain failures, and independent energy-gradient checks.

## Corrected WUFR governing constitutive authority

The governing WUFR source is the Google Sheet:

`https://docs.google.com/spreadsheets/d/1rJjQBnSOMEGQmyromb9SjNgOEMwBBOdUpUKPPLOf-3c/edit?gid=0#gid=0`

sheet `ARB FEA vs Simulink`, column `FEA SolidWorks Stiffness`.

The five authorized blade settings are discrete linear blade-tip force/deflection stiffnesses:

| Setting | Source stiffness [N/mm] | SI stiffness [N/m] |
| ---: | ---: | ---: |
| 1 | 280 | 280000 |
| 2 | 300 | 300000 |
| 3 | 400 | 400000 |
| 4 | 700 | 700000 |
| 5 | 2300 | 2300000 |

The sheet's beam-theory expressions use `k=3EI/L^3` and divide by `1000` from N/m to N/mm. The governing quantity is therefore linear blade-tip stiffness, not torque per degree.

The WUFR constitutive law is

`F_b = k_b delta_b`

`U_b = 0.5 k_b delta_b^2`

and, only after a reviewed geometry Jacobian exists,

`Q_ARB = -J_delta_b^T F_b`.

`load_wufr27_blade_anti_roll_bar_package()` freezes the five values and constructs one definition per setting with coordinate unit `m`, action unit `N`, and SI stiffness in `N/m`.

## Discrete setting boundary

Settings 1 through 5 are categorical choices. The adapter rejects non-integer and out-of-range setting requests. No interpolation, averaging, blending, or stiffness stacking is authorized.

The following remain comparison-only evidence:

- historical MATLAB reduced axle values: `2560/2270 N*m/deg`;
- Simulink: `285/309/400/724/2628 N/mm`;
- Instron: `900/980/1320/1970/2630 N/mm`.

None of these is averaged with or added to the SolidWorks FEA blade stiffness.

## Frozen 1 mm blade-law benchmark

`BENCH-SUSP-0012` evaluates an externally supplied blade-tip deformation `delta_b=1 mm` without claiming a suspension-to-blade geometry map:

| Setting | Force [N] | Energy [J] |
| ---: | ---: | ---: |
| 1 | 280 | 0.140 |
| 2 | 300 | 0.150 |
| 3 | 400 | 0.200 |
| 4 | 700 | 0.350 |
| 5 | 2300 | 1.150 |

The benchmark also verifies the comparison-only arrays, discrete-selection boundary, and conservative energy gradient in blade coordinate space.

## WUFR Z-bar geometry boundary

PR #50 does **not** authorize or implement

`(q_L, q_R) -> delta_b`

or

`partial(delta_b)/partial(q_L,q_R)`.

Therefore the WUFR adapter may compute blade force, energy, and tangent stiffness for a supplied `delta_b`, but it does not claim vehicle/suspension generalized force without a separately reviewed Jacobian.

In particular, PR #50 does not infer `delta_b` from:

- body roll angle;
- left/right wheel travel alone;
- track width;
- CAD/exporter sketch row ordering;
- a scalar historical motion ratio.

Body roll is not treated as blade deformation, and no track-width approximation is used.

## Explicitly not implemented

No WUFR Z-bar closure, suspension-to-blade mapping, blade stress/fatigue release, linkage/member/bearing loads, damper force, tire force, vehicle equilibrium/load transfer, contact switching, friction/backlash/hysteresis, installed travel/limits, installed/as-built validation, or production optimization is added in PR #50.

The frozen result record is `benchmarks/suspension/suspension_anti_roll_bar_result_v0.1.0.toml`, with regression coverage in `tests/test_suspension_anti_roll_bar.py` and `tests/test_suspension_anti_roll_bar_result_record.py`.
