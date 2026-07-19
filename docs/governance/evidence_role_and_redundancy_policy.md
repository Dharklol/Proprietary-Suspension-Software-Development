# Evidence Role, Redundancy, and Circular-Validation Policy

**Status:** Proposed Phase 0 governance  
**Applies to:** Parameters, external simulations, spreadsheets, measurements, telemetry, calibration, identification, validation, and regression datasets

## 1. Purpose

The canonical model must avoid redundant active inputs while preserving independent evidence. Two values that describe the same physical quantity are not automatically duplicates to delete. They may be:

- repeated copies of one source;
- independent measurements;
- measurements under different configurations;
- model predictions;
- calibration references;
- validation evidence;
- historical values that remain useful for comparison.

The project stores all defensible observations with provenance, but resolves only one active value or one explicit reconciliation model for a given configuration and analysis.

## 2. Evidence roles

Every observation, file, curve, parameter value, or derived dataset receives exactly one primary role for a particular use.

| Role | Purpose | May set an active parameter? | May validate the same parameter/model? |
|---|---|---:|---:|
| `source_copy` | Duplicate or transformed copy of another artifact | No | No |
| `candidate_observation` | Possible value awaiting authority review | Not directly | Only after reclassification |
| `calibration_reference` | Establish sensor scale, zero, nonlinearity, hysteresis, or temperature correction | Yes, for calibration parameters | No, for the same calibration |
| `installation_calibration` | Establish sensor pose, linkage ratio, fixture geometry, or installed conversion | Yes, for installation parameters | No, for the same installation model |
| `parameter_identification` | Estimate physical model parameters from vehicle or rig response | Yes, through an identified estimate | No, for the fitted parameter/model on the same data |
| `model_validation` | Test predictions using held-out evidence | No tuning after designation | Yes |
| `regression_test` | Detect unintended software/model changes using frozen expected results | No | Verifies implementation continuity, not physical truth by itself |
| `cross_tool_evidence` | Compare with CAD, FEA, multibody, or another calculator | No automatic authority | Yes, if assumptions and inputs are independent and aligned |
| `published_benchmark` | Reproduce an analytical or published case | No vehicle-specific authority | Yes, for equations and implementation within the benchmark scope |
| `historical_context` | Preserve prior-car or prior-method knowledge | No, unless applicability is re-established | No direct current-car validation |
| `research_exploration` | Explore hypotheses or immature models | No production authority | No until promoted through review |

A dataset may have different roles for different quantities only when those uses are explicitly partitioned. For example, one run may calibrate steering zero during a static segment and validate yaw response during a separate maneuver segment, provided the segmentation and independence are documented.

## 3. Redundancy classification

When two records appear to describe the same quantity, classify the relationship before resolving an active value.

### 3.1 Exact duplicate

Same underlying source, copied or reformatted. Keep one authoritative artifact and lineage links to copies. Do not treat agreement as corroboration.

### 3.2 Derived duplicate

One value is calculated from the other, such as mass converted to weight or a polynomial fitted from a CAD sweep. Preserve both if useful, but mark the dependency. They are not independent evidence.

### 3.3 Shared-input correlation

Two estimates use a common uncertain input. Example: measured total roll stiffness and predicted roll stiffness both use the same assumed effective roll moment arm. Agreement is partially circular and must not be reported as independent validation.

### 3.4 Independent repeated measurement

Same method repeated under controlled conditions. Use to estimate repeatability and random uncertainty.

### 3.5 Independent alternate method

Different measurement or calculation method for the same quantity. This is strong corroboration when shared assumptions are identified.

### 3.6 Configuration-specific observation

Values differ because vehicle revision, setup, driver, tire, ride height, pressure, temperature, or loading differs. Store applicability conditions rather than averaging them blindly.

### 3.7 Conflicting observation

Definitions or conditions should match, but values disagree beyond combined uncertainty. Create a conflict record, block dependent high-risk results where appropriate, and assign a resolution test.

## 4. Active-value resolution

An active parameter selection must record:

- quantity ID;
- selected observation or estimation result;
- vehicle/configuration applicability;
- source type and date;
- uncertainty and confidence;
- competing observations;
- reason for selection;
- resolver and reviewer;
- expiration or revalidation condition;
- dependent model IDs.

