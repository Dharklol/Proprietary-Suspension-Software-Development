# No-driver/no-fuel pitch-inertia sensitivity v0.1.0

Owner continuation on 2026-11-01 authorizes the reviewed electrical-at-CG
approximation and provisional sprung/unsprung allocation study. Drive is read-only.
The source is WUFR-26 COM, native Sheet id
1gUrRtNkEQ4w44esKezqMjeMxAnAau1kG8DxIGr_S-6I, read 2026-11-01.
The compact snapshot retains sheet, assembly, original row, CAD mass, component
CG x/y/z and labelled centroidal Lyy. No production mass or erroneous origin-tensor
column is consumed. Assumption: centroidal Lyy uses the common CAD lateral axis;
the macro/coordinate rotation convention remains unverified. Snapshot shocks use
SU row 573's manual aggregate once, since it has no individual part rows. It is
not summed again with a parent assembly. Empty assemblies are not filled in.

## Reconstruction

Use exact lb-to-kg 0.45359237 and inch-to-m 0.0254. Remove DT_3 row 59 (12 lb
liquid fuel); there is no added driver. Recompute CG from retained masses.
Jy=sum(Lyy_i + m_i*((xi-xCG)^2+(zi-zCG)^2)). Independently sum moments about the
CAD origin and subtract M*(xCG^2+zCG^2); require agreement <1e-8 kg*m^2.
Include all populated parts and the one shock aggregate: wet CAD mass must
reconcile to 461.149 lb after adding 15.842 lb electrical, tolerance 1e-6 lb.
Dry mass must be 449.149 lb, tolerance 1e-6 lb. Snapshot has 2469 selected records,
including the fuel and shock records. Require finite nonnegative masses/Lyy,
finite positions; no invented origin or negative-moment repair.

Place electrical as a 15.842 lb point at the reconstructed dry whole-car CG,
with zero intrinsic inertia (explicit owner approximation). Keep that point fixed
when splitting the body; recompute each sprung CG afterward. This approximation
preserves whole-car CG, but omits real distributed electrical inertia.

## Allocation

BOM WUFR-26, id 1-Pdp7Rr7YukPKFrN0oOKeIvz9OmlzNG9R-1NlxpxsEY,
and Box drawings 2120119871272 (front corners), 2142858842201 (rear corners),
2173006792564 (front upright) and 2173032112480 (wheels/tires) support the
component boundaries. Fully outboard: WT plus BR brake discs and calipers.
Mixed moving groups: SU front/rear corners, ST tie rods, DT driveshafts.
Retain mixed-group mass and centroidal inertia fractions 0, 0.5, 1 as bookkeeping
sensitivity axes only. This is NOT an exact effective mass reduction, nor rigorous
uncertainty bounds. Inboard shocks/rockers/ARBs are retained in the body lump;
their relative motion is an additional unquantified approximation. Flexible brake
lines remain with the body; their small distributed motion is not identified.
Do not substitute this partition for the existing static provider's 5 kg corner
lumps or silently combine it with driver/no-fuel 306 kg equilibrium results.
The 477 lb scale state is not reconciled to the 449.149 lb CAD inventory.

## Half-car study

Use the verified MOD-VEH-0011 engine without changes. Fix sprung mass and CG at
the 50% bookkeeping scenario; change only Jy between the three reconstructed
values. Front/rear lever arms use CAD front x=0 and rear x=-1.5624 m, projected
onto the reference longitudinal axis (small-pitch approximation). These are an
exploratory mixed-source model, not a native solved dynamic equilibrium.
Explicit illustrative axle parameters: mu_f=mu_r=18 kg, kf=50000,kr=65000 N/m,
ktf=360000,ktr=380000 N/m, cf=cr=800 N*s/m. No KW calibration is claimed.
Separate 1 mm cosine bumps: front start .1 s, rear start .3 s, each duration .2 s.
The .2 s delay is an explicit scenario, not an inferred vehicle speed. Simulate
2 s, initial perturbations zero, dt=.0002 and .0001 s, travel bounds ±.01 m
(study guards, not installed hardware travel). No physical correlation claim.

Require all runs complete, fine energy residual <1e-6 J, matching-grid max state
difference <1e-6 corresponding SI units, and peak pitch acceleration/body
acceleration/normal load changes <0.5% (absolute floors 1e-5 SI for acceleration,
1e-4 N for loads). Compute acceleration from each accepted state's scalar force
balance. Retain coarse/fine errors and report which parameter changed.

## Stopping point

Do not promote Jy to installed authority: finish mass inventory reconciliation,
centroidal frame validation, distributed electrical inertia sensitivity, and a
kinetic-energy-based moving-link reduction first. These cases answer sensitivity
to a selected provisional Jy range, not final vehicle pitch predictions.
