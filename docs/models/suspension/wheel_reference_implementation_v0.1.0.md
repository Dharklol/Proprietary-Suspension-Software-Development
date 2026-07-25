# MOD-SUSP-0002 wheel-reference implementation v0.1.0

## Decision

`MOD-SUSP-0002` implements the bounded wheel-reference and physical suspension-state layer authorized by `AUTH-SUSP-0002`. It composes `MOD-SUSP-0001`; it does not create a second suspension mechanism solver or absorb front steering, tire/contact, actuation, load, compliance, or whole-vehicle-origin physics.

Implementation:

- `src/pssd_suspension/wheel_reference.py`
- tests: `tests/test_wheel_reference_state_adapter.py`
- report: `scripts/run_wheel_reference_benchmarks.py`
- frozen result: `benchmarks/suspension/wheel_reference_result_v0.1.0.toml`

## Source boundary

The first source adapter is intentionally specific to the frozen WUFR OptimumK setup:

- setup: `WUFR-26 FINAL 8.21.2025.xlsx`, Box file `2014803790843`, version `2224178574043`, SHA-1 `15eadfb93369192038888da92ebaa6674db56cfa`;
- external result: `WUFR-26 8.21 Heaves 1inch.xlsx`, SHA-256 `db071b7e696149ec82213e9ed05aa557349d18d19debe7925e7e01058534e4b8`, OptimumK Result `2.3.0`;
- longitudinal, lateral, and vertical wheel offsets are all zero;
- higher-precision result-backed half tracks are retained for the wheel-reference fixture: front `615.98556 mm`, rear `603.28556 mm`;
- the Box setup text representation remains separately preserved at its displayed `615.986 mm` / `603.286 mm` precision.

Nonzero OptimumK wheel-offset semantics are not inferred. `load_wufr26_wheel_reference_profile` rejects a nonzero-offset source profile in this implementation.

## EQ-SUSP-0005: nominal wheel reference

For side sign `s=+1` left, `s=-1` right, tire radius `R`, source half-track `h`, and source static camber `gamma`, the reviewed zero-offset source rule is

```text
x_wc = 0
y_wc = s * (h + R sin(gamma))
z_wc = R cos(gamma)
```

The nominal wheel-plane basis is not reimplemented with a new toe/camber sign convention. The suspension module calls the existing reviewed `pssd_steering.projection.reference_from_static_alignment` primitive:

- canonical axes: `+x` forward, `+y` vehicle left, `+z` upward;
- side-local positive toe means toe-out;
- positive camber means wheel top outward.

The resulting source-backed nominal wheel centers are:

```text
front left   [0, +0.6068611862194348, 0.2322308203127064] m
front right  [0, -0.6068611862194348, 0.2322308203127064] m
rear left    [0, +0.5992294462199110, 0.2323746028312969] m
rear right   [0, -0.5992294462199110, 0.2323746028312969] m
```

## EQ-SUSP-0006: upright transport

`transport_wheel_reference` applies the upstream rigid upright transform to the nominal wheel center and to the wheel-plane normal/forward reference.

The ownership rule is explicit:

- front uses `SuspensionCornerStateResult.minimum_twist_transform`, preserving `upright_reference_pose_excludes_tie_rod_steering_rotation`;
- rear uses the final `upright_transform`, which may include `EQ-SUSP-0004` rear chassis locating toe-link closure.

A front `upright_transform` is deliberately not treated as permission to solve or apply driver steering inside suspension. The test suite injects a deliberately different final transform and verifies the front wheel reference still follows the unresolved minimum-twist transform.

The state result reports

```text
Delta p_wc = p_wc - p_wc,nominal
Delta z_wc_body = Delta p_wc.z
```

with positive `Delta z_wc_body` upward.

## EQ-SUSP-0007: physical vertical-state inversion

`q_L` remains an internal mechanism coordinate. The public physical scalar for this slice is body-frame wheel-center vertical displacement.

