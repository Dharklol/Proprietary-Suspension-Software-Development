# Phase 3 WUFR synchronized static rocker included-load implementation review

## Outcome

`MOD-SUSP-0010` is implemented under merged `AUTH-SUSP-0018`. It composes the accepted `MOD-SUSP-0009` four-corner static Level-1 result with exact matching current spring and physical Z-bar linkage states through the unchanged incomplete `MOD-SUSP-0008` rocker adapter.

## Reviewed mechanics

The implementation introduces no physical load. For every corner it copies the signed Level-1 actuation `force_on_remote_N` at `remote_point_m` unchanged, then combines it with the physical conservative-spring vector at the coilover rocker eye and the physical Z-bar-link vector at the current mechanism pickup.

Before composition, the Level-1 actuation body point, remote point, and signed axis are checked against the current arm attachment, rocker pickup, and physical link line. The Level-1 state is also synchronized with the regenerated spring/Z-bar actuation state. Any mismatch rejects the entire four-corner collection.

The existing rigid-rocker ideal-revolute projection is unchanged. The support contribution removes only force and moment perpendicular to the free rocker axis. The signed free-axis moment is retained without clipping, fitting, or balancing repair.

## Frozen result

The setting-1/1 fixture produces pivot-force contributions approximately:

```text
FL [-1.30, -3128.38, -1481.20] N
FR [-1.20,  3106.17, -1459.13] N
RL [ 2.22,   147.44,  -813.00] N
RR [ 2.22,  -146.94,  -791.44] N
```

Signed free-axis residuals are approximately:

```text
[+0.0140722, -0.0138634, +1.40762e-6, -1.36282e-6] N*m
```

The force, perpendicular-moment, and support-axis-moment closure residuals are zero in the frozen result. These residuals demonstrate exact execution of the included-load projection, not complete rocker equilibrium.

## Damper influence result

A per-unit non-spring damper-force sensitivity is frozen for the exact current coilover eye line. The pivot-force coefficient is the negative chassis-to-rocker eye direction. Because the current eye line and rocker pivot geometry produce a moment only about the free rocker axis, the perpendicular pivot-moment coefficient is zero.

The signed free-axis coefficients are approximately:

```text
[-0.0649298, +0.0649459, -0.126979, +0.126983] m
```

An independent unit point-load evaluation through the existing rocker kernel verifies the analytic coefficients. No actual KW V5 force is selected or implied.

## Failure and publication policy

The implementation fails closed for unsuccessful upstream results, missing or reordered corners, moved actuation endpoints, reversed actuation axes, configuration/state/load-case mismatch, nonfinite inputs, spring or Z-bar provider failure, and any corner composition failure. Failed results publish no partial corner set.

The frozen packet retains:

- `missing_load_ids=[KW_V5_non_spring_static_force]`;
- `complete_hardware_reaction=false`;
- `complete_rocker_equilibrium=false`;
- `actual_damper_force_applied=false`; and
- no structural, maneuver, installed/as-built, setup, correlation, or production authority.

## Deliberate stopping boundary

This completes the strongest static rocker result available before lab or manufacturer evidence for the KW V5 non-spring static force. Complete rocker or bearing reactions remain blocked by `AUTH-SUSP-0015` and require a physically consistent upstream vehicle-equilibrium rerun after the missing force is characterized and separately authorized.
