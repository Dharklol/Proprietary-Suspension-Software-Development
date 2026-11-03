# No-driver/no-fuel mass-budget consistency study v0.1.0

Owner direction, 2026-11-01: COM export axes are the same as the software axes;
close the PR stack and continue. Record this as owner confirmation, not an
independent macro audit. Existing KW evidence is complete for present access;
no new KW source or calibrated damping curve is assumed. Drive stays read-only.

PRs 121–127 merged in sequence with merge commits, each bound to its checked
head, all workflows successful and no outstanding review threads. The source
snapshot and verified HalfCar engine on main are reused without modification.
Affected registry references: MOD-VEH-0011, EQ-VEH-0030, EQ-VEH-0031 and
BENCH-VEH-0024; this offline scenario does not change their governing equations.

## Mass contract

Reuse the COM CAD rows, exact SI conversions, explicit fuel exclusion and owner
point-electrical assumption. For each f=0,.5,1 retain f of each mixed component
mass/centroidal Jy in the body and assign the complementary 1-f mass to an axle.
Fully outboard WT/brake-disc/caliper groups go to axles; body groups and electrical
remain in the body. Never double count a fractional component. Assign axle by
nearest reference station x=0 or -1.5624 m; retain original positions for checking
all three first moments before any axle-lump simplification. Keep front/rear
source CGs visible. This is bookkeeping, not kinematic effective-mass authority.

Require each body+front+rear mass to equal the same 203.73055939313 kg CAD dry
inventory within 1e-9 kg and all first moments to reconstruct within 1e-9 kg*m.
Whole-system CG must be invariant under f. Component mass/first moment allocation
is independent of the dynamic system's usual linear axle-lump simplification.
Report the longitudinal first-moment residual incurred when replacing the axle
CGs by contact-reference stations. Do not call it exact source reconstruction.
The old measured 5 kg corner allocation and 306 kg driver-loaded equilibrium
are not inputs. No scaling to the unreconciled 477 lb scale state.

## Dynamic cases

Three coupled parameter scenarios use their matching body mass, Jy, body CG and
front/rear axle masses; unlike the earlier inertia-only study, multiple physical
parameters change together. a=-xs, b=1.5624-a. Only x-CG enters the small-pitch
model; z-CGs remain audit data, not hidden extra geometry. Use the previous
explicit illustrative kf/kr=50000/65000 N/m, ktf/ktr=360000/380000 N/m,
cf/cr=800/800 N*s/m, 1 mm front/rear bumps starting .1/.3 s over .2 s, two-second
horizon. These stiffness/damping values remain scenarios, not WUFR calibration.
Travel ±.01 m is a study guard. Initial perturbations are zero about the model's
assumed static force balance; this is not a native nonlinear equilibrium solve.

Verify matching-state refinement <1e-6 SI component units, energy residual <1e-6 J,
peak pitch/body acceleration and normal-load changes <0.5% with absolute floors
1e-5 acceleration SI /1e-4 N at dt=.0002/.0001 s. All runs must complete with
positive sampled contact. Preserve static baseline loads computed from the exact
HalfCar scalar model. Independently verify their sum equals total weight and
front-load moment about rear axle equals weight's moment using body CG and axle
lumps. These identities verify the represented model, not measured corner scales.

## Limits and next dependency

The COM axes gap is owner-resolved. Inventory mismatch (449.149 vs 477 lb), moving
link kinetic reduction, inboard relative motion, electrical intrinsic inertia,
KW force-velocity calibration and tire operating conditions remain visible.
Mass consistency is necessary but does not convert this study into a vehicle
prediction. Analytical scenario work may proceed with explicit parameters.
