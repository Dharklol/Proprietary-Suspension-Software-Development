# Provider-neutral steady-state lateral tire function specification

## Identity

- Authorization: `AUTH-TIRE-0001`
- Model: `MOD-TIRE-0001`
- Equations: `EQ-TIRE-0001` through `EQ-TIRE-0003`
- Benchmarks: `BENCH-TIRE-0001` through `BENCH-TIRE-0003`
- Planned package: `src/pssd_tire/steady_state_lateral.py`

## Purpose

Provide one shared, immutable, source-bounded interface for steady-state pure-lateral tire response:

\[
F_y=f(\alpha,F_z,\gamma,P).
\]

The first implementation is a tabulated response kernel. It is designed so a later reviewed TTC table, fitted `.tir` evaluator, or other source-specific provider can implement the same result contract without changing vehicle or steering consumers.

It does not fit data or activate a real Hoosier provider by itself.

## Canonical records

### `SteadyStateLateralOperatingState`

Required fields:

```text
slip_angle_rad: float
normal_load_N: float
inclination_rad: float
pressure_Pa: float
state_id: str
source_id: str
source_convention_id: str
```

Validation:

- all numeric fields finite;
- `normal_load_N > 0`;
- `pressure_Pa > 0`;
- pure-lateral steady-state role explicit;
- source pressure basis declared by the adapter.

### `SteadyStateLateralCurve`

Required fields:

```text
curve_id
operating_state_without_alpha
slip_angle_rad[]
lateral_force_N[]
source_tire_id
intended_tire_id
source_path
source_hash
source_convention_id
adapter_id
fidelity_label
domain_and_censor_metadata
source_preprocessing
source_branch_role
```

Validation:

- at least two samples;
- arrays have equal length;
- all samples finite;
- slip samples strictly increasing;
- duplicate curve IDs and duplicate operating states rejected;
- no monotonic-force requirement;
- no hidden source symmetry.

### `SteadyStateLateralResponse`

Required fields:

```text
ok
status
failure_code
message
operating_state
lateral_force_N
left_segment_slope_N_per_rad
right_segment_slope_N_per_rad
derivative_unique
participating_curve_ids
slip_segment_ids
state_interpolation_weights
source_and_adapter_provenance
domain_and_censor_metadata
fidelity_label
```

A failed result contains no numeric force or derivative and no partial successful source subset.

### `SteadyStateLateralInverseCandidate`

Required fields:

```text
slip_angle_rad
segment_id
branch_id
interpolation_fraction
source_curve_ids
source_and_adapter_provenance
```

### `SteadyStateLateralInverseResult`

Required fields:

```text
ok
status
failure_code
message
requested_lateral_force_N
candidates[]
branch_selection_applied
selected_candidate
out_of_domain
```

Multiple candidates are a successful multi-root result, not a failure, unless the caller demands one root without supplying a valid policy.

## Canonical tire contact frame

`CANONICAL_TIRE_CONTACT_ISO_LEFT_UP`:

- origin: current contact-center reference on the road plane;
- `+x_t`: forward in the wheel plane projected onto the road;
- `+z_t`: road normal upward;
- `+y_t = +z_t × +x_t`: leftward;
- force role: road on tire.

Positive slip angle is measured about `+z_t` from contact-patch velocity direction to `+x_t`:

\[
\alpha=-\operatorname{atan2}(v_{y,t},v_{x,t})
\]

for positive forward transport.

`MOD-TIRE-0001` receives already-adapted canonical values. It does not infer source signs.

## Forward evaluation

### Exact curve lookup

For an exact operating state, select one and only one identity-compatible curve.

For query \(\alpha\):

1. If \(\alpha\) matches a source knot within the frozen absolute tolerance, return the exact stored value.
2. Otherwise find the unique adjacent pair \((\alpha_j,F_{y,j})\), \((\alpha_{j+1},F_{y,j+1})\) with \(\alpha_j<\alpha<\alpha_{j+1}\).
3. Compute

\[
t=\frac{\alpha-\alpha_j}{\alpha_{j+1}-\alpha_j}
\]

and

\[
F_y=F_{y,j}+t(F_{y,j+1}-F_{y,j}).
\]

4. Preserve the source segment identity and interpolation fraction.

Outside the curve domain, return `slip_out_of_domain`.

### Operating-state interpolation

Axes:

- normal load;
- inclination;
- pressure.

For each axis, an exact grid match has one weight of one. An interior coordinate has two ordinary linear weights.

The Cartesian product of active axis points defines the participating curves. Every nonzero-weight curve must:

- exist exactly once;
- share source tire and intended tire identities;
- share a compatible source-convention adapter family;
- share response role and compatible fidelity;
- support the requested slip angle.

