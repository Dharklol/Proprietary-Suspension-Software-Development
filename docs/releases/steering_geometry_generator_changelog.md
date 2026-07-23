# Steering Geometry Generator Changelog

## v0.1.0 — PR #21

### Added

- source-preserving inheritance loading for `WUFR27_STEERING_BASELINE_V0`;
- role vocabulary, variable definitions, immutable resolved candidates, and bound enforcement;
- ability to change a supported parameter between bounded-variable and fixed roles through the requirement set;
- explicit development-only nominal outer-pickup local frame;
- exact symmetric rack-inner-joint and outer-pickup generation;
- derived reference tie-rod joint-center lengths;
- centered-state preflight through the existing `MOD-STEER-0001` analyzer;
- structured candidate errors for role, bounds, symmetry, closure, branch, and singularity failures;
- zero-offset, reflection, transform, depth-bound, role-switching, derived-length, and analyzer-composition tests;
- implementation and review records for `P1-STR-002`.

### Authority boundary

This release does not implement optimizer search, target scoring, candidate ranking, full-sweep constraints, packaging, articulation, manufacturing, tire, effort, compliance, robustness, suspension-state, or physical-correlation models.

### Re-correlation

No physical re-correlation is required because this release adds only development geometry generation upstream of the unchanged rigid analyzer. Any later installed or as-built claim remains subject to the existing Level F gates.
