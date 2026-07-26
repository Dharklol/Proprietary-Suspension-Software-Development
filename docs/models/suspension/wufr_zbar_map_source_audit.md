# WUFR Z-Bar Deformation-Map Source Audit

**Authorization:** `AUTH-SUSP-0006`  
**Model:** `MOD-SUSP-0005`  
**Configuration:** `WUFR27_SUSPENSION_BASELINE_V0`  
**Source record:** `data_catalog/wufr27_zbar_mapping_source_v0.toml`

## Review question

Can the current WUFR source set uniquely support the map

`(q_L, q_R) -> delta_b`

and its signed Jacobian

`J_delta_b = partial(delta_b)/partial(q_L,q_R)`

without using a body-roll, track-width, wheel-travel, historical motion-ratio, or sketch-row shortcut?

## Decision

**Not yet.** The current sources are sufficient to establish Z-bar topology, blade/link hardware identity, zero-preload intent, historical static-angle/service information, and the PR50 discrete blade constitutive law. They do not yet freeze the explicit named three-dimensional mechanism fixture required for a unique branch-consistent WUFR blade-tip deformation map.

This is a geometry-authority gap, not a constitutive-law gap. PR50 remains valid for an externally supplied `delta_b`:

`F_b = k_b delta_b`

`U_b = 0.5 k_b delta_b^2`.

WUFR vehicle-coordinate generalized force remains blocked because

`Q_ARB = -J_delta_b^T F_b`

requires a reviewed `J_delta_b`.

## Recovered source evidence

### ARB Owner's Manual

The team owner's manual identifies the Z-bar as a left/right-coupled mechanism. Differential suspension motion twists/loads the system, blade orientation changes stiffness, and linkage position changes the lever geometry. It also documents the linkage/rod-end/blade assembly relationships. This is strong topology and service evidence, but it does not provide a complete numerical suspension-state-to-blade-deflection closure.

### WUFR-25 inboard FDR

The WUFR-25 design narrative records an approximately 90-degree blade/link relationship at CAD static and a subsequent roughly 4 mm linkage/static-angle adjustment intended to improve rod-end loading. This is useful mechanism history and a warning that nominal linkage geometry matters. It is not enough to reconstruct the current 3D branch uniquely.

### WUFR-26 inboard FDR

The WUFR-26 FDR preserves the five-way adjustable Z-bar architecture and points to `WUFR26InboardSuspensionCalculator.m`. It also reports historical axle roll-stiffness/roll-gradient results. Those results are reduced vehicle-level calculations and cannot be inverted into a blade kinematic map without circularly assuming the geometry being sought.

### `WUFR26InboardSuspensionCalculator.m`

Recovered Box source:

- file `2026725896730`
- SHA-1 `2f98937654a43914bb586a7e0a1ae9908d97bcb5`

The script performs quarter-car natural-frequency, pitch, lateral weight-transfer, and roll calculations. Its roll section uses track width and spring installation ratios. It does **not** solve an assembled Z-bar, name blade/link pivots, solve a blade working point from left/right suspension states, or compute `d(delta_b)/d(q_L,q_R)`.

Therefore its `MR_f/MR_r`, track, and roll-angle formulas are historical analysis only. They are not ARB map authority.

### `ARB Force Calculation.pdf`

The three-page historical hand calculation uses a roll-angle/single-lever construction to obtain an ARB displacement and then torque. That approach is exactly the class of approximation intentionally excluded by PR50 as governing WUFR blade-map authority. It remains useful for historical comparison and sanity checking after a real mechanism map exists.

### `ARB Calculations.xlsx`

The workbook contains historical beam-section inertia/deflection calculations, required ARB-load calculations, and roll calculations. The blade sheet varies section/load angles and computes beam deflection. The vehicle sheets compute roll/required ARB forces. No sheet recovered in this audit supplies a named assembled left/right Z-bar closure tied to the reviewed suspension/rocker states.

The workbook therefore supports the design lineage but does not close the current geometry-authority gap.

### Populated WUFR-26 CAD/drawings

Current populated carryover sources retain front/rear assembly, blade, linkage, and suspension-geometry identities. Front and rear linkage nominal lengths are 7.22 in and 6.22 in respectively. These are valuable hardware/geometry evidence.

However, the existing suspension exporter does not preserve sketch connectivity reliably enough to use raw ARB sketch-row ordering as topology. A valid fixture still needs explicitly named mechanism entities and their relationship to the already-reviewed rocker state.

## What must be frozen next

A WUFR map implementation requires an explicit front and rear mechanism fixture containing at least:

- blade pivot point and rotation axis;
- blade working/load point and signed elastic working direction;
- both linkage endpoint definitions and rigid link lengths;
- rocker ARB pickup point and the rigid transform that moves it with the reviewed rocker angle/state from `MOD-SUSP-0003`;
- coordinate frame, units, left/right convention, and sign convention for `delta_b`;
- zero-preload nominal branch;
- rigid-link/rod-end closure equations;
- branch-selection/continuation rule and singularity behavior.

The fixture must come from named CAD entities, a traceable CAD export, or an equivalent reviewed measurement/definition. It must not be reconstructed from point-row order or from a vehicle-level roll result.

## Required verification for a later implementation

A future map implementation must demonstrate:

1. closure residuals over a reviewed left/right suspension domain;
2. unique/continuable mechanism branch or explicit ambiguity failure;
3. correct nominal zero-preload state without hidden residual subtraction;
4. common-mode and differential behavior produced by the actual mechanism rather than forced by a symmetry formula;
5. signed `J_delta_b` agreement with independent finite differences at two step sizes;
6. explicit failure near singular, unreachable, or branch-ambiguous states;
7. composition with the PR50 blade law without interpolation or stiffness-source stacking.

## Consequence for sequencing

The next source task is to recover/export the named front and rear mechanism fixture. A WUFR numerical Z-bar map should **not** be implemented from the currently recovered approximations.

The planned prescribed-force quasi-static vehicle equilibrium/load-state solver remains downstream. It should consume a reviewed ARB generalized force rather than reproduce or approximate the missing Z-bar geometry internally.
