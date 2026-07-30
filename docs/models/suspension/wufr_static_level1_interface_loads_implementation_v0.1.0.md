# WUFR synchronized static Level-1 interface-load implementation v0.1.0

## Scope

`MOD-SUSP-0009` is implemented under `AUTH-SUSP-0017` as an atomic source-preserving orchestration layer. It consumes the reviewed `MOD-VEH-0008` four-corner static carrier-wrench result and invokes the unchanged `MOD-SUSP-0007` three-body Level-1 solver once for each exact matching corner state.

No force, couple, constitutive law, joint idealization, load split, or numerical repair is introduced.

## Current-state synchronization

For each corner, the implementation:

1. retains the exact accepted wheel coordinate from the corrected static-equilibrium fixture;
2. evaluates the matching branch-preserving suspension state using the reviewed physical-wheel map;
3. evaluates the matching arm-mounted actuation state;
4. obtains front tie-rod endpoints from an explicit centered-rack `MOD-STEER-0001` closure, or the rear toe-link endpoints from the current `MOD-SUSP-0001` upright closure;
5. constructs the exact `WUFR27_LEVEL1_LINKAGE_TOPOLOGY_V0` geometry;
6. verifies the current upper/lower spherical centers and midpoint carrier reference against the frozen `MOD-VEH-0008` record; and
7. solves the existing exact 18x18 carrier/UCA/LCA equilibrium system.

Corner order is fixed as front-left, front-right, rear-left, rear-right. Any identity, frame, reference, source, geometry, steering, conditioning, pivot, or physical-residual failure rejects the complete collection. Failed results contain no publishable partial corner set.

## Frozen setting-1/1 result

Signed lateral-link axial forces `[FL, FR, RL, RR]` are:

```text
[14.5936224217, 14.3849239198, -1.75768846298, -1.69088557053] N
```

Signed actuation-rod axial forces `[front pullrod FL/FR, rear pushrod RL/RR]` are:

```text
[2620.75972225, 2579.80861492, -1125.26239934, -1092.29912780] N
```

Positive values retain the existing tension-positive convention. Negative rear values are valid compression and are not clipped.

Across all twelve solved rigid-body balances, the maximum force residual is `1.1368683772161603e-13 N` and the maximum moment residual is `1.1901590823981678e-13 N*m`. The maximum scaled infinity-norm condition number is `59.21685443725399`, far below the `1e10` rejection gate.

## Records and verification

- full record: `benchmarks/suspension/wufr_static_level1_interface_loads_result_v0.1.0.json`;
- summary record: `benchmarks/suspension/wufr_static_level1_interface_loads_result_v0.1.0.toml`;
- benchmark generator: `scripts/run_wufr_static_level1_interface_load_benchmarks.py`;
- implementation tests: `tests/test_wufr_static_level1_interface_loads*.py`;
- benchmark gates: `BENCH-SUSP-0029`, `BENCH-SUSP-0030`, and `BENCH-SUSP-0031`.

The tests freeze exact synchronization, centered-rack steering ownership, signed forces, action-reaction pairs, physical residuals, and fail-closed behavior for reordered corners, unsuccessful upstream results, frame/reference mismatch, unavailable steering closure, and forced solver conditioning failure.

## Fidelity boundary

The result is complete only for Level-1 interface equilibrium under the exact authorized uncorrelated static-gravity fixture. It is not a complete physical vehicle load case and does not authorize maneuver loads, individual A-arm chassis-joint or welded-member loads, rocker-result publication, complete rocker reaction, structural packets, stress, FEA, setup selection, installed/as-built claims, or production use.

The only later rocker handoff is the unchanged successful actuation `force_on_remote_N` at `remote_point_m`. The unavailable KW V5 non-spring static force remains an explicit missing input under `AUTH-SUSP-0015`.
