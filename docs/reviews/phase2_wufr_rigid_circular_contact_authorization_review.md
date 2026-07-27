# Phase 2 WUFR rigid circular contact authorization review

## Decision

Authorize `ASM-VEH-0005` / `EQ-VEH-0014` as the first replacement contact geometry for `MOD-VEH-0006` after the failed `ASM-VEH-0004` source interpretation.

This is deliberately a **rigid circular centerline reference**, not a claim about the physical tire contact patch.

## Why the replacement is source-bounded

The already reviewed `WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0` fixture freezes:

- tire radius `232.41 mm`;
- nominal physical wheel centers;
- nominal wheel-plane normals;
- the zero-offset source scope used by `MOD-SUSP-0002`.

`MOD-SUSP-0002` already transports wheel center and wheel plane through the suspension kinematics. For the front, `MOD-STEER-0001` remains the only runtime centered-rack steering closure. The replacement contact model therefore adds only the missing tire-to-road geometric relation; it does not introduce another suspension or steering solve.

## Geometry

For unit road normal `n_R`, unit wheel-plane normal `n_w`, current wheel center `r_wc`, and radius `R`:

`v = n_R - (n_R dot n_w)n_w`

`e = v / ||v||`

`r_cp = r_wc - R e`

This chooses the point on the zero-width wheel-plane circle that minimizes road-normal height.

The construction has useful non-negotiable checks:

- radius from center is exactly `R`;
- radial vector is in the wheel plane;
- wheel-normal sign reversal does not change the result;
- an upright wheel on a horizontal road reduces to center minus radius in road-normal direction;
- a wheel plane parallel to the road plane is explicitly degenerate and must fail rather than use a fallback.

## Nominal WUFR consequence

Using the frozen source wheel centers and wheel planes with `R=0.23241 m`, the nominal ideal-circle points are approximately:

| Corner | x (mm) | y (mm) | z (mm) |
|---|---:|---:|---:|
| FL | +0.159242 | +615.984170 | 0 |
| FR | +0.159242 | -615.984170 | 0 |
| RL | -0.035396 | +603.285406 | 0 |
| RR | -0.035396 | -603.285406 | 0 |

The small longitudinal offsets are a direct consequence of using the full toe/camber wheel plane. They are **not** repaired to the historical OptimumK Contact Patch `x=0` output.

That intentional disagreement is important. PR #64 already demonstrated that the OptimumK Contact Patch output is not valid authority for a rigidly attached material point. The new circle model is not fitted to that output.

## Fidelity boundary

The model assumes a fixed source-setup radius. It contains no:

- loaded-radius reduction;
- tire vertical stiffness;
- finite tread width or edge contact;
- contact-patch footprint or pressure distribution;
- load, pressure, temperature, speed, or wear dependence;
- carcass deformation.

This means the first integrated static QSS result will be a **rigid-tire design-intent baseline**. It is suitable for closing the suspension/spring/Z-bar/gravity/road geometry chain and then comparing the result against scale and ride-height data. It is not yet an installed-tire prediction.

## Relationship to prior authorizations

- `AUTH-VEH-0007` and failed `BENCH-VEH-0008` remain valid negative evidence against `ASM-VEH-0004`.
- `AUTH-VEH-0008` satisfies the replacement-contact gate without weakening that failed benchmark.
- `MOD-VEH-0006`, `EQ-VEH-0011` through `0013`, and `BENCH-VEH-0009` may resume implementation only through `ASM-VEH-0005` / `EQ-VEH-0014`.
- A separate downstream authorization is still required before the generic QSS kernel may publish WUFR road reactions/static wheel loads.

## Implementation gate

Before the implementation PR may merge:

1. implement `EQ-VEH-0014` as a focused, source-radius-driven geometry provider;
2. pass `BENCH-VEH-0010` exact geometry and limiting-case checks;
3. compose the fully steered front wheel plane rather than duplicating steering closure;
4. re-run `BENCH-VEH-0009` road roots, two-step `J_wb`, contact-coefficient virtual work, and unsprung gravity projection;
5. prove there is no second radius constant, `ASM-VEH-0004` fallback, loaded-radius inference, or body/track shortcut.

## Downstream recommendation

After that implementation passes, the next useful authorization should be the first integrated WUFR static equilibrium composition. That result should immediately be treated as a correlation baseline against corner scales, ride heights, spring/perch state, and damper/shock-pot position before adding maneuver load transfer or higher-fidelity tire compliance.
