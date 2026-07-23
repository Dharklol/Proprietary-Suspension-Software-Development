# Steering Operating-State Target Changelog

## v0.1.0 — PR #25

Adds the first explicit suspension-state objective layer to `MOD-STEER-0002`.

### Added

- `OperatingStateTarget` and `OperatingStateTargetSet` contracts.
- Explicit `objective` and `report_only` state roles.
- Mandatory report-only treatment for unlisted states in the first contract.
- Per-state left/right heading curves, sample weights, normalization scales, objective weights, convention adapters, source authority, and provenance.
- Analyzer-generated synthetic multi-state targets for software recovery testing.
- Provider-neutral explicit target-table loading for later manual or external target sources.
- State-level two-wheel weighted RMS objective decomposition.
- Transparent weighted normalized state aggregation.
- `OperatingStateCandidateEvaluation` with hard whole-envelope infeasibility.
- Deterministic operating-state inverse-design wrapper reusing the existing coordinate-pattern search core.
- Machine-readable operating-state candidate and search reports.
- `BENCH-STEER-0016` and `BENCH-STEER-0017` plus frozen numerical result and regression test.

### Verification fixture

The synthetic recovery case uses a known `+0.01875 m` rack-longitudinal source with three target states weighted `1.0`, `0.8`, and `0.6`. The frozen search recovers the source to floating-point precision with zero aggregate objective, while the baseline reference geometry has a nonzero aggregate error.

### Authority boundary

This release does not add or authorize tire-force target generation, real WUFR suspension-pose authority, steering-effort/load optimization, hardware feasibility, tolerance/robustness, physical correlation, global/Pareto claims, or production geometry selection.
