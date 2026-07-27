# WUFR static-gravity provider function specification

## Scope

`MOD-VEH-0005` is a source-driven adapter. It does not solve equilibrium.

The implementation consumes `WUFR27_STATIC_GRAVITY_ALLOCATION_V0` and returns explicit mass/point-gravity definitions suitable for later composition with `MOD-VEH-0003` and `MOD-VEH-0004`.

## Required outputs

The public provider must expose, with source/configuration/assumption provenance:

1. total driver/no-fuel mass;
2. four prototype unsprung masses in canonical corner order `[front_left, front_right, rear_left, rear_right]`;
3. nominal unsprung wheel-center source points;
4. derived sprung mass;
5. derived sprung-CG source point and body-origin offset;
6. gravity acceleration;
7. a sprung-body point-force definition;
8. four unsprung point-force definitions.

## Required arithmetic

Use the exact conversion frozen in the source record:

`m_total = 675 * 0.45359237 = 306.17484975 kg`.

Under `ASM-VEH-0003`:

`m_u = [5,5,5,5] kg`, `sum(m_u)=20 kg`.

Then

`m_s = m_total - sum(m_u) = 286.17484975 kg`.

With total CG `r_t` and wheel-center lump points `r_ui`, compute

`r_s = (m_total*r_t - sum_i(m_ui*r_ui))/m_s`.

No hard-coded derived CG may bypass this identity; implementation tests must verify the recombination residual.

## Gravity action

The sprung force is the road-frame gravity point force

`F_s,g = [0,0,-m_s*g]`

applied at the derived sprung CG. Its body generalized force is obtained through the existing `MOD-VEH-0003` point-force/virtual-work mapping.

Each unsprung point force is

`F_ui,g = [0,0,-m_ui*g]`

applied at the corresponding physical wheel center. The provider returns the physical point-force definition, not a globally hard-coded wheel generalized force. A later wheel/contact composition must map that point load into the reviewed wheel coordinate by virtual work.

## Failure behavior

The implementation must fail explicitly when:

- the source record/configuration/state ID is not the reviewed one;
- `ASM-VEH-0003` is absent or mismatched;
- corner order is not canonical;
- measured axle totals and assumed corner splits do not reconcile;
- any mass, point coordinate, or gravity value is nonfinite/nonpositive where applicable;
- the mass/first-moment recombination check fails;
- a caller requests installed/as-built or maneuver-unsprung-inertia authority.

There is no fallback to historical WUFR mass values.

## Verification

`BENCH-VEH-0007` is the implementation gate. Tests must independently recompute the mass and first moments rather than comparing only to copied constants.

The implementation should also expose enough provenance for later QSS result records to state that the 5 kg/corner split and wheel-center lump locations are prototype assumptions.

## Downstream boundary

No function in this module may manufacture the road-compatible wheel map, spring/ARB force, contact reaction, crossweight, roll gradient, or load transfer. Those remain downstream providers/gates.
