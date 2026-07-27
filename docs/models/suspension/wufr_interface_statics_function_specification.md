# WUFR Level-1 suspension interface statics function specification

## Scope

`MOD-SUSP-0007` is the first WUFR-specific suspension load-path statics layer. It consumes current reviewed suspension geometry plus one **complete prescribed external wrench** on a declared outboard-carrier boundary and solves only the first useful structural abstraction:

> net suspension interface reactions for the outboard carrier/upright, upper A-arm, and lower A-arm, while preserving arm-mounted actuation.

It is intentionally not a maneuver-load generator, upright/brake/bearing internal model, rocker/spring/ARB reaction solver, or beam/stress model.

## Source and carryover authority

`data_catalog/wufr27_level1_linkage_topology_v0.toml` is the governing source packet for this adapter. On 2026-07-27 the project reviewer explicitly confirmed that WUFR27 retains WUFR26 suspension load paths, geometry, and hardware, authorized source-backed connection inference, and selected **Level 1 interface reactions** as the first output fidelity.

The adapter must still use the existing current-state geometry providers. Carryover is topology/hardware authority, not permission to replace current kinematic state with nominal coordinates.

## Solved bodies

The first graph contains exactly three rigid bodies:

1. `outboard_carrier` — the suspension-interface carrier/upright boundary;
2. `upper_a_arm`;
3. `lower_a_arm`.

The rocker is not part of v0.1 equilibrium. Its current rod pickup is used only as the remote point defining the push/pull-rod axis.

## Joint and element idealizations

### Upper/lower arm outboard joints

Each HAB spherical-bearing center is an ideal spherical joint. A spherical joint transmits three force components and no couple.

For a joint point `r_J` and body reference `r_O`, Cartesian force basis `e_k` contributes the body wrench column

`a_Fk = [e_k ; (r_J-r_O) x e_k]`.

The carrier-side force is the reported interface force. The arm receives the exact equal-and-opposite force at the same physical joint point.

### Upper/lower arm inboard supports

The two fore/aft chassis rod-end centers of one rigid A-arm are condensed to a **net ideal revolute support** about their exact hinge line.

Let

`u_h = normalize(r_aft-r_fore)`.

Choose deterministic unit vectors `v1,v2` such that `v1 dot u_h = v2 dot u_h = 0` and `v2 = u_h x v1` up to the frozen basis convention.

The net hinge unknowns are:

- force `[Rx,Ry,Rz]` at a declared hinge reference point;
- moment `m1 v1 + m2 v2`.

There is **no reaction moment about `u_h`**.

This support reports only a net hinge wrench. It cannot determine unique forward/aft rod-end or chassis-tab loads.

### Lateral link

Front uses the **current steering-closure tie-rod axis**. Rear uses the reviewed current toe-link endpoints.

For body point `r_b`, remote point `r_r`,

`u = (r_r-r_b)/||r_r-r_b||`.

Signed axial force `N>0` means tension, and force on the body is `N u`.

### Actuation rod

The same signed two-force convention applies to the front pullrod and rear pushrod.

Application ownership is mandatory:

- front pullrod acts on the **upper A-arm** source pickup;
- rear pushrod acts on the **lower A-arm** source pickup.

The adapter must never move either pickup to the carrier/upright.

## Unknown order

The fixed scalar order is:

1. UCA hinge `Rx,Ry,Rz,m_v1,m_v2` — 5;
2. LCA hinge `Rx,Ry,Rz,m_v1,m_v2` — 5;
3. upper spherical force on carrier `Fx,Fy,Fz` — 3;
4. lower spherical force on carrier `Fx,Fy,Fz` — 3;
5. lateral-link axial force — 1;
6. actuation-rod axial force — 1.

Total: 18 unknowns.

The three rigid bodies provide 18 force/moment equilibrium equations. No stiffness force-sharing law is required at this fidelity.

## External wrench contract

The caller must provide one complete finite force/couple wrench acting on `outboard_carrier`, including:

