# Suspension Calculations 2026 — Structural Inventory

**Migration ID:** `MIG-SC26-0001`  
**Drive source:** https://docs.google.com/spreadsheets/d/1mW6JVHnSgvJJmXwYGV9AZV3ybRiolN9vPI8NAJjdvLA  
**Captured artifact SHA-256:** `8faf626624075aa3c842ac153debf7eb30be44489d551f6c421786875b09a162`  
**Inventory status:** Structural inventory complete; equation, parameter, and application audits remain open  
**Authority status:** Not authoritative

Detailed sheet notes are split into:

- [`sheet_inventory_01.md`](sheet_inventory_01.md): Variables through Sheet8
- [`sheet_inventory_02.md`](sheet_inventory_02.md): Alignment through Sheet18

## Workbook-level observations

- 17 visible sheets and no hidden sheets.
- No workbook-defined names, formal table objects, data-validation rules, protected sheets, or external-workbook-link objects.
- 20 embedded charts.
- Several sheets are scratchpads, historical design-study exports, source links, or empty placeholders rather than self-contained calculators.
- Formula output relies heavily on cell position and repeated blocks. Cell addresses must not become software interfaces.
- Current values, previous-car values, approximations, test observations, fitted tire curves, design-study exports, and explicit placeholders are mixed without structured provenance.

## Sheet inventory

| Sheet | Meaningful range | Formula cells | Shared blocks | Charts | Observed role | Preliminary disposition |
|---|---:|---:|---:|---:|---|---|
| Variables | A1:I38 | 11 | 0 | 0 | Shared parameter and conversion table | Rewrite into canonical parameter registry; preserve values only with provenance |
| Load Transfer | A1:X186 | 449 | 19 | 0 | Static/steady load, transfer, aero, and ARB calculations | Rewrite; retain selected closed-form blocks as restricted benchmarks |
| Tire Forces | B1:R57 | 21 | 2 | 1 | Tire fit curves and sanity notes | Benchmark/data-provenance only until source tire data and fit are recovered |
| Optimal Front and Rear Force Di | A1:AO108 | 1767 | 47 | 11 | Longitudinal force-distribution and brake-bias sweeps | Rewrite as equilibrium/optimization workflow; preserve analytical plots as benchmarks |
| Pitch & dive | B2:G29 | 15 | 1 | 0 | First-order pitch/dive calculation | Accepted with restrictions as educational benchmark; rewrite production model |
| ARB & Roll | G1:G2 | 0 | 0 | 0 | Source pointer only | Unknown/incomplete; recover referenced workbook or deprecate |
| Sheet8 | B1:Y22 | 20 | 0 | 0 | Corner-weight, ride-height, and inferred wheel-rate scratch work | Rewrite or archive after provenance recovery |
| Alignment | B2:N31 | 19 | 0 | 0 | String/toe measurement conversion and setup targets | Rewrite; formula and definition audit required |
| Natural Frequency | F1:F2 | 0 | 0 | 0 | Source pointer only | Unknown/incomplete; deprecate after source is catalogued |
| Steering Breakaway | A1:G12 | 1 | 0 | 0 | Steering-breakaway input scratchpad | Incomplete; rewrite around canonical tire and steering models |
| Ackerman Steering | B1:G42 | 9 | 0 | 0 | Ideal Ackermann and historical steering-angle comparisons | Benchmark only for low-speed geometry; rewrite performance objective |
| Steer Ratio | B1:BN44 | 8 | 0 | 0 | SolidWorks design-study exports and polynomial fits | Retain as imported evidence; replace with native steering-map representation |
| Understeer Gradient | A1:W152 | 1223 | 132 | 5 | Several linear/nonlinear understeer and roll-stiffness studies | Rewrite; preserve named variants as separate benchmark/research models |
| Steering Forces | B1:R122 | 309 | 50 | 1 | Steering-axis moment and rack-force approximations | Rewrite; selected mechanics may become restricted benchmarks |
| Steering Column Forces | B2:M79 | 45 | 0 | 0 | Rack, gear, shaft, and bearing loads | Restricted use only after upstream rack load is validated |
| Beam Deflection | — | 0 | 0 | 0 | Empty sheet | Deprecate |
| Sheet18 | A1:C22 | 22 | 1 | 2 | Unidentified numerical table with torque conversion | Block migration until provenance and purpose are identified |

## Cross-cutting conflicts and blockers

### Quantity and unit ambiguity

- `Fz0,l` and `Fz0,r` are described as normal forces but stored near `80.96` and `79.04`, consistent with mass-equivalent values rather than newtons.
- Variables prefixed `W` are used for masses in kilograms.
- Accelerations are stored in `g`; downstream formulas inconsistently multiply by `9.8` or `9.81`.
- ARB values may represent bar torsional stiffness, wheel-rate contribution, or axle roll stiffness. The workbook labels do not resolve this.
- Steering ratio is represented as rack travel per angle, polynomial road-wheel response, and an implicit steering-wheel ratio in different places.

**Migration status:** Blocked until canonical quantity definitions and conversion rules are established.

### Conflicting parameter observations

Examples include:

- wheelbase `1.5624 m` in `Variables` versus `1.538 m` in `Pitch & dive`;
- current and older roll-center values in the same rows;
- nominal spring rates alongside notes describing progressive behavior;
- WUFR-24, WUFR-25, and WUFR-26 steering data mixed with active parameters;
- one straight-line aero coefficient and a separate fixed two-degree-roll coefficient.

All observations may remain in the registry, but one resolved value and applicability rule must be selected per vehicle configuration.

### External-process dependencies

Notes reference MATLAB tire models and transient simulations, Box folders, SolidWorks design studies, `ARB Calculations.xlsx`, and manually observed test maxima. These are evidence sources, not reproducible dependencies until exact files, versions, scripts, inputs, and hashes are catalogued.

### Mixed fidelity and purpose

The workbook combines hand calculations, static and steady-state approximations, quasi-static sweeps, fitted tire relations, structural loading, alignment procedures, historical geometry exports, and charts. Migration must split these into component models, scenarios, evidence records, and benchmarks.

## Dependency outline

- `Variables` imports several values from `Load Transfer`, while most calculators treat `Variables` as input authority.
- `Load Transfer` depends heavily on `Variables`.
- `Optimal Front and Rear Force Di` depends on both.
- `Ackerman Steering` depends on `Variables` and polynomial coefficients in `Steer Ratio`.
- `Pitch & dive`, `Sheet8`, `Steering Breakaway`, `Understeer Gradient`, and `Steering Forces` depend on selected variables and load-transfer results.
- `Steering Column Forces` depends on upstream steering-force results.
- Several sheets additionally depend on untracked MATLAB, SolidWorks, Box, and historical test artifacts.

This creates circular conceptual authority even where the spreadsheet has no direct circular formula: calculated values are promoted into the variable table and later treated as independent inputs.

## Immediate documentation tasks

1. Assign stable block IDs to every major range in the detailed sheet inventories.
2. Recover external evidence files and record their hashes.
3. Map every `Variables` entry to a canonical quantity candidate.
4. Resolve mass/force, degree/radian, stiffness, motion-ratio, and steering-ratio definitions.
5. Create separate equation cards for every model variant rather than selecting the newest-looking block.
6. Create retired records for explicitly wrong, empty, or unidentified content.
7. Define benchmark cases before implementation.
