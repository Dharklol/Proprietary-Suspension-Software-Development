# Steering Suspension-Pose Provider Changelog

## v0.1.0 — PR #24 review candidate

This release extends the steering inverse-design vertical slice from a single nominal suspension pose to provider-neutral suspension operating states while preserving `MOD-STEER-0001` as the sole steering mechanism evaluator.

### Added

- Canonical left/right rigid upright-pose transforms with named state coordinates, units, source path, and authority.
- Mandatory `upright_reference_pose_excludes_tie_rod_steering_rotation` contract to prevent double-counting bump steer from external sources.
- Pose application that moves steering axes, outer tie-rod pickups, and wheel-plane references while keeping rack geometry and inner joints chassis-fixed.
- Fixed nominal tie-rod design length through suspension-state evaluation.
- Separate pose-definition validity and steering-state feasibility semantics.
- Multi-state complete rack sweeps through `MOD-STEER-0001`.
- Centered global heading and side-local dynamic-toe reporting.
- Symmetric and asymmetric suspension operating-state support without enabling asymmetric design variables.
- Synthetic identity, +5 mm symmetric bump, and +5/-5 mm opposed-travel fixtures.
- Full and summary CI reports plus frozen synthetic results.
- `BENCH-STEER-0014` and `BENCH-STEER-0015`.

### Preserved

- The existing role resolver and parametric geometry generator define design geometry.
- `MOD-STEER-0001` remains authoritative for tie-rod closure, branch continuation, singularity, and steering response.
- Historical WUFR target curves remain regression evidence and are not automatically applied as non-nominal suspension-state objectives.
- Missing physical/hardware evidence remains unavailable rather than passed.
- WUFR-26/27 physical-correlation work remains open but nonblocking for generic provider development.

### Not included

- Native suspension kinematics.
- A reviewed WUFR, OptimumK, CAD, or native-solver suspension-pose data set.
- Multi-state target aggregation inside the optimizer objective.
- Tire-informed targets or handling-state generation.
- Rack load or steering effort.
- Tolerance/robustness propagation.
- Physical transmission, compliance, backlash, stop, or as-built corrections.
- Packaging, manufacturing, physical-correlation, or production geometry authority.
