# Consistent dry no-driver CAD mass scenarios

Reproduce: `PYTHONPATH=src python scripts/run_no_driver_mass_consistency.py`.
All three cases pass mass/first-moment reconstruction, represented-model static
force/moment closure, time-step refinement and energy checks.

| Mixed retention | Body mass kg | Front axle mass kg | Rear axle mass kg | Body Jy kg*m² |
|---|---:|---:|---:|---:|
| 0 | 164.396 | 18.664 | 20.671 | 67.771 |
| 0.5 | 167.945 | 17.409 | 18.376 | 69.932 |
| 1 | 171.494 | 16.155 | 16.082 | 72.089 |

Every row sums to the same 203.730559 kg no-driver/no-fuel CAD inventory. Source
first moments reconstruct to <3e-14 kg*m before axle-station lumping. Actual axle
component CGs are reported; substituting axle reference stations produces a
longitudinal first-moment difference of -0.140 to -0.129 kg*m, which is retained
explicitly rather than claimed as exact. This is an approximate longitudinal
axle-lump model, not a kinematic effective-mass calculation.

All body/axle masses, body CG and Jy change together in these allocation cases.
In the explicit illustrative bump, peak pitch acceleration spans 0.5102–0.5243
rad/s² and peak body acceleration 0.4597–0.4873 m/s²: about 2.7% and 5.8% of
the middle-case peaks. Compare this with the earlier inertia-only study, whose
other parameters stayed fixed. These percentages describe selected scenarios,
not uncertainty bounds or measured vehicle response. Fine energy residuals are
below 9.3e-13 J. Full controls, static loads, residuals and hashes are retained.

Owner confirmed COM/software axes match on 2026-11-01. Electrical remains a point
at the reconstructed dry whole-car CG with zero intrinsic inertia. KW data is
limited to already available evidence; damping and axle/tire rates remain explicit
illustrative scenarios. Neither the 18 kg-per-axle placeholder from the earlier
inertia study nor the 306 kg driver-loaded static solution is used here.

The 449.149 lb CAD dry inventory is still 27.851 lb below the documented 477 lb
no-driver scale state. No mass is invented or scaled to close that gap. Moving
links, inboard relative motion and distributed electrical inertia remain modelling
limits. The next useful analytical improvement is a kinetic-energy-based link
mass reduction, before native vehicle prediction. Drive is unchanged.
