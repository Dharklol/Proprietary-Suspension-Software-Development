# Quasi-static load-state source audit

## Purpose

This audit defines the next whole-vehicle gate after the WUFR spring and anti-roll-bar force chain was completed through PR #56 and the governance matrix was synchronized in PR #57.

The target downstream capability is a source-bounded quasi-static load-state solver that can eventually combine:

- whole-vehicle/body/contact coordinates from `MOD-VEH-0003`;
- conservative spring generalized forces from `MOD-SUSP-0004`;
- coupled WUFR Z-bar generalized forces from `MOD-SUSP-0005`;
- gravity and later separately authorized external loads;
- compatibility/equilibrium closure;
- four road-normal reactions subject to the reviewed all-four-active rigid-road contact mode.

This document does **not** authorize a WUFR wheel-load solver. Its purpose is to identify exactly which source inputs are already sufficient and which mass-model inputs still require reviewer authority.

## 1. Resolved upstream mechanics

The previously blocking suspension-force chain is now available.

### Whole-vehicle coordinates/contact

`MOD-VEH-0003` provides the common body frame, body pose `q=[z_s, phi, theta]`, explicit body/contact points, wrench assembly, virtual-work generalized-force mapping, and the first flat-rigid-road/all-four-contact admissibility model. It deliberately does not solve equilibrium.

The reviewed WUFR frame snapshot is `data_catalog/wufr26_whole_vehicle_frame_v0.toml`:

- `+x` forward, `+y` vehicle left, `+z` upward;
- front axle center `[0, 0, 0.228600] m`;
- rear axle center `[-1.562400, 0, 0.228600] m`;
- front track `1.231972 m`;
- rear track `1.206572 m`;
- nominal flat road at source `z=0`.

### Spring force

`MOD-SUSP-0004` / PR #48 supplies conservative source-bounded spring forces and energy through the physical wheel/actuation coordinate chain. The current WUFR design-intent model uses:

- front: `36 N/mm` linear;
- rear: `30 -> 36 N/mm` progressive under the explicitly reviewed provisional tangent-rate law;
- zero intentional preload;
- the reviewed KW full-extension/direct-coilover reference.

These outputs are force-model values, not solved road reactions.

### Anti-roll bar

`MOD-SUSP-0005` now supplies the WUFR coupled Z-bar chain through physical left/right wheel-center vertical coordinates.

The governing SolidWorks per-arm blade settings remain discrete:

`280 / 300 / 400 / 700 / 2300 N/mm`.

PR #54/#55 implemented and promoted the two-arm mechanism closure and rocker-coordinate Jacobian. PR #56 added the reviewed branch-preserving chain into physical wheel coordinates and returns work-conjugate `Q_z` in newtons. No historical scalar motion-ratio, body-roll, track-width, or reduced-axle-stiffness shortcut is required.

Therefore spring/ARB constitutive mechanics are no longer the principal blocker to the first equilibrium program.

## 2. Reviewed whole-vehicle mass/CG evidence

The primary driver/no-fuel scale state remains:

```text
LF = 178 lb
RF = 175 lb
LR = 163 lb
RR = 159 lb
total = 675 lb
```

Using the frozen CAD axle/track coordinates, the reviewed planar reaction centroid is:

```text
x_CG = -0.7453226666666667 m
y_CG = +0.006312743703703716 m
```

The separately sourced `0.290 m` CG-height value is from a tilt test using ballast to simulate a driver. The combined point

```text
[-0.7453226666666667, +0.006312743703703716, +0.290] m
```

remains a **driver/no-fuel design-intent R&D reference**, not same-session installed metrology.

The no-driver/no-fuel scale state remains separate:

```text
LF = 113 lb
RF = 104 lb
LR = 126 lb
RR = 134 lb
total = 477 lb
```

and has no authorized vertical CG coordinate.

The corner-scale readings establish measured total reaction and planar centroid information. They do not by themselves define sprung/unsprung decomposition or a unique four-corner elastic equilibrium rule.

## 3. Current unsprung-mass evidence

The reviewer reported the current measured unsprung totals as:

```text
front axle unsprung mass = 10 kg
rear axle unsprung mass  = 10 kg
total unsprung mass      = 20 kg
```

No reviewed per-corner split or unsprung center-of-mass locations accompanied those measurements.

This distinction is already frozen in the WUFR spring source record. `data_catalog/wufr27_spring_package_v0.toml` states that the historical WUFR-26 inboard calculator labels `m_u=10 kg` as a **quarter-car** unsprung mass, but that this conflicts with the reviewer's current measurement of `10 kg front axle + 10 kg rear axle`; the historical script is therefore not mass authority.

The current mass evidence is sufficient to say that the old `10 kg per corner` assumption must not silently enter a new QSS model.

## 4. Additional current-project calculations found during this audit

These files are useful context but do not supersede the reviewed scale/unsprung measurements.

### WUFR-27 Vehicle Dynamics PDR

Google Doc:

`https://docs.google.com/document/d/1Mf15p86R1e-PDsIVCobtCIhZjc5G3xPN2UmZES8SbF4`

A design-materials tab explicitly labels the following as **"Ride frequency target assumptions WUFR-26"**:

- `10 kg per corner unsprung`;
- `65 kg per front corner sprung`;
- `61 kg per rear corner sprung`;
- springs, tires, and ARBs as the only compliance elements considered;
- no aero forces.

