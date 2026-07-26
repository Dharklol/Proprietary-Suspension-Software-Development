# Whole-vehicle force-coordinate source audit

## Purpose

This audit bounds the evidence used by `AUTH-VEH-0003` and `MOD-VEH-0003`. The authorized slice creates a common coordinate/wrench/generalized-force/contact foundation. It does **not** create spring, ARB, tire, load-transfer, equilibrium, or linkage-force physics.

## 1. Project state entering this implementation

The repository already contains three reviewed suspension providers:

- `MOD-SUSP-0001`: rigid ideal-joint double-wishbone position kinematics;
- `MOD-SUSP-0002`: source-bounded wheel-center/wheel-plane reference and body-frame vertical-state inversion;
- `MOD-SUSP-0003`: rigid push/pull-rod, rocker, coilover-displacement, and signed local actuation derivative.

Those providers retain suspension-source identities and do not by themselves create whole-vehicle force equilibrium. `WUFR27_SUSPENSION_BASELINE_V0` remains an active design-intent R&D configuration, not installed/as-built authority.

The project also contains:

- `MOD-VEH-0001`, an explicit operating-state exchange provider that does not generate wheel loads or vehicle response;
- `MOD-VEH-0002`, a planar wheel-velocity/slip-kinematics provider that consumes externally supplied `u`, `v`, and `r` and does not solve equilibrium.

`AUTH-VEH-0003` / PR #45 therefore authorized a common whole-vehicle geometry and force-coordinate layer rather than a hidden load-transfer calculation inside an existing provider.

## 2. User-reviewed design decisions

The following decisions are frozen for this program:

1. WUFR-27 will not use suspension geometry different from WUFR-26.
2. The first contact model is a flat rigid road with vertically rigid tires and all four contacts active.
3. A negative road-normal reaction is wheel lift/contact-mode invalidity and must not be clipped.
4. The first later linkage-force model will use ideal pin-jointed two-force members as a global load-path approximation, followed by separate structural/FEA work rather than treating ideal member forces as final stresses.
5. Corner-scale states supplied on 2026-07-26 are explicitly distinguished as driver/no-fuel and no-driver/no-fuel states; they must not be blended into one mass state.

The first four decisions are represented by `ASM-VEH-0001`, `ASM-VEH-0002`, and `ASM-SUSP-0001`. The measured scale values are frozen only in the reviewed WUFR adapter record used by PR #46.

## 3. Literature basis

### Guiggiani

`The Science of Vehicle Dynamics` supplies the primary road-vehicle coordinate and equilibrium framework:

- Chapter 1 defines the vehicle axes as `+x` forward, `+y` left, and `+z` upward and distinguishes wheelbase, tracks, CG location, suspension geometry, and static/reference conditions.
- Chapter 9 develops vehicle position and orientation using yaw-pitch-roll elemental rotations and writes equilibrium equations with roll and pitch motion.
- Section 9.7 separates equilibrium, load transfer, tire constitutive equations, and kinematic congruence.
- Section 10.1 explicitly organizes a vehicle model into kinematic, equilibrium, and constitutive equations and distinguishes suspension forces from road-contact reactions.

The implementation uses those concepts to keep coordinate transport, wrench assembly, force laws, and equilibrium as separate software responsibilities.

### Pacejka

`Tyre and Vehicle Dynamics`, Section 11.3, defines generalized forces from virtual work. Equations 11.62 and 11.82-11.84 express virtual work as the sum of generalized forces multiplied by their associated virtual coordinates and obtain generalized forces by substituting the application-point virtual displacements.

The present implementation adopts only this general mechanics structure:

```text
delta_W = F dot delta_r + M dot delta_omega = Q^T delta_q
Q = J_r^T F + J_omega^T M
```

The motorcycle-specific coordinates, parameters, and equations in that section are not imported.

### Gillespie

`Fundamentals of Vehicle Dynamics` is retained as an independent consistency source for vehicle free-body equilibrium and quasi-static load-transfer moment balances. It does not authorize importing a legacy spreadsheet load-transfer block, fixed coefficient, or hidden elastic-load-distribution rule.

## 4. WUFR whole-vehicle geometry evidence added for PR #46

After PR #45 merged, the reviewer supplied SolidWorks metadata exports from:

- `SU-00001-AA 2026 SUSPENSION GEOMETRY.SLDPRT`, Box file `1943897977651`, version `2546941960247`, SHA-1 `2cfb771f296961be0857161f7b57a6c178180d7a`;
- `FSA SUSPENSION.SLDASM`, Box file `1966637303418`, version `2547286736404`, SHA-1 `cfb95b650db19ca0624eaf82f272690aa70625df`.

The reviewed unsuppressed reference geometry and raw 3D-sketch coordinates establish one internally consistent CAD frame:

```text
+x forward
+y vehicle left
+z upward
front axle center = [ 0.000000, 0, 0.228600] m
rear axle center  = [-1.562400, 0, 0.228600] m
front wheel-center track = 1.231972 m
rear wheel-center track  = 1.206572 m
```

The corresponding wheelbase is `1.562400 m`. These CAD values independently agree with the rounded competition spec-sheet wheelbase/track entries but the adapter freezes the CAD values rather than replacing them with the rounded fields.

The export also separates suppression from visibility. Suppressed components/features are excluded from the active configuration; unsuppressed hidden construction remains eligible design/reference geometry. Visibility is not interpreted as physical presence. The active FSA assembly shows the top-level rear ARB assembly suppressed; this is preserved only as configuration evidence and does not authorize ARB physics.

