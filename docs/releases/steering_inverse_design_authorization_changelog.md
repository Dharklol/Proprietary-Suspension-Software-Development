# Steering Inverse-Design Authorization Changelog

## Added

- `AUTH-STEER-0002` for a bounded nominal-height steering inverse-design prototype.
- `MOD-STEER-0002` as a role-driven orchestration layer that composes the existing `MOD-STEER-0001` analyzer.
- `WUFR27_STEERING_BASELINE_V0` as the unchanged WUFR-26/27 nominal geometry baseline for current calculations, regression, documentation, and later physical correlation.
- `STEERING_INVERSE_DESIGN_DEV_V0` with role-selectable variables, exact first-release symmetry, tightly bounded outer-pickup depth, historical regression target, alternative target modes, and multi-candidate reporting requirements.
- A cohesive optimizer architecture with future suspension-pose, tire-target, rack-load/effort, uncertainty, and physical-parameter provider boundaries.
- Phase 1 steering progress tasks for geometry generation, constrained search, candidate reporting, robustness, and later provider integration.
- Automated authorization tests covering analyzer composition, baseline inheritance, role selection, depth bounds, symmetry, target alternatives, candidate visibility, and nonblocking physical tasks.

## Changed

- `MOD-STEER-0001` is clarified as the sole rigid steering-linkage evaluator and downstream dependency of `MOD-STEER-0002`.
- The implementation authorization matrix now permits the phased inverse-design prototype after focused review while retaining production, physical, tire, effort, compliance, robustness, and learned-optimizer gates.
- WUFR-26 installed-state and Level F tasks remain active but no longer block generic nominal inverse-design development.
- The literature concordance now records the optimizer-specific basis from Guiggiani, Gillespie, Romano, Huang et al., Milliken, and Pacejka.

## Re-correlation

No existing rigid analyzer or Level E numerical result is changed by this authorization packet. The next geometry-generator implementation must prove zero-offset identity with the existing analyzer. Later optimizer outputs require re-evaluation whenever their requirement set, target provider, constraints, bounds, analyzer version, or future physical-provider inputs change.
