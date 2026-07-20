# Parameter Observation and Active-Value Specification

**Status:** Proposed Phase 0 governance  
**Applies to:** Geometry, component properties, setup values, calibration constants, identified parameters, CAD outputs, manufacturer data, and legacy-calculator inputs

## Purpose

A numerical value found in a workbook, drawing, FDR, CAD file, test report, or telemetry analysis is an **observation**. It is not an active model value merely because it is current-looking, precise, frequently copied, or present in an official submission.

The project separates:

1. the canonical physical quantity;
2. one or more observations of that quantity;
3. derived observations and unit conversions;
4. conflicts or configuration differences;
5. the explicit active-value selection for a named configuration and model use.

## Record classes

### Quantity definition

Defines meaning, dimension, canonical unit, frame, reference point, sign, and aliases. It contains no car-specific active value.

### Parameter observation

Records one reported, measured, CAD-derived, calculated, manufacturer, identified, estimated, or placeholder value and its provenance. An observation may be reviewed evidence while remaining inactive.

### Derived observation

Calculated from one or more parent observations. It records the equation or conversion and all parent IDs. A unit conversion or fitted curve is not independent corroboration of its parent data.

### Active-value selection

Selects one observation or one explicit reconciliation result for a vehicle revision, setup, model fidelity, validity interval, and engineering use. It records rationale, competing observations, uncertainty treatment, reviewer, and revalidation trigger.

### Reconciliation or identified estimate

Combining observations creates a new derived observation with method, weights, assumptions, covariance or uncertainty, residuals, and parent IDs. Undocumented averaging is prohibited.

## Required observation fields

Formal observations should include:

- stable parameter ID and canonical quantity ID, or an explicit unresolved mapping;
- source-native label, definition, value, and unit;
- canonical value and unit where mapping is accepted;
- source artifact, location, revision, and hash state;
- vehicle/configuration applicability;
- frame, reference point, and sign where applicable;
- evidence role and observation method;
- uncertainty or explicit `not provided` state;
- authority state: inactive observation, active-selection candidate, or active selection;
- assumptions, unresolved questions, dependent models, benchmarks, reviewer, and revalidation trigger.

Missing metadata remains explicit. It is never replaced with zero uncertainty.

## Mapping rules

- Do not force a source label into a canonical quantity when definitions differ.
- Preserve both source-native and canonical values.
- One model configuration receives one active input for one physical quantity unless it explicitly represents a distribution or reconciliation model.
- A derived quantity cannot also enter the same model as an unrelated unconstrained input.
- A tread-center track is not steering-axis ground-intersection track.
- A scalar steering-arm length is not a substitute for the steering-axis line and outer-joint point.
- An Ackermann percentage is not mapped to dimensional Ackermann error until its definition is recovered.
- Axle sum toe is not divided into left/right values without a declared setup or symmetry assumption.

## Uncertainty and conflicts

Uncertainty may include repeatability, calibration, installation datum, resolution, rounding, manufacturing tolerance, CAD/configuration uncertainty, model-form uncertainty, and source ambiguity. Significant digits alone are not an uncertainty estimate.

Observations conflict only when definition and applicability should match but disagreement exceeds their defensible uncertainty. Different car revisions or setup states are configuration-specific observations, not automatically conflicts.

A conflict record identifies the competing observations, expected common definition, consequence, likely causes, blocked decisions, resolution test, and owner.

## Active-value gate

An observation may become active only when:

1. the quantity definition is reviewed;
2. source and applicability are known;
3. units, frame, sign, and reference are compatible;
4. competing observations are listed;
5. uncertainty is stated or its absence is accepted for the bounded use;
6. the selection rationale and affected models are documented;
7. a reviewer approves the selection;
8. an expiration or revalidation trigger is stated.

## Steering application

The first steering parameter set distinguishes wheelbase, tread-center track, steering-axis ground-intersection track, steering-axis lines, rack origin and axis, rack joints and stops, rack displacement per pinion angle, steering-wheel-to-pinion relation, left/right static toe, axle sum toe, steering-arm outer-joint points, tie-rod joint-center length and adjustment range, center steering ratio, and reported Ackermann metrics.

The WUFR-26 design specification is a useful seed because it records current design intent and defines several labels. It is not sufficient by itself to reconstruct the mechanism or validate the built vehicle.

## Change control

Source observations are immutable. Corrections create a new or superseding record. Active selections are versioned and reference exact observation IDs. New car revisions and setups do not overwrite prior configurations. Code and UI consume active selections through stable quantity IDs, never source-cell addresses or display labels.
