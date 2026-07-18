# LLTD Calculator — Structural Inventory

**Migration ID:** `MIG-LLTD-0001`  
**Drive source:** https://docs.google.com/spreadsheets/d/1kwAzxos_H7goRRTbuyWT3U6eArh5o65v6DR0wY28b6s  
**Captured artifact SHA-256:** `9af4fcd0da6ffd9c31b16f50f48687aba919f038cbc24366d0622014898d9049`  
**Inventory status:** Structural inventory complete; equation, sensor, identification, and application audits remain open  
**Authority status:** Not authoritative

Detailed sheet notes are in [`sheet_inventory.md`](sheet_inventory.md).

## Workbook-level observations

- 7 visible sheets and no hidden sheets.
- No workbook-defined names, formal table objects, data-validation rules, protected sheets, or external-workbook-link objects.
- Four cell comments clarify chassis stiffness, rigid roll gradient, chassis twist, and LLTD-proxy limitations.
- The workbook deliberately separates inputs, rigid model, compliance model, raw data, derived data, summary, and cell map.
- The chassis-compliance block explicitly calls itself a placeholder.
- The measured LLTD result explicitly calls itself a proxy.
- Raw and derived ranges are preallocated to 1,000 data rows, creating many formula cells when no logger data is present.

## Sheet inventory

| Sheet | Meaningful range | Formula cells | Shared blocks | Comments | Observed role | Preliminary disposition |
|---|---:|---:|---:|---:|---|---|
| Inputs | A1:J53 | 5 | 1 | 1 | Vehicle, corner-rate, sensor, chassis, sweep, and filter inputs | Rewrite into canonical parameter and sensor registries |
| Rigid_Model | A1:F29 | 42 | 5 | 1 | Rigid-chassis spring/ARB/tire roll-stiffness baseline | Restricted first-order benchmark after re-derivation |
| Compliance_Model | A1:X40 | 450 | 4 | 0 | Placeholder chassis-compliance model and sensitivity sweeps | Replace with coupled model; preserve sweep workflow |
| Raw_Data | A1:N3003 | 1000 | 0 | 0 | Logger paste area and automatic row selection | Replace with immutable telemetry import and selection masks |
| Derived_Data | A1:V1003 | 22000 | 9 | 1 | Ride-height/damper-derived roll, twist, moment, and LLTD proxies | Research/benchmark until measurement model is validated |
| Summary | A1:F32 | 21 | 1 | 1 | Model-versus-data dashboard and regression slopes | Dashboard only; metrics depend on validated upstream definitions |
| Cell_Map | A1:E30 | 0 | 0 | 0 | Human-readable workbook map | Retain as migration documentation; replace cell addresses with stable IDs |

## Useful architectural patterns to preserve

- Direct wheel-rate input versus spring-rate/motion-ratio calculation.
- Front/rear ARB and chassis multipliers.
- Explicit rigid and compliant model outputs.
- Raw-data and derived-data separation.
- Row-selection flag.
- Model-versus-measurement summary.
- Warning that the LLTD proxy is not direct wheel-load LLTD.
- Replaceable compliance-model block.

These are workflow patterns, not approval of the formulas.

## Primary physics issue

The current compliance model softens front and rear axle roll stiffness independently by placing each in series with the full chassis torsional stiffness. Chassis torsion actually couples the front and rear body/suspension roll planes through equilibrium and angular compatibility. The current method can misrepresent the coupling and effectively reuse the same compliance twice.

The replacement should be a named coupled front–chassis–rear torsional model. The current placeholder must remain reproducible as a retired model revision.

## Circular-validation risks

Potential circular paths include:

1. model axle stiffness creates front/rear moment proxies;
2. those proxies create the LLTD proxy;
3. the proxy is compared against the model LLTD;
4. the same effective roll moment arm is used to infer measured total stiffness and predict model roll gradient;
5. row filters are chosen using expected steady-state behavior.

Controls required before calibration or validation:

- classify each dataset as sensor calibration, installation calibration, parameter identification, validation, or regression;
- hold out validation runs;
- store filtering and selection masks with parameters and reason codes;
- do not delete data merely because it disagrees with the model;
- report sensitivity, parameter correlation, residuals, and uncertainty;
- compare directly measured channels before model-assisted proxies;
- use independent rod-force or wheel-load evidence where available.

## Required model variants

The workbook should lead to separate named models rather than one LLTD result:

- rigid linear elastic roll;
- coupled first-mode chassis torsion;
- distributed or FEA-derived chassis compliance;
- total lateral load-transfer decomposition;
- ride-height and damper measurement model;
- model-assisted elastic LLTD proxy;
- direct wheel-load or rod-force LLTD estimate;
- transient roll/LLTD model.

Each requires a separate validity envelope and maturity status.

## Immediate documentation tasks

1. Create equation cards for every rigid-model relationship.
2. Create a retired equation card for the independent-series compliance placeholder.
3. Recover the chassis-stiffness source and define its boundary conditions.
4. Define the ARB stiffness quantity and reconcile it with the older workbook.
5. Document every sensor channel, calibration, position, orientation, timing, and uncertainty field.
6. Define the ride-height/road-plane/body-plane measurement model.
7. Define regression, filtering, uncertainty, and holdout procedures.
8. Create direct-measurement and proxy quantity names that cannot be confused.
