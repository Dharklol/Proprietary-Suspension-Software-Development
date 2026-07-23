# Nominal-Height Steering Inverse-Design Prototype Authorization

**Authorization ID:** `AUTH-STEER-0002`  
**Optimizer model:** `MOD-STEER-0002`  
**Authoritative evaluator dependency:** `MOD-STEER-0001`  
**Status:** Proposed for focused review

## Decision

This packet authorizes development of a bounded nominal-height steering inverse-design prototype after review and merge. It does not authorize production geometry selection, automatic CAD modification, suspension-state optimization, tire-informed target generation, steering effort, compliance, robustness, or as-built claims.

The optimizer must compose the existing rigid steering analyzer rather than replacing it. `MOD-STEER-0001` remains the only authority for rigid rack translation, spatial steering-axis rotation, tie-rod closure, branch selection, singularity diagnostics, wheel-plane projection, ratios, Ackermann references, and turning-path calculations. `MOD-STEER-0002` may generate candidates, resolve parameter roles, call the evaluator, assess constraints, compare targets, archive alternatives, and rank candidates.

## Why this is the correct next layer

The existing analyzer has completed the necessary mechanism and verification foundation. Continuing directly into a parametric geometry generator and constrained search preserves that work and exposes the next real engineering capability: generating complete steering geometry from fixed vehicle geometry, selected design freedoms, constraints, and target curves.

The implementation is intentionally nominal-height and rigid. Suspension motion, tire targets, loads, manufacturing variation, and physical identification are future provider layers using the same geometry and result contracts. This prevents the first optimizer from becoming a disposable special case while avoiding premature dependence on unavailable 2027 data.

## Authorized first study boundary

The first study keeps wheel centers, steering axes, upright poses, suspension hardpoints, wheelbase, steering-axis track, static alignment, and rack-axis direction fixed. Exact left/right reflection is enforced. The design vector may vary rack longitudinal position, rack vertical position, rack inner-joint half-spacing, and upright-local outer tie-rod pickup coordinates. The pickup depth coordinate is tightly bounded and may be switched to fixed by the requirement set. Tie-rod joint-center length is derived at the reference state.

No coordinate is permanently coded as fixed or variable. Each study assigns roles from the requirement set, allowing future studies to fix an existing steering arm, vary only rack placement, enumerate hardware, or enable a redesigned upright without replacing the generator.

## Initial target and alternatives

The corrected WUFR-26/27 nominal wheel-response map is the first regression target because it grounds development in known vehicle geometry and the completed audit. It is not treated as the permanent design objective. The target-provider contract also permits exact geometric Ackermann, user-entered wheel maps, steering-ratio or gain bands, turning-capability requirements, and later tire-informed operating targets.

## Candidate output

The prototype must return several feasible or nondominated candidates where alternatives exist. A convenience ranking is permitted, but the report must preserve individual objective contributions, hard-constraint margins, sensitivities, solver status, and the reason each candidate differs. Infeasible candidates remain separate from the ranked set and include named failure diagnostics.

## Literature and evidence boundary

The optimizer inherits the exact steering equations and validity limits already cited in the rigid evaluator packet. Guiggiani Chapter 3 and Gillespie Chapter 8 support the steering geometry, Ackermann reference, linkage, ratio, and steering-error definitions. Romano’s steering-system thesis supports comparing configurations through steering-angle and ratio functions before progressing to suspension and full-vehicle validation. Huang et al. (2026) emphasizes that optimized kinematic targets do not guarantee physically feasible suspension geometry, supporting explicit packaging and feasibility constraints rather than reward-only optimization.

The first deterministic optimizer establishes the benchmark against which later global, learned, or reinforcement-learning methods must be compared. No learned method is authorized by this packet.

## Required code sequence

The first code PR implements only the role resolver and parametric geometry generator. A zero-offset candidate must reproduce the baseline `MOD-STEER-0001` geometry and results. The second code PR may implement deterministic constrained search and candidate reporting after target-recovery, infeasibility, repeatability, and method-documentation benchmarks are frozen.

## Promotion gates

Exploratory nominal geometry studies require completion of the first optimizer benchmarks. Hardware-feasible ranking additionally requires reviewed packaging, articulation, thread engagement, rack, stop, and manufacturing constraints. Suspension-coupled studies require a reviewed pose provider. Tire-informed and effort-aware studies require reviewed tire, operating-point, and load models. Robustness claims require a reviewed uncertainty model. Production WUFR-28 selection and as-built claims require later focused authorization and physical correlation.
