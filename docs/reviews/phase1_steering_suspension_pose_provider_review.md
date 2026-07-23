# Phase 1 Steering Suspension-Pose Provider Review

**Tasks:** `P1-STR-006A`, `P1-STR-006B`  
**Pull request:** #24  
**Authorization:** `AUTH-STEER-0002`  
**Status:** Review ready

## Review question

Does the implementation provide a source-agnostic suspension-pose contract and multi-state steering evaluator that preserves `MOD-STEER-0001` as the sole tie-rod/steering-response authority, prevents double-counting of externally generated toe, supports symmetric and asymmetric operating states, and remains explicitly nonphysical until reviewed suspension-state data are supplied?

## Evidence reviewed

- `src/pssd_steering/optimization/poses.py`
- `src/pssd_steering/optimization/multistate.py`
- `src/pssd_steering/optimization/pose_reporting.py`
- `benchmarks/steering/STEERING_SYNTHETIC_POSE_SET_V0.toml`
- `tests/test_steering_suspension_pose_provider.py`
- `scripts/run_steering_pose_provider_benchmarks.py`
- `benchmarks/steering/steering_pose_provider_result_v0.1.0.toml`
- `docs/models/steering/steering_suspension_pose_provider_implementation_v0.1.0.md`
- `docs/models/steering/steering_optimizer_architecture.md`
- `docs/literature/literature_concordance.md`

## Gate disposition

| Gate | Disposition |
|---|---|
| Provider is source-agnostic | Satisfied. No OptimumK, CAD, or native-suspension API appears in the steering package. |
| Provider excludes steering DOF | Satisfied. Every accepted pose declares `upright_reference_pose_excludes_tie_rod_steering_rotation`; pre-steered pose declarations are rejected. |
| Analyzer remains authoritative | Satisfied. Pose transforms only relocate upright-bound geometry; `MOD-STEER-0001` solves rack center and every rack state. |
| Rack remains chassis-fixed | Satisfied. Rack axis and inner joints are unchanged by upright transforms. |
| Tie-rod length remains a design property | Satisfied. The nominal generated joint-center length is retained through suspension poses. |
| Identity composition | Satisfied. Identity pose preserves nominal geometry and analyzer results. |
| Pose validity separated from steering feasibility | Satisfied. A valid but unreachable pose returns an infeasible steering state rather than a pose-definition error. |
| Asymmetric operating states | Satisfied. Opposed wheel travel is supported without enabling asymmetric design variables. |
| Dynamic-toe reporting | Satisfied for synthetic software-verification states using the canonical wheel-plane projection and side-local toe convention. |
| Literature boundary | Satisfied. Gillespie, Guiggiani, and Romano support state-specific alignment/steering treatment and staged steering-to-suspension integration; project-specific interface choices are identified as such. |
| Physical claims excluded | Satisfied. Synthetic pose numbers are explicitly not WUFR suspension or bump-steer evidence. |

## Frozen benchmark summary

The identity state produces zero dynamic-toe change by definition and preserves the nominal analyzer path.

For the synthetic rigid +5 mm vertical upright translation, the reference geometry returns approximately `+0.4721293147 deg` side-local toe-out change on both sides. The opposed +5/-5 mm state returns approximately `+0.4721293147 deg` left and `-0.3970622842 deg` right. All fifteen rack samples per side solve in the three frozen states; the minimum recorded singularity ratio for the nonnominal states is approximately `0.3894383917`.

These values demonstrate that the canonical pose transforms affect the existing tie-rod mechanism consistently. They are not predictions of actual WUFR bump steer because the synthetic vertical-only transforms are not a suspension kinematics model.

## Open gates

- No reviewed WUFR suspension-pose data set is connected yet.
- No external OptimumK/CAD adapter has been reviewed against the canonical pose contract.
- Multi-state responses are report-only; the nominal optimizer does not yet aggregate pose-state objectives.
- Tire, effort/load, tolerance/robustness, hardware packaging, and physical-parameter providers remain separate gates.
- Physical correlation remains deferred until installed data exist.

## Proposed decision

Advance `P1-STR-006A` and `P1-STR-006B` to complete after team review and merge of PR #24. Permit the next nonphysical steering work to focus on either a reviewed external suspension-pose adapter/data set or `P1-STR-006C` operating-state target aggregation. Do not activate `P1-STR-006E` physical-parameter work from this review.
