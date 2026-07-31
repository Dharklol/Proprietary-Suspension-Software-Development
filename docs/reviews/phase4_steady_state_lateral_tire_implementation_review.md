# Phase 4 steady-state lateral tire implementation review

## Decision

`MOD-TIRE-0001` is implemented consistently with merged `AUTH-TIRE-0001` for the
provider-neutral and synthetic-verification scope. It is ready for review after repository
workflows and deterministic frozen-record regeneration pass.

## Reviewed implementation

The implementation package is:

`src/pssd_tire/steady_state_lateral.py`

The synthetic benchmark support and deterministic runner are:

- `src/pssd_tire/steady_state_lateral_benchmarks.py`;
- `scripts/run_steady_state_lateral_tire_benchmarks.py`.

The implementation preserves the authorized source-table mechanics. It does not call a fit,
reconstruct a curve from stiffness or peak summaries, infer odd symmetry, smooth a peak,
clip a request, or substitute a nearby operating state.

## Frozen evidence

The frozen records are:

- `benchmarks/tires/steady_state_lateral_tire_result_v0.1.0.json`;
- `benchmarks/tires/steady_state_lateral_tire_result_v0.1.0.toml`.

Frozen properties:

- JSON bytes: `2338`;
- JSON SHA-256: `2bb9652348eb4fbcad5eca389580de2c7c222ed6bf3005cc7f707311dd85a234`;
- TOML bytes: `1874`;
- TOML SHA-256: `bd9a30d4a0cb04515064e66fd41f827d06f4d37f3eaa292bb26130428d97fb72`;
- `BENCH-TIRE-0001`: pass;
- `BENCH-TIRE-0002`: pass;
- `BENCH-TIRE-0003`: pass.

## Mechanics review

The forward evaluator:

- preserves exact source knots;
- interpolates only between adjacent supplied slip samples;
- returns left and right local slopes at nonsmooth knots;
- requires every nonzero-weight state-cell corner exactly once;
- rejects source, intended-tire, adapter, convention, fidelity, and role mixing;
- records participating curves, segments, state weights, provenance, and censor metadata; and
- fails the whole query when any participating curve does not support the requested slip.

The inverse evaluator:

- uses the exact composite piecewise-linear response;
- returns all distinct signed roots;
- deduplicates shared-knot roots while preserving contributing segment identities;
- reports coincident horizontal intervals as ambiguity;
- selects a root only through explicit source-declared named branch metadata; and
- returns a structured out-of-domain failure when no root exists.

## Failure coverage

The implementation and frozen record cover:

- invalid or duplicate source curves;
- nonfinite input;
- invalid normal load or pressure;
- slip and operating-state extrapolation;
- incomplete interpolation cells;
- source and adapter identity mismatch;
- nonunique derivative reporting;
- unavailable force demand;
- ambiguous horizontal inverse intervals; and
- blocked source-specific R25B activation.

No failed query publishes a partial successful cell or an invented inverse branch.

## Boundary review

The accepted result remains synthetic software evidence. The real R25B provider is not active
because a reviewed binary processed-Trojan full-curve exchange and source-to-canonical adapter
have not been frozen. The R25B summary is not sufficient to reconstruct a response curve.

The implementation does not authorize physical tire prediction, R20 substitution, track
scaling, steering optimization ranking, setup recommendations, installed/as-built correlation,
design release, or production use. `Mz`, `Fx`, combined slip, transient relaxation, thermal and
wear state, and vertical compliance remain separate future authorizations.

## Recommendation

Approve and merge after all repository workflows pass and the two frozen records regenerate
byte-identically. The next separately authorized tire step should be the reviewed source-side
full-curve export and canonical adapter for a real provider. Downstream vehicle or steering
consumers should continue using only the explicit fidelity carried by each response.