`solve_body_vertical_displacement` requires an explicit reviewed `q_L` interval that brackets nominal `q_L=0`. It then:

1. sweeps the negative and positive branches outward from nominal using `MOD-SUSP-0001` branch continuation;
2. transports the wheel reference at every sample;
3. checks the sampled `Delta z_wc_body(q_L)` map for monotonicity and unresolved plateaus;
4. records the reachable displacement image of the reviewed `q_L` interval;
5. rejects out-of-domain requests rather than clipping or extrapolating;
6. accepts an exact sampled root only when unique;
7. otherwise requires exactly one sign-changing bracket;
8. uses bracket-preserving bisection until the displacement or `q_L` tolerance is met;
9. propagates upstream suspension infeasibility as an explicit adapter failure.

Failure codes distinguish nonfinite input, unsupported source, upstream failure, unreachable request, no bracket, ambiguous mapping, and nonconvergence.

For the first WUFR benchmark the reviewed test domain is the frozen ±25.4 mm pure-heave source-derived `q_L` range plus a `0.15 deg` margin. Its corresponding calculated body-frame wheel-center displacement image is approximately `[-0.0262207, +0.0260174] m`. This is benchmark scope, not an installed suspension-travel or bump-stop claim.

## EQ-SUSP-0008: historical OptimumK source-steering removal

The historical front pure-heave export already contains tie-rod-constrained steering. A source pose cannot be sent directly into `MOD-STEER-0001` without double counting steering.

For each current state, `reconstruct_source_steering_twist` uses:

- current lower and upper upright points;
- nominal upright tie point transported by the `EQ-SUSP-0003` minimum-twist transform;
- current source-result upright tie point.

With current steering axis `k`, the two tie-point radius vectors are projected perpendicular to `k` and the signed source twist is

```text
psi = atan2(k dot (a_perp cross b_perp), a_perp dot b_perp)
```

An upright-attached point is then unsteered by

```text
p_unresolved = p_L + R(k, -psi) (p_source - p_L)
```

The implementation also reports projected tie-point lever-arm magnitudes and rejects a degenerate lever arm.

The scalar OptimumK `Steer Angle` channel is never used as the rotation input. Direct 3D fixtures for both front corners demonstrate the difference. At `-25.4 mm` heave the source scalar magnitude is about `0.1534 deg`, while the reconstructed 3D upright twist magnitude is about `0.24354 deg`.

The left/right equal-and-opposite twist behavior is verified only as a property of this historical mirrored source result. It is not promoted to an installed/as-built symmetry assumption.

## Verification

`BENCH-SUSP-0004` checks all four nominal source wheel centers and wheel-plane bases.

`BENCH-SUSP-0005` checks 22 direct source states: 11 heave states on each front corner. It reconstructs the 3D source twist, removes it from the source wheel center, compares against minimum-twist unresolved transport, checks tie-lever conditioning, checks the historical bilateral sign relationship, and proves that scalar `Steer Angle` was not used as the rotation input.

`BENCH-SUSP-0006` round-trips selected frozen WUFR source-derived `q_L` states through the body-frame wheel-center vertical coordinate, checks nominal recovery, rejects an outside-domain request, rejects a deliberately nonmonotonic mapping as ambiguous, and propagates an upstream failure.

The dedicated suspension workflow runs both the original `MOD-SUSP-0001` tests/reports and the `MOD-SUSP-0002` tests/reports so this layer cannot silently regress the underlying mechanism solver.

## Result authority

Passing these benchmarks establishes a source-grounded rigid kinematic adapter for the reviewed WUFR development baseline. It does not establish:

- installed/as-built wheel-center or bearing-axis metrology;
- tire loaded radius, tire deflection, or a generic contact patch;
- nonzero OptimumK wheel-offset semantics;
- whole-vehicle front/rear source-origin placement;
- spring/damper/pushrod/rocker/ARB motion ratios;
- forces, load transfer, compliance, packaging, articulation, durability, or production authority.

Those remain separate model and evidence gates.
