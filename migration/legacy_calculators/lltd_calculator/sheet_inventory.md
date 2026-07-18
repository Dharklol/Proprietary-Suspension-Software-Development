# LLTD Calculator — Detailed Sheet Inventory

Observations are structural and semantic inventory findings, not final engineering approval.

## `Inputs`

**Observed role:** Central vehicle, corner-rate, sensor, chassis, sweep, and row-filter input sheet.

**Major blocks**

- `A6:G14`: geometry, sprung mass/weight, effective roll moment arm, and axle fractions.
- `A16:G25`: per-corner spring rate, motion ratio, tire vertical stiffness, ride-height zero, damper-pot zero, pot-to-wheel scale, direct wheel rate, and input-mode flag.
- `A27:J36`: ARB stiffness, chassis stiffness, and scenario multipliers.
- `A38:G47`: chassis and ARB sensitivity-sweep controls.
- `A49:G53`: automatic steady-state row-filter controls.

**Useful explicit definitions**

- wheel rate from spring rate and squared motion ratio;
- direct wheel-rate override;
- ride-height and damper-pot zero/scale fields;
- angular stiffness displayed in both `N·m/rad` and `N·m/deg`;
- instruction that logger data belongs only in `Raw_Data`.

**Concerns**

- “effective roll moment arm” is a lumped parameter that can absorb errors from CG height, roll-axis definition, unsprung effects, and aero;
- front/rear sprung fractions are present but not integrated consistently into every result;
- sensor fields omit frame, exact location, orientation, uncertainty, sample rate, latency, and temperature behavior;
- ARB and chassis values conflict with values in the older suspension workbook and may not represent the same physical quantities;
- model-selection and filter controls are spreadsheet flags rather than typed records.

**Migration action**

Map every field to a parameter, sensor, channel, calibration, scenario, or analysis-control registry record. Preserve current values as observations with provenance and uncertainty.

## `Rigid_Model`

**Observed role:** Linear no-chassis-compliance baseline including springs, ARBs, and tire vertical stiffness.

**Major blocks**

- `B7:E11`: scaled spring rates, motion ratios, calculated/direct/active wheel rates.
- `B13:E13`: scaled tire vertical stiffness.
- `B14:B19`: spring and suspension roll stiffness.
- `B21:B25`: tire roll stiffness and effective rigid axle stiffness.
- `B27:B29`: total rigid roll stiffness, elastic LLTD, and roll gradient.
- `E14:F19`: repeated key outputs for display.

**Core relationships observed**

- wheel rate = spring rate × motion ratio²;
- axle spring roll stiffness is assembled from left/right wheel rates and track geometry;
- suspension and tire roll stiffness are combined in series at each axle;
- front and rear effective axle stiffnesses add for total roll stiffness;
- elastic LLTD = front effective axle stiffness / total effective axle stiffness;
- roll gradient = sprung weight × effective roll moment arm / total roll stiffness.

**Preliminary assessment**

These relationships can be defensible as a linear, small-angle, symmetric first-order baseline. They do not represent total LLTD, geometric transfer, unsprung transfer, nonlinear motion ratio, bump stops, asymmetric setup, damping, or transient behavior.

**Migration action**

Re-derive in canonical units, document limiting cases, and retain as a named benchmark model such as `rigid_linear_elastic_roll` rather than a universal roll model.

## `Compliance_Model`

**Observed role:** Placeholder chassis-compliance model and three sensitivity sweeps.

**Major blocks**

- `B6:B8`: rigid front/rear axle stiffness and active chassis stiffness.
- `B10:B16`: effective front/rear stiffness, total compliant stiffness, compliant LLTD, LLTD shift, roll gradient, and roll-gradient delta.
- `A20:H40`: chassis-stiffness sweep.
- `J20:P40`: front-ARB multiplier sweep.
- `R20:X40`: rear-ARB multiplier sweep.

**Explicit workbook statement**

Rows 8:15 use a simple placeholder in which each axle stiffness is independently softened in series with the chassis stiffness.

**Physics concern**