Evaluate each curve at the query slip using the exact-curve algorithm. Then

\[
F_y=\sum_k w_kF_{y,k},
\qquad
w_k\ge0,
\qquad
\sum_kw_k=1.
\]

No common slip grid is required.

The result records every participating curve and weight. Any missing or incompatible corner fails the entire query.

## Local slope

For an open segment:

\[
\frac{\partial F_y}{\partial\alpha}
=
\frac{F_{y,j+1}-F_{y,j}}
{\alpha_{j+1}-\alpha_j}.
\]

For state interpolation:

\[
\frac{\partial F_y}{\partial\alpha}
=
\sum_kw_k
\frac{\partial F_{y,k}}{\partial\alpha}.
\]

At an interior knot:

- return the left slope;
- return the right slope;
- set `derivative_unique=false` when they differ beyond tolerance;
- return a single value only for an explicit left- or right-sided query, or when the two slopes agree within tolerance.

The kernel never silently averages unequal knot slopes.

## Signed force inversion

For demand \(F_{y,d}\), inspect every adjacent response segment.

A non-horizontal segment is a candidate when the closed signed force interval contains the demand. Solve

\[
t_j=
\frac{F_{y,d}-F_{y,j}}
{F_{y,j+1}-F_{y,j}}
\]

with \(0\le t_j\le1\), and return

\[
\alpha_j^*=\alpha_j+t_j(\alpha_{j+1}-\alpha_j).
\]

Rules:

- retain every distinct root;
- deduplicate a shared-knot root within tolerance while preserving all contributing segment identities;
- report a horizontal segment coincident with the demand as an interval ambiguity, not one arbitrary point;
- do not select a physical branch unless the caller supplies an explicit recognized policy;
- no root means `force_demand_out_of_domain`.

Planned generic selectors may include `named_pre_peak_branch` or `named_post_peak_branch`, but only when branch metadata from the provider explicitly defines them. A selector cannot infer branches from slip magnitude alone.

## Source-specific activation boundary

The generic package may load synthetic fixtures immediately after authorization.

A real R25B provider must remain disabled until all of the following are present:

1. reviewed source-side binary processed-Trojan export;
2. frozen file hash and curve exchange;
3. source-to-canonical unit/frame/sign/pressure/inclination adapter;
4. exact supported state and slip domains;
5. explicit status for positive/negative slip and pre/post-peak coverage;
6. representative source cross-checks;
7. a source-specific authorization update or follow-on authorization.

The current 36-point summary cannot be expanded into full curves.

## Structured failure codes

```text
source_curve_unavailable
source_curve_invalid
source_identity_mismatch
source_adapter_mismatch
nonfinite_input
invalid_normal_load
invalid_pressure
slip_out_of_domain
operating_state_out_of_domain
interpolation_cell_incomplete
interpolation_identity_mismatch
derivative_nonunique
force_demand_out_of_domain
inverse_branch_ambiguous
source_specific_activation_blocked
```

## Benchmark design

### `BENCH-TIRE-0001`

Use a synthetic signed nonlinear curve with unequal adjacent slopes and at least one interior peak. Verify:

- exact knots;
- interior affine values;
- local slopes;
- knot derivative behavior;
- malformed-source rejection;
- no slip extrapolation.

### `BENCH-TIRE-0002`

Use a complete synthetic 2×2×2 state cell with an analytic response affine in all state axes and slip. Permit different slip grids at each corner while retaining a common supported query interval. Verify:

- exact state corners;
- interior analytic response;
- slope interpolation;
- weights;
- missing-corner, identity, fidelity, and domain failures.

### `BENCH-TIRE-0003`

Use a synthetic signed peak/post-peak curve. Verify:

- multiple roots for one demand;
- shared-knot deduplication;
- explicit named branch selection;
- force-domain failure;
- no hidden symmetry;
- blocked real R25B activation.

## Result freeze

The implementation PR must freeze:

```text
benchmarks/tires/steady_state_lateral_tire_result_v0.1.0.json
benchmarks/tires/steady_state_lateral_tire_result_v0.1.0.toml
```

The record must include:

- source fixture hashes;
- canonical convention identity;
- benchmark inputs and exact expected values;
- maximum force, slope, weight, and root errors;
- failure-code coverage;
- explicit real-R25B-disabled state;
- all fidelity flags.

## Prohibited implementation shortcuts

- reconstructing a curve from summary stiffness/peak data;
- applying odd symmetry to one-sided source data;
- spline or fitted response generation;
- clipping to source limits;
- nearest-neighbor state substitution;
- source identity mixing;
- automatic `2/3` force scaling;
- Mz, Fx, combined-slip, transient, thermal, wear, vertical-compliance, vehicle-state, or steering-ranking logic.
