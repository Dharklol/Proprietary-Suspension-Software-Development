# Phase 2 Anti-Roll-Bar Authorization Review

**Authorization:** `AUTH-SUSP-0005`  
**Model:** `MOD-SUSP-0005`  
**PR:** #49  
**Status:** reviewer approved with reduced-stiffness source update; merge after green CI

## Proposed authorization

Authorize the first bounded conservative anti-roll-bar prototype contract:

- `EQ-SUSP-0016` — source-defined bilateral elastic deformation coordinate/vector and Jacobian;
- `EQ-SUSP-0017` — conservative stored energy, conjugate elastic action, and tangent stiffness/matrix;
- `EQ-SUSP-0018` — signed generalized ARB force from virtual work;
- `ASM-SUSP-0003` — WUFR-27 Z-bar carryover, zero-preload, and reviewer-selected reduced roll-stiffness boundary;
- `BENCH-SUSP-0011` — analytical common/differential synthetic benchmark;
- `BENCH-SUSP-0012` — WUFR geometry/source/reduced-stiffness authority benchmark.

No ARB implementation is included in PR #49.

## Key architecture decision

The ARB is not represented as an independent spring at each wheel and is not governed by an `ARB wheel rate` scalar.

The sequence is:

`(left state, right state, geometry) -> s_ARB, J_s`

`s_ARB -> U_ARB, a_ARB, K_ARB`

`Q_ARB = -J_s^T a_ARB`

For the first WUFR reduced implementation, the source-defined scalar coordinate is an effective axle ARB differential/roll angle `phi_ARB`, and the selected `K_phi` is already an axle-level reduced stiffness. A detailed Z-bar/blade reconstruction remains a future replacement fidelity layer.

## WUFR evidence accepted now

The source packet freezes:

- reviewer direction to carry the 2025 Z-bar/blade design basis into WUFR-27;
- zero intentional ARB preload;
- populated WUFR-26 suspension and front/rear ARB geometry/drawings as carryover design-intent evidence;
- current front/rear blade material and linkage identities;
- raw exporter ARB sketch points with an explicit no-connectivity-inference warning;
- 2025 ARB Stiffness SolidWorks Simulation lineage;
- WUFR-26 active/suppressed ARB assembly-state evidence;
- current WUFR-27 A0303/A0305 identical-file placeholder condition;
- `Weight_transfer_sensitivity.m` source identity and raw `K_phif_neutral=2560`, `K_phir_neutral=2270` values;
- the source's displayed `N*m/deg` unit context and front-line `%change and figure out` warning;
- the reviewer's explicit decision to use those values as the most reliable available reduced ARB stiffness, with Instron described as qualitative corroboration.

## Numeric WUFR reduced stiffness now authorized

The reviewer's 2026-07-26 decision promotes only the two MATLAB values to prototype design-intent authority:

- front `K_phi = 2560 N*m/deg = 146677.19555349075 N*m/rad`;
- rear `K_phi = 2270 N*m/deg = 130061.41949469688 N*m/rad`.

The script itself uses the K values mainly through their ratio and therefore does not independently validate the absolute scale. The absolute-value authority is the team's explicit reviewer selection, not a claim that the script contains a complete derivation.

For radian deformation:

`U_ARB = 0.5 K_phi phi_ARB^2`

`M_ARB = K_phi phi_ARB`

At exactly `1 deg` deformation the restoring-action magnitude is therefore `2560 N*m` front and `2270 N*m` rear. This is a useful benchmark because it simultaneously checks the source value and the degree-to-radian conversion.

The values are **effective axle ARB roll stiffness**, not blade torsional stiffness. An additional Z-bar/motion-ratio stiffness reduction would double-count the source quantity and is prohibited.

## Evidence still deliberately unavailable

The 2025 SolidWorks files do not yet provide a traceable component force-deflection/torque-angle result with the full load/fixture/deformation definition. Exact Instron data also has not been frozen in this packet.

Those gaps block a detailed blade/system constitutive model and quantitative test correlation. They do **not** block the explicitly reduced 2560/2270 prototype selected by the reviewer.

The 2026 spec-sheet `Suspension Roll rate` values `556 N*m/deg` front and `458 N*m/deg` rear remain whole-suspension comparison values and are not substituted for the selected ARB law.

## Zero preload

Zero preload is a named setup/reference statement, not permission for hidden offset correction. The source-specific bilateral/reduced coordinate must define the nominal state consistently before `s_ARB=0` or `phi_ARB=0` is accepted as its zero-energy reference.

## Configuration boundary

The current WUFR-26 `FSA` assembly has the front ARB active and the rear top-level ARB suppressed. The authorization records that state but does not generalize it into a WUFR-27 design rule.

A later vehicle configuration must state front/rear ARB enablement explicitly. An explicit no-bar mode returns zero energy/action/generalized force with provenance; it is not modeled as a present bar with zero stiffness.

## Benchmarks before implementation merge

`BENCH-SUSP-0011` requires the synthetic differential mechanism to demonstrate common-mode cancellation, nonzero equal-and-opposite response, sign preservation, energy-gradient agreement, explicit preload/reference behavior, explicit no-bar behavior, and structured failures.

`BENCH-SUSP-0012` additionally requires:

- exact source/provenance freeze for 2560/2270;
- exact `N*m/deg -> N*m/rad` conversion;
- one-degree front/rear action and energy hand cases;
- proof that no additional motion-ratio reduction is applied;
- preservation of the FEA, spec-sheet, Instron, assembly-state, and installed-authority boundaries.

## Explicitly excluded

Damper force, spring-force duplication, tire force, vehicle equilibrium/load transfer, contact-mode switching, linkage/member/bearing reactions, blade stress/fatigue/FEA release, quantitative Instron correlation, friction/backlash, installed limits, packaging, installed/as-built validation, and production optimization.

## Reviewer decision

On 2026-07-26 the reviewer approved PR #49 and directed that the MATLAB values `2560` front and `2270` rear be used because they are the most reliable available ARB values; available Instron data was described as somewhat close, while the MATLAB/simulation values were more consistent for the stiffer settings. Merge approval therefore authorizes implementation of the bounded coupled mechanics **and** the explicitly reduced WUFR effective axle roll-stiffness law above, subject to green CI and the preserved authority boundaries.
