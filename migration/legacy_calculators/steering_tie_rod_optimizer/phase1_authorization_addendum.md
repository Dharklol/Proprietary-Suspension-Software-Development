# Steering Inverse-Design Phase 1 Authorization Addendum

**Migration ID:** `MIG-STR-0001`  
**Original transition specification:** `transition_specification.md`  
**Authorization:** `AUTH-STEER-0002`

The original transition specification correctly defines the desired integrated inverse-design workflow, but its early model labeling predates implementation of the rigid analyzer. Phase 1 now separates the workflow into two cohesive models:

- `MOD-STEER-0001`: authoritative rigid steering evaluator and derived-metric layer;
- `MOD-STEER-0002`: role resolver, parametric geometry generator, constrained search, candidate comparison, and reporting layer.

The migration objective is unchanged. The optimizer must still accept fixed geometry, design variables, discrete options, hard constraints, acceptable bands, target curves, and report-only evidence; solve the linkage directly; return complete geometry and steering maps; expose margins and sensitivity; and keep CAD or multibody studies as comparison evidence.

This addendum supersedes only the original implication that one model record would contain both evaluation and optimization. It does not supersede the transition specification's terminology, requirement roles, objective hierarchy, constraints, outputs, or first-release fidelity boundary.

WUFR-26/27 physical-correlation tasks remain open. They block installed and as-built claims but do not block generic nominal geometry generation or target-recovery development. Higher-fidelity tire, effort, suspension-state, compliance, robustness, transient, learned-optimizer, and production-selection layers remain outside `AUTH-STEER-0002`.
