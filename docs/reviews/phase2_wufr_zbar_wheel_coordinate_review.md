# WUFR Z-bar physical wheel-coordinate force review

## Decision

The next composition step after AUTH-SUSP-0008 is accepted for implementation: map each reviewed physical wheel-center vertical coordinate to its corresponding rigid rocker angle, chain that local derivative into the existing two-arm Z-bar Jacobian, and expose conservative ARB generalized force in the two declared wheel-center vertical coordinates.

This is **not** a whole-vehicle equilibrium or load-transfer solver.

## Coordinate chain

MOD-SUSP-0002 defines

`z_i = delta_z_wc_body_i`

with positive wheel-center motion upward relative to the body.

MOD-SUSP-0003 supplies the signed rocker state `theta_R_i`. The local derivative is

`rho_rw_i = d(theta_R_i)/d(z_i)`.

For the existing independent-corner rigid suspension kinematics,

`J_theta_z = diag(rho_rw_L, rho_rw_R)`.

AUTH-SUSP-0008 supplies

`J_dtheta = partial([d_L,d_R]) / partial([theta_RL,theta_RR])`.

Therefore

`J_dz = J_dtheta J_theta_z`

and the work-conjugate wheel-coordinate ARB force is

`Q_z = -J_dz^T F = J_theta_z^T Q_rocker`.

The units of `Q_z` are newtons because the generalized coordinates are meters.

## Derivative policy

`rho_rw` is not taken from the historical OptimumK Motion Ratio Heave channel. It is computed directly from the reviewed physical wheel-coordinate inversion and rocker closure.

The center state is solved first. Neighbor physical wheel states use the center rocker angle as the continuation predecessor. Centered differences are used where both neighbors are reachable; a one-sided difference is permitted only at a reviewed reachable-domain boundary. Two step sizes are required and their disagreement is reported.

## Verification

The implementation is promoted only if:

1. nominal front and rear maps produce finite signed local rocker derivatives and zero ARB force because the nominal blade deflection is zero;
2. the local rocker derivative is stable at the two reviewed finite-difference steps;
3. algebraic chain-rule force equals `diag(rho_rw)^T Q_rocker`;
4. an independent nonzero rear case matches centered finite differences of total two-arm ARB energy after re-solving the complete wheel/rocker/Z-bar state;
5. the high-level provider obtains stiffness only from the frozen discrete setting table.

These checks are recorded as BENCH-SUSP-0017.

## Remaining boundary

After this slice, the ARB model can return conservative generalized force in left/right physical wheel-center vertical coordinates. That still does not determine actual wheel loads under a maneuver. A whole-vehicle equilibrium solver must separately define chassis/body generalized coordinates, mass/inertia/gravity/aero/external loads, tire/contact constraints, spring and ARB elastic forces, and the static or quasi-static residual to solve.

Historical effective axle roll stiffness remains comparison/correlation evidence only and is not used to back-fit this coordinate chain.
