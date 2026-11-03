# Front tube travel and convective inertia checkpoint

Reproduce: `PYTHONPATH=src python scripts/run_front_tube_travel.py`.
Specification: `docs/models/suspension/front_tube_travel_spec_v0.1.0.md`.

All fifteen checks pass for the fixed-chassis, four-tube-per-corner study.
The left qL metric varies from 0.01659849 to 0.01637694 kg m^2 over the five
sampled states from -0.06 to +0.06 rad. The right corner reflects this trend.
At qL=0, the metric is 0.01648092518 kg m^2, matching the earlier nominal
bilateral matrix's arm diagonal. These values are coordinate inertias, not
wheel-effective mass and not a full corner inventory.

Native compatible upper-arm motion, CG derivatives, metric derivatives and
upper-arm second derivatives pass independent centered-difference checks.
Full source tensors rotate with each arm, with a manufactured asymmetric-tensor
orientation check in addition to scalar energy/trace checks.

| Power quadrature steps | Work minus kinetic-energy change (J) |
|---:|---:|
| 200 | 6.68469e-8 |
| 400 | 1.67111e-8 |
| 800 | 4.17773e-9 |

Omitting 0.5 M' qdot^2 gives -1.61708e-6 J at 800 steps, detecting the missing
term. The prescribed motion has no road, tire, damping, gravity or external
vehicle load interpretation. A force-driven integration test remains future work.

## Housing result

The source-supported housing owners from BENCH-SUSP-0041 remain useful, but
all four full source tensors pass physicality under both candidate product-sign
interpretations. No sign choice is inferred from that. Both candidates and the
failed source-binding status are recorded in results.json. The housing snapshot
retains source values unchanged; Drive is read-only.

## Goal alignment and next boundary

This advances G3/G5a from a nominal kinetic-energy matrix to a verified
configuration-dependent inertia/convective calculation for an enumerated subset.
Next is coupling body motion to those arms and checking multi-coordinate power
balance, followed by a controlled force-driven verification case. Housing sign
resolution and remaining component ownership can proceed independently; neither
justifies stalling the verified tube kernel or starting UI/release work.
No new owner information is required for that next analytical increment.
