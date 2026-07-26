# Phase 2 WUFR Z-Bar Map Authorization Review

**Authorization:** `AUTH-SUSP-0006`  
**Model:** `MOD-SUSP-0005`  
**PR51:** source-boundary gate, merged  
**Current revision:** nominal mechanism-fixture authority  
**Status:** review-ready after green CI

## Decision requested

Approve the recovered named WUFR Z-bar nominal point/topology fixture while continuing to block the scalar `delta_b(q_L,q_R)`, its Jacobian, and vehicle-coordinate ARB generalized force until the two-ended blade elastic-coordinate reduction is explicitly frozen.

## Why this revision exists

PR50 corrected the governing WUFR constitutive authority to the discrete SolidWorks blade-tip stiffness law:

`F_b = k_b delta_b`

`U_b = 0.5 k_b delta_b^2`.

PR51 then correctly rejected body-roll, track, wheel-travel, scalar-motion-ratio, sketch-row, and reduced-stiffness back-conversion shortcuts. It conservatively left the entire named mechanism fixture unresolved.

A deeper pass through the files already available to the project shows that the nominal mechanism fixture **is** recoverable without using those shortcuts.

## Recovered nominal fixture

Cross-source agreement among the populated WUFR-26 suspension/ARB geometry, ARB assemblies/drawings, Simscape lineage, ARB owner's manual, WUFR-25 inboard FDR, and structural design binder identifies:

- central blade/housing pivot and `+z` pivot axis;
- left/right blade-link joints at opposite blade ends;
- left/right rocker ARB pickups;
- the corresponding reviewed `MOD-SUSP-0003` rocker pivots and `+x` axes;
- nominal rigid-link geometry.

Raw exporter sketch row order is still explicitly non-authoritative. The row coordinates are used only after the physical roles are independently identified.

## Frozen identity checks

Front:

- blade half-span: `0.0725424000193 m` = `2.85600000076 in`;
- tip-to-tip span: `0.145084800039 m`;
- left/right nominal joint-center link length: `0.227517947831 m`;
- nominal blade-arm/link angle: `88.8740442205 deg`;
- physical linkage tube drawing length remains separately labelled `7.22 in`.

Rear:

- blade half-span: `0.0725423996293 m` = `2.85599998541 in`;
- tip-to-tip span: `0.145084799259 m`;
- left/right nominal joint-center link length: `0.198151336665 m`;
- nominal blade-arm/link angle: `86.7741933427 deg`;
- physical linkage tube drawing length remains separately labelled `6.22 in`.

The recovered angles independently agree with the WUFR-25 FDR's approximately 90-degree static blade/link design narrative.

## Rocker-state integration

The rocker ARB pickups are fixed points on the rockers. Their motion is therefore authorized to use the already-reviewed `MOD-SUSP-0003` one-axis rocker state and rigid point-transport primitive.

No historical scalar motion ratio is promoted into the ARB map.

## Rear registration boundary

The raw rear ARB sketch is registered into the rear OptimumK local suspension frame using the historical source translation `+1.5604 m` in x. This exactly maps the raw central pivot x `-1.582625 m` to rear-local x `-0.022225 m`.

This value is source-frame registration only. It does **not** replace the separately reviewed current WUFR-27 wheelbase `1.5624 m`.

## Preserved PR50 authority

The governing blade settings remain exactly:

- `280000 N/m`
- `300000 N/m`
- `400000 N/m`
- `700000 N/m`
- `2300000 N/m`

with discrete setting selection only. No interpolation or source stacking is introduced.

## Remaining blocking question

The physical blade has two end linkages, while PR50 intentionally exposes one scalar `delta_b` and one energy law.

The recovered files do not explicitly state whether the governing SolidWorks `k_b` should be interpreted as a one-arm/one-end tip stiffness or as an already condensed symmetric two-ended installed-blade mode.

Therefore this revision does **not**:

- double the PR50 energy;
- halve the PR50 stiffness;
- introduce a `sqrt(2)` modal coordinate;
- instantiate separate left/right copies of the blade energy;
- back-fit the scale from historical axle roll stiffness.

That narrower coordinate-definition question must be resolved before a numerical map implementation.

## Benchmarks

`BENCH-SUSP-0013` remains the source-authority/shortcut-rejection gate.

`BENCH-SUSP-0014` freezes the recovered nominal mechanism fixture, frame registration, rocker-point transport, nominal symmetry/length/angle checks, and the explicit no-rescaling boundary.

## Sequencing decision

After approval/merge of this revision, the next work item is to freeze the exact installed two-ended-blade deformation corresponding to the single PR50 `delta_b`. A later implementation PR can then solve the linkage closure and `J_delta_b` against the already frozen fixture.

Quasi-static vehicle equilibrium/load-state work remains downstream of that reviewed map.
