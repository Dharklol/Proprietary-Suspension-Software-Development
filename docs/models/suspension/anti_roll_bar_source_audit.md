# Anti-Roll-Bar Source Audit

**Program:** `AUTH-SUSP-0005` / PR #49, corrected by PR #50  
**Configuration:** `WUFR27_SUSPENSION_BASELINE_V0`  
**Constitutive snapshot:** `data_catalog/wufr27_anti_roll_bar_package_v0.toml`  
**Geometry-map follow-on:** `data_catalog/wufr27_zbar_mapping_source_v0.toml`

## Current authority decision

PR50 corrected the WUFR constitutive source. The governing WUFR values are the **SolidWorks FEA blade-tip force/deflection stiffnesses** in the Google Sheet tab `ARB FEA vs Simulink`, column `FEA SolidWorks Stiffness`:

- setting 1: 280 N/mm = 280000 N/m;
- setting 2: 300 N/mm = 300000 N/m;
- setting 3: 400 N/mm = 400000 N/m;
- setting 4: 700 N/mm = 700000 N/m;
- setting 5: 2300 N/mm = 2300000 N/m.

The sheet beam-theory formulas use `k=3EI/L^3` and divide N/m by 1000 to report N/mm, confirming that these are linear blade-tip stiffness quantities rather than `N*m/deg` axle roll stiffness.

For signed blade-tip elastic deflection `delta_b` in meters:

`F_b = k_b delta_b`

`U_b = 0.5 k_b delta_b^2`.

The settings are discrete. Interpolation, averaging, blending, or stacking sources is not authorized.

## Frozen one-millimeter benchmark

At `delta_b=1 mm`, the five settings give:

- 280 N / 0.140 J;
- 300 N / 0.150 J;
- 400 N / 0.200 J;
- 700 N / 0.350 J;
- 2300 N / 1.150 J.

These values are frozen by `BENCH-SUSP-0012` and the PR50 implementation tests.

## Comparison-only stiffness evidence

The following quantities remain useful historical/comparison evidence but are not governing WUFR blade stiffness and are not combined with the SolidWorks values:

- MATLAB `Weight_transfer_sensitivity.m`: 2560/2270 N*m/deg reduced axle values;
- Simulink values from the governing spreadsheet: 285/309/400/724/2628 N/mm;
- Instron values from the governing spreadsheet: 900/980/1320/1970/2630 N/mm;
- whole-suspension spec-sheet roll-rate values: 556/458 N*m/deg.

The earlier PR49 source audit promoted the MATLAB pair before the reviewer corrected the authority source. Git history preserves that decision trail, but it is superseded by PR50.

## Populated geometry evidence

The current populated carryover suspension/ARB geometry remains the WUFR-26 design-intent source until a populated WUFR-27 revision supersedes it. Relevant identities include:

- suspension geometry `SU-00001-AA 2026 SUSPENSION GEOMETRY.SLDPRT`, Box `1943897977651`;
- front ARB assembly `SU-A0703-AA FRONT ANTI-ROLL BAR.SLDASM`, Box `1966622548582`;
- rear ARB assembly `SU-A0705-AA REAR ANTI-ROLL BAR.SLDASM`, Box `1966622815072`;
- front linkage nominal length 7.22 in;
- rear linkage nominal length 6.22 in.

The suspension exporter provides ARB sketch points but does not preserve sketch connectivity reliably enough to assign blade/link roles or working directions from row ordering. Raw sketch row order is therefore not mechanism authority.

The direct WUFR-27 front/rear ARB assembly files inspected during PR49 were byte-identical placeholders and do not supersede the populated carryover sources.

## Zero-preload boundary

The reviewer/team design intent is zero intentional ARB preload. This means the reviewed nominal mechanism branch should correspond to the zero-energy blade reference. It does not authorize hidden subtraction of a reconstruction residual.

## Geometry map is a separate authority problem

The PR50 WUFR adapter intentionally stops at externally supplied `delta_b`. Vehicle-coordinate generalized force requires

`Q_ARB = -J_delta_b^T F_b`

with

`J_delta_b = partial(delta_b)/partial(q_L,q_R)`.

PR50 does not authorize or implement either the WUFR map `(q_L,q_R)->delta_b` or its Jacobian.

PR51 / `AUTH-SUSP-0006` performs the dedicated geometry-map source audit. The recovered ARB Owner's Manual, WUFR-25/WUFR-26 FDR material, `WUFR26InboardSuspensionCalculator.m`, `ARB Force Calculation.pdf`, `ARB Calculations.xlsx`, and populated CAD lineage establish topology and useful historical calculations, but they do not yet freeze the explicit named three-dimensional mechanism fixture required for a unique branch-consistent map.

See `docs/models/suspension/wufr_zbar_map_source_audit.md` for the detailed finding.

## Prohibited geometry shortcuts

Until a named mechanism fixture is reviewed, do not define WUFR blade deformation or its Jacobian from:

- body roll angle;
- track/half-track multiplication or a single lever-arm approximation;
- left-right wheel-travel difference by itself;
- historical scalar motion ratios;
- exporter sketch row ordering;
- inverse fitting from the old MATLAB/reduced axle roll-stiffness values.

These may later serve as independent comparison checks only when their original quantity semantics are preserved.

## Current implementation boundary

Authorized and implemented:

- generic conservative ARB coordinate/action/energy/generalized-force architecture;
- explicit zero-reference and no-bar behavior;
- five discrete WUFR SolidWorks blade-tip stiffness settings;
- WUFR blade force/energy/tangent for externally supplied `delta_b`.

Not yet authorized/implemented:

- the explicit WUFR Z-bar mechanism fixture;
- `(q_L,q_R)->delta_b`;
- `J_delta_b`;
- WUFR vehicle-coordinate generalized ARB force derived from suspension state;
- installed/as-built correlation, friction/backlash, linkage loads, blade stress/fatigue release, or vehicle equilibrium/load transfer.

The next source gate is recovery/export and review of the named front/rear Z-bar mechanism fixture. Quasi-static vehicle equilibrium remains downstream of that map.
