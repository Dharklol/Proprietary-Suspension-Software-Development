# Phase 2 Anti-Roll-Bar Implementation Review

**Model:** `MOD-SUSP-0005`  
**Authorization:** `AUTH-SUSP-0005` / PR #49  
**Implementation PR:** #50  
**Status:** review-ready after green final-head CI

## Implemented scope

PR #50 retains the authorized generic conservative ARB architecture:

- source-defined signed elastic coordinate/reference (`EQ-SUSP-0016`);
- linear conservative action, energy, and tangent stiffness (`EQ-SUSP-0017`);
- signed generalized force `Q_ARB=-J_s^T a_ARB` when the relevant Jacobian is available (`EQ-SUSP-0018`);
- explicit no-bar configuration;
- structured source/configuration/unit/domain failures;
- executable `BENCH-SUSP-0011/0012`, frozen result record, and regression tests.

The WUFR-specific adapter has been revised to use the corrected governing constitutive source rather than the previously promoted reduced axle MATLAB values.

## Governing WUFR source

Primary authority is the Google Sheet `ARB FEA vs Simulink`, column `FEA SolidWorks Stiffness`:

- setting 1: `280 N/mm` (`280000 N/m`);
- setting 2: `300 N/mm` (`300000 N/m`);
- setting 3: `400 N/mm` (`400000 N/m`);
- setting 4: `700 N/mm` (`700000 N/m`);
- setting 5: `2300 N/mm` (`2300000 N/m`).

The sheet beam-theory formulas use `k=3EI/L^3` and divide by `1000` from N/m to N/mm, confirming that these values are linear blade-tip force/deflection stiffness.

The governing blade law is

`F_b = k_b delta_b`

`U_b = 0.5 k_b delta_b^2`

`Q_ARB = -J_delta_b^T F_b` only when a reviewed `J_delta_b` is available.

## No interpolation or source stacking

Blade settings are discrete. PR #50 does not interpolate between settings.

Comparison-only evidence is retained separately:

- MATLAB reduced axle values `2560/2270 N*m/deg`;
- Simulink `285/309/400/724/2628 N/mm`;
- Instron `900/980/1320/1970/2630 N/mm`.

None of those values is averaged with, added to, or substituted for the governing SolidWorks FEA blade stiffness.

## Frozen verification

`BENCH-SUSP-0011` remains the generic synthetic bilateral mechanics test. It verifies common-mode cancellation, differential force/energy, equal-and-opposite generalized reactions, reference handling, no-bar behavior, structured failures, and the energy gradient.

`BENCH-SUSP-0012` freezes the simple WUFR blade-law hand case at `delta_b=1 mm`:

| Setting | Force [N] | Energy [J] |
| ---: | ---: | ---: |
| 1 | 280 | 0.140 |
| 2 | 300 | 0.150 |
| 3 | 400 | 0.200 |
| 4 | 700 | 0.350 |
| 5 | 2300 | 1.150 |

The benchmark also checks the exact comparison-only arrays, rejects interpolation, and verifies conservative blade-coordinate energy behavior.

## Critical geometry boundary

The WUFR Z-bar map

`(q_L,q_R) -> delta_b`

and its Jacobian

`partial(delta_b)/partial(q_L,q_R)`

are **not authorized or implemented in PR #50**.

Consequently, an externally supplied blade deflection may be evaluated for `F_b`, `U_b`, and tangent stiffness, but PR #50 does not manufacture vehicle-coordinate generalized ARB force from an unreviewed geometry approximation.

Specifically prohibited substitutes are:

- body roll angle equals blade deformation;
- wheel-travel/track-width approximations;
- CAD sketch row ordering as mechanism connectivity;
- historical scalar motion-ratio shortcuts.

## Configuration and source behavior

`enabled=False` remains an explicit no-bar state rather than a zero-stiffness present mechanism. Installed/as-built authority remains false. The generic ARB provider remains reusable for future source-defined coordinates; the WUFR adapter adds only the discrete blade constitutive authority and does not alter the generic mechanics.

## Explicitly excluded

No WUFR Z-bar closure, suspension-to-blade deformation map, vehicle equilibrium/load transfer, wheel-load generation, damper/tire force, linkage/member/bearing loads, blade stress/fatigue release, contact-mode switching, friction/backlash, installed limits, installed/as-built validation, or production optimization is added here.

## Next gate

Before this blade law is used to create WUFR vehicle-coordinate ARB reactions, separately review and authorize the Z-bar geometry map `(q_L,q_R)->delta_b` and its signed Jacobian. PR #50 remains open for review and must not be merged without explicit approval.