A limitation was found in this exporter run: sketch-point `model_x_m/model_y_m/model_z_m` transformation columns are not reliable. PR #46 therefore uses only raw 3D-sketch coordinates and SolidWorks reference-point coordinates. The exact export hashes used for review are frozen in `data_catalog/wufr26_whole_vehicle_frame_v0.toml`.

## 5. WUFR mass/CG evidence and source separation

The reviewer supplied two distinct level-scale states, confirmed in pounds.

### No driver, no fuel

```text
LF=113, RF=104, LR=126, RR=134, total=477 lb
```

Using the explicitly frozen CAD axle and left/right contact-reference stations, the vertical-reaction centroid gives the planar design reference:

```text
x_CG_source = -0.8516226415094339 m
y_CG_source = +0.0015043731656184725 m
```

The 2026 FSAE Design IC spec sheet, Box file `2149814001036`, version `2510738677599`, SHA-1 `588669d320ff8097ec0bc85a85a970640d5a4d38`, separately reports a no-driver CG height of `0.290 m`.

The scale session and spec-sheet CG-height measurement are **not proven to be the same physical mass/setup state**. PR #46 therefore labels the composite point

```text
[-0.8516226415094339, +0.0015043731656184725, +0.290] m
```

as a named **design-intent no-driver reference only**, not one-session metrology or installed/as-built authority.

### Driver, no fuel

```text
LF=178, RF=175, LR=163, RR=159, total=675 lb
```

The separately frozen planar reference is:

```text
x_CG_source = -0.7453226666666667 m
y_CG_source = +0.006312743703703716 m
```

No driver/no-fuel vertical CG coordinate is currently authorized. The no-driver `0.290 m` value is not reused.

The corner-weight readings are provenance for these named planar CG-reference calculations in PR #46. They do **not** authorize gravity-force generation, sprung/unsprung allocation, spring preload, four-corner equilibrium, or dynamic load transfer.

## 6. Contact-model boundary

The first contact model intentionally uses:

- one flat rigid road plane;
- one declared unit road normal;
- one explicit contact-reference point per corner;
- vertically rigid tires;
- all four contacts active;
- zero gap at each active contact;
- nonnegative externally supplied road-normal reaction at each active contact.

For the WUFR design-intent adapter, the nominal road datum is source `z=0`. The four model contact references are the reviewed axle station and wheel-center track station projected to that plane. This projection is an explicit modeling convention for the vertically rigid first-contact slice; it is **not** a claim about physical tire footprint centroid, loaded radius, contact patch shape, or installed ride height.

A negative normal reaction is not a small numerical defect. It means the assumed all-four-active contact mode is not admissible. The model returns explicit `wheel_lift` / contact-mode invalidity and retains the negative value. It may not clip the load, redistribute it, or change contact mode internally.

Tire radial compliance, uneven roads, curbs, aerodynamic platform control, and contact-mode switching require later authorizations.

## 7. Why the static corner weights are not a wheel-load solver benchmark

With four vertical road reactions, rigid-body static equilibrium supplies only total vertical force, roll moment, and pitch moment. Those three equations do not uniquely determine the diagonal split among four reactions. The reviewer-supplied no-driver state has about `51.78%` LF+RR crossweight even though its lateral CG is nearly centered.

That diagonal split must be closed by later suspension elastic/preload/ride-height constraints, measured imposed corner loads, or another separately authorized compatibility model. `MOD-VEH-0003` therefore does not attempt to reproduce all four scale readings from CG position alone and does not smuggle a crossweight rule into the coordinate layer.

## 8. Linkage-force boundary

The user-approved first linkage fidelity remains downstream work:

- tie rods, push/pull rods, ARB links, and individual wishbone legs may be idealized as two-force members along declared centerlines;
- upright, rocker, and ideal node bodies may be treated as rigid;
- external wheel/contact, spring/ARB, brake-reaction, inertia, and aero loads must enter at explicit application points;
- equilibrium rank, conditioning, and residuals must be reported.

That model can produce useful global axial load paths and deterministic FEA boundary-condition inputs. It cannot by itself establish tube bending, weld stress, bracket flexibility, bearing load distribution, fatigue, buckling, compliance, or installed durability.

No linkage-force equation is implemented by PR #46.

## 9. Remaining unresolved authority

The PR #46 evidence is sufficient for the bounded whole-vehicle coordinate/wrench/contact implementation, but it does not close later force/equilibrium programs. Still unavailable or separately gated are:

- driver/no-fuel `z_CG`;
- authoritative total/sprung/unsprung mass allocation for force generation;
- spring free length, installed length/preload, and force law;
- coupled ARB geometry/preload/torsion law;
- aero/brake/powertrain/component force application points and force laws;
- physical tire radial compliance/contact patch geometry;
- alternate contact modes and wheel-lift continuation;
- installed/as-built ride height, hardpoints, stops, compliance, and correlation.

## 10. Audit decision

The evidence now supports implementation of:

- body-fixed point transport;
- force/couple wrench translation and summation;
- virtual-work generalized-force mapping;
- flat-road rigid-contact gap/reaction classification;
- an explicit WUFR-26/27 **design-intent** whole-vehicle frame/axle/contact adapter;
- strict frame, origin, application-point, source-state, and provenance diagnostics.

The evidence does not authorize spring/ARB/tire force laws, wheel loads, QSS equilibrium, alternate contact modes, linkage forces, stress, installed/as-built correlation, or production decisions.
