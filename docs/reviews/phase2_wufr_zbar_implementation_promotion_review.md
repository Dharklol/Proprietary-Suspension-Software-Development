# WUFR two-arm Z-bar implementation promotion review

## Decision

PR54's numerical mechanism closure is accepted as the first implemented WUFR Z-bar deformation map **in left/right rocker-angle coordinates only**.

The implementation composes two previously reviewed authorities:

- `AUTH-SUSP-0006`: named front/rear mechanism fixture, rigid-link nominal geometry, and rocker-pickup transport;
- `AUTH-SUSP-0007`: one transverse elastic coordinate per blade arm with the same discrete SolidWorks per-arm stiffness and additive conservative energy.

`AUTH-SUSP-0008` records the implementation boundary after PR54.

## Implemented state

For prescribed rocker rotations

`q_R = [theta_RL, theta_RR]`,

the solver transports the left/right rocker ARB pickups, solves the two fixed-length end-link constraints, and treats the central blade housing angle as a free internal coordinate. Each blade tip is its rigidly rotated nominal arm plus a transverse elastic deflection `d_i`. The selected housing angle minimizes

`d_L^2 + d_R^2`,

which is proportional to the authorized equal-`k_b` two-arm elastic energy.

The returned constitutive state is

`F = [k_b d_L, k_b d_R]`,

`U = 0.5 k_b (d_L^2 + d_R^2)`.

The implementation then evaluates a branch-preserving two-step finite-difference Jacobian

`J_d = partial([d_L,d_R]) / partial([theta_RL,theta_RR])`

and returns

`Q_rocker = -J_d^T F`.

## Verification accepted

The focused PR54 test suite verifies:

1. nominal zero-deflection closure for front and rear;
2. rigid-link residuals below the configured tolerance;
3. reachability of small common/differential rocker states;
4. left/right reversal energy symmetry on the symmetric front fixture;
5. availability and agreement of two finite-difference Jacobian step sizes;
6. independent centered finite-difference energy-gradient agreement with `Q_rocker`.

These criteria are frozen as `BENCH-SUSP-0016`.

## Explicit boundary

The current generalized force is work-conjugate to **rocker angle**, not wheel-center vertical travel, body roll, contact-patch load, or axle load transfer.

The next coordinate-chain task is to obtain and verify the signed local mapping between the reviewed MOD-SUSP-0002 physical wheel coordinate and the MOD-SUSP-0003 rocker angle for both sides, then apply the chain rule to the already reviewed `J_d`. This must preserve left/right signs and branch continuity. Historical scalar motion ratios remain prohibited as a substitute.

Vehicle equilibrium, load transfer, tire force, structural loads, and installed/as-built claims remain downstream.
