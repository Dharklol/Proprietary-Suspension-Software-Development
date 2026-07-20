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
- Reconstruction of the historical angular-branch orientation, monitor-datum subtraction, toe-inclusive wheel heading, incremental steer, wheel-angle fit, road-wheel gain, and reciprocal conventional steering-ratio definitions.
- Machine-readable WUFR-26 Ackermann export metadata and provisional audit-fit coefficients.
- Updated `BENCH-STEER-0001` authority hierarchy using `2026Ackermann.csv` as the primary final response and `Test_3.csv` as selection-era cross-check evidence.
- Explicit correction that the calculator quantity labeled `Steer Ratio` is road-wheel gain unless reciprocated and referenced to steering-wheel input.
- Rigid steering evaluator function specification documenting equation sources, validity, numerical behavior, branch control, failure semantics, and future car-specific extensions.
- Proposed equation records `EQ-STEER-0001` through `EQ-STEER-0007` for Ackermann reference, tie-rod closure, spatial position solution, transmission, ratios, turning radius, and Ackermann error.
- Fully specified `GEO-STEER-BASIC-001` synthetic mechanism fixture with expected closure, sweep, derivative, symmetry, Ackermann, radius, singularity, and deliberate failure results.
- Proposed analytical and limiting-case benchmark records `BENCH-STEER-0002` through `BENCH-STEER-0008`.
- Steering preimplementation freeze packet separating the fundamental evaluator gate from the still-open WUFR-26 Level E and physical Level F gates.
- Parameter-observation and active-value governance for separating quantity definitions, source observations, derived values, reconciliation, and reviewed active selections.
- WUFR-26 steering design-spec source catalog and inactive observations for wheelbase, axle sum toe, C-factor, and through-center steering ratio.
- Proposed `QTY-ALIGN-0003` axle sum-toe quantity and recovered WUFR-26 C-factor definition.
- WUFR-26 steering drawing/BOM authority manifest covering system assemblies, rack, tie rods, front uprights, drawing-number conventions, source hierarchy, and active-geometry extraction requirements.
- `RISK-STEER-0001` for steering BOM scope, historical identity, and title-block mismatch risk.
- WUFR-26 steering baseline-reconciliation packet linking `GEOMETRY FINAL.SLDPRT` to the active linkage assembly and defining the remaining native SolidWorks export.
- `PAR-STEER-0003` provisional symmetric one-sided rack-travel observation derived from the reported 1.00-in total travel.
- SolidWorks geometry-export CSV template for steering axes, joints, rack states, wheel planes, setup, and transmission sweep.
- Catalog and coordinate adapter for `WUFR-26 FINAL 8.21.2025.xlsx`, including numerical reconciliation with Test 3 and the steering FDR pickup table.
- Nominal WUFR-26 steering hardpoint source merge using final OptimumK upright points and final-FDR tie-rod pickups.
- Team-confirmed front-left interpretation of the steering FDR coordinates and corrected SolidWorks-to-OptimumK lateral sign mapping.
- Nominal static-toe reference-state rule: zero solved upright rotation represents the imported nonzero-toe geometry, while absolute wheel heading remains gated on a reviewed wheel-plane basis.

### Changed

- Ackermann comparisons now default to incremental steer with static toe handled separately, while total toe-inclusive wheel heading remains a required output.
- The WUFR-26 zero-input `20.57 deg` monitor value is treated as an observation rather than a frozen toe-inclusive subtraction datum.
- Design-study and active-assembly geometry are treated as connected evidence layers because `GEOMETRY FINAL.SLDPRT` is instantiated inside the fuller linkage subassembly; the active configuration still requires explicit export.
- Current `ST-60306` through `ST-60310` rack-family identities are accepted from the individual drawings; omission from the purchased-rack BOM is classified as a BOM/cost-report scope difference.
- `RISK-STEER-0001` severity is reduced after identity clarification, while native active-assembly reference confirmation remains required.
- The specification's `3.12:1` steering ratio is now a rejected observation prohibited from active calculations, targets, benchmarks, and validation.
- Rack center is defined as the midpoint between equal left/right stop limits; the reported 1.00-in total travel is provisionally interpreted as `+/-0.50 in` pending CAD or measurement verification.
- The native SolidWorks assembly export is reclassified from a blocker to nominal-design mechanism evaluation into a Level E/F installed-state correlation gate.
- The FDR tie-rod pair is no longer treated as a right-side point set; it is the front-left set in a lateral-positive-left SolidWorks frame.
- Static toe is treated as embedded in the imported nominal reference orientation and is not removed by modifying hardpoint coordinates.
