# Coupled tube inertia and integration checkpoint

Reproduce: `PYTHONPATH=src python scripts/run_coupled_tube_inertia.py`.
Specification: `docs/models/suspension/coupled_tube_inertia_spec_v0.1.0.md`.

All ten checks pass. The eight front tubes now retain complete heave/pitch/left
arm/right arm coupling at finite pitch and arm motion, with analytic acceleration
bias and gyroscopic contributions. No additional native masses are included.
The earlier nominal matrix is recovered within 1e-12 in matching SI units.

Independent mass-matrix derivatives agree with generalized inertial bias to
better than 1e-9 in the declared coordinate force units at the sampled states.
Power-identity error is below 2.3e-10 W. Five-point world-pose/omega differences
check the member acceleration terms independently of mass-matrix differentiation.
See results.json for all values, fixture states and source hashes.

The short manufactured-force integration gives work-energy residuals of
2.36e-10, 1.00e-11 and 4.92e-13 J at 2,4,8 steps. Endpoint differences shrink
by about eighteenfold. The unforced run conserves energy at about 4e-15 J and
endpoint changes are already at the numerical floor; no convergence order is
claimed for that case. Omitting inertial bias violates the sampled power identity.

## Stopping point and goal alignment

This completes coupled inertia, convective power verification and a bounded
force-driven integration case for the verified tube subset. It is not a full
vehicle transient model, and its manufactured loads are not installed predictions.
Housing tensors remain excluded because source signs are ambiguous; neither the
current HalfCar nor Drive is changed.

The next useful step is connecting generalized spring/damper/road forces to a
compatible mass inventory and verifying energy/dissipation and contact/travel
boundaries. Resolve remaining ownership as needed for that inventory. This keeps
G3/G5a analytical integration ahead of UI/release work. No new owner information
is required for developing the force contracts and analytical verification cases.
