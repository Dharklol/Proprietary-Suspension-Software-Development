# WUFR Z-Bar Deformation-Map Source Audit

**Authorization:** `AUTH-SUSP-0006`  
**Configuration:** `WUFR27_SUSPENSION_BASELINE_V0`  
**Source record:** `data_catalog/wufr27_zbar_mapping_source_v0.toml`  
**Named fixture:** `benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml`

## Updated finding

The source set already available to the project is sufficient to freeze the **nominal WUFR Z-bar point/topology fixture**.

PR51 was correct to reject the historical roll/track shortcuts, but its stronger statement that the named mechanism fixture itself was unavailable was too conservative. The raw ARB sketch points become usable once their roles are assigned from independent topology evidence rather than from row order.

The recovered fixture now identifies, for each axle:

- central blade/housing pivot and `+z` pivot axis;
- left/right blade-link joints at opposite blade ends;
- left/right rocker ARB pickups;
- the corresponding reviewed `MOD-SUSP-0003` rocker pivots and `+x` axes;
- nominal rigid linkage joint-center lengths;
- the source-frame relationship needed to register the rear ARB sketch to the rear OptimumK local frame.

This still does **not** finish the WUFR map. The remaining source question is narrower: how the installed two-ended blade deformation is reduced to the single scalar PR50 elastic coordinate `delta_b` associated with the governing SolidWorks `k_b`.

## Evidence used to assign point roles

### Populated suspension / ARB geometry

The prior source package had already frozen raw front/rear ARB sketch coordinates from:

- `SU-00001-AA 2026 SUSPENSION GEOMETRY.SLDPRT`;
- Box `1943897977651`;
- SHA-1 `2cfb771f296961be0857161f7b57a6c178180d7a`.

The raw point rows themselves are not connectivity authority. This revision does not change that boundary.

### Populated ARB assemblies and drawings

Front:

- `SU-A0703-AA FRONT ANTI-ROLL BAR.SLDASM`, Box `1966622548582`;
- blade drawing `SU-70301-AA FRONT, ARB, BLADE.pdf`;
- linkage drawing `SU-70308-AA FRONT, ARB, LINKAGE.pdf`;
- linkage tube nominal length `7.22 in`.

Rear:

- `SU-A0705-AA REAR ANTI-ROLL BAR.SLDASM`, Box `1966622815072`;
- blade drawing `SU-70502-AA REAR, ARB, BLADE.pdf`;
- linkage drawing `SU-70508-AA REAR, ARB, LINKAGE.pdf`;
- linkage tube nominal length `6.22 in`.

These sources establish hardware identity and the blade/linkage architecture.

### ARB Owner's Manual

The owner's manual independently establishes that:

- the blade passes through a blade housing;
- the housing is supported by top/bottom bearings, defining the central blade/housing rotation line;
- linkages connect to both sides of the blade;
- the Z-bar is a left/right coupled mechanism;
- blade orientation and linkage lever position alter stiffness.

That is enough to distinguish a central housing pivot, opposite blade ends, and the two linkage paths without using sketch row ordering.

### Simscape / multibody lineage

Recovered Box model lineage includes:

- `FRONT_TRACK.slx`, Box `2027160870540`, SHA-1 `a5518f4dd29e142626b1fcd07ca92148ac850d02`;
- `REAR_ARB.slx`, Box `2027153797982`, SHA-1 `c0a215a5cf6f4f9abac686059373228cca513fbc`;
- `REAR_ARB_FIGURE.png`, Box `2027140002033`, SHA-1 `27b48346c2bb5625a3aa3dad5f8e568f03d08d34`.

The recovered figure/model lineage independently depicts two rockers connected by two linkages to opposite ends of the central blade/housing system. The connector did not expose the raw `.slx` XML, so this audit does not claim direct XML inspection.

### WUFR-25 inboard FDR

The historical FDR documents:

- the rocker as the ARB linkage attachment;
- an approximately `90 deg` blade/link relationship at CAD static;
- later linkage shortening of roughly `4 mm` to bias the static angle and reduce rod-end bending.

The nominal angles recovered from the named geometry are `88.874 deg` front and `86.774 deg` rear, which independently agrees with that design narrative.

### Structural design binder

The 2025 suspension structural binder contains ARB load-path material, Instron/FEA blade-stiffness tables, and blade FEA slides. It corroborates the two-link/two-ended-blade design and the stiffness lineage. It does not explicitly define how the installed two-ended deformation is condensed to the single PR50 scalar `delta_b`.

## Named front fixture

Canonical frame: `+x` forward, `+y` vehicle left, `+z` upward; meters.

Blade/housing pivot:

`C_F = [0, 0, 0.088803563820]`

Blade-link joints:

