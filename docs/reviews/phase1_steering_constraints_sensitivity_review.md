# Phase 1 Steering Constraint, Sensitivity, and Candidate-Comparison Review

**Task:** `P1-STR-004`  
**Pull request:** #23  
**Authorization:** `AUTH-STEER-0002`  
**Status:** Review ready

## Review question

Does the implementation add an evidence-aware constraint layer, analyzer-composed local sensitivity, and clearer multi-candidate comparison without duplicating steering physics, inventing missing hardware limits, or promoting development results to packaging, manufacturing, robustness, or production authority?

## Evidence reviewed

- `src/pssd_steering/optimization/constraints.py`
- `src/pssd_steering/optimization/sensitivity.py`
- `src/pssd_steering/optimization/candidate_comparison.py`
- `src/pssd_steering/optimization/study_reporting.py`
- `configurations/steering/STEERING_CONSTRAINT_PROVIDER_DEV_V0.toml`
- `tests/test_steering_constraints_sensitivity.py`
- `scripts/run_steering_constraint_sensitivity_benchmarks.py`
- `benchmarks/steering/steering_constraint_sensitivity_result_v0.1.0.toml`
- `docs/models/steering/steering_constraints_sensitivity_implementation_v0.1.0.md`
- repository registry validation, unit tests, and generated CI reports

## Gate disposition

| Gate | Disposition |
|---|---|
| Existing analyzer remains authoritative | Satisfied. Screening and sensitivity consume complete `CandidateEvaluation` records produced by the existing generator and `MOD-STEER-0001`; no closure, branch, projection, ratio, Ackermann, or turning equations are added. |
| Active constraints are explicit | Satisfied. Each active provider result includes value, limit, margin, unit, state, authority, blocking status, and message. |
| Missing evidence is not passed | Satisfied. Six hardware or installed-state constraints are returned as `unavailable`, nonblocking, with the missing evidence stated. |
| Failed blocking constraint cannot retain ranked objective | Satisfied. The deliberate short tie-rod result fails screening and exposes no screened objective. |
| Local sensitivity reuses complete evaluation path | Satisfied. Every perturbation is role-resolved, regenerated, swept through the analyzer, and constraint-screened. |
| Sensitivity is deterministic and bounded | Satisfied. The frozen rack-X case uses a central bounded step and repeated calls return identical records. |
| Candidate differences remain visible | Satisfied. Reports show objective deltas, normalized design distance, hardpoints, tie-rod length, constraint margins, unavailable gates, and ranking explanations. |
| Candidate comparison authority is limited | Satisfied. The method is described as objective-ranked diversity filtering, not Pareto completeness or global optimality. |
| Search integration limitation is visible | Satisfied. Supplemental development constraints screen the retained archive; reviewed hardware constraints must later enter every search-candidate disposition before hardware-feasible optimization claims. |
| Literature grounding | Satisfied for the current method boundary through the existing steering references, Fornberg finite differences, and Saltelli’s local-versus-global sensitivity distinction. |

## Frozen numerical evidence

The reference WUFR-27 candidate passes the three active development constraints and reports six unavailable future constraints. The historical target objective remains `0.6259259771798616`.

The frozen local sensitivity is:

```text
variable = rack_longitudinal_offset
step = 0.0003 m
scheme = central
objective derivative = -7.244456509246101 per m
normalized derivative = -2.17333695277383 over the full declared variable span
```

The comparison benchmark screens twenty candidates, retains four separated candidates, and excludes four near-duplicates before reaching the four-candidate limit.

## Open gates

The following remain unavailable and block hardware-feasible or production claims:

- selected rod-end articulation geometry and limits;
- tie-rod thread engagement and adjustment stack;
- steering-arm material and manufacturing envelope;
- rack housing, boot, inner-joint, chassis, and service clearance;
- wheel, tire, brake, upright, and chassis collision geometry;
- installed physical stops;
- suspension-state pose maps;
- tolerance distributions or worst-case manufacturing bounds;
- discrete rack, rod-end, tie-rod, and steering-arm hardware options;
- tire-informed target and steering-effort providers; and
- physical correlation.

## Proposed decision

Advance `P1-STR-004` to complete after team review and merge of PR #23. Permit `P1-STR-005` to begin only with reviewed tolerance inputs or discrete hardware options. Permit `P1-STR-006` to begin when suspension-pose, tire-target, load/effort, or physical-parameter providers become actual steering dependencies.
