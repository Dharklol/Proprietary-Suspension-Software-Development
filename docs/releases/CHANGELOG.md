# Changelog

All notable project changes should be recorded here. Model releases must identify affected registry IDs, benchmark changes, migration impact, and whether re-correlation is required.

## Unreleased

### Added

- Initial Phase 0 governance, convention, literature, and registry scaffolding.
- Standard-library registry validator and CI workflow.
- Initial quantity, risk, model, benchmark, and migration records.
- Documentation-before-implementation gate.
- Structural inventories for the suspension and LLTD workbooks.
- Steering geometry and tie-rod inverse-design transition specification.
- Stable block-level disposition register.
- Legacy-to-canonical quantity mapping.
- Evidence-role, redundancy, active-value, and circular-validation policy.
- External source-recovery register.
- Equation-card and benchmark backlog.
- Physics implementation authorization matrix.
- Proposed steering canonical-definition subset covering geometry, transmission, road-wheel angles, tie-rod length, ratios, Ackermann metrics, and turning paths.
- Formal proposed quantity records for the first rigid-steering review subset.
- Steering source-recovery search log and team-assisted recovery worksheet.
- Steering requirement-role matrix for inverse design.
- Steering analytical, limiting-case, cross-tool, and physical benchmark plan.
- Box manifest and directory inventory for the recovered WUFR-26 steering geometry, candidate motion-study CSV exports, reference workbook, and supporting CAD files.
- Source designation of `GEOMETRY FINAL.SLDPRT` as the WUFR-26 legacy SolidWorks benchmark parent, pending benchmark-freeze metadata.
- WUFR-25 `Steering_range_optimization.m` semantic audit and benchmark-only disposition.
- FDR Test 3 selection mapping and explicit interpretation of `0.5 inch back` as a relative rearward rack-placement change.
- Catalog and structural parse of `2026Ackermann.csv` as the WUFR-26 final-geometry second-motion-study export.
- Reconstruction of the historical angular-branch orientation, monitor-datum subtraction, toe-inclusive wheel heading, incremental steer, wheel-angle fit, finite-difference road-wheel gain, and reciprocal conventional steering-ratio definitions.
- Machine-readable WUFR-26 Ackermann export metadata and provisional fit coefficients.
- Updated `BENCH-STEER-0001` authority hierarchy using `2026Ackermann.csv` as the primary final response and `Test_3.csv` as selection-era cross-check evidence.
- Explicit correction that the calculator quantity labeled `Steer Ratio` is road-wheel gain unless reciprocated and referenced to steering-wheel input.
- Parameter-observation and active-value governance specification.
- WUFR-26 design-spec source catalog and steering parameter-observation seed.
- Proposed `QTY-ALIGN-0003` axle sum-toe definition.
- Candidate inactive observations for WUFR-26 wheelbase, front sum toe, rack displacement per pinion angle, and through-center steering ratio.

### Changed

- The WUFR-26 design-spec C-factor definition is recorded as effective rack travel per revolution of the steering input/pinion shaft.
- Source-native tread-center track, Ackermann percentage, and scalar steering-arm length are retained without forced canonical mapping.
- WUFR values remain inactive observations until a reviewed active-value selection is made for a named configuration and model use.
