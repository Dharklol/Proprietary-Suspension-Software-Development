# Phase 1 Steering Dynamic-Toe and Gain Objective Review

**Change:** PR #27  
**Authorization:** `AUTH-STEER-0002`  
**Review state:** Ready for team review

## Review question

Does the change add explicit dynamic-toe and state-dependent steering-gain objectives using only quantities produced by the reviewed `MOD-STEER-0001` multi-state path, preserve all pose-state feasibility gates and source authority, reuse the existing deterministic search, and prevent the supplied OptimumK result export from being misrepresented as an unresolved-steering suspension pose?

## Scope reviewed

The objective chain is:

```text
candidate geometry
 -> provider-supplied zero-steer suspension poses
 -> complete MOD-STEER-0001 rack sweeps
 -> existing centered dynamic-toe and incremental-heading outputs
 -> explicit scalar dynamic-toe / centered-gain targets
 -> visible normalized objective terms
 -> existing deterministic search
```

No suspension solver, tire model, rack-load model, compliance model, or alternate steering closure is introduced.

## Architecture disposition

Accepted for review:

- Center dynamic toe is read from the existing side-local toe-out change fields.
- Center steering gain is a documented centered finite difference of the existing rack-to-wheel incremental heading response and uses `deg_per_mm`.
- Left and right target values remain explicit rather than being collapsed into a hidden symmetry assumption.
- Each state/metric objective retains normalization, weight, authority, source path, and sign adapters.
- Every supplied suspension pose remains a hard mechanism-feasibility state before any objective is admitted.
- `run_state_metric_inverse_design` reuses `bounded_coordinate_pattern_search_v0.1.0`; no second optimizer is introduced.
- Analyzer-generated metric targets are software-recovery fixtures only.

## OptimumK heave evidence disposition

The supplied `WUFR-26 8.21 Heaves 1inch.xlsx` contains sufficient channels to support this objective-family work and a later external-pose adapter. The export includes front toe, steer angle, steering ratio, `Steering Toe Angle Gain`, wheel-center coordinates, upper/lower upright points, tie-rod upright/chassis points, and other steering-axis geometry across the heave sweep.

Selected scalar channels are frozen in `benchmarks/steering/WUFR26_OPTIMUMK_HEAVE_1IN_EVIDENCE_V0.toml` with the source hash and explicit evidence-only authority.

The export is **not** directly accepted as a `SuspensionPoseSet`. Its reported upright/wheel state already reflects steering action from the steering linkage. The reviewed canonical pose contract instead requires an upright reference pose with the tie-rod steering DOF unresolved. Direct ingestion would therefore risk double-counting the same steering rotation when `MOD-STEER-0001` restores tie-rod closure.

The next external-pose adapter should reconstruct the instantaneous steering axis from the exported upright geometry and remove the tie-rod-induced steering component before producing canonical rigid transforms. That is a source-adapter problem; it does not require changing the steering kernel.

## Verification gates

The first tests establish:

1. analyzer-generated dynamic-toe/gain targets return zero objective at their source geometry;
2. the reference geometry produces a nonzero result against that source;
3. centered steering gain changes with suspension state; and
4. dynamic toe uses the existing side-local convention.

A CI-backed frozen numerical benchmark can be added after the first review if the team wants exact search counts and recovery values promoted in the same manner as `BENCH-STEER-0016/0017`.

## Authority boundary

This review does **not** promote:

- the OptimumK export to an unresolved-steering canonical pose source;
- historical WUFR-26 toe/gain values to tire-optimal targets;
- any state weight or normalization to vehicle truth;
- centered finite-difference gain to the only valid gain definition;
- synthetic target recovery to global optimality;
- development bounds to packaging/manufacturing authority; or
- rigid results to physical/as-built steering behavior.

`P1-STR-006D` rack-load/effort and `P1-STR-006E` physical installed-correlation remain separate gates.

## Proposed decision

Accept the explicit state-metric objective family as the next nonphysical extension of `P1-STR-006C`. Preserve the existing `P1-STR-006D` identifier for rack-load/effort rather than silently repurposing it. Record this PR under a new steering subtask and keep the OptimumK spreadsheet as evidence/target input until a reviewed de-steering pose adapter is implemented.
