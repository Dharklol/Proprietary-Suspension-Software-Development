# Suspension Calculations 2026 — Detailed Sheet Inventory 02

Covers `Alignment` through `Sheet18`. Observations are structural and semantic inventory findings, not final engineering approval.

## `Alignment`

**Observed role:** Convert string/bar measurements into toe angles and store desired setup values.

**Major blocks**

- measured left/right front string distances and calculated front toe;
- measured left/right rear distances and calculated rear toe;
- desired front/rear toe values;
- historical “ideal calculated values” and tie-rod-turn guidance.

**Known formula defects or ambiguities**

- formulas such as `SIN(DEGREES(angle))` apply degree conversion in the wrong direction for spreadsheet trigonometric functions;
- front and rear measurement geometry are not fully defined;
- the rim diameter and geometric constant lack formal provenance;
- desired toe sign is locally documented but not linked to the project convention;
- per-wheel toe and total axle toe are both present without canonical quantity names.

**Migration action**

Rewrite as a setup-measurement model with explicit fixture geometry, measured points, calibration, uncertainty, toe sign, per-wheel versus axle-total definitions, and a physical validation case.

## `Natural Frequency`

Contains only a source link.

**Migration action**

Catalog the source and deprecate the sheet. A future ride-frequency model must distinguish installed wheel rate, tire stiffness, sprung and unsprung mass, damping, and coupled modes.

## `Steering Breakaway`

**Observed role:** Input scratchpad for a MATLAB-derived tire force at a selected normal load and operating condition.

**Concerns**

- only one workbook formula is present;
- the critical tire-force result lives outside the workbook;
- the inside tire is assumed to contribute very little;
- parked breakaway, low-speed scrub, and high-lateral-acceleration steering conditions are not separated;
- tire pressure, camber, slip ratio, and load are treated as one fixed scenario.

**Migration action**

Rewrite around canonical tire, steering-axis, trail, scrub, rack, column, friction, and compliance models. Preserve the listed operating point as a candidate benchmark scenario after the external tire result is recovered.

## `Ackerman Steering`

**Observed role:** Ideal low-speed Ackermann angles and historical WUFR steering-angle comparisons.

**Major blocks**

- ideal geometric turn at a selected radius;
- WUFR-24 skidpad and full-lock values;
- WUFR-25 and WUFR-26 full-lock values;
- estimated Ackermann percentages with and without a slip-angle adjustment.

**Concerns**

- the Ackermann percentage definition is not canonical;
- low-speed ideal geometry is mixed with performance interpretation;
- slip-angle adjustment is not derived from a current tire model;
- minimum turning radius is treated near the objective rather than as a boundary condition;
- historical cars and current design values are mixed.

**Migration action**

Preserve ideal Ackermann as a low-speed benchmark and the historical steering maps as evidence. Future optimization should minimize tire-force/slip mismatch across weighted operating conditions, with turning radius, rack travel, clearance, joint angle, monotonicity, manufacturability, and packaging as constraints.

## `Steer Ratio`

**Observed role:** Pasted SolidWorks design-study exports for WUFR-24 and WUFR-25 with polynomial coefficients.

**Major blocks**

- `B3:BN17`: WUFR-24 design study.
- `B27:G27`: inside/outside tire summary.
- `B30:BN42`: WUFR-25 design study.
- polynomial coefficients near `T13:V17` and `T40:V42`.

**Concerns**

- scenario columns are imported evidence, not a calculation model;
- CAD revision, motion-study definition, steering input, and sign convention are absent;
- polynomial fits can hide mechanism branch changes, left/right asymmetry, and extrapolation failure;
- no loaded/compliant steering map is represented.

**Migration action**

Catalog as imported evidence with CAD revision and source export. The canonical representation should be a left/right road-wheel map versus rack displacement or shaft angle, including derivatives, travel limits, branch identity, compliance state, and uncertainty.

## `Understeer Gradient`

**Observed role:** Several separate handling studies combined on one sheet.

**Major blocks**

- `B1:E21`: bicycle-model parameters and apparent slip/steer quantities.
- `A25:W61`: first method explicitly labelled wrong or garbage.
- `A62:W76`: ARB/load-transfer case with steering-wheel angle and yaw-rate outputs.
- `A79:T92`: one roll-stiffness balance case.
- `A94:T107`: neutral case.
- `A109:T122`: another balance case.
- `A124:T137`: high-rear/low-front case.
- `A139:T152`: another neutral/stiffer-front case.
- five charts.

**Concerns**

- one scalar name is used for multiple definitions;
- bicycle, four-wheel load-sensitive, steering-wheel, tire-angle, and yaw-rate metrics are mixed;
- empirical cornering-stiffness polynomials are reused without a validity envelope;
- hardcoded scale factors distribute axle stiffness among wheels;
- some sections are explicitly marked not to use.

**Migration action**

Do not migrate this as one function. Create separate model cards for:

- road-wheel steering gradient;
- steering-wheel gradient;
- yaw-rate gain;
- neutral steer/static margin;
- handling-map slope;
- local nonlinear sensitivity/understeer budget.

Explicitly rejected sections should remain as retired records explaining why they were rejected.

## `Steering Forces`

**Observed role:** Approximate steering-axis moments from longitudinal, lateral, vertical, and aligning-moment contributions, followed by parked scrub calculations.

**Major blocks**

- `B2:D12`: steering geometry inputs.
- `B16:D27`: straight-line braking contribution.
- `B33:G38`: mass, aero, geometry, and steering scenario.
- `B42:P50`: combined corner-entry braking force and moment.
- `B54:J62`: lateral-force contribution.
- `B66:N74`: vertical-force contribution.
- `B78:J86`: tire aligning-moment contribution.
- `B89:D97`: total corner-entry moment.
- `B103:E122`: parked scrub/breakaway model.
- one chart.

**Explicit limitations**

No bump steer, linear steering, elliptical combined-force assumption, approximate friction scaling, and strong dependence on steering-input speed not represented.

**Migration action**

Split into independent moment contributors sharing one steering-axis geometry and tire interface. Re-derive signs, frames, force directions, scrub, mechanical trail, pneumatic trail, caster, and KPI terms. Parked and moving cases require separate applicability.

## `Steering Column Forces`

**Observed role:** Convert steering-axis moment into rack and column torque, then estimate miter-gear and bearing reactions.

**Major blocks**

- `B3:C24`: parked/cornering rack and column moments plus ratio alternatives.
- `B26:F37`: gear geometry.
- `B40:F49`: miter-gear forces.
- `B63:F76`: shaft bearing reactions.

**Concerns**

- a note states the signs were mishandled;
- upstream steering moment is inherited from approximate calculations;
- efficiency, backlash, preload, support stiffness, and load reversals are not represented;
- local aliases obscure the load-case identity.

**Migration action**

Re-derive free-body diagrams and signs. Downstream gear and bearing mechanics may become restricted structural benchmarks only after the upstream rack-force scenario is trustworthy.

## `Beam Deflection`

Empty.

**Migration action:** Deprecate with no replacement dependency.

## `Sheet18`

**Observed role:** Unknown. Column `C` converts column `B` by approximately `1.3558179483`, consistent with `ft·lbf` to `N·m`; column `A` appears to be an independent sweep such as speed or RPM.

Two charts are present, but labels and provenance are absent.

**Migration action**

Mark blocked and unknown. Do not infer a canonical purpose without recovering the source context.
