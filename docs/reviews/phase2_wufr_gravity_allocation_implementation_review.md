# Phase 2 WUFR static-gravity allocation implementation review

## Implemented scope

`MOD-VEH-0005` now provides the exact bounded capability authorized in `AUTH-VEH-0005`:

- load the reviewed driver/no-fuel mass packet;
- preserve measured 10 kg front / 10 kg rear unsprung axle totals;
- preserve `ASM-VEH-0003`'s explicit 5 kg/corner prototype allocation;
- independently derive and verify the sprung mass/CG by first moments;
- expose physical sprung and unsprung gravity point loads;
- map sprung-body gravity through the existing `MOD-VEH-0003` body generalized coordinates;
- expose structured source, allocation, first-moment, and authority failures.

## Verification burden

`BENCH-VEH-0007` checks the source arithmetic independently of the stored derived values. A modified source packet fails if its exact total scale conversion, axle allocation, derived sprung state, or first-moment reconstruction changes without review.

The benchmark also freezes the authority boundary that each 5 kg unsprung lump is a prototype wheel-center point model, not measured per-corner CG data.

## Important implementation choice

The module does not expose a convenience function returning a constant `-49.05 N` generalized force per wheel. It exposes the physical point force only. The downstream road/contact map must calculate the work-conjugate wheel-coordinate projection from actual geometry.

This avoids baking a nominal-level projection into rolled or pitched states.

## Not implemented

- road-compatible `z_w(q_b)` / `J_wb`;
- contact normal-to-wheel-coordinate coefficients;
- spring + ARB composition into `MOD-VEH-0004`;
- WUFR road reactions or wheel loads;
- wheel-lift continuation;
- lateral/longitudinal unsprung inertia/load transfer;
- installed/as-built mass claims.

## Next review

The next focused vehicle authorization should freeze the exact flat-road all-four-contact wheel-state compatibility map using the existing body-pose mechanics and `MOD-SUSP-0002` physical wheel-state inversion. It must resolve the relation between the authorized ideal road contact reference and the moving physical wheel state without introducing body-roll-times-track or scalar motion-ratio shortcuts.
