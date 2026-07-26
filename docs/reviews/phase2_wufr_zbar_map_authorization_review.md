# Phase 2 WUFR Z-Bar Map Authorization Review

**Authorization:** `AUTH-SUSP-0006`  
**Model:** `MOD-SUSP-0005`  
**PR:** #51  
**Status:** review-ready after green CI

## Decision requested

Approve the recovered-source boundary for the WUFR Z-bar deformation map and explicitly keep numerical vehicle-coordinate ARB force blocked until a named mechanism fixture is frozen.

## Why this gate exists

PR50 corrected the WUFR constitutive authority to discrete SolidWorks blade-tip stiffness. That solved the blade force/energy law but deliberately did not define

`(q_L,q_R) -> delta_b`

or

`partial(delta_b)/partial(q_L,q_R)`.

Those quantities are required before the constitutive force can be mapped into suspension/vehicle generalized coordinates.

## Source-recovery result

The audit reviewed the team ARB Owner's Manual, WUFR-25/WUFR-26 inboard FDR material, `WUFR26InboardSuspensionCalculator.m`, `ARB Force Calculation.pdf`, `ARB Calculations.xlsx`, and populated WUFR-26 ARB/CAD lineage.

The sources establish the Z-bar architecture and useful design history, but the recovered calculations rely on vehicle-level roll/track or beam approximations and do not freeze a named assembled three-dimensional mechanism closure tied to the reviewed rocker states.

Therefore PR51 does **not** invent a numerical WUFR map.

## Preserved PR50 authority

The five governing blade settings remain:

- 280000 N/m
- 300000 N/m
- 400000 N/m
- 700000 N/m
- 2300000 N/m

with discrete setting selection only. The blade law remains valid for externally supplied signed `delta_b`.

## Prohibited shortcuts

PR51 explicitly rejects body-roll-equals-blade-deflection, track/half-track lever approximations, direct left-right wheel-travel difference, historical scalar motion ratios, exporter sketch-row topology, and inverse fitting from reduced axle stiffness.

## Required next source fixture

Before a map implementation PR, front and rear must each freeze named blade pivot/axis, blade working point/direction, linkage endpoints/length, rocker ARB pickup, relationship to the `MOD-SUSP-0003` rocker state, frames/units/signs, nominal zero-preload branch, and closure/branch rules.

## Sequencing decision

After PR51, the next work item is source extraction/review of that explicit mechanism fixture. The quasi-static equilibrium/load-state solver remains downstream of the reviewed ARB map so it can consume source-grounded generalized forces rather than embedding a geometry approximation.

This PR adds no WUFR Z-bar numerical solver and no vehicle equilibrium solver.
