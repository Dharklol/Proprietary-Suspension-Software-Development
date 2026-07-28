# Rocker included-load implementation v0.1.0

## Implemented scope

`src/pssd_suspension/rocker_included_load.py` implements `EQ-SUSP-0029` through `EQ-SUSP-0031` as an exact Cartesian rigid-body statics kernel.

For a named point-load set, pivot `R`, and normalized same-sign rocker axis `a`, it returns:

```text
F_inc = sum(F_i)
M_inc = sum((r_i-R) cross F_i)
tau_axis = a dot M_inc
F_p = -F_inc
M_p = -(M_inc - tau_axis*a)
```

The implementation verifies:

```text
F_inc + F_p = 0
(M_inc + M_p)_perpendicular_to_a = 0
a dot M_p = 0
```

A nonzero `tau_axis` remains a successful signed diagnostic. It is not clipped and no balancing term is added.

## WUFR adapter

`src/pssd_suspension/wufr_rocker_included_load.py` consumes:

- `WufrInterfaceStaticsResult.actuation.force_on_remote_N` at `remote_point_m`;
- `WufrSpringRockerForceResult.force_on_rocker_N` at `rocker_eye_m`;
- the selected `ZBarLinkSideForce.force_on_rocker_N` at the corresponding current `ZBarMechanismResult` rocker pickup.

It verifies successful upstream providers and matching axle, side, configuration, fixture identity, rocker pivot, and same-sign rocker axis. It retains frame, geometry source, load-case, and external-wrench provenance from the Level-1 result.

Every WUFR result contains:

```text
included_load_ids = [push_pull, conservative_spring, physical_arb_link]
missing_load_ids = [KW_V5_non_spring_static_force]
complete_hardware_reaction = false
```

## Failure behavior

The kernel fails closed for empty/duplicate/conflicting identities, nonfinite values, metadata mismatch, degenerate axes, and residual violations. The adapter additionally fails for upstream provider failure, unavailable side data, source mismatch, and geometry mismatch.

## Verification

- Exact 3D hand case with nonzero free-axis residual.
- Translation invariance.
- Force reversal and homogeneous scaling.
- Zero-axis-moment complete algebraic balance for the included set.
- Structured generic failures.
- WUFR physical source/application-point ownership and incompleteness contract.

## Boundary

This implementation does not produce complete rocker equilibrium, total pivot or bearing loads, damper gas/friction values, vehicle operating load cases, structural results, or installed/as-built claims.
