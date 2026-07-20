# Parameter Observation and Active-Value Specification

**Status:** Proposed Phase 0 governance  
**Applies to:** Vehicle geometry, component properties, setup values, calibration constants, identified parameters, manufacturer values, CAD outputs, and legacy-calculator inputs

## 1. Purpose

A numerical value found in a workbook, FDR, drawing, CAD file, test report, or telemetry analysis is an **observation**. It does not become the active value for a model merely because it is current-looking, precise, frequently copied, or present in an official submission.

This specification separates:

1. the canonical physical quantity;
2. one or more observations of that quantity;
3. transformations or derivations applied to an observation;
4. conflicts and applicability differences;
5. the explicit active-value selection for a named configuration and model use.

The separation prevents duplicate values from becoming redundant model inputs and prevents historical, design-target, measured, and derived values from being silently mixed.

## 2. Record classes

### 2.1 Quantity definition

A quantity record states meaning, dimension, canonical unit, frame, reference point, sign, and aliases. It contains no car-specific active value.

### 2.2 Parameter observation

A parameter observation records one reported or calculated value and its provenance. An observation may be accepted as evidence while remaining inactive.

Examples:

- wheelbase stated in a design specification;
- rack travel measured on a fixture;
- C-factor stated by a rack drawing or design sheet;
- static toe entered in an FDR;
- steering ratio calculated from a CAD sweep;
- chassis stiffness identified from a physical test;
- a tire-model coefficient fitted from a declared dataset.

### 2.3 Derived observation

A derived observation is calculated from one or more parent observations. It records the equation or conversion and all parent IDs.

Examples:

- `88.9 mm/rev` converted to `0.014148874440869498 m/rad`;
- total mass calculated from four corner-scale observations;
- wheel rate calculated from spring rate and a motion-ratio observation;
- a polynomial fitted from an immutable CAD response table.

A derived observation is not independent corroboration of its parents.

### 2.4 Active-value selection

An active-value record selects one observation or one explicit reconciliation result for:

- a vehicle revision;
- a setup/configuration;
- a named model and fidelity;
- a validity interval;
- a stated engineering use.

The active-value record contains the selection rationale, competing observations, reviewer, uncertainty treatment, and revalidation trigger. It never deletes or overwrites source observations.

### 2.5 Reconciliation or identified estimate

When several observations are combined statistically or through a physical identification model, the result is a new derived observation with method, weights, assumptions, covariance/uncertainty, residuals, and parent IDs. It is not an undocumented average.

## 3. Required parameter-observation fields

Every formal parameter observation should contain:

- stable observation/parameter ID;
- canonical quantity ID or explicit `mapping_unresolved` state;
- source-native label and definition;
- source artifact ID, exact path, provider file/version ID, and hash;
- source location such as sheet, table, drawing view, CAD feature, or test channel;
- source-native value and unit;
- canonical value and unit where mapping is accepted;
- conversion equation and parent IDs for derived observations;
- vehicle generation and configuration applicability;
- coordinate frame, reference point, and sign where applicable;
- evidence role;
- observation method: reported, measured, CAD-derived, manufacturer, identified, calculated, estimated, or placeholder;
- uncertainty or explicit `not provided` state;
- significant-figure interpretation;
- date/revision/author where available;
- status: candidate, reviewed, superseded, conflicting, rejected, or archived;
- authority state: inactive observation, active selection candidate, or active selection;
- assumptions and unresolved questions;
- dependent models and benchmarks;
- reviewer and revalidation trigger.

Missing metadata remains explicit. It is not replaced by a guessed zero uncertainty.

## 4. Evidence-role rules

The primary evidence role follows `evidence_role_and_redundancy_policy.md`.

Common parameter-observation roles are:

- `candidate_observation`;
- `calibration_reference`;
- `installation_calibration`;
- `parameter_identification`;
- `cross_tool_evidence`;
- `historical_context`;
- `source_copy`;
- `research_exploration`.

