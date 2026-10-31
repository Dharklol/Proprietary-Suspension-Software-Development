# Manufactured half-car verification

Reproduce with `PYTHONPATH=src python scripts/run_half_car_verification.py`.

Six tests pass, in addition to nine retained quarter-car/stiffness tests.
The symmetric heave and pitch cases use exact hand-derived cosine trajectories
for both eigenvalues 1 and 6; asymmetric tests independently form point-force
balances, pitch moments and the energy directional derivative. Independent
front/rear road bumps generate pitch and pass the predeclared refinement check.

For the manufactured asymmetric bump fixture, dt=0.002/0.001 s gives maximum
matching state-component difference 1.17e-12 in corresponding SI units; fine-run
energy residual is 2.20e-15 J. This is a two-grid agreement check, not a measured
convergence order or an estimate of vehicle accuracy. Full explicit parameters,
source hashes and metrics are in `summary.json`.

The model has four DOFs: sprung heave/pitch and front/rear unsprung vertical
motion. Eight physical states and two energy quadratures are integrated. All
masses, axle rates and pitch inertia refer to the represented system directly;
they are not automatically converted from corner or whole-vehicle values.
Sampled stage guards preserve accepted history and fail on contact loss, travel
or nonfinite evaluation. They do not locate exact continuous events.

No native WUFR prediction is included. Native pitch inertia and an equilibrium-
based local linearization remain required. The earlier independent-corner static
mass proxies do not establish coupled modal inertia.

KW curve digitization was attempted through the authenticated Box connection.
Text access works, but both advertised raw-file tools returned `Tool ... not
found` on 2026-10-31. Thus no plot samples, click-specific force law or viscous
coefficient were invented. The separately recovered one-speed standard-setting
force envelope remains evidence only. Next source step is recover a renderable
vendor PDF through an available file path, then digitize/verify the plotted
curves with explicit settings. Existing static gas/friction holds remain valid.
