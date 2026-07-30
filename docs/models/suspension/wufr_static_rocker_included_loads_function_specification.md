# WUFR synchronized static rocker included-load function specification

## Purpose

`MOD-SUSP-0010` is a narrow orchestration layer between the accepted four-corner static Level-1 result (`MOD-SUSP-0009`) and the existing incomplete rocker included-load adapter (`MOD-SUSP-0008`). It adds no physical load or constitutive law.

The implementation must evaluate exactly front-left, front-right, rear-left, and rear-right in that order. One failed or mismatched corner rejects the entire collection.

## Required inputs

For each corner, the orchestration layer must consume:

1. the successful `MOD-SUSP-0009` corner result from the exact accepted static-gravity fixture;
2. `solve.actuation.force_on_remote_N` at `solve.actuation.remote_point_m`, copied unchanged;
3. the matching current `AUTH-SUSP-0014` spring force on the rocker at the spring eye;
4. the matching current `AUTH-SUSP-0013` physical Z-bar linkage force at the exact mechanism rocker pickup;
5. the exact current rocker pivot and signed rocker axis used by both physical-force providers; and
6. the `AUTH-SUSP-0015` missing-force identity `KW_V5_non_spring_static_force`.

Configuration, state, load-case, corner, axle, side, frame, point, axis, spring source, and ARB fixture identities must agree exactly except where an authorization explicitly defines a finite geometry tolerance.

## Per-corner mechanics

The unchanged `MOD-SUSP-0008` adapter owns the physical included-load calculation. For the named point-load set

```text
push_pull
conservative_spring
physical_arb_link
```

about current rocker pivot `R` and signed unit axis `a`, it evaluates

```text
F_inc = Σ F_j
M_inc = Σ [(r_j - R) × F_j]
F_p   = -F_inc
M_p   = -(M_inc - (a·M_inc)a)
tau_axis = a·M_inc
```

`F_p` and `M_p` are the ideal-revolute support contributions for the named included load set only. `tau_axis` is a signed unrepaired free-axis residual. A nonzero value is a diagnostic, not permission to add a balancing torque.

Every result must retain:

- the three exact point-load records;
- included resultant force and moment;
- support-force and perpendicular-moment contributions;
- signed free-axis residual and full residual vectors;
- exact points, pivot, axis, source, frame, configuration, state, load-case, axle, side, and corner identities;
- `missing_load_ids = [KW_V5_non_spring_static_force]`;
- `complete_hardware_reaction = false`; and
- `complete_rocker_equilibrium = false`.

## Unit non-spring damper-force influence

The implementation may additionally report a geometric coefficient for a hypothetical signed scalar damper force. Let `C` be the current chassis eye, `D` the current rocker eye, and

```text
e_d = (D - C) / ||D - C||
```

A positive unit force is `+1 N * e_d` acting on the rocker at `D`. The analytic coefficients are

```text
dF_p/dF_d = -e_d
m_unit = (D - R) × e_d
dM_p/dF_d = -(m_unit - (a·m_unit)a)
dtau_axis/dF_d = a·m_unit
```

The coefficient is not an estimate of KW V5 force. It must not be multiplied by a guessed or generic value. A future affine reconstruction is allowed only after a separate reviewed source supplies a signed force for the exact same position, temperature, service/charge state, and coordinate convention.

## Atomic collection contract

The successful collection must:

- contain exactly four corners in canonical order;
- carry one configuration and one accepted static-state identity;
- retain every corner result without mirroring or substitution;
- report maximum force, perpendicular-moment, support-axis, and unit-influence verification residuals; and
- carry explicit collection-level boundaries denying complete reaction, maneuver, structural, installed/as-built, and production authority.

A failed collection must contain no publishable successful subset.

## Numerical policy

The existing `MOD-SUSP-0008` tolerances remain authoritative:

- point consistency: `1e-9 m`;
- axis consistency: `1e-10`;
- force residual: `1e-10 N`;
- perpendicular moment residual: `1e-10 N·m`;
- support-axis moment component: `1e-10 N·m`.

The implementation may not use clipping, absolute values, least squares, pseudoinverse, regularization, historical fallback, hidden balancing forces/couples, or partial publication.

## Failure behavior

The adapter must return a structured failure naming the exact corner and stage for:

- unsuccessful or incomplete `MOD-SUSP-0009` input;
- corner count/order or identity mismatch;
- stale spring or ARB state;
- frame, source, point, pivot, or axis mismatch;
- unsuccessful spring, ARB mechanism, ARB force, or included-load kernel result;
- degenerate/nonfinite damper eye geometry;
- failed unit-influence cross-check; or
- any nonfinite output.

## Fidelity boundary

The output label is `uncorrelated_design_intent_static_rocker_included_loads`.

It is complete only for the explicitly named push/pull, spring, and ARB load set under the accepted static-gravity fixture. It is not a complete physical rocker equilibrium or total pivot/bearing reaction because the KW V5 non-spring static contribution remains unavailable under `AUTH-SUSP-0015`.

No bearing split, chassis pickup load, stress, buckling, fatigue, compliance, factor of safety, FEA boundary condition, maneuver case, setup recommendation, correlation, installed/as-built claim, or production use is authorized.
