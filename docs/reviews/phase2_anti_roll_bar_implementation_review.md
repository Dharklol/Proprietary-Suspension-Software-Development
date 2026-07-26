# Phase 2 Anti-Roll-Bar Implementation Review

**Model:** `MOD-SUSP-0005`  
**Authorization:** `AUTH-SUSP-0005` / PR #49  
**Implementation PR:** #50  
**Status:** review-ready after green final-head CI

## Implemented scope

PR #50 implements the conservative scalar anti-roll-bar provider authorized by PR #49:

- source-defined signed elastic coordinate/reference (`EQ-SUSP-0016`);
- linear conservative action, energy, and tangent stiffness (`EQ-SUSP-0017`);
- signed generalized force `Q_ARB=-J_s^T a_ARB` (`EQ-SUSP-0018`);
- explicit no-bar configuration;
- structured source/configuration/unit/domain failures;
- WUFR-27 reduced effective axle roll-stiffness adapter using `ASM-SUSP-0003`;
- executable `BENCH-SUSP-0011/0012`, frozen result record, and result-record regression tests.

The implementation does not add vehicle equilibrium or a detailed WUFR Z-bar mechanism solver.

## Important coordinate decision

The authorization permits a source-defined scalar or vector elastic coordinate. PR #50 keeps that contract rather than forcing every ARB into an angular blade coordinate.

`BENCH-SUSP-0011` remains exactly the authorized translational differential case:

`s=z_L-z_R-s0`, `J=[1,-1]`, `k=10000 N/m`.

The WUFR reduced adapter separately uses signed `phi_ARB` in radians because the selected source quantity is effective axle roll stiffness in `N*m/deg`.

This separation avoids silently treating wheel travel, blade angle, body roll, and reduced axle roll angle as interchangeable quantities.

## WUFR reduced law

The merged PR #49 source decision is implemented without modification:

- front `2560 N*m/deg = 146677.19555349075 N*m/rad`;
- rear `2270 N*m/deg = 130061.41949469688 N*m/rad`;
- zero intentional preload reference;
- `U=0.5 K_phi phi_ARB^2`;
- `M=K_phi phi_ARB`;
- `Q=-J_phi^T M`.

The loader computes the SI conversion from the frozen degree-based values and checks it against the source snapshot. It also checks that the selected values continue to match the raw MATLAB literals.

The definitions are explicitly tagged `reduced_axle_level=true`. No Z-bar, blade, link, or wheel motion ratio is applied to those rates.

## Why no direct WUFR geometry-to-force closure is added

The current CAD/source packet proves the Z-bar/blade design lineage but does not yet authorize a unique detailed deformation map from the existing exporter rows alone. More importantly, the selected 2560/2270 quantities are already reduced axle-level stiffness values.

PR #50 therefore requires downstream code to supply the reviewed `phi_ARB(q)` coordinate/Jacobian rather than guessing it from:

- body roll angle;
- left/right wheel travel;
- track width;
- exporter sketch row order;
- a historical scalar motion ratio.

That keeps a future detailed Z-bar mechanism reconstruction from being double-counted with the reduced source stiffness.

## Verification results frozen by the result record

`BENCH-SUSP-0011`:

- common mode: zero deformation, action, and energy;
- differential `z_L=+10 mm`, `z_R=-10 mm`: `s=20 mm`;
- action `200 N`;
- energy `2 J`;
- generalized reactions `[-200,+200] N`;
- explicit shifted reference gives `17 mm` deformation;
- explicit no-bar returns zero action/energy/generalized force;
- missing stiffness and outside-domain states return structured failures;
- centered energy finite differences verify the signed generalized force.

`BENCH-SUSP-0012`:

- exact source front/rear rates `2560/2270 N*m/deg`;
- exact SI conversion to `146677.19555349075/130061.41949469688 N*m/rad`;
- one-degree front action `2560 N*m`, energy `22.340214425527417 J`;
- one-degree rear action `2270 N*m`, energy `19.80948701013564 J`;
- front generalized force for `q=phi_ARB` is `-2560` in the conjugate generalized-force unit;
- zero-reference action/energy are zero;
- Instron remains `qualitative_corroboration_only`;
- installed/as-built authority remains false.

## Configuration behavior

`enabled=False` returns explicit `no_bar`, rather than representing a present mechanism with zero stiffness. The WUFR package loader does not infer front/rear enablement from the WUFR-26 FSA assembly where the rear top-level ARB was suppressed.

A later vehicle configuration owns that choice.

## Numerical behavior

The provider is algebraic for the first linear law. Signed generalized force is checked independently by centered finite differences of stored energy at two steps.

No clipping, absolute Jacobian, hidden reference offset, hidden unit conversion, constitutive extrapolation, or stiffness averaging occurs.

## Source limitations retained

- the MATLAB front assignment still carries `%change and figure out`;
- the source script largely exercises the rates through their ratio, so absolute-value authority is the explicit reviewer/team selection;
- exact Instron data is not frozen in this packet;
- 2025 SolidWorks Simulation data remains future detailed component-law recovery evidence;
- spec-sheet 556/458 N*m/deg suspension roll rates remain comparison-only;
- WUFR-27 direct A0303/A0305 assembly files remain identical-file placeholders in the source packet.

## Explicitly excluded

No detailed blade/component stiffness, physical Z-bar closure, body-roll-to-bar-angle inference, wheel-rate shortcut, damper force, tire force, heave/roll/pitch equilibrium, load transfer, contact-mode switching, linkage/member/bearing loads, blade stress/fatigue/FEA release, friction/backlash, installed limits, packaging, installed/as-built validation, or production optimization.

## Next gate

After PR #50 review and merge, the program can move to the separately reviewed **prescribed-force quasi-static equilibrium/load-state authorization**. That solver should consume the spring and ARB providers rather than duplicating their constitutive equations.
