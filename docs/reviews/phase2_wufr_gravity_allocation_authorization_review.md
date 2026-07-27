# Phase 2 WUFR static-gravity allocation authorization review

## Review target

Authorize `MOD-VEH-0005` as the first WUFR-specific mass/gravity provider downstream of the generic `MOD-VEH-0004` quasi-static kernel.

## Reviewer decision incorporated

On 2026-07-27 the reviewer approved an equal split of the currently reviewed unsprung axle totals:

- `10 kg` front axle -> `5 kg` left + `5 kg` right;
- `10 kg` rear axle -> `5 kg` left + `5 kg` right.

The decision is frozen as `ASM-VEH-0003` and deliberately labeled a prototype assumption.

## Source-preserving decomposition

The governing total state remains the reviewed driver/no-fuel `675 lb` scale state and source-separated 3D design reference in `WUFR26_WHOLE_VEHICLE_FRAME_V0`.

With the four 5 kg prototype wheel-center lumps, exact mass/first-moment subtraction gives:

- total mass: `306.17484975 kg`;
- total unsprung: `20 kg`;
- sprung mass: `286.17484975 kg`;
- sprung CG: `[-0.7428152951513378, +0.006753924590788551, +0.29429108288542044] m` in the frozen source frame.

The sprung-CG result is derived design-intent authority only. It inherits the separate scale/tilt sources and the prototype wheel-center lump assumption.

## Accepted mechanics boundary

The future provider may return physical gravity point loads and their provenance. It may use existing `MOD-VEH-0003` virtual-work mapping for sprung body gravity.

Wheel gravity remains a physical point load at the solved wheel center. Its generalized-force projection must be evaluated through the later reviewed wheel/contact Jacobian. A constant `-49.05 N` generalized wheel force is not authorized for arbitrary rolled/pitched states merely because it is the nominal level-state magnitude.

## Explicitly not approved in this review

- measured-per-corner or installed/as-built mass claims;
- historical `10 kg/corner`;
- LLTD `207 kg` sprung mass;
- `220+100 kg` calculation input;
- hidden crossweight/diagonal closure;
- WUFR road-compatible wheel map;
- WUFR road reactions or solved static wheel loads;
- lateral/longitudinal unsprung inertia/load transfer.

## Next gate

After this authorization and its implementation, the next focused review is the road-compatible four-corner map/contact projection:

`q_b -> z_w`, `J_wb=partial(z_w)/partial(q_b)`

using the actual whole-vehicle pose, road plane, and `MOD-SUSP-0002` physical wheel-state solver. That gate should precede the first real WUFR spring+ARB static-equilibrium result.
