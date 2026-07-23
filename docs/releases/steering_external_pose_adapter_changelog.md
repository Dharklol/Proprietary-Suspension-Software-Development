# Steering External Suspension-Pose Adapter Changelog

## v0.1.0 — PR #26

Adds the first source-neutral external suspension-pose exchange route to `MOD-STEER-0002`.

### Added

- `external_rigid_upright_pose_csv_v0.1.0` adapter.
- CSV state table with full left/right rigid transforms and manifest-declared state coordinates.
- TOML manifest requiring source path/revision, authority, canonical frame identity/definition, rotation convention, translation unit, and unresolved-steering declaration.
- Explicit rejection of inputs that already contain tie-rod-induced steering response.
- Explicit rule that source/vendor coordinate conversion occurs upstream rather than through hidden steering-package assumptions.
- Synthetic external exchange fixture reproducing the PR #24 canonical pose set.
- `BENCH-STEER-0018`, analyzer parity tests, and machine-readable report generation.
- Source audit recording available SolidWorks/OptimumK lineage evidence and the absence of a reviewed WUFR zero-steer upright transform series.

### Verification fixture

The external exchange fixture reproduces the existing nominal, symmetric +5 mm, and opposed +5/-5 mm synthetic states. The expected result is zero difference in state coordinates and rigid-transform components, followed by zero difference in `MOD-STEER-0001` wheel-heading and centered dynamic-toe results.

### Authority boundary

This release does not make the synthetic exchange fixture a WUFR pose source. A WUFR/OptimumK/SolidWorks/native-solver source still requires a reviewed source-specific conversion, revision, frame definition, unresolved-steering treatment, and reconstruction check before state-dependent design ranking. No physical testing, tire/load physics, robustness, hardware-feasibility, or production authority is introduced.
