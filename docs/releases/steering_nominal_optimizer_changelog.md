# Steering Nominal Optimizer Changelog

## v0.1.0 — PR #22 review candidate

This release adds the first deterministic nominal-height inverse-design search around the existing steering analyzer.

### Added

- Frozen historical WUFR-26/27 wheel-heading regression target with the reviewed Level E convention adapter.
- Analyzer-generated synthetic target-recovery fixture.
- Complete left/right analyzer sweep for every evaluated candidate.
- Explicit hard-constraint results for geometry preflight, rack domain, analyzer completion, projection availability, singularity diagnostics, and monotonic response.
- Weighted left/right incremental-heading RMS objective with raw units, normalization, weight, domain, and residual summary.
- Normalized bounded coordinate-pattern search with deterministic seeded multistart.
- Study-selectable active variables; inactive variables remain at requirement-set references.
- Multiple retained feasible candidates with transparent single-objective convenience ranking.
- Machine-readable geometry, objective, constraint, analyzer, start, method, and provenance reports.
- CI benchmark reports for historical baseline evaluation and synthetic recovery.
- `BENCH-STEER-0010` and `BENCH-STEER-0011`.

### Preserved

- `MOD-STEER-0001` remains the sole rigid steering-kinematics and projection authority.
- Historical fits remain target evidence and never replace candidate mechanism evaluation.
- Infeasible candidates receive no objective score.
- WUFR-26/27 physical-correlation tasks remain open but nonblocking for generic inverse-design development.

### Not included

- Steering-arm, rack-housing, wheel, brake, chassis, or tire clearance constraints.
- Rod-end articulation, thread engagement, physical stop, hardware, or manufacturing constraints.
- Objective sensitivity or tolerance propagation.
- Multiobjective nondominated-set calculation.
- Discrete hardware selection.
- Suspension-travel, tire-informed, steering-effort, compliance, backlash, transient, or physical-parameter providers.
- Packaging-feasibility, manufacturing-feasibility, global-optimality, as-built, or production geometry claims.
