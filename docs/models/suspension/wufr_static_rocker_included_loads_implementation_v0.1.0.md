# WUFR synchronized static rocker included-load implementation v0.1.0

## Scope

`MOD-SUSP-0010` is implemented under `AUTH-SUSP-0018` as an atomic source-preserving composition from the accepted `MOD-SUSP-0009` static Level-1 interface-load packet into the existing incomplete `MOD-SUSP-0008` rocker adapter.

The implementation adds no vehicle load, constitutive law, force magnitude, balancing term, joint idealization, or hardware load split. It regenerates the exact matching spring and Z-bar states from the accepted setting-1/1 static fixture and copies the solved push/pull remote-end reaction unchanged.

## Exact four-corner handoff

For each corner in fixed front-left, front-right, rear-left, rear-right order, the implementation verifies:

1. the `MOD-SUSP-0009` corner, configuration, state, frame, and load-case identities;
2. the solved actuation body and remote points against the current arm attachment and rocker push/pull pickup;
3. the solved actuation axis against the exact current physical link line with its sign retained;
4. the Level-1 and regenerated spring/Z-bar actuation coordinates and rocker angle;
5. the spring force at the exact current rocker coilover eye;
6. the physical Z-bar linkage force at the exact current mechanism rocker pickup; and
7. the rocker pivot and signed axis agreement already enforced by `MOD-SUSP-0008`.

A mismatch at any corner rejects the complete collection. No successful subset is published.

## Included-load mechanics

The unchanged `MOD-SUSP-0008` kernel receives exactly three physical point loads:

- signed pushrod or pullrod force on the rocker at the Level-1 remote endpoint;
- conservative coil-spring force on the rocker at the current coilover eye; and
- physical Z-bar linkage force on the rocker at the current Z-bar pickup.

For rocker pivot `R`, signed unit axis `a`, and the named loads `(r_j,F_j)`, it evaluates:

```text
F_inc = sum(F_j)
M_inc = sum((r_j - R) cross F_j)
F_p = -F_inc
M_p = -(M_inc - (a dot M_inc) a)
tau_axis = a dot M_inc
```

The free-axis moment is retained as a signed diagnostic. It is not removed by a hidden couple and is not an equilibrium failure because the named included set is explicitly incomplete.

## Frozen setting-1/1 result

Ideal-revolute pivot-force contributions `[x,y,z]` N are:

```text
FL [-1.29659286, -3128.37827083, -1481.19985884]
FR [-1.19666897,  3106.16840246, -1459.12826058]
RL [ 2.21527876,   147.43620321,  -812.99782150]
RR [ 2.22479594,  -146.94133659,  -791.43810155]
```

Perpendicular pivot-moment contributions `[x,y,z]` N*m are:

```text
FL [0, -0.03403858, -0.17871219]
FR [0, -0.03533263,  0.18082831]
RL [0,  0.21932847, -0.26119740]
RR [0,  0.21991462,  0.26189088]
```

Signed unrepaired free-axis residuals `[FL,FR,RL,RR]` N*m are:

```text
[0.0140721934, -0.0138633791, 1.40761847e-6, -1.36282337e-6]
```

Force, perpendicular-moment, and support-axis-moment closure residuals are exactly zero in the frozen record.

## Unit non-spring damper-force influence

The implementation also publishes a geometric coefficient for a hypothetical positive `+1 N` force on the rocker along the exact current chassis-eye-to-rocker-eye line. For unit direction `e` and rocker-eye point `D`:

```text
dF_p/dF_d = -e
dM_p/dF_d = -(((D-R) cross e) - (a dot ((D-R) cross e)) a)
dtau_axis/dF_d = a dot ((D-R) cross e)
```

For the current direct-coilover geometry the unit force produces only a free-axis moment about the ideal rocker axis, so the perpendicular support-moment coefficient is zero. The signed free-axis coefficients `[FL,FR,RL,RR]` m are:

```text
[-0.0649298170, 0.0649459470, -0.1269787471, 0.1269828972]
```

These values are not KW V5 force estimates. They are linear geometric sensitivities for later use only after a reviewed measured or manufacturer-sourced signed force is available for the exact same state.

## Verification

The implementation is covered by:

- exact four-corner synchronization and load-handoff tests;
- moved-point, reversed-axis, reordered/missing-corner, source/state/load-case, nonfinite, and unsuccessful-upstream failure tests;
- an independent unit-load evaluation through the existing `MOD-SUSP-0008` kernel;
- deterministic full JSON and summary TOML records;
- regeneration comparison with `1e-12` numeric tolerance; and
- dedicated CI artifact publication.

The frozen records are:

- `benchmarks/suspension/wufr_static_rocker_included_loads_result_v0.1.0.json`;
- `benchmarks/suspension/wufr_static_rocker_included_loads_result_v0.1.0.toml`.

## Fidelity boundary

Every result remains `uncorrelated_design_intent_static_rocker_included_loads` and is complete only for the explicitly named push/pull, conservative-spring, and physical-Z-bar point-load set.

`KW_V5_non_spring_static_force` remains explicitly missing under `AUTH-SUSP-0015`. Consequently:

- `complete_hardware_reaction=false`;
- `complete_rocker_equilibrium=false`;
- no actual damper force is applied or assumed zero;
- no bearing split, chassis pickup load, stress, fatigue, compliance, factor of safety, or FEA boundary condition is authorized; and
- no maneuver, setup, correlation, installed/as-built, production, or structural-release authority is created.
