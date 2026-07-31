# Provider-neutral steady-state lateral tire implementation v0.1.0

## Scope

`MOD-TIRE-0001` implements the generic and synthetic-verification scope authorized by
`AUTH-TIRE-0001`. The implementation package is:

`src/pssd_tire/steady_state_lateral.py`

It evaluates immutable source-adapted signed steady-state pure-lateral response curves

\[
F_y=f(\alpha,F_z,\gamma,P)
\]

in the frozen canonical tire contact frame. It does not fit tire data, reconstruct missing
curve shape, infer source signs, apply symmetry, or activate the pending real R25B source.

## Forward response

For one exact operating-state curve, the kernel preserves stored force values at source
knots and uses ordinary piecewise-linear interpolation only between adjacent supplied
samples. Outside the supplied slip domain, the complete query fails without clipping or
extrapolation.

At an interior knot, the result retains the left and right segment slopes separately and
sets `derivative_unique=false` when they differ. It never silently averages unequal slopes.

For a query inside a normal-load, inclination, and pressure cell, the kernel constructs the
Cartesian product of the active axis brackets. Every nonzero-weight corner must exist exactly
once and must share compatible source-tire, intended-tire, source-convention, adapter,
fidelity, and response-role identities. Every participating curve is evaluated independently
at the requested slip angle and the final force and one-sided slopes are combined using the
frozen multilinear weights.

A missing or incompatible corner fails the entire query. Nearest-neighbor substitution and
partial-source publication are prohibited.

## Signed force inversion

The inverse evaluator forms the exact composite piecewise-linear response over the union of
all participating curve knots inside their common supported slip interval. For a requested
signed lateral force, it returns every distinct signed slip-angle root.

Shared-knot roots are deduplicated within the frozen tolerance while retaining every
contributing source segment and branch identity. A horizontal segment coincident with the
requested force is returned as `inverse_branch_ambiguous`; no arbitrary point is selected.

The only implemented selectors are `named_pre_peak_branch` and
`named_post_peak_branch`. They operate only on explicit source-declared segment metadata and
must identify exactly one root. Slip magnitude is never used to invent a branch.

## Source and fidelity boundary

The real source-specific Hoosier provider remains disabled:

- source tire: `HOOSIER_43105_18X7.5-10_R25B`;
- intended tire: `HOOSIER_43104_18X7.5-10_R20`;
- `source_specific_r25b_runtime_activation_authorized=false`.

Calling the explicit activation gate returns `source_specific_activation_blocked`. The
existing summary and synthetic processed-Trojan tests are not expanded into real full curves.

The implementation contains no `Mz`, `Fx`, combined-slip, transient, thermal, wear, vertical
compliance, track correction, vehicle-equilibrium, steering-ranking, installed/as-built,
setup, release, or production authority.

## Deterministic verification

The benchmark runner is:

`scripts/run_steady_state_lateral_tire_benchmarks.py`

The frozen records are:

- `benchmarks/tires/steady_state_lateral_tire_result_v0.1.0.json`;
- `benchmarks/tires/steady_state_lateral_tire_result_v0.1.0.toml`.

Frozen record properties:

- JSON byte count: `2338`;
- JSON SHA-256: `2bb9652348eb4fbcad5eca389580de2c7c222ed6bf3005cc7f707311dd85a234`;
- TOML byte count: `1874`;
- TOML SHA-256: `bd9a30d4a0cb04515064e66fd41f827d06f4d37f3eaa292bb26130428d97fb72`.

`BENCH-TIRE-0001` verifies exact knots, affine segment evaluation, unequal one-sided knot
slopes, malformed-source rejection, and no slip extrapolation.

`BENCH-TIRE-0002` uses a complete synthetic `2 x 2 x 2` state cell whose analytic response
is affine in slip, normal load, inclination, and pressure. The eight participating curves use
different valid slip grids. The interior query returns the analytic force, slope, and eight
weights of `0.125` exactly within floating-point tolerance.

`BENCH-TIRE-0003` verifies two signed roots for one demand, explicit pre-peak and post-peak
selection, shared-knot deduplication, force-domain failure, horizontal-interval ambiguity,
and the blocked real-R25B activation gate.

All fixtures are labeled `synthetic_software_verification` and carry no physical Hoosier,
TTC, R25B, R20, WUFR, or track authority.
