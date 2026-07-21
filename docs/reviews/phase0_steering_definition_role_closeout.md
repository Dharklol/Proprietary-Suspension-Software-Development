# Phase 0 Steering Definition and Requirement-Role Closeout

**Review date:** 2026-07-21  
**Tasks:** `P0-STR-001`, `P0-STR-003`  
**Conclusion:** Complete for the bounded rigid nominal-height steering evaluator and frozen WUFR-26 benchmark requirement set.

## Reviewed evidence

- `docs/conventions/conventions_and_definitions.md`
- `docs/conventions/steering_canonical_definitions.md`
- `schemas/steering_definition_contract.toml`
- `registry/steering_quantity_subset_review.md`
- `registry/records/quantities/QTY-GEO-0001.toml`
- `registry/records/quantities/QTY-GEO-0004.toml`
- `registry/records/quantities/QTY-ALIGN-0001.toml`
- `registry/records/quantities/QTY-ALIGN-0002.toml`
- `registry/records/quantities/QTY-STEER-0001.toml` through `QTY-STEER-0007.toml`
- `registry/records/quantities/QTY-STEER-0010.toml` through `QTY-STEER-0015.toml`
- `configurations/steering/WUFR26_DESIGN_NOMINAL_V0.toml`
- `configurations/steering/WUFR26_STEERING_REQUIREMENT_ROLES_V0.toml`
- frozen rigid steering equation, implementation, benchmark, and Level E records
- WUFR-26 force, free-play, compliance, and sensor evidence boundaries

## `P0-STR-001` decisions

The following are reviewed and frozen for rigid steering use:

- SI internal units and the `+x` forward, `+y` left, `+z` up right-handed body frame;
- directed point, axis-line, wheel-plane, and reference-configuration object requirements;
- separate steering-wheel, primary-shaft, pinion, rack, and road-wheel quantities;
- rack-center and angular-zero declaration rules;
- global projected road-wheel heading and side-local static-toe conversion;
- static-toe versus incremental-steer separation;
- joint-center tie-rod length versus physical component dimensions;
- local and secant steering-ratio metadata;
- exact low-speed Ackermann reference and dimensional error sign;
- path-qualified turning-radius semantics;
- function/map provenance, fit metadata, no-extrapolation default, and explicit failure states.

`QTY-STEER-0008`, `QTY-STEER-0009`, and a normalized Ackermann coefficient remain deliberately deferred. Their absence does not block the left/right rigid evaluator because they are prohibited from serving as implicit aliases.

The frozen definitions do not claim that WUFR-26 installed stops, steering-wheel transmission, physical compliance, or as-built geometry are known.

## `P0-STR-003` decisions

`WUFR26_STEERING_REQUIREMENT_ROLES_V0` is frozen as an evaluation-only benchmark set:

- geometry and design-study transmission are fixed;
- rack domain is a hard nominal study bound;
- closure and branch identity are hard requirements;
- wheel headings, upright states, track, and joint-center lengths are derived;
- Test 3, FDR endpoints, free play, compliance, supplier information, and the rejected 3.12:1 value remain evidence or report items;
- no geometry variable, target curve, objective weight, or optimizer is active.

A future steering design study must create a new requirement-set ID. Candidate variables and constraints are retained only as a template and cannot become active until numerical bounds, packaging evidence, target authority, objective normalization, uncertainty treatment, and focused optimizer authorization are reviewed.

## Consistency checks

- Equal side-local toe values map to mirrored global centered headings through an explicit side conversion.
- Total and incremental wheel headings remain separate.
- The WUFR-26 CAD input-to-rack map is not labeled as installed steering-wheel transmission.
- The nominal ±1-inch rack study range is not labeled as installed stop travel.
- Level E residuals are not reused as targets or validation tolerances.
- Whole-system free play is not decomposed or added to supplier backlash without staged measurements.
- Missing sensor channel, sample-rate, and calibration values remain absent rather than zero-filled.

## Reopening conditions

Reopen `P0-STR-001` for a semantic change to frame, sign, zero, quantity meaning, projection, Ackermann error, turning-path identity, or result/failure schema.

Reopen `P0-STR-003` if the WUFR-26 benchmark changes roles, a source observation is promoted to an active target/input, or an optimizer attempts to use the frozen requirement-set ID.

New vehicle parameter values, source observations, sensor calibrations, measurement sessions, and separately identified design requirement sets do not automatically reopen these tasks.

## Work intentionally left open

- `P0-STR-002`: source byte hashing and formal unavailable-source disposition;
- `P0-STR-006`: installed stops, staged transmission, setup uncertainty, component attribution, and Level F acceptance;
- `P0-STR-011`: calibration and physical correlation;
- optimizer authorization and tire-informed targets;
- project-wide non-steering convention decisions.
