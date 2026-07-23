# Steering Constraint and Sensitivity Changelog

## v0.1.0 — PR #23 review candidate

This release adds evidence-aware constraint screening, analyzer-composed local sensitivity, and clearer multi-candidate comparison around the existing nominal optimizer.

### Added

- Named `STEERING_CONSTRAINT_PROVIDER_DEV_V0` contract.
- Separate active, failed, and unavailable constraint dispositions.
- Three broad development-only active checks for tie-rod length, singularity margin, and outer-pickup depth.
- Six explicit unavailable gates for articulation, thread engagement, steering-arm envelope, rack clearance, wheel/brake/chassis clearance, and installed stops.
- Blocking supplemental screening that removes a failed candidate from screened objective use while retaining the complete base analyzer result.
- Bounded central or one-sided local finite-difference objective and constraint-margin sensitivity.
- Objective-ranked candidate comparison with normalized design-space separation, geometry differences, constraint margins, unavailable gates, and ranking explanations.
- Machine-readable screening, sensitivity, and comparison reports.
- CI benchmark artifacts and frozen `steering_constraint_sensitivity_result_v0.1.0.toml`.
- `BENCH-STEER-0012` and `BENCH-STEER-0013`.

### Preserved

- `MOD-STEER-0001` remains the sole steering-kinematics and projection authority.
- Every sensitivity perturbation uses the role resolver, geometry generator, complete analyzer sweep, and target comparison.
- Missing hardware evidence remains unavailable rather than passed.
- Blocking constraint failures cannot be offset by objective accuracy.
- Historical and synthetic targets retain their existing evidence boundaries.

### Current limitation

Supplemental development constraints screen the retained search archive. They do not yet guide coordinate-pattern polling. Reviewed hardware constraints must enter every search-candidate disposition before the optimizer can be described as navigating a hardware-feasible design region.

### Not included

- Reviewed rod-end, tie-rod, rack, upright, steering-arm, wheel, brake, chassis, tire, or installed-stop limits.
- Discrete hardware selection.
- Manufacturing tolerance, uncertainty propagation, worst-case, probabilistic, or global sensitivity.
- Multiobjective nondominated-set or Pareto calculation.
- Suspension-state, tire-informed, steering-effort, compliance, backlash, transient, or physical-parameter providers.
- Packaging-feasibility, manufacturing-feasibility, global-optimality, as-built, or production geometry claims.
