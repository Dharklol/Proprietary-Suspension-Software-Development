# Suspension Calculations 2026 — Detailed Sheet Inventory 01

Covers `Variables` through `Sheet8`. Observations are structural and semantic inventory findings, not final engineering approval.

## `Variables`

**Observed role:** Shared parameter list and imperial/SI conversion table.

**Major blocks**

- `A1:C38`: variable name, value, and definition.
- `D`: informal provenance and quality notes.
- `E2:F6`: conversion constants.
- `H1:I18`: approximation and sign notes.

**Important observations**

- The sheet is not a pure input table. Several values are formulas imported from other sheets, including static corner values and CG-to-front distance.
- Variable names do not consistently distinguish mass, weight, load, or force.
- Units are embedded in descriptions rather than machine-readable metadata.
- Approximation status is encoded in free text.
- Historical and current values are mixed.
- Sign notes such as right-turn-positive are local rather than workbook-wide conventions.

**Migration action**

Create one candidate parameter observation for every populated value. Preserve source cell, source hash, formula/value, unit label, note, vehicle generation, and confidence. No value becomes active merely because it appears here.

## `Load Transfer`

**Observed role:** Multiple generations of static mass distribution, longitudinal/lateral transfer, aero, ARB, and combined wheel-load calculations.

**Major blocks**

- `B3:F16`: static mass distribution.
- `A33:L59`: older longitudinal/lateral transfer method and four edge-case matrices.
- `A69:X116`: aero force, aero balance, and static-plus-aero load matrices.
- `A120:X186`: later block labelled “USE THIS ONE,” including roll-center, spring/ARB stiffness, lateral-transfer functions, ARB sensitivity, bump cases, and combined cornering/bump matrices.
- `N133:R162`: lateral-transfer and roll-stiffness sensitivity sweeps.

**Explicit workbook limitations**

Notes state that portions omit or simplify aero, non-steady behavior, CG movement, jacking, ARB contribution, pitch effects, unsprung effects, and changing roll centers. One earlier block contains a fixed “magic number” or fudge factor for lateral transfer.

**Preliminary model separation**

At least three distinct model families are present:

1. total longitudinal/lateral equilibrium transfer;
2. fixed-coefficient aero load addition;
3. front/rear lateral-transfer distribution using roll stiffness and static roll centers.

These must not become one opaque `load_transfer()` function.

**Migration action**

Create separate equation cards for:

- total longitudinal load transfer;
- total lateral load transfer;
- geometric transfer;
- elastic transfer;
- unsprung contribution;
- aerodynamic wheel-load distribution;
- wheel-load assembly;
- bump and combined load cases;
- roll-stiffness sensitivity.

The fixed-fudge-factor method is benchmark-only unless independently derived.

## `Tire Forces`

**Observed role:** Polynomial tire-fit curves and qualitative sanity/scaling notes.

**Major content**

- fitted cornering-stiffness relation versus normal load;
- one chart;
- notes referencing a different Hoosier tire, sandpaper test surface, fitted-model extrapolation, pressure, camber, slip ratio, and proposed scale factors.

**Blockers**

- The source dataset and fitting script are not embedded.
- The tire specification is stated to differ from the current tire.
- Units and sign conventions are incomplete.
- Suggested scaling factors are observations, not a documented physical model.
- The workbook points to MATLAB and Box content that is not revision-controlled here.

**Migration action**

Recover and hash the source dataset and fitting script. Preserve current curves as historical evidence only. Production tire work must use a canonical tire API with load, pressure, camber, speed, slip, combined-slip, temperature/condition where applicable, and explicit interpolation/extrapolation limits.

## `Optimal Front and Rear Force Di`

**Observed role:** Analytical front/rear longitudinal-force distribution under acceleration and braking, with and without basic aero, plus constant-friction curves and charts.

**Major blocks**

- `A1:Y65`: non-dimensional acceleration/braking force-distribution curves.
- `Z2:AO66`: aero-adjusted force distribution and front/rear bias values.
- `A67:Y108`: constant front/rear friction-coefficient curves.
- 11 charts.

**Important observations**

- “Optimal” is used before a complete tire capability/combined-slip model is present.
- Steady-state and fixed-CG assumptions are noted.
- Some chart notes say displayed friction lines should be ignored.
- Aero inherits all assumptions and uncertainties from `Load Transfer`.
- Requested force distribution, hydraulic bias, tire-limited force, lock sequence, and actual achieved force are not kept as separate quantities.

**Migration action**

Preserve the analytical curves as textbook-style benchmarks. Replace the design workflow with a constrained four-corner equilibrium/optimization problem that distinguishes requested force distribution, brake-system torque capacity, tire limits, lock order, drive layout, combined slip, and aero state.

## `Pitch & dive`

**Observed role:** First-order pitch calculation with spring and tire stiffness combined in series.

**Major blocks**

- `B3:C10`: parameters.
- `B11:C18`: no-load-transfer pitch block.
- `B19:C23`: load-transfer pitch block.
- `G22:G29`: assumptions.

**Explicit assumptions**

Small angle, linear spring/tire elasticity, no damping, no aero, no anti-geometry, negligible tire mass, and effectively 1:1 motion ratio.

**Concerns**

- Wheelbase conflicts with the primary variable sheet.
- A note states load transfer was added without completing the derivation.
- Pitch sign and reference state are not globally defined.
- Tire stiffness is an approximate interpolated value.

**Migration action**

Re-derive and retain as a restricted analytical benchmark. Production behavior belongs in the reduced heave/pitch model with explicit motion ratios, anti-dive/anti-squat, aero platform, damping, and compliance options.

## `ARB & Roll`

Only a source label and `ARB Calculations.xlsx` reference are present.

**Migration action**

Search Drive and Box for the exact workbook. Record the source hash and revision if found. Otherwise deprecate this sheet and create a missing-source risk.

## `Sheet8`

**Observed role:** Scratch calculation using corner weights with and without driver, ride-height change, inferred motion ratio, and inferred stiffness.

**Major content**

- corner weights in pounds and converted newtons;
- with-driver versus without-driver differences;
- one left-rear ride-height change;
- inferred spring compression, motion ratio, and stiffness.

**Concerns**

- Purpose, vehicle configuration, date, and test method are not identified.
- Units mix pounds, newtons, metres, `N/mm`, and a derived `N/m`-like value.
- Inference relies heavily on one corner and no uncertainty estimate.
- Suspension friction, cross-coupling, tire deflection, chassis twist, and measurement repeatability are not documented.

**Migration action**

Identify the original test and vehicle. If recoverable, migrate this as installation-calibration evidence with uncertainty and method. Otherwise archive as non-authoritative scratch work.
