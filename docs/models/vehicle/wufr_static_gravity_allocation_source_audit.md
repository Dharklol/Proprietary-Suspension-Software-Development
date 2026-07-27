# WUFR static-gravity allocation source audit

## Decision

The mass-source gap identified in PR #58 and retained through PR #60 is now resolved **for the first driver/no-fuel static-gravity R&D prototype only**.

On 2026-07-27 the reviewer approved splitting the measured unsprung axle totals equally left/right:

- front axle measured unsprung total: `10 kg` -> `5 kg` FL + `5 kg` FR;
- rear axle measured unsprung total: `10 kg` -> `5 kg` RL + `5 kg` RR.

This is recorded as `ASM-VEH-0003`. It is an explicit prototype allocation assumption, not measured per-corner mass data.

## Governing total vehicle state

The whole-vehicle design reference remains `WUFR26_WHOLE_VEHICLE_FRAME_V0` in the driver/no-fuel state:

- LF `178 lb`;
- RF `175 lb`;
- LR `163 lb`;
- RR `159 lb`;
- total `675 lb`;
- total design-reference CG source position `[-0.7453226666666667, +0.006312743703703716, +0.290] m`.

The x/y coordinates come from the scale reaction centroid and the 0.290 m height comes from the separately sourced driver-equivalent-ballast tilt test. That source separation remains unchanged.

Using the exact conversion `1 lb = 0.45359237 kg`, the total driver/no-fuel mass is

`m_total = 306.17484975 kg`.

## Prototype unsprung point model

For this static-gravity slice only, each 5 kg allocation is attached to its corresponding physical wheel-center point/state. At nominal design intent the four source-frame wheel centers are

- FL `[0, +0.615986, 0.228600] m`;
- FR `[0, -0.615986, 0.228600] m`;
- RL `[-1.562400, +0.603286, 0.228600] m`;
- RR `[-1.562400, -0.603286, 0.228600] m`.

These locations come from the already-reviewed axle, track, and wheel-center-height geometry. They are **not** measured unsprung centers of mass.

For gravity, the implementation must preserve the physical point-load interpretation. The nominal level-state weight magnitude of each lump is `5*9.81 = 49.05 N`, but a downstream generalized wheel-coordinate force must be obtained by virtual work through the actual wheel/contact coordinate projection. This authorization does not permit hard-coding `-49.05 N` as the generalized force for every nonlevel state.

## Derived sprung body

The sprung body is obtained by exact mass and first-moment subtraction,

`m_total r_total = m_s r_s + sum_i(m_ui r_ui)`.

This gives

- sprung mass `m_s = 286.17484975 kg`;
- sprung-CG source position `[-0.7428152951513378, +0.006753924590788551, +0.29429108288542044] m`;
- sprung-CG offset from the existing total-CG body origin `[+0.002507371515328871, +0.0004411808870848346, +0.004291082885420461] m`.

At `g=9.81 m/s^2`, sprung weight magnitude is `2807.3752760475004 N`.

The derived z coordinate is not new metrology. It inherits both the source-separated 0.290 m total-CG height and the wheel-center lump assumption. The entire derived sprung body therefore remains design-intent R&D authority under `ASM-VEH-0003`.

## Sources deliberately not promoted

The following remain comparison/context only:

- historical WUFR-26 `10 kg per corner` ride-frequency assumption;
- LLTD `207 kg` sprung-mass template input;
- Suspension Calculations `220 kg car + 100 kg driver` input;
- any hidden equal-crossweight or diagonal-load rule.

## What this closes

This audit closes the missing **mass allocation** required to build explicit WUFR gravity providers:

- body gravity can be applied at the derived sprung CG through `MOD-VEH-0003`;
- four unsprung gravity point loads can be attached to the four physical wheel-center states;
- all values retain their source and assumption provenance.

## What remains open

This does **not** by itself define the road-compatible map required by `MOD-VEH-0004`:

`z_w(q_b), J_wb = partial(z_w)/partial(q_b)`.

The next vehicle gate must construct that map from the reviewed whole-vehicle pose/contact geometry and the actual `MOD-SUSP-0002` physical wheel-state solver. It must also define the work-conjugate road-normal/contact projection for each wheel state. It may not replace that geometry with body-roll-times-track, direct wheel-travel-difference, or scalar motion-ratio formulas.

Only after that gate can the real WUFR spring and Z-bar providers be composed into a static four-corner equilibrium and road-reaction benchmark.
