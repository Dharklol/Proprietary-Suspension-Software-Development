# Rocker included-load contribution function specification

## Purpose

`MOD-SUSP-0008` evaluates the reaction contribution associated with an explicitly named subset of physical point loads on one rigid rocker. It is intentionally not a complete rocker equilibrium model.

The first WUFR adapter consumes only:

- the Level-1 push/pull force at the rocker endpoint;
- the conservative spring force at the current rocker eye;
- the physical ARB-link force at the current mechanism rocker pickup.

`AUTH-SUSP-0015` keeps the KW V5 non-spring static contribution unavailable and nonzero-by-default. Every WUFR v0.1 result is therefore incomplete.

## Coordinate contract

Inputs use one right-handed Cartesian frame. The rocker pivot is `R` and the finite rocker-axis vector is normalized to `a` without changing its sign.

Each point load has:

```text
load_id
source_id
application_point r_i
force F_i
```

Load IDs are unique and application points remain source-owned.

## Equations

Included resultants:

```text
F_inc = sum_i F_i
M_inc = sum_i ((r_i - R) cross F_i)
```

Ideal revolute support contribution:

```text
tau_axis = a dot M_inc
F_p = -F_inc
M_p = -(M_inc - tau_axis*a)
```

Residual check:

```text
F_res = F_inc + F_p = 0
M_res = M_inc + M_p = tau_axis*a
M_perp_res = M_res - (a dot M_res)*a = 0
```

The support carries force in all directions and a moment only perpendicular to the free axis. `tau_axis` is retained exactly; the model does not invent a support-axis couple.

## Result interpretation

A successful result means the included-load algebra and support projection are internally consistent. It does not mean the rocker is in equilibrium.

Required fields include:

```text
included_load_ids
missing_load_ids
complete_hardware_reaction
included_resultant_force
included_resultant_moment
pivot_force_contribution
pivot_moment_contribution
free_axis_moment_residual
force_residual
perpendicular_moment_residual
```

For the WUFR v0.1 adapter:

```text
included_load_ids = [push_pull, conservative_spring, physical_arb_link]
missing_load_ids = [KW_V5_non_spring_static_force]
complete_hardware_reaction = false
```

## WUFR source adapter

### Push/pull input

Consume the successful `MOD-SUSP-0007` actuation `AxialReaction`:

```text
point = remote_point_m
force = force_on_remote_N
```

The body-side value acts on the A-arm and is not the rocker load.

### Spring input

Consume the successful `AUTH-SUSP-0014` result:

```text
point = rocker_eye_m
force = force_on_rocker_N
pivot = rocker_pivot_m
axis = rocker_axis_unit
```

### ARB input

Select the requested side from the successful `AUTH-SUSP-0013` result:

```text
force = side.force_on_rocker_N
point = matching current ZBarMechanismResult rocker_pickup_left_m/right_m
```

The physical point force must not be replaced by blade transverse force, generalized rocker torque, wheel-coordinate force, or a scalar ratio.

## Source and identity checks

The WUFR adapter fails closed for:

- failed upstream results;
- axle, side, frame, configuration, or geometry mismatch;
- missing or duplicate load identity;
- nonfinite points or forces;
- degenerate axis;
- mismatch between current rocker pivots/axes or expected current application points;
- unavailable requested ARB side.

No value is clipped, averaged, sign-repaired, moved, or fitted.

## Benchmarks

- `BENCH-SUSP-0026`: exact 3D hand cases and translation invariance.
- `BENCH-SUSP-0027`: zero/nonzero free-axis residual, reversal/scaling, and failures.
- `BENCH-SUSP-0028`: WUFR source composition and incompleteness contract.

## Explicit exclusions

No complete rocker reaction, damper gas/friction value, dynamic rocker inertia, bearing split, shaft bending, stress, fatigue, compliance, FEA load release, vehicle load-case generation, or installed/as-built claim is produced.
