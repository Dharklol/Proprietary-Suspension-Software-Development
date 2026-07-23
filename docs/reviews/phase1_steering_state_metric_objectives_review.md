# Phase 1 Steering Dynamic-Toe and Gain Objective Review

**Task:** `P1-STR-006G`  
**Change:** PR #27  
**Authorization:** `AUTH-STEER-0002` v0.8.0  
**Review state:** Ready for team review

## Review question

Does the change add explicit dynamic-toe and state-dependent steering-gain objectives using only quantities produced by the reviewed `MOD-STEER-0001` multi-state path, preserve all pose-state feasibility gates and source authority, reuse the existing deterministic search, and prevent the supplied OptimumK result export from being misrepresented as either an unresolved-steering suspension pose or a directly equivalent rack-to-wheel gain target?

## Scope reviewed

The objective chain is:

```text
candidate geometry
 -> provider-supplied zero-steer suspension poses
 -> complete MOD-STEER-0001 rack sweeps
 -> existing centered dynamic-toe and incremental-heading outputs
 -> explicit scalar dynamic-toe / centered rack-gain targets
 -> visible normalized objective terms
 -> existing deterministic search
```

No suspension solver, tire model, rack-load model, compliance model, or alternate steering closure is introduced.

## Architecture disposition

Accepted for review:

- Center dynamic toe is read from the existing side-local toe-out change fields.
- Center rack-to-wheel steering gain is a documented centered finite difference of the existing rack-to-wheel incremental heading response and uses `deg_per_mm`.
- Left and right target values remain explicit rather than being collapsed into a hidden symmetry assumption.
- Each state/metric objective retains normalization, weight, authority, source path, and sign adapters.
- Every supplied suspension pose remains a hard mechanism-feasibility state before any objective is admitted.
- `run_state_metric_inverse_design` reuses `bounded_coordinate_pattern_search_v0.1.0`; no second optimizer is introduced.
- Analyzer-generated metric targets are software-recovery fixtures only.
- PR #26 is merged at `be241172998684e1f40a6f2af2d9801a2c1911c8` and supplies the canonical source-neutral external-pose exchange adapter; PR #27 consumes the same `SuspensionPoseSet` contract and does not bypass that adapter boundary.

## OptimumK heave evidence disposition

The supplied `WUFR-26 8.21 Heaves 1inch.xlsx` contains useful front toe, steer angle, steering ratio, `Steering Toe Angle Gain`, wheel-center coordinates, upper/lower upright points, tie-rod upright/chassis points, and other steering-axis geometry across the heave sweep.

Selected scalar channels are frozen in `benchmarks/steering/WUFR26_OPTIMUMK_HEAVE_1IN_EVIDENCE_V0.toml` with the source hash and explicit evidence-only authority.

Two distinctions are frozen after direct workbook inspection:

1. The export is **not** directly accepted as a `SuspensionPoseSet`. Its reported upright/wheel state already reflects steering action from the steering linkage. The canonical pose contract requires an upright reference pose with the tie-rod steering DOF unresolved. Direct ingestion would risk double-counting the same steering rotation when `MOD-STEER-0001` restores tie-rod closure.
2. OptimumK labels `Steering Toe Angle Gain` with unit `-`. That channel is therefore **not** treated as equivalent to PR #27's rack-to-wheel centered gain in `deg_per_mm`. It may later inform a separately reviewed steering-input/transmission target provider, but no silent conversion is permitted here.

A future OptimumK-specific converter can reconstruct the instantaneous steering axis from the exported upright geometry, remove the tie-rod-induced steering component, and emit canonical rigid transforms through the merged PR #26 adapter. That source conversion remains outside PR #27.

## BENCH-STEER-0019 freeze

`BENCH-STEER-0019` uses the synthetic PR #24 pose set and analyzer-generated scalar targets from a known source geometry with:

```text
rack_longitudinal_offset = +0.01875 m
```

The target terms are:

| State | Metric | Unit | Scale | Weight |
|---|---|---|---:|---:|
| symmetric_bump_5mm | center dynamic toe-out change | deg | 0.1 | 1.0 |
| opposed_travel_5mm | center dynamic toe-out change | deg | 0.1 | 0.8 |
| nominal | centered rack-to-wheel gain | deg/mm | 0.02 | 0.6 |
| symmetric_bump_5mm | centered rack-to-wheel gain | deg/mm | 0.02 | 0.6 |

Frozen analyzer-generated source quantities are:

- nominal rack gain: left `-0.9428033664908934 deg/mm`, right `-0.942803366490894 deg/mm`;
- symmetric +5 mm rack gain: left `-0.945434423994838 deg/mm`, right `-0.9454344239948376 deg/mm`;
- symmetric +5 mm dynamic toe: left `+0.4575584618658124 deg`, right `+0.45755846186580607 deg`;
- opposed +5/-5 mm dynamic toe: left `+0.4575584618658124 deg`, right `-0.38507219565203976 deg`.

Frozen deterministic recovery result:

- source total objective: `0.0`;
- WUFR-27 reference total objective: `2.0743640931890073`;
- recovered rack longitudinal offset: `0.01874999999999999 m`;
- absolute recovery error: `1.0408340855860843e-17 m`;
- recovered total objective: `0.0`;
- all four recovered objective contributions: `0.0`;
- 34 unique candidates evaluated;
- 32 feasible;
- 2 infeasible;
- 8 retained for comparison.

The 18.75 mm source lies on the deterministic refinement grid. Exact recovery verifies state-metric target/search composition; it is not a global-optimality claim.

The result is frozen in `benchmarks/steering/steering_state_metric_objective_result_v0.1.0.toml`, regenerated by `scripts/run_steering_state_metric_benchmarks.py`, and directly checked by `tests/test_steering_state_metric_freeze.py`.

## Verification gates

The implementation establishes:

1. analyzer-generated dynamic-toe/gain targets return zero objective at their source geometry;
2. the reference geometry produces a nonzero result against that source;
3. centered rack-to-wheel gain changes with suspension state;
4. dynamic toe uses the existing side-local convention;
5. every pose remains a hard analyzer-feasibility state before a scalar objective is scored;
6. deterministic state-metric search recovers the frozen source geometry through the same search core used by the nominal and operating-state optimizers; and
7. the frozen result record checks target units/scales/weights, source metric pairs, recovery error, search counts, and method identity.

## Authority boundary

This review does **not** promote:

- the OptimumK export to an unresolved-steering canonical pose source;
- the OptimumK dimensionless steering-toe-gain channel to the `deg_per_mm` rack-gain objective;
- historical WUFR-26 toe values to tire-optimal targets;
- any state weight or normalization to vehicle truth;
- centered finite-difference rack gain to the only valid gain definition;
- synthetic target recovery to global optimality;
- development bounds to packaging/manufacturing authority; or
- rigid results to physical/as-built steering behavior.

`P1-STR-006D` rack-load/effort and `P1-STR-006E` physical installed-correlation remain separate gates.

## Proposed decision

Advance `P1-STR-006G` to complete after team review and merge of PR #27. Keep the supplied OptimumK workbook as evidence and later source-conversion input until an OptimumK-specific de-steering converter is reviewed against the PR #26 canonical external-pose adapter. The next meaningful fidelity increase after this PR is reviewed real suspension-state input and/or a reviewed vehicle/tire target generator; do not activate physical `P1-STR-006E` from this review.