- frame ID;
- explicit reference point;
- force `[Fx,Fy,Fz]` N;
- moment `[Mx,My,Mz]` N*m about that point;
- source ID;
- load-case/provenance ID.

A complete wrench may be translated exactly to another reference point. The model must reject an incomplete/ambiguous wrench rather than infer missing brake, drive, contact, gravity, aero, spring, ARB, or damper terms.

The carrier boundary intentionally allows wheel/hub/bearing/brake/drive internals to remain upstream for this first interface solve. That is a load-transmission abstraction, not internal upright structural fidelity.

## Equilibrium assembly

Body row order is fixed:

`[carrier force, carrier moment, UCA force, UCA moment, LCA force, LCA moment]`.

Assemble physical SI matrix `A` and right-hand side `b` so

`A x = b = -W_prescribed`.

Internal spherical columns appear with equal/opposite signs on carrier and corresponding arm. Lateral-link force acts only on the carrier. Front actuation acts only on UCA; rear actuation acts only on LCA. Hinge reactions act only on their arm body.

## Numerical scaling and solve

For body `i`, define

`L_i = max_j ||r_ij-r_Oi||`

over finite force application points on that body. Require `L_i > 1e-12 m`.

Define

`S_i = diag(1,1,1,1/L_i,1/L_i,1/L_i)`

and

`S = blockdiag(S_C,S_U,S_L)`.

Solve

`(S A)x = S b`

using deterministic pivoted direct linear algebra only.

Default numerical gates:

- exactly `18 x 18`;
- full rank;
- relative pivot threshold `1e-12`;
- `cond_inf(SA) <= 1e10`;
- no least squares, pseudoinverse, minimum norm, regularization, stiffness weighting, force clipping, or hidden geometry perturbation.

## Result reconstruction

Return named physical outputs, not only the raw 18-vector:

- signed lateral-link axial force;
- signed push/pull-rod axial force;
- upper/lower carrier-to-arm spherical force vectors;
- upper/lower net inboard hinge force vectors;
- upper/lower net inboard hinge moment vectors;
- equal/opposite body-side interface actions;
- condition/pivot/scaling diagnostics;
- source/configuration/load provenance.

Reconstruct equilibrium using the original unscaled physical geometry. For every body:

`R_F = F_prescribed + sum F_interface`

`R_M = M_prescribed + sum[(r-r_O) x F + M_interface]`.

The default physical residual tolerances are `1e-9 N` and `1e-9 N*m` infinity norm. Also require

`M_hinge dot u_h = 0`

within `1e-9 N*m`.

## WUFR current-state adapter

The source adapter must use the existing reviewed suspension/steering state rather than duplicate kinematics:

- UCA/LCA current points and hinge axes from the suspension state;
- upper/lower current upright bearing centers from the solved carrier pose;
- front current tie-rod endpoints after `MOD-STEER-0001` steering closure;
- rear current toe-link endpoints from reviewed rear closure;
- current front UCA pullrod pickup or rear LCA pushrod pickup from `MOD-SUSP-0003` ownership;
- current rocker rod pickup from `MOD-SUSP-0003`.

No scalar OptimumK steer angle, scalar motion ratio, body-roll-times-track, or load-percentage shortcut is permitted.

## Failure behavior

Structured failures include nonfinite/frame/source mismatch, missing identities, degenerate hinge/axial geometry, source-ownership mismatch, incomplete external wrench, unsupported topology, degenerate scaling length, singular/ill-conditioned solve, hinge-axis moment violation, and physical residual failure.

A failed result remains unsolved. No hidden repair is allowed.

## Explicit fidelity boundary

Authorized Level 1 outputs stop at net interface resultants. The following remain downstream:

- forward/aft chassis rod-end/tab load split;
- welded A-arm tube loads, bending, stress, weld/bearing stress, buckling, fatigue, compliance, or factor of safety;
- rocker pivot, spring, ARB, and damper structural reactions;
- internal upright/hub/bearing/brake/drive reaction decomposition;
- maneuver/tire/road load generation;
- FEA release or production authority.
