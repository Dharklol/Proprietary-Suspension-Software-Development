# Phase 2 wheel-reference implementation review

## Decision

`MOD-SUSP-0002` is implemented within the restrictions of `AUTH-SUSP-0002` and is ready for review once the final PR head reproduces the frozen benchmark and regression suite.

The implementation provides the source-bounded wheel reference and first physical suspension-state coordinate that `MOD-SUSP-0001` intentionally left unavailable. It does not expand suspension authority into front steering, contact/tire geometry, actuation, loads, compliance, whole-vehicle source placement, or installed/as-built claims.

## Affected stable IDs

- `AUTH-SUSP-0002`
- `MOD-SUSP-0002`
- `EQ-SUSP-0005`
- `EQ-SUSP-0006`
- `EQ-SUSP-0007`
- `EQ-SUSP-0008`
- `BENCH-SUSP-0004`
- `BENCH-SUSP-0005`
- `BENCH-SUSP-0006`

## Implementation reviewed

Primary code:

- `src/pssd_suspension/wheel_reference.py`

Verification:

- `tests/test_wheel_reference_state_adapter.py`
- `scripts/run_wheel_reference_benchmarks.py`
- `.github/workflows/suspension-kinematics-validation.yml`
- `benchmarks/suspension/wheel_reference_result_v0.1.0.toml`

Source evidence:

- `benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml`
- `benchmarks/suspension/WUFR26_OPTIMUMK_HEAVE_FRONT_LEFT_WHEEL_REFERENCE_SOURCE_V0.toml`
- `benchmarks/suspension/WUFR26_OPTIMUMK_HEAVE_FRONT_RIGHT_WHEEL_REFERENCE_SOURCE_V0.toml`
- `benchmarks/suspension/WUFR26_OPTIMUMK_HEAVE_FRONT_KINEMATICS_V0.toml`

## Architecture findings

### Wheel reference

The nominal wheel-center construction remains explicitly source-specific to the frozen zero-offset WUFR OptimumK setup. Higher-precision result-backed half-track values are retained in the wheel-reference source fixture instead of silently modifying the earlier Box-text geometry transcription.

Wheel-plane orientation reuses the already reviewed steering static-alignment primitive. This prevents a second toe/camber convention from developing inside suspension.

### Front steering ownership

Front `MOD-SUSP-0002` output is transported with the `EQ-SUSP-0003` minimum-twist transform. The tie rod has not yet rotated the upright. `MOD-STEER-0001` remains the owner of front steering closure.

A focused ownership test supplies a deliberately different final upright transform and verifies that the front wheel-reference result still follows the unresolved minimum-twist transform.

### Physical state

The user-facing scalar is

```text
delta_z_wc_body = z_wc(q_L) - z_wc(0)
```

with positive values upward.

The inverse adapter requires an explicit `q_L` domain, sweeps outward from nominal with branch continuation, verifies a single monotonic displacement map, rejects out-of-domain requests, rejects ambiguous/nonmonotonic mappings, and uses a bracket-preserving solve. It never clips or extrapolates the request and does not relabel `q_L` as jounce/heave.

### Historical OptimumK steering removal

Both front corners now have direct 3D source fixtures across all 11 frozen pure-heave states. The source upright twist is reconstructed from lower/upper upright and upright tie-point geometry relative to the minimum-twist reference.

The source scalar `Steer Angle` is never used as a 3D rotation. Its mismatch with the reconstructed twist is retained as a regression guard.

The left/right equal-and-opposite result is checked only as historical source evidence; it is not an as-built symmetry claim.

## Frozen benchmark outcome

The current frozen result record reports:

`BENCH-SUSP-0004`

- max nominal wheel-center component error: `1.1102230246251565e-16 m` versus `2e-9 m` acceptance;
- max wheel-plane component error: `2.220446049250313e-16` versus `1e-12` acceptance.

`BENCH-SUSP-0005`

- 22 direct source states, both front corners;
- max reconstructed 3D twist error: `6.922847711754443e-15 rad` versus `2e-10 rad` acceptance;
- max unsteered wheel-center error: `1.3030825062884576e-15 m` versus `2e-9 m` acceptance;
- max historical bilateral twist sum: `5.603156827405087e-16 rad` versus `2e-12 rad` acceptance;
- minimum projected tie lever arm remains about `65.16 mm`;
- max scalar `Steer Angle` versus 3D twist difference is about `0.09014 deg`;
- scalar `Steer Angle` used as rotation: `false`.

`BENCH-SUSP-0006`

- reviewed benchmark `q_L` domain: `[-0.06976604887606597, 0.06954460516700353] rad`;
- calculated body-frame wheel-center displacement image: approximately `[-0.02622071346, +0.02601738462] m`;
- max selected-state `q_L` recovery error: `5.041942675865219e-09 rad`;
- max displacement residual: `1.896267531886764e-09 m` under the configured `2e-9 m` displacement tolerance;
- outside-domain request fails explicitly;
- nonmonotonic mapping fails as ambiguous;
- upstream kinematic failure is propagated.

These ranges are verification domains, not installed suspension-travel or bump-stop authority.

## Restrictions retained

The implementation does not authorize:

- nonzero OptimumK wheel-offset semantics;
- generic contact patch, loaded radius, or tire deflection;
- front tie-rod steering inside suspension;
- whole-vehicle translation between the front and rear OptimumK source-local frames;
- pushrod/pullrod, rocker, damper, spring, ARB, or motion-ratio kinematics;
- forces, load transfer, compliance, packaging, articulation, or durability;
- installed/as-built or production geometry claims.

## Review disposition

The implementation is suitable for the bounded prototype role defined by `AUTH-SUSP-0002`. Final PR disposition requires the final head to pass registry validation, the complete unit/regression suite, the dedicated suspension workflow, visualization validation, and motion-aware vehicle/steering validation.

After merge, the suspension stack can provide a real source-backed wheel/upright state to steering and visualization. The next physics expansion should remain a separate authorization decision rather than being added implicitly to `MOD-SUSP-0002`.