No spreadsheet location, newest timestamp, or visually plausible value is sufficient authority by itself.

## 5. Circular-validation failure modes

### 5.1 Model-based filtering removes model disagreement

Example: telemetry rows are discarded because the response differs from the expected steady-state model. This can remove genuine transient, compliance, saturation, sensor, or missing-physics behavior.

**Control:** Selection rules use maneuver definitions and sensor-quality criteria first. Model residuals may be used for diagnosis or robust weighting, but every exclusion/down-weight receives a reason code and remains recoverable.

### 5.2 Calibration and validation use the same response

Example: steering compliance is tuned to match a ramp-steer run, then the same run is reported as validation.

**Control:** Predeclare calibration/identification and holdout datasets. Any reuse changes the validation claim and must be disclosed.

### 5.3 A derived measurement uses the model being tested

Example: LLTD proxy is calculated from measured suspension roll multiplied by modeled axle stiffness, then compared with the same modeled LLTD.

**Control:** Label the result model-assisted. Validate intermediate measured quantities and seek independent wheel-load or strain-based evidence where possible.

### 5.4 External software and native implementation share the same derivation

Matching results may confirm transcription but not the physical model.

**Control:** Record source independence. Cross-tool comparison counts as verification level E only after conventions, inputs, model options, and shared assumptions are documented.

### 5.5 Parameter compensation

A fitted effective parameter absorbs multiple missing effects, then is interpreted as one physical property.

**Control:** Report identifiability, sensitivity, correlations, confidence intervals, and residual structure. Effective parameters retain names that reveal their lumped meaning.

### 5.6 Polynomial or surrogate validates its own source

A curve fit matching the CAD or tire data from which it was fitted is interpolation verification, not independent validation.

**Control:** Separate fit residuals, cross-validation, extrapolation checks, and independent physical measurements.

## 6. Dataset partition requirements

Every test program should define before analysis:

1. calibration segments;
2. installation-calibration segments;
3. parameter-identification maneuvers;
4. validation maneuvers or held-out repetitions;
5. regression datasets;
6. excluded maneuvers and reasons.

For small datasets where complete separation is impossible, use blocked or leave-one-run-out validation and state the resulting limitation.

## 7. Filtering and annotation controls

Raw data is immutable. Processing produces new artifacts linked through parent hashes.

Per-sample or per-window annotations should support reason codes including:

- sensor saturation;
- dropout or invalid status;
- time-synchronization failure;
- outside maneuver window;
- insufficient excitation;
- excessive derivative/noise;
- wheel lift or contact loss;
- model extrapolation;
- transient region excluded from a steady-state estimate;
- manual review exclusion;
- robust-estimator down-weight;
- unknown anomaly retained for investigation.

A model residual alone is never an automatic deletion reason.

## 8. External simulation evidence

CAD, OptimumK, ADAMS, VI-Grade, ANSYS, MATLAB, and spreadsheet results must include:

- software and version;
- model/template revision;
- geometry/configuration revision;
- input deck or parameter file hash;
- coordinate and sign conventions;
- solver/options;
- sweep definition;
- output definitions;
- known omissions;
- export hash;
- relationship to the native model.

External tools remain optional evidence or adapters, not untracked runtime dependencies.

## 9. Review outcomes

Evidence review may produce:

- `accepted_as_active_source`;
- `accepted_as_independent_validation`;
- `accepted_with_restrictions`;
- `historical_only`;
- `derived_duplicate`;
- `conflict_requires_test`;
- `insufficient_provenance`;
- `rejected`.

The outcome and reason are preserved even when a value is superseded.

## 10. Required links to FMEA and model assurance

High-impact evidence failures receive risk records linked to affected quantities and models. Examples include:

- incorrect unit or frame;
- stale vehicle revision;
- uncalibrated sensor;
- shared-input circularity;
- insufficient excitation;
- unidentifiable parameter set;
- model extrapolation;
- external artifact not reproducible.

Evidence maturity is separate from equation maturity. A model with reviewed equations cannot reach design-decision approval until its active parameters and applicable validation evidence meet the required level.