Chassis torsion couples the front and rear suspension/body roll planes. Treating both axles as independent series combinations with the full chassis stiffness can violate the intended compatibility model and effectively double-use the same compliance.

**Migration action**

Replace with a coupled front–chassis–rear torsional equilibrium and compatibility model. Preserve the sweep layout and outputs as workflow requirements. Keep the placeholder formulas under a retired model revision for reproducibility.

## `Raw_Data`

**Observed role:** Logger-data paste area.

**Columns**

- time;
- lateral acceleration;
- speed;
- steering angle;
- four ride-height signals;
- four damper-pot signals;
- `Use_Row_1_0`;
- notes.

**Formula block**

- `M4:M1003`: automatic row selection using minimum `|Ay|`, minimum speed, maximum `|dAy/dt|`, and an enable flag.

**Concerns**

- raw data is mixed with a formula-generated selection result;
- row selection has no separate provenance, reviewer, or reason code;
- steering input, yaw rate, longitudinal acceleration, wheel speed, brake pressure, sensor status, and synchronization are absent from the filter;
- finite-difference `dAy/dt` is noise- and sample-time-sensitive;
- fixed paste ranges can silently truncate longer runs;
- manual overrides alter the working table rather than creating a separate annotation artifact.

**Migration action**

Keep raw files immutable. Create normalized channel datasets and selection masks as derived artifacts with rule ID, parameters, software revision, and per-sample reason codes. Manual overrides become separate annotations.

## `Derived_Data`

**Observed role:** Convert logger channels into wheel travel, body roll, chassis twist, suspension roll, moment proxies, and LLTD proxy.

**Column map**

- `A:C`: time, lateral acceleration, selection flag.
- `D:G`: wheel travels from damper pots.
- `H:I`: front and rear body roll from ride-height left/right differences.
- `J`: average body roll.
- `K`: front minus rear body-plane angle, labelled chassis twist.
- `L:M`: front and rear suspension roll from wheel-travel differences.
- `N:O`: front and rear elastic roll-moment proxies.
- `P`: LLTD proxy.
- `Q:V`: selected values used by summary regressions.

**Critical interpretation controls**

- Four ride-height sensors observe a mixture of heave, pitch, roll, road plane, local flexibility, sensor geometry, and error.
- Front body roll minus rear body roll is not automatically pure chassis twist.
- Damper-pot-to-wheel conversion changes with kinematics when motion ratio is state-dependent.
- Suspension moment proxies depend on the stiffness model being evaluated.
- Proxy LLTD is therefore model-assisted rather than an independent direct wheel-load measurement.

**Migration action**

Define a measurement model before parameter identification. Include sensor positions and orientations, road-plane estimation, kinematic maps, time alignment, filtering, uncertainty, and identifiability. Preserve the current proxy under an explicit research quantity name.

## `Summary`

**Observed role:** Compare rigid model, compliant model, and selected-row measured proxies.

**Major outputs**

- rigid/compliant roll gradients;
- rigid/compliant total roll stiffness;
- rigid/compliant elastic LLTD;
- LLTD shift;
- measured roll, twist, and suspension-roll gradients from regression against `Ay`;
- inferred measured total roll stiffness;
- mean LLTD proxy;
- error metrics.

**Concerns**

- regressions are unweighted and do not expose intercept, confidence interval, residual structure, sample quality, hysteresis, or direction asymmetry;
- inferred measured stiffness uses the same effective roll-arm input as the model prediction;
- selected rows can be generated using expectations about steady-state model behavior;
- LLTD comparison is proxy-to-model rather than direct validation;
- no uncertainty bands are shown.

**Migration action**

Preserve the comparison workflow, but replace it with an identification/validation report that declares dataset role, selection mask, preprocessing lineage, regression model, uncertainty, residuals, parameter correlations, and holdout status.

## `Cell_Map`

**Observed role:** Human-readable map of important workbook cells.

**Value**

This demonstrates the desired discoverability and is useful migration documentation.

**Limitation**

Cell addresses are fragile and cannot serve as canonical IDs.

**Migration action**

Translate every mapped item into a stable quantity, model, parameter, sensor, or channel ID. The future UI should generate a similar map from registry metadata.