A design-review or competition specification is strong evidence of **reported design intent**. It is not automatically a calibrated measurement of the built car.

## 5. Mapping rules

### 5.1 No forced mapping

A source label is mapped to a canonical quantity only when its definition is compatible.

Examples:

- a source-defined tread-center track is not silently mapped to steering-axis ground-intersection track;
- a scalar steering-arm length is not substituted for the authoritative outer-joint point and steering-axis line;
- an Ackermann percentage is not mapped to dimensional Ackermann error without recovering the percentage definition;
- front total toe is not divided equally between wheels unless a symmetry assumption is declared.

### 5.2 Native and canonical values are both retained

The source-native value is immutable evidence. Canonical conversion is a separate field. Unit conversion never erases the reported form or its significant figures.

### 5.3 One active input per quantity and applicability

A model may not receive two independent active values for the same physical quantity and configuration. Multiple observations remain available for review and uncertainty analysis, but active selection is singular unless the model explicitly represents a distribution or reconciliation process.

### 5.4 Derived quantities are not duplicate inputs

If tie-rod length is derived from joint coordinates, the same model does not also accept an unrelated tie-rod length as an unconstrained active input. It may compare the derived result against an availability or adjustment bound.

## 6. Uncertainty treatment

Observation uncertainty may include:

- measurement repeatability;
- calibration uncertainty;
- installation and datum uncertainty;
- resolution and rounding;
- manufacturing tolerance;
- CAD/configuration uncertainty;
- model-form uncertainty for identified or calculated values;
- source ambiguity.

`not provided` is an acceptable initial state. It blocks claims that require a numerical confidence interval but does not require inventing one.

A displayed number of significant digits is not an uncertainty estimate. It may only establish a rounding interval when the source process supports that interpretation.

## 7. Conflict handling

Observations conflict when their definitions and applicability should match but their uncertainty intervals do not reasonably overlap.

A conflict record states:

- involved observation IDs;
- expected common definition/configuration;
- magnitude and engineering consequence;
- likely causes;
- blocked dependent decisions;
- proposed resolution test or source review;
- responsible owner.

Values under different car revisions or setup states are configuration-specific observations, not conflicts merely because they differ.

## 8. Active-value selection gate

An observation may become active only when:

1. the quantity definition is reviewed;
2. the source and applicability are known;
3. unit, frame, sign, and reference are compatible;
4. competing observations are listed;
5. uncertainty is stated or its absence is accepted for the bounded use;
6. the selection rationale is documented;
7. affected models and benchmarks are identified;
8. a reviewer approves the selection;
9. an expiration or revalidation trigger is stated.

A competition spec, FDR, CAD file, drawing, or physical measurement can satisfy the source requirement, but each has a different evidence role and uncertainty path.

## 9. Steering-specific application

The first steering parameter-observation set should distinguish:

- wheelbase;
- front wheel/tread-center track;
- steering-axis ground-intersection track;
- left/right steering-axis lines;
- rack origin, axis, center joints, width, and stops;
- rack displacement per pinion angle;
- steering-wheel-to-pinion relation;
- left/right static toe and axle sum toe;
- steering-arm outer-joint points;
- scalar steering-arm length as report/supporting evidence;
- tie-rod joint-center length and physical adjustment range;
- center steering ratio and its exact average/output definition;
- reported Ackermann percentage and its unresolved metric definition.

The WUFR-26 design specification is an appropriate initial seed because it records current design intent and defines several source labels. It is not sufficient by itself to reconstruct the rigid mechanism or validate the built vehicle.

## 10. Change control

- Source observations are immutable; corrections create a new revision or superseding record.
- Active selections are versioned and reference exact observation IDs.
- A new car revision or setup does not overwrite the previous configuration.
- Discovering a definition mismatch reopens dependent model and benchmark reviews.
- Code and UI consume active selections through stable quantity IDs, never source-cell addresses or display labels.