`B_FL = [-0.070956780108, +0.015084268536, 0.088803563820]`

`B_FR = [+0.070956780108, -0.015084268536, 0.088803563820]`

Rocker ARB pickups:

`R_FL = [-0.028035250000, +0.238489003082, 0.085270375306]`

`R_FR = [+0.028035250000, -0.238489003082, 0.085270375306]`

Reviewed rocker pivots in the same canonical local suspension frame:

`P_FL = [0, +0.226746, 0.132080]`

`P_FR = [0, -0.226746, 0.132080]`

with rocker axis `+x`.

Derived identity checks:

- `C_F = (B_FL + B_FR)/2` to stored precision;
- blade half-span `0.0725424000193 m = 2.85600000076 in`;
- blade tip-to-tip span `0.145084800039 m`;
- left/right nominal joint-center linkage length `0.227517947831 m`;
- nominal blade-arm/link angle `88.8740442205 deg`.

The `7.22 in` linkage drawing value is retained separately as the physical linkage tube nominal length. It is not silently substituted for the rod-end joint-center distance.

## Named rear fixture

The raw rear ARB sketch and the rear OptimumK suspension state use different local x origins.

An exact historical registration is recovered by adding `+1.5604 m` to the raw rear ARB sketch x coordinate. In particular:

`-1.582625 + 1.5604 = -0.022225 m`

which exactly aligns the central rear ARB pivot x coordinate with the reviewed rear rocker local x coordinate.

This `1.5604 m` is **only** a source-frame registration value from the WUFR-26 source lineage. It does not replace the separately reviewed current WUFR-27 wheelbase authority `1.5624 m`.

After registration:

`C_R = [-0.022225, 0, 0.423024046]`

`B_RL = [+0.047689754, +0.019347530, 0.423024046]`

`B_RR = [-0.092139754, -0.019347530, 0.423024046]`

`R_RL = [+0.005708703, +0.212858444, 0.415603147]`

`R_RR = [-0.050158703, -0.212858444, 0.415603147]`

Reviewed rocker pivots:

`P_RL = [-0.022225, +0.224536, 0.312420]`

`P_RR = [-0.022225, -0.224536, 0.312420]`

with rocker axis `+x`.

Derived identity checks:

- `C_R = (B_RL + B_RR)/2` to stored precision;
- blade half-span `0.0725423996293 m = 2.85599998541 in`;
- blade tip-to-tip span `0.145084799259 m`;
- left/right nominal joint-center linkage length `0.198151336665 m`;
- nominal blade-arm/link angle `86.7741933427 deg`.

Again, the `6.22 in` physical linkage tube nominal length is retained separately from the joint-center distance.

## Rocker-state composition

The ARB pickups are points rigidly attached to the rockers. Their nominal offsets from the reviewed rocker pivots are frozen in the fixture.

They therefore move using the already-reviewed `MOD-SUSP-0003` one-axis rocker state, with the same rigid point-transport primitive used for other rocker-fixed points. This source recovery does not authorize a historical scalar ARB motion ratio.

## What is now authorized

The source packet is sufficient for:

- the named nominal point/topology fixture;
- left/right identity;
- blade/housing and rocker axes;
- nominal linkage geometry;
- rigid transport of the rocker ARB pickups using `MOD-SUSP-0003`;
- later rigid-link closure development against those named entities.

## Remaining scalar elastic-coordinate gap

PR50 deliberately defines one scalar blade elastic coordinate:

`F_b = k_b delta_b`

`U_b = 0.5 k_b delta_b^2`.

The current sources establish a physical blade with two end linkages. They do not state unambiguously whether the governing SolidWorks `k_b` should be interpreted as:

- one blade-arm / one-end tip force-deflection stiffness; or
- an already condensed symmetric two-ended installed blade mode.

The three-point Instron source and the SolidWorks/beam lineage do not resolve that installed-coordinate reduction by themselves.

Therefore this revision **does not** introduce a factor of `2`, `1/2`, `sqrt(2)`, or any other modal scaling. It also does not stack separate left/right copies of the PR50 energy law.

Until that scalar coordinate is explicitly frozen, the repository must continue to report:

- `scalar_delta_b_map_authorized = false`;
- `jacobian_authorized = false`;
- `vehicle_coordinate_generalized_force_authorized = false`.

## Next gate

The next review should answer one narrow source/definition question: what exact signed installed two-ended blade deformation corresponds to the single PR50 `delta_b` used with the governing SolidWorks `k_b`?

Once that is frozen, a separate implementation PR can solve the actual linkage closure, calculate `delta_b(q_L,q_R)`, verify `J_delta_b` at two finite-difference step sizes, and finally map the existing blade force through `Q_ARB=-J_delta_b^T F_b`.
