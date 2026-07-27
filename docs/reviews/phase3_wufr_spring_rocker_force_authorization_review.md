# Phase 3 WUFR physical spring force at rocker authorization review

## Decision

Authorize one narrow structural/load-path bridge from the existing conservative spring provider to a physical force vector at the current rocker/chassis eyes.

The spring constitutive model is **not** changed. `MOD-SUSP-0004` still owns spring compression, force magnitude, energy, tangent stiffness, and the existing WUFR27 assumptions. This slice only gives that already-reviewed force magnitude a current three-dimensional line of action.

## Source basis

The reviewed WUFR27 spring package freezes the direct-coilover placement line, current spring setup, and nominal force values. The existing `MOD-SUSP-0003` actuation model owns the current rocker eye, chassis eye, rocker pivot, and rocker axis. The WUFR26 shock assembly drawing corroborates the KW spring/piggyback-damper hardware but does not provide an independent gas-force or friction model.

The reviewer has separately confirmed that WUFR27 retains WUFR26 suspension load paths, geometry, and hardware. No new carryover assumption is introduced here.

## Authorized mechanics

For current chassis eye `C`, rocker eye `D`, spring compression magnitude `F_s >= 0`, rocker pivot `R`, and unit rocker axis `a`:

`e = (D-C)/||D-C||`

`F_rocker = F_s e`

`F_chassis = -F_s e`

The physical spring torque about the rocker axis is

`tau_s = a · ((D-R) × F_rocker)`.

Rigid rocker kinematics also give

`dD/dtheta = a × (D-R)`

and therefore

`dL_d/dtheta = e · [a × (D-R)]`.

Thus the exact virtual-work identity is

`tau_s = F_s dL_d/dtheta`,

which is the rocker-angle form of the already-reviewed `MOD-SUSP-0004` generalized spring-force rule. This gives the implementation a strong independent geometry/sign check without relying on a historical scalar motion ratio.

## Fidelity boundary

`ASM-SUSP-0007` deliberately treats only the **spring contribution** as an ideal axial direct-coilover load. It does not make the total damper assembly a two-force member with a known total force.

The following remain outside authority: damper velocity force, gas force, seal friction/hysteresis, bump/top-out stops, side load, rocker equilibrium, rocker pivot reactions, individual bearing/tab loads, member stress, FEA release, and installed/as-built claims.

This distinction matters for the next stage. A static rocker free-body model can be assembled after the physical spring and ARB linkage forces are available, but calling its pivot reaction a complete physical hardware load requires an explicit decision on omitted non-spring damper forces—especially any static gas extension force.

## Promotion gate

Implementation must consume successful source-matched actuation and spring states, use the exact current eye line, preserve equal-and-opposite action/reaction, pass `BENCH-SUSP-0025`, and remain labeled spring-only. No guessed damper force may be inserted to close a later rocker equilibrium.
