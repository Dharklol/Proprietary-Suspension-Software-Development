# WUFR static-gravity allocation implementation v0.1.0

## Scope

`src/pssd_vehicle/wufr_gravity.py` implements `MOD-VEH-0005` under `AUTH-VEH-0005`.

It is a source-driven adapter, not an equilibrium solver. It loads `WUFR27_STATIC_GRAVITY_ALLOCATION_V0`, verifies the reviewed source/assumption identity, independently reconstructs the mass decomposition, and exposes physical gravity point loads for later QSS composition.

## Source validation

The loader rejects any source packet that does not preserve:

- record ID `WUFR27_STATIC_GRAVITY_ALLOCATION_V0`;
- assumption ID `ASM-VEH-0003`;
- canonical corner order `[front_left, front_right, rear_left, rear_right]`;
- measured axle totals `10 kg` front and `10 kg` rear;
- the reviewed 5 kg/corner prototype split;
- exact total scale conversion from `675 lb` using `0.45359237 kg/lb`;
- the mass/first-moment-derived sprung mass and CG.

There is no fallback to historical `10 kg/corner`, `207 kg` sprung mass, or `220+100 kg` calculation inputs.

## Derived state

The implementation independently obtains:

- total mass `306.17484975 kg`;
- prototype unsprung mass `20 kg`;
- sprung mass `286.17484975 kg`;
- sprung CG source position `[-0.7428152951513378, +0.006753924590788551, +0.29429108288542044] m`;
- sprung CG offset from the reviewed total-CG body origin `[+0.002507371515328871, +0.0004411808870848346, +0.004291082885420461] m`.

It recombines the sprung body and four point lumps and rejects a source packet if total mass or any first moment no longer matches the reviewed total reference.

## Gravity actions

Every point mass returns a physical inertial gravity force

`F_g = [0, 0, -m g]`.

The sprung point is body-fixed at the derived sprung-CG offset. `sprung_body_generalized_gravity()` composes that point with `MOD-VEH-0003`'s analytical virtual-work mapping for `q=[z_s, phi, theta]`.

At the nominal level pose the resulting sprung generalized gravity is approximately

`[-2807.375276, -1.238560315, +7.039132800]`

with units `[N, N*m, N*m]`.

The four unsprung masses deliberately remain physical wheel-center point-load definitions. The module does **not** turn `49.05 N` into a globally fixed wheel generalized force. That projection belongs to the later reviewed wheel/contact coordinate map.

## Authority failures

The provider exposes explicit `authority_exceeded` failures when callers attempt to treat the prototype allocation as installed/as-built mass authority or as a maneuver unsprung inertia model.

## Verification

`BENCH-VEH-0007` is implemented by:

- `tests/test_wufr_static_gravity.py`;
- `tests/test_wufr_static_gravity_authorization.py`;
- `tests/test_wufr_static_gravity_result_record.py`;
- `scripts/run_wufr_static_gravity_benchmarks.py`;
- `benchmarks/vehicle/wufr_static_gravity_result_v0.1.0.toml`.

The benchmark independently recomputes the mass and all three first moments rather than merely comparing copied derived constants.

## Remaining boundary

This implementation does not create `z_w(q_b)`, `J_wb`, contact coefficients, spring/ARB composition, road reactions, crossweight, LLTD, or load transfer. The next vehicle gate is the exact flat-road four-corner physical wheel-coordinate/contact map built from `MOD-VEH-0003` and `MOD-SUSP-0002`.