Because the document itself labels these values as assumptions and the `10 kg per corner` value conflicts with the later reviewed axle-total measurement, they are retained as historical target-study context only.

### LLTD Calculator

Google Sheet:

`https://docs.google.com/spreadsheets/d/1kwAzxos_H7goRRTbuyWT3U6eArh5o65v6DR0wY28b6s`

Its `Inputs` tab currently contains, among other template inputs:

- sprung mass `207 kg`;
- effective roll moment arm `0.29 m`;
- front sprung weight fraction `0.509`;
- direct wheel-rate inputs and scalar ARB roll-stiffness inputs.

The sheet's own usage notes describe replaceable template inputs. The values are not tied by provenance to the reviewed driver/no-fuel scale state, and its scalar wheel-rate/ARB representation is not the current generalized-force architecture. It is therefore comparison/study evidence, not governing QSS mass authority.

### Suspension Calculations 2026

Google Sheet:

`https://docs.google.com/spreadsheets/d/1mW6JVHnSgvJJmXwYGV9AZV3ybRiolN9vPI8NAJjdvLA`

The `Variables` tab currently contains `220 kg` car mass, `100 kg` driver mass, and `320 kg` total mass. Those values are calculation inputs rather than the reviewed corner-scale state and are not promoted to current gravity-force authority.

## 5. Why total mass/CG is not enough for the intended elastic four-corner solve

For the complete vehicle, vertical force equilibrium plus roll and pitch moment equilibrium provide three independent rigid-body equations for four road-normal reactions. A fourth compatibility relation must come from the suspension/contact system rather than an invented crossweight rule.

The spring and ARB providers can supply that elastic compatibility only when their wheel-coordinate forces are assembled consistently with the wheel/unsprung free-body equations.

For each physical wheel vertical coordinate, the static equation contains at least:

```text
road-normal reaction
+ suspension generalized force
+ unsprung gravity contribution
= 0
```

under the first bounded flat-road/no-other-wheel-force slice.

Consequently, converting elastic wheel-coordinate generalized forces into actual road reactions requires a reviewed unsprung gravity allocation. Equivalently, a sprung-body formulation requires a reviewed sprung mass and sprung CG obtained from a source-bounded decomposition of total vehicle mass.

The available `10 kg front + 10 kg rear` measurement does not uniquely define the left/right split or the unsprung mass application points. Assigning `5 kg` to every corner, placing unsprung mass at wheel centers, or reusing the old `10 kg per corner` value would all be additional modeling decisions. None is silently authorized by the current evidence.

## 6. What can be implemented without new WUFR mass assumptions

A **generic** equilibrium kernel can be implemented and verified independently of WUFR parameter authority if all mass properties and external generalized forces are explicit inputs.

A suitable first generic scope is:

1. declared body generalized coordinates and explicit contact/wheel coordinates;
2. externally supplied conservative suspension generalized-force callback/provider results;
3. explicit sprung/body mass and CG, or equivalent explicit gravity generalized force;
4. explicit per-corner unsprung masses and their gravity-force application convention;
5. flat rigid road and all four contacts active;
6. nonlinear residual solve for compatibility/equilibrium;
7. residual norm, iteration/conditioning diagnostics, and negative-reaction rejection;
8. energy-gradient/virtual-work and synthetic hand-case benchmarks.

Such a kernel must not contain WUFR default masses, hidden equal-corner allocation, a crossweight rule, or legacy scalar load-transfer equations.

## 7. WUFR implementation gate

Before a WUFR driver/no-fuel four-corner gravity-equilibrium adapter can be promoted, one of the following must be reviewed explicitly:

- measured/reviewed per-corner unsprung masses and suitable application locations; or
- a clearly named prototype assumption that allocates the measured `10 kg` front and `10 kg` rear axle totals between left/right corners and defines the applicable unsprung mass locations; or
- an alternative directly reviewed sprung-mass/sprung-CG data set that removes the need to infer it from total mass.

For later lateral/longitudinal QSS, the mass model will additionally need a reviewed vertical location for unsprung inertia/load-transfer effects rather than relying on a static-gravity-only convention.

## 8. Other later force inputs remain separate

The first gravity/static equilibrium slice need not include every later maneuver force. These remain separate gates:

- aerodynamic forces and center-of-pressure/application points;
- brake and powertrain forces/moments;
- tire constitutive force laws and radial compliance;
- damper forces for transient work;
- alternate contact modes after wheel lift;
- chassis compliance beyond the first rigid-body model;
- installed/as-built ride-height, preload, hard-stop, and correlation evidence.

They must not be used to block a properly bounded gravity/static generic solver, but they also must not be silently inserted into it.

## 9. Audit decision

The source review supports continuing architecture work on a **provider-neutral generic quasi-static equilibrium kernel** with explicit mass inputs and synthetic verification.

The source review does **not** yet support a WUFR-specific four-corner road-reaction result because per-corner unsprung mass/gravity allocation remains unresolved.

The first WUFR equilibrium benchmark must therefore remain blocked until that mass allocation is reviewed. The historical `10 kg per corner`, `207 kg sprung`, `220+100 kg`, scalar wheel-rate, and scalar ARB calculator values are not substitutes for that review.
