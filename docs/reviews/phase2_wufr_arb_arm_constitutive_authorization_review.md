# Phase 2 WUFR Blade-Arm Constitutive Authorization Review

**Authorization:** `AUTH-SUSP-0007`  
**Model:** `MOD-SUSP-0005`  
**Status:** review-ready after green CI

## Source correction

A deeper read of the already-authoritative `ARB FEA vs Simulink` sheet resolves the remaining constitutive semantics.

The sheet's calculation block is explicitly labelled **Blade arm** and checks the weak/strong settings with the cantilever relation `k=3EI/L^3` using an approximately `2.3 in` arm length. The calculated weak-axis value is about `293 N/mm`, close to setting-1 SolidWorks `280 N/mm`; the strong-axis value is about `2787 N/mm`, close to setting-5 SolidWorks `2300 N/mm`.

Therefore the discrete SolidWorks setting value is used as **one blade-arm transverse tip stiffness**, not a pre-condensed whole two-ended Z-bar modal stiffness.

## Installed constitutive law

For one selected setting, the physical blade has two elastic arm coordinates:

`d = [d_L, d_R]`

`F = [k_b d_L, k_b d_R]`

`U = 0.5 k_b (d_L^2 + d_R^2)`

and, after the mechanism Jacobian is available,

`Q_ARB = -J_d^T F`.

This avoids the unsupported scalar factors considered in PR52. No `2`, `1/2`, `sqrt(2)`, averaging, or duplicated whole-bar law is introduced.

## PR50 benchmark interpretation

PR50's 1 mm values remain valid as a **one-arm local constitutive benchmark**. For setting 1, one arm at 1 mm gives `280 N` and `0.140 J`. If two arms are elastically deflected `+1 mm/-1 mm`, the two-arm state gives `[+280,-280] N` and `0.280 J` total stored energy.

## Historical 2560/2270 provenance correction

The 2025 Suspension Structural Design Binder directly reports the FEA-stiffness-to-effective-axle sequence. Its setting-1 row maps approximately `282 N/mm` to `2560 N*m/deg` front and `2270 N*m/deg` rear. `Weight_transfer_sensitivity.m` later carries `2560/2270` but does not derive them.

Thus `2560/2270` is downstream setting-1 effective axle roll-stiffness evidence from the same blade-study lineage, not an independent MATLAB constitutive source. It stays comparison-only and must not be back-fit into the geometry solver.

## Remaining gate

`WUFR26_ZBAR_MECHANISM_V0` already freezes the nominal geometry. After this authorization, the remaining implementation task is mechanical rather than semantic: solve the two rigid linkage constraints plus blade/housing internal motion to obtain `d_L,d_R` from left/right rocker states, verify the branch and energy gradient, and calculate `J_d`.
