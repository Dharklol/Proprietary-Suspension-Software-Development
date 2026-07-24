# Steering Dynamic-Toe and State-Dependent Gain Objectives v0.1.0

## Purpose

This implementation extends the reviewed operating-state target architecture with two explicit scalar objective families that are already observable from the `MOD-STEER-0001` multi-state evaluation:

1. centered suspension-induced dynamic toe-out change at a named suspension pose; and
2. centered rack-to-wheel steering gain at a named suspension pose.

The change does not add suspension kinematics, tire physics, rack-load physics, compliance, or a second steering mechanism model. Candidate geometry is still generated once, each provider-supplied suspension pose is applied, and the complete rack sweep is solved by `MOD-STEER-0001` before the new objective layer reads the resulting quantities.

## Objective definitions

### Center dynamic toe

For state `k`, the existing multi-state evaluator reports the centered wheel-heading change relative to the declared nominal pose. The right-side global heading change is sign-adapted into the side-local toe-out convention already frozen by the pose-provider implementation.

The objective input pair is therefore

```text
D_k = [
  center_left_side_local_toe_out_change_deg,
  center_right_side_local_toe_out_change_deg
]
```

No toe value is recomputed in the objective layer.

### Center rack-to-wheel gain

For each side at state `k`, the state-dependent incremental projected road-wheel heading curve is already evaluated across the shared rack-displacement samples. The first gain objective uses the centered secant surrounding the exact rack-center sample:

```text
G_side,k = (delta_side,k[i+1] - delta_side,k[i-1])
           / ((rack[i+1] - rack[i-1]) * 1000)
```

where rack displacement is stored in metres and the reported gain unit is `deg_per_mm`.

This is intentionally a transparent local finite-difference metric, not a new steering equation or a claim about the complete nonlinear gain curve. A later provider can request additional gain samples or bands without replacing the analyzer.

### Pair objective and aggregation

For either scalar metric, explicit left and right targets are compared with the analyzer result:

```text
J_qk = sqrt(0.5 * (e_left^2 + e_right^2))
```

Each term retains its raw value, unit, normalization scale `S_qk`, weight `W_qk`, state, metric identity, authority, and residual description. The convenience search scalar is

```text
J_total = sum_qk W_qk * (J_qk / S_qk)
```

This scalar remains a project optimization method rather than a physical law or Pareto-completeness claim.

## Provider contract

`StateMetricTargetSet` carries explicit state/metric targets. Supported metric IDs in v0.1.0 are:

- `center_dynamic_toe_out_change`
- `center_rack_to_wheel_gain`

The explicit TOML loader requires the pose-set identity and shared rack-sampling target identity to match. A state/metric pair cannot be duplicated. Sign adapters are available independently for left and right provider conventions.

Analyzer-generated targets are retained only for deterministic software-recovery tests. They do not become vehicle-dynamics design truth.

## Search composition

`run_state_metric_inverse_design` reuses `bounded_coordinate_pattern_search_v0.1.0`, including variable normalization, seeded starts, polling, step contraction, infeasible handling, termination, and retained-candidate behavior. Only the candidate-evaluation adapter changes.

Every supplied pose remains a hard mechanism-feasibility state. A failed analyzer sweep produces no scalar objective.

## Supplied OptimumK heave export

The user-supplied `WUFR-26 8.21 Heaves 1inch.xlsx` was reviewed as an external kinematics result export. Selected front-axle channels are frozen in `benchmarks/steering/WUFR26_OPTIMUMK_HEAVE_1IN_EVIDENCE_V0.toml`, including:

- heave position;
- left/right toe angle;
- left/right steer angle;
- front steering ratio; and
- left/right `Steering Toe Angle Gain`.

The exported sweep spans `-25.4 mm` to `+25.4 mm` heave. Relative to the exported nominal row, the recorded toe changes from approximately `-0.15417 deg` at `-25.4 mm` to `+0.15745 deg` at `+25.4 mm`.

The workbook explicitly labels `Steering Toe Angle Gain` with unit `-`. It is therefore preserved as a **dimensionless steering-input-related gain channel**. It is not the same quantity as this PR's `center_rack_to_wheel_gain`, whose input is rack displacement and whose unit is `deg_per_mm`. The OptimumK channel is useful evidence that the exported steering gain varies with heave, but it is not used to validate or target the rack-to-wheel metric without a separately reviewed transmission/convention conversion.

The spreadsheet is also **not** admitted directly as a canonical `SuspensionPoseSet`: the OptimumK result geometry and toe/steer outputs already include tie-rod-constrained steering response. The current pose contract requires the supplied upright reference pose to exclude tie-rod-induced steering rotation so that `MOD-STEER-0001` does not solve that degree of freedom twice.

PR #26 now supplies the source-neutral canonical external-pose exchange adapter. A future OptimumK-specific converter can use the exported upper/lower upright points and related geometry to reconstruct an instantaneous steering axis, remove the exported steering rotation, and then emit the canonical unresolved-steering rigid transforms accepted by that adapter. Until that source conversion is reviewed, the spreadsheet-derived table remains historical external kinematics evidence and target-provider input only.

## Verification

`tests/test_steering_state_metric_objectives.py` checks that:

- an analyzer-generated source candidate has zero combined state-metric objective;
- another geometry produces a nonzero objective;
- centered rack-to-wheel gain is explicitly state-dependent; and
- dynamic toe consumes the frozen side-local centered toe-change fields rather than introducing another convention.

The next verification step is a frozen deterministic recovery benchmark that exercises `run_state_metric_inverse_design` through the same search core used by PR #22 and PR #25.

## Authority boundary

This implementation does not establish tire-optimal toe, desired steering gain, real pose importance weights, packaging feasibility, hardware feasibility, robustness, steering effort, as-built behavior, or WUFR-28 production geometry authority. The OptimumK dimensionless gain channel is not silently converted into the rack-to-wheel gain objective. Those promotions require separately reviewed providers, conventions, and evidence.